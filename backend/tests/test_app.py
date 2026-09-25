import pytest
from fastapi.testclient import TestClient

from fastapi import FastAPI

from app.main import SESSION_COOKIE, FrontendFiles, app, sessions


@pytest.fixture
def client(tmp_path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("PM_DATABASE_PATH", str(tmp_path / "project.sqlite3"))
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
    response = client.get("/api/board")

    assert response.status_code == 401


def test_protected_api_accepts_authenticated_request(client: TestClient) -> None:
    login(client)

    response = client.get("/api/board")

    assert response.status_code == 200
    assert response.json()["name"] == "My Project"


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


def test_unknown_api_route_returns_json_404_not_the_spa_shell(client: TestClient) -> None:
    response = client.get("/api/does-not-exist")

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/json")


def test_unknown_api_route_ignores_an_exported_404_page(tmp_path) -> None:
    """The real Next.js export ships a 404.html, which StaticFiles would happily
    return for an API path. The placeholder static directory has no such file, so
    this mounts a production-shaped one to keep that case covered."""
    (tmp_path / "index.html").write_text("<html>app shell</html>", encoding="utf-8")
    (tmp_path / "404.html").write_text("<html>exported not found</html>", encoding="utf-8")
    probe = FastAPI()
    probe.mount("/", FrontendFiles(directory=tmp_path, html=True), name="frontend")

    with TestClient(probe) as probe_client:
        api = probe_client.get("/api/does-not-exist")
        spa = probe_client.get("/board")

    assert api.status_code == 404
    assert api.headers["content-type"].startswith("application/json")
    assert "exported not found" not in api.text
    assert spa.status_code == 200
    assert "app shell" in spa.text
