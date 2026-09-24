import json
from pathlib import Path


SCHEMA_PATH = Path(__file__).parents[2] / "docs" / "database-schema.json"


def test_database_schema_document_is_valid_and_complete() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    tables = schema["database"]["tables"]

    assert set(tables) == {"users", "boards", "columns", "cards"}
    assert tables["users"]["unique"] == [["username"]]
    assert tables["boards"]["unique"] == [["user_id"]]
    assert tables["columns"]["unique"] == [["board_id", "position"]]
    assert tables["cards"]["unique"] == [["column_id", "position"]]


def test_database_schema_has_cascading_parent_relationships() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    foreign_keys = {
        table: definition["foreign_keys"][0]
        for table, definition in schema["database"]["tables"].items()
        if "foreign_keys" in definition
    }

    assert foreign_keys["boards"]["references"] == "users(id)"
    assert foreign_keys["columns"]["references"] == "boards(id)"
    assert foreign_keys["cards"]["references"] == "columns(id)"
    assert all(key["on_delete"] == "CASCADE" for key in foreign_keys.values())


def test_database_schema_documents_seed_and_public_shape() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    assert schema["seed"]["idempotent"] is True
    assert schema["seed"]["user"]["username"] == "user"
    assert schema["seed"]["columns"] == [
        "Backlog",
        "Discovery",
        "In Progress",
        "Review",
        "Done",
    ]
    assert set(schema["public_board_shape"]) == {"id", "name", "columns", "updated_at"}
