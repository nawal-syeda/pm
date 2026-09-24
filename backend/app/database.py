import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator
from uuid import uuid4

DEFAULT_DATABASE_PATH = Path("data/project_management.sqlite3")
COLUMNS = ["Backlog", "Discovery", "In Progress", "Review", "Done"]
SEED_CARDS = [
    ("Align roadmap themes", "Draft quarterly themes with impact statements and metrics.", 0, 0),
    ("Gather customer signals", "Review support tags, sales notes, and churn feedback.", 0, 1),
    ("Prototype analytics view", "Sketch initial dashboard layout and key drill-downs.", 1, 0),
    ("Refine status language", "Standardize column labels and tone across the board.", 2, 0),
    ("Design card layout", "Add hierarchy and spacing for scanning dense lists.", 2, 1),
    ("QA micro-interactions", "Verify hover, focus, and loading states.", 3, 0),
    ("Ship marketing page", "Final copy approved and asset pack delivered.", 4, 0),
    ("Close onboarding sprint", "Document release notes and share internally.", 4, 1),
]

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    username TEXT NOT NULL UNIQUE CHECK (length(trim(username)) > 0),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS boards (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL CHECK (length(trim(name)) > 0),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS "columns" (
    id TEXT PRIMARY KEY,
    board_id TEXT NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
    title TEXT NOT NULL CHECK (length(trim(title)) > 0),
    position INTEGER NOT NULL CHECK (position >= 0),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE (board_id, position)
);
CREATE TABLE IF NOT EXISTS cards (
    id TEXT PRIMARY KEY,
    column_id TEXT NOT NULL REFERENCES "columns"(id) ON DELETE CASCADE,
    title TEXT NOT NULL CHECK (length(trim(title)) > 0),
    details TEXT NOT NULL,
    position INTEGER NOT NULL CHECK (position >= 0),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE (column_id, position)
);
CREATE INDEX IF NOT EXISTS idx_columns_board_position ON "columns" (board_id, position);
CREATE INDEX IF NOT EXISTS idx_cards_column_position ON cards (column_id, position);
"""


def database_path() -> Path:
    return Path(os.environ.get("PM_DATABASE_PATH", DEFAULT_DATABASE_PATH)).resolve()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def connect() -> sqlite3.Connection:
    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(SCHEMA)
    seed(connection)
    connection.commit()
    return connection


@contextmanager
def connection() -> Iterator[sqlite3.Connection]:
    db = connect()
    try:
        yield db
        db.commit()
    finally:
        db.close()


def seed(db: sqlite3.Connection) -> None:
    now = utc_now()
    user = db.execute("SELECT id FROM users WHERE username = ?", ("user",)).fetchone()
    if user is None:
        user_id = "user-1"
        db.execute(
            "INSERT INTO users (id, username, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (user_id, "user", now, now),
        )
    else:
        user_id = user["id"]

    board = db.execute("SELECT id FROM boards WHERE user_id = ?", (user_id,)).fetchone()
    if board is not None:
        return

    board_id = "board-1"
    db.execute(
        "INSERT INTO boards (id, user_id, name, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
        (board_id, user_id, "My Project", now, now),
    )
    column_ids: list[str] = []
    for position, title in enumerate(COLUMNS):
        column_id = f"col-{position + 1}"
        column_ids.append(column_id)
        db.execute(
            'INSERT INTO "columns" (id, board_id, title, position, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)',
            (column_id, board_id, title, position, now, now),
        )
    for title, details, column_position, position in SEED_CARDS:
        db.execute(
            "INSERT INTO cards (id, column_id, title, details, position, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (f"card-{len(db.execute('SELECT id FROM cards').fetchall()) + 1}", column_ids[column_position], title, details, position, now, now),
        )


def board_for_user(db: sqlite3.Connection, username: str) -> sqlite3.Row | None:
    return db.execute(
        "SELECT boards.* FROM boards JOIN users ON users.id = boards.user_id WHERE users.username = ?",
        (username,),
    ).fetchone()


def public_board(db: sqlite3.Connection, username: str) -> dict:
    board = board_for_user(db, username)
    if board is None:
        raise LookupError("Board not found")
    columns = db.execute(
        'SELECT * FROM "columns" WHERE board_id = ? ORDER BY position', (board["id"],)
    ).fetchall()
    result_columns = []
    for column in columns:
        cards = db.execute(
            "SELECT id, title, details, position FROM cards WHERE column_id = ? ORDER BY position",
            (column["id"],),
        ).fetchall()
        result_columns.append(
            {
                "id": column["id"],
                "title": column["title"],
                "position": column["position"],
                "cards": [dict(card) for card in cards],
            }
        )
    return {"id": board["id"], "name": board["name"], "columns": result_columns, "updated_at": board["updated_at"]}


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:12]}"
