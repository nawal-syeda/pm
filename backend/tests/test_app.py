import pytest
from fastapi.testclient import TestClient

from app.main import SESSION_COOKIE, app, sessions


@pytest.fixture
def client() -> TestClient:
    sessions.clear()
    with TestClient(app) as test_client:
        yield test_client
    sessions.clear()


def login(client: TestClient) -> None:
    response = client.post(
        "/api/auth/login",
        json={"username": "user", "password": "password"},
    )
    assert response.status_code == 200


def test_health_is_public(client: TestClient) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_valid_login_sets_secure_session_cookie(client: TestClient) -> None:
    response = client.post(
        "/api/auth/login",
        json={"username": "user", "password": "password"},
    )

    assert response.status_code == 200
    assert response.json() == {"username": "user"}
    assert client.cookies.get(SESSION_COOKIE)
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie
    assert "samesite=lax" in cookie


@pytest.mark.parametrize(
    ("username", "password"),
    [("wrong", "password"), ("user", "wrong"), ("", "")],
)
def test_invalid_login_is_rejected(
    client: TestClient, username: str, password: str
) -> None:
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid username or password"}
    assert client.cookies.get(SESSION_COOKIE) is None


def test_current_session_requires_login(client: TestClient) -> None:
    response = client.get("/api/auth/session")

    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}


def test_current_session_returns_user_after_login(client: TestClient) -> None:
    login(client)

    response = client.get("/api/auth/session")

    assert response.status_code == 200
    assert response.json() == {"username": "user"}


def test_logout_invalidates_session(client: TestClient) -> None:
    login(client)

    logout_response = client.post("/api/auth/logout")
    session_response = client.get("/api/auth/session")

    assert logout_response.status_code == 200
    assert logout_response.json() == {"message": "Logged out"}
    assert session_response.status_code == 401
    assert client.cookies.get(SESSION_COOKIE) is None


def test_protected_api_rejects_anonymous_request(client: TestClient) -> None:
    response = client.get("/api/example")

    assert response.status_code == 401


def test_protected_api_accepts_authenticated_request(client: TestClient) -> None:
    login(client)

    response = client.get("/api/example")

    assert response.status_code == 200
    assert response.json() == {"message": "Hello from FastAPI"}


def test_index_serves_static_html(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "Hello world" in response.text


def test_frontend_route_falls_back_to_index(client: TestClient) -> None:
    response = client.get("/board")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "Hello world" in response.text


def test_missing_static_asset_does_not_fall_back_to_html(client: TestClient) -> None:
    response = client.get("/missing.js")

    assert response.status_code == 404


def test_api_routes_are_not_shadowed_by_frontend(client: TestClient) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
