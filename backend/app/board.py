"""Board mutations shared by the HTTP API and the AI operations.

Callers are responsible for checking that the user owns the column or card
before calling these. Titles and details are expected to be already validated
and stripped by the request models.
"""

import sqlite3
from typing import Annotated

from pydantic import StringConstraints

from app.database import new_id, utc_now

Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Details = Annotated[str, StringConstraints(strip_whitespace=True)]

STAGING_OFFSET = 1000000


def owned_column(db: sqlite3.Connection, username: str, column_id: str) -> sqlite3.Row | None:
    return db.execute(
        'SELECT "columns".* FROM "columns"'
        ' JOIN boards ON boards.id = "columns".board_id'
        " JOIN users ON users.id = boards.user_id"
        ' WHERE "columns".id = ? AND users.username = ?',
        (column_id, username),
    ).fetchone()


def owned_card(db: sqlite3.Connection, username: str, card_id: str) -> sqlite3.Row | None:
    return db.execute(
        "SELECT cards.* FROM cards"
        ' JOIN "columns" ON "columns".id = cards.column_id'
        ' JOIN boards ON boards.id = "columns".board_id'
        " JOIN users ON users.id = boards.user_id"
        " WHERE cards.id = ? AND users.username = ?",
        (card_id, username),
    ).fetchone()


def _require_card(db: sqlite3.Connection, card_id: str) -> sqlite3.Row:
    card = db.execute("SELECT * FROM cards WHERE id = ?", (card_id,)).fetchone()
    if card is None:
        raise LookupError("Card not found")
    return card


def _compact_positions(db: sqlite3.Connection, column_id: str) -> None:
    rows = db.execute(
        "SELECT id FROM cards WHERE column_id = ? ORDER BY position", (column_id,)
    ).fetchall()
    for position, row in enumerate(rows):
        db.execute("UPDATE cards SET position = ? WHERE id = ?", (position, row["id"]))


def rename_column(db: sqlite3.Connection, column_id: str, title: str) -> None:
    db.execute(
        'UPDATE "columns" SET title = ?, updated_at = ? WHERE id = ?',
        (title, utc_now(), column_id),
    )


def create_card(db: sqlite3.Connection, column_id: str, title: str, details: str) -> None:
    position = db.execute(
        "SELECT COUNT(*) AS count FROM cards WHERE column_id = ?", (column_id,)
    ).fetchone()["count"]
    now = utc_now()
    db.execute(
        "INSERT INTO cards (id, column_id, title, details, position, created_at, updated_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (new_id("card"), column_id, title, details, position, now, now),
    )


def update_card(
    db: sqlite3.Connection, card_id: str, title: str | None, details: str | None
) -> None:
    card = _require_card(db, card_id)
    db.execute(
        "UPDATE cards SET title = ?, details = ?, updated_at = ? WHERE id = ?",
        (
            card["title"] if title is None else title,
            card["details"] if details is None else details,
            utc_now(),
            card_id,
        ),
    )


def move_card(
    db: sqlite3.Connection, card_id: str, target_column_id: str, position: int
) -> None:
    source_column_id = _require_card(db, card_id)["column_id"]
    target_ids = [
        row["id"]
        for row in db.execute(
            "SELECT id FROM cards WHERE column_id = ? ORDER BY position", (target_column_id,)
        ).fetchall()
        if row["id"] != card_id
    ]
    target_ids.insert(min(position, len(target_ids)), card_id)

    # Park both columns above the live range so the UNIQUE (column_id, position)
    # constraint cannot trip while positions are rewritten.
    db.execute(
        "UPDATE cards SET position = position + ? WHERE column_id IN (?, ?)",
        (STAGING_OFFSET, source_column_id, target_column_id),
    )
    staging_position = db.execute(
        "SELECT COALESCE(MAX(position), 0) + 1 FROM cards WHERE column_id = ?",
        (target_column_id,),
    ).fetchone()[0]
    db.execute(
        "UPDATE cards SET column_id = ?, position = ?, updated_at = ? WHERE id = ?",
        (target_column_id, staging_position, utc_now(), card_id),
    )
    for index, moved_id in enumerate(target_ids):
        db.execute("UPDATE cards SET position = ? WHERE id = ?", (index, moved_id))
    if source_column_id != target_column_id:
        _compact_positions(db, source_column_id)


def delete_card(db: sqlite3.Connection, card_id: str) -> None:
    column_id = _require_card(db, card_id)["column_id"]
    db.execute("DELETE FROM cards WHERE id = ?", (card_id,))
    _compact_positions(db, column_id)
