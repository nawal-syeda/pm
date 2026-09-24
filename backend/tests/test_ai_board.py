import json

import pytest
from fastapi.testclient import TestClient

from app.main import app, sessions


@pytest.fixture
def client(tmp_path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("PM_DATABASE_PATH", str(tmp_path / "project.sqlite3"))
    sessions.clear()
    with TestClient(app) as test_client:
        assert test_client.post(
            "/api/auth/login", json={"username": "user", "password": "password"}
        ).status_code == 200
        yield test_client
    sessions.clear()


def test_ai_chat_applies_multiple_operations_atomically(client, monkeypatch):
    response = {
        "assistant_message": "I updated the board.",
        "operations": [
            {"type": "rename_column", "column_id": "col-1", "title": "Ideas"},
            {"type": "edit_card", "card_id": "card-1", "title": "Updated roadmap"},
            {"type": "move_card", "card_id": "card-1", "column_id": "col-4", "position": 0},
            {"type": "delete_card", "card_id": "card-2"},
            {"type": "create_card", "column_id": "col-1", "title": "New AI card", "details": "Created by AI."},
        ],
    }
    monkeypatch.setattr("app.ai_board.ask_structured", lambda *_args, **_kwargs: json.dumps(response))

    result = client.post(
        "/api/ai/chat",
        json={"message": "Update the board", "history": [{"role": "user", "content": "Hello"}]},
    )

    assert result.status_code == 200
    body = result.json()
    assert body["assistant_message"] == "I updated the board."
    assert body["board_changed"] is True
    assert body["board"]["columns"][0]["title"] == "Ideas"
    assert body["board"]["columns"][3]["cards"][0]["id"] == "card-1"
    assert any(card["title"] == "New AI card" for card in body["board"]["columns"][0]["cards"])
    assert all(card["id"] != "card-2" for column in body["board"]["columns"] for card in column["cards"])


def test_ai_chat_text_only_does_not_change_board(client, monkeypatch):
    monkeypatch.setattr(
        "app.ai_board.ask_structured",
        lambda *_args, **_kwargs: json.dumps({"assistant_message": "No changes needed.", "operations": []}),
    )
    before = client.get("/api/board").json()
    result = client.post("/api/ai/chat", json={"message": "What is on my board?"})

    assert result.status_code == 200
    assert result.json() == {
        "assistant_message": "No changes needed.",
        "board_changed": False,
        "board": None,
    }
    assert client.get("/api/board").json() == before


def test_invalid_operation_rolls_back_all_changes(client, monkeypatch):
    monkeypatch.setattr(
        "app.ai_board.ask_structured",
        lambda *_args, **_kwargs: json.dumps(
            {
                "assistant_message": "Attempted update.",
                "operations": [
                    {"type": "rename_column", "column_id": "col-1", "title": "Should roll back"},
                    {"type": "delete_card", "card_id": "missing-card"},
                ],
            }
        ),
    )

    result = client.post("/api/ai/chat", json={"message": "Make an invalid update"})

    assert result.status_code == 422
    assert client.get("/api/board").json()["columns"][0]["title"] == "Backlog"


def test_ai_chat_rejects_malformed_model_response(client, monkeypatch):
    monkeypatch.setattr("app.ai_board.ask_structured", lambda *_args, **_kwargs: "not json")
    result = client.post("/api/ai/chat", json={"message": "Hello"})
    assert result.status_code == 503
    assert "invalid board response" in result.json()["detail"]


def test_ai_chat_prompt_contains_board_and_history(client, monkeypatch):
    captured = {}

    def fake_model(messages, schema):
        captured["messages"] = messages
        captured["schema"] = schema
        return json.dumps({"assistant_message": "Okay.", "operations": []})

    monkeypatch.setattr("app.ai_board.ask_structured", fake_model)
    result = client.post(
        "/api/ai/chat",
        json={"message": "Summarize", "history": [{"role": "assistant", "content": "Previous answer"}]},
    )

    assert result.status_code == 200
    prompt = captured["messages"]
    assert "card-1" in prompt[0]["content"]
    assert prompt[-2:] == [
        {"role": "assistant", "content": "Previous answer"},
        {"role": "user", "content": "Summarize"},
    ]
    assert "properties" in captured["schema"]
    assert "OPENROUTER_API_KEY" not in json.dumps(prompt)


def test_ai_chat_requires_authentication(tmp_path, monkeypatch):
    monkeypatch.setenv("PM_DATABASE_PATH", str(tmp_path / "project.sqlite3"))
    sessions.clear()
    with TestClient(app) as test_client:
        result = test_client.post("/api/ai/chat", json={"message": "Hello"})
    assert result.status_code == 401


def test_ai_chat_stream_sends_deltas_and_final_response(client, monkeypatch):
    raw = json.dumps({"assistant_message": "A complete reply.", "operations": []})
    monkeypatch.setattr("app.ai_board.stream_structured", lambda *_args, **_kwargs: (part for part in [raw[:18], raw[18:]]))

    result = client.post("/api/ai/chat/stream", json={"message": "Hello"})

    assert result.status_code == 200
    assert '"type": "delta"' in result.text
    assert '"type": "done"' in result.text
    assert "A complete reply." in result.text


def test_ai_can_reorder_cards_within_a_column(client, monkeypatch):
    monkeypatch.setattr(
        "app.ai_board.ask_structured",
        lambda *_args, **_kwargs: json.dumps(
            {
                "assistant_message": "I reordered the backlog.",
                "operations": [
                    {
                        "type": "move_card",
                        "card_id": "card-2",
                        "column_id": "col-1",
                        "position": 0,
                    }
                ],
            }
        ),
    )

    result = client.post("/api/ai/chat", json={"message": "Reorder the backlog"})

    assert result.status_code == 200
    assert [
        card["id"] for card in result.json()["board"]["columns"][0]["cards"]
    ][:2] == ["card-2", "card-1"]
