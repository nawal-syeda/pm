import pytest
from fastapi.testclient import TestClient

from app.database import connection, utc_now
from app.main import app, sessions


@pytest.fixture
def client(tmp_path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("PM_DATABASE_PATH", str(tmp_path / "project.sqlite3"))
    sessions.clear()
    with TestClient(app) as test_client:
        login = test_client.post(
            "/api/auth/login",
            json={"username": "user", "password": "password"},
        )
        assert login.status_code == 200
        yield test_client
    sessions.clear()


def test_board_requires_authentication(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PM_DATABASE_PATH", str(tmp_path / "project.sqlite3"))
    with TestClient(app) as test_client:
        response = test_client.get("/api/board")

    assert response.status_code == 401


def test_seeded_board_has_five_columns_and_eight_cards(client: TestClient) -> None:
    response = client.get("/api/board")
    board = response.json()

    assert response.status_code == 200
    assert board["name"] == "My Project"
    assert [column["title"] for column in board["columns"]] == [
        "Backlog",
        "Discovery",
        "In Progress",
        "Review",
        "Done",
    ]
    assert sum(len(column["cards"]) for column in board["columns"]) == 8


def test_seed_is_idempotent(client: TestClient) -> None:
    first = client.get("/api/board").json()
    second = client.get("/api/board").json()

    assert first == second
    with connection() as db:
        assert db.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 1
        assert db.execute("SELECT COUNT(*) FROM boards").fetchone()[0] == 1
        assert db.execute('SELECT COUNT(*) FROM "columns"').fetchone()[0] == 5
        assert db.execute("SELECT COUNT(*) FROM cards").fetchone()[0] == 8


def test_rename_create_edit_move_and_delete_card(client: TestClient) -> None:
    board = client.get("/api/board").json()
    backlog = board["columns"][0]
    review = board["columns"][3]
    first_card = backlog["cards"][0]["id"]

    assert client.patch(
        f"/api/board/columns/{backlog['id']}", json={"title": "Ideas"}
    ).status_code == 200
    created = client.post(
        f"/api/board/columns/{backlog['id']}/cards",
        json={"title": "New card", "details": "New details"},
    )
    assert created.status_code == 200
    created_card = created.json()["columns"][0]["cards"][-1]["id"]

    updated = client.patch(
        f"/api/board/cards/{created_card}",
        json={"title": "Edited card", "details": "Edited details"},
    )
    assert updated.status_code == 200
    moved = client.post(
        f"/api/board/cards/{created_card}/move",
        json={"column_id": review["id"], "position": 0},
    )
    assert moved.status_code == 200
    assert moved.json()["columns"][3]["cards"][0]["id"] == created_card

    deleted = client.delete(f"/api/board/cards/{first_card}")
    assert deleted.status_code == 200
    all_ids = [card["id"] for column in deleted.json()["columns"] for card in column["cards"]]
    assert first_card not in all_ids


def test_invalid_resources_and_payloads_are_rejected(client: TestClient) -> None:
    assert client.patch("/api/board/columns/missing", json={"title": "X"}).status_code == 404
    assert client.patch("/api/board/cards/missing", json={"title": "X"}).status_code == 404
    assert client.delete("/api/board/cards/missing").status_code == 404
    assert client.post(
        "/api/board/columns/col-1/cards", json={"title": ""}
    ).status_code == 422


def test_reorders_cards_within_a_column(client: TestClient) -> None:
    before = client.get("/api/board").json()
    backlog = before["columns"][0]
    moved_card = backlog["cards"][1]["id"]

    response = client.post(
        f"/api/board/cards/{moved_card}/move",
        json={"column_id": backlog["id"], "position": 0},
    )

    assert response.status_code == 200
    assert [card["id"] for card in response.json()["columns"][0]["cards"]][:2] == [
        moved_card,
        backlog["cards"][0]["id"],
    ]


def test_user_cannot_access_another_users_board_resources(client: TestClient) -> None:
    now = utc_now()
    with connection() as db:
        db.execute(
            "INSERT INTO users (id, username, created_at, updated_at) VALUES (?, ?, ?, ?)",
            ("user-2", "other-user", now, now),
        )
        db.execute(
            "INSERT INTO boards (id, user_id, name, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            ("board-2", "user-2", "Other Board", now, now),
        )
        db.execute(
            'INSERT INTO "columns" (id, board_id, title, position, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)',
            ("other-column", "board-2", "Private", 0, now, now),
        )
        db.execute(
            "INSERT INTO cards (id, column_id, title, details, position, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("other-card", "other-column", "Private card", "Hidden", 0, now, now),
        )

    assert client.get("/api/board").json()["id"] == "board-1"
    assert client.patch(
        "/api/board/columns/other-column", json={"title": "Exposed"}
    ).status_code == 404
    assert client.patch(
        "/api/board/cards/other-card", json={"title": "Exposed"}
    ).status_code == 404
    assert client.post(
        "/api/board/cards/other-card/move",
        json={"column_id": "col-1", "position": 0},
    ).status_code == 404
    assert client.delete("/api/board/cards/other-card").status_code == 404
