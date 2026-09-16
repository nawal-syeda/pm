from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_example_api() -> None:
    response = client.get("/api/example")

    assert response.status_code == 200
    assert response.json() == {"message": "Hello from FastAPI"}


def test_index_serves_static_html_that_calls_api() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "Hello world" in response.text
    assert 'fetch("/api/example")' in response.text

