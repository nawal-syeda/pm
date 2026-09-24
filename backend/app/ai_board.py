"""Validated, atomic AI operations for the current user's board."""

import json
import re
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

from app.database import connection, new_id, public_board, utc_now
from app.openrouter import OpenRouterError, ask_structured, stream_structured


class ChatMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class RenameColumnOperation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["rename_column"]
    column_id: str = Field(min_length=1)
    title: str = Field(min_length=1, max_length=200)


class CreateCardOperation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["create_card"]
    column_id: str = Field(min_length=1)
    title: str = Field(min_length=1, max_length=300)
    details: str = Field(default="", max_length=4000)


class EditCardOperation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["edit_card"]
    card_id: str = Field(min_length=1)
    title: str | None = Field(default=None, min_length=1, max_length=300)
    details: str | None = Field(default=None, max_length=4000)


class MoveCardOperation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["move_card"]
    card_id: str = Field(min_length=1)
    column_id: str = Field(min_length=1)
    position: int = Field(default=0, ge=0)


class DeleteCardOperation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["delete_card"]
    card_id: str = Field(min_length=1)


AIOperation = Annotated[
    Union[
        RenameColumnOperation,
        CreateCardOperation,
        EditCardOperation,
        MoveCardOperation,
        DeleteCardOperation,
    ],
    Field(discriminator="type"),
]


class AIResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assistant_message: str = Field(min_length=1, max_length=4000)
    operations: list[AIOperation] = Field(default_factory=list, max_length=20)


class AIChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1, max_length=4000)
    history: list[ChatMessage] = Field(default_factory=list, max_length=20)


class AIOperationError(ValueError):
    """An invalid or unauthorized board operation."""


AI_RESPONSE_SCHEMA = TypeAdapter(AIResponse).json_schema()


def _owned_column(db, username: str, column_id: str):
    return db.execute(
        'SELECT "columns".* FROM "columns" JOIN boards ON boards.id = "columns".board_id JOIN users ON users.id = boards.user_id WHERE "columns".id = ? AND users.username = ?',
        (column_id, username),
    ).fetchone()


def _owned_card(db, username: str, card_id: str):
    return db.execute(
        'SELECT cards.* FROM cards JOIN "columns" ON "columns".id = cards.column_id JOIN boards ON boards.id = "columns".board_id JOIN users ON users.id = boards.user_id WHERE cards.id = ? AND users.username = ?',
        (card_id, username),
    ).fetchone()


def _validate_operations(db, username: str, operations: list[AIOperation]) -> None:
    for operation in operations:
        if isinstance(operation, RenameColumnOperation):
            if _owned_column(db, username, operation.column_id) is None:
                raise AIOperationError("A column in the request was not found.")
            if not operation.title.strip():
                raise AIOperationError("Column titles cannot be empty.")
        elif isinstance(operation, CreateCardOperation):
            if _owned_column(db, username, operation.column_id) is None:
                raise AIOperationError("A target column in the request was not found.")
            if not operation.title.strip():
                raise AIOperationError("Card titles cannot be empty.")
        elif isinstance(operation, EditCardOperation):
            if _owned_card(db, username, operation.card_id) is None:
                raise AIOperationError("A card in the request was not found.")
            if operation.title is None and operation.details is None:
                raise AIOperationError("Card edits must include a title or details.")
            if operation.title is not None and not operation.title.strip():
                raise AIOperationError("Card titles cannot be empty.")
        elif isinstance(operation, MoveCardOperation):
            if _owned_card(db, username, operation.card_id) is None or _owned_column(db, username, operation.column_id) is None:
                raise AIOperationError("A card or target column in the request was not found.")
        elif isinstance(operation, DeleteCardOperation):
            if _owned_card(db, username, operation.card_id) is None:
                raise AIOperationError("A card in the request was not found.")


def _move_card(db, card_id: str, target_column_id: str, position: int) -> None:
    card = db.execute("SELECT column_id FROM cards WHERE id = ?", (card_id,)).fetchone()
    if card is None:
        raise AIOperationError("A card in the request was not found.")
    source_column_id = card["column_id"]
    target_ids = [
        row["id"]
        for row in db.execute(
            "SELECT id FROM cards WHERE column_id = ? ORDER BY position", (target_column_id,)
        ).fetchall()
        if row["id"] != card_id
    ]
    target_ids.insert(min(position, len(target_ids)), card_id)
    db.execute(
        "UPDATE cards SET position = position + 1000000 WHERE column_id IN (?, ?)",
        (source_column_id, target_column_id),
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
        source_ids = db.execute(
            "SELECT id FROM cards WHERE column_id = ? ORDER BY position", (source_column_id,)
        ).fetchall()
        for index, row in enumerate(source_ids):
            db.execute("UPDATE cards SET position = ? WHERE id = ?", (index, row["id"]))


def _apply_operations(db, username: str, operations: list[AIOperation]) -> None:
    for operation in operations:
        now = utc_now()
        if isinstance(operation, RenameColumnOperation):
            db.execute(
                'UPDATE "columns" SET title = ?, updated_at = ? WHERE id = ?',
                (operation.title.strip(), now, operation.column_id),
            )
        elif isinstance(operation, CreateCardOperation):
            position = db.execute(
                "SELECT COUNT(*) AS count FROM cards WHERE column_id = ?",
                (operation.column_id,),
            ).fetchone()["count"]
            db.execute(
                "INSERT INTO cards (id, column_id, title, details, position, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (new_id("card"), operation.column_id, operation.title.strip(), operation.details.strip(), position, now, now),
            )
        elif isinstance(operation, EditCardOperation):
            card = db.execute("SELECT title, details FROM cards WHERE id = ?", (operation.card_id,)).fetchone()
            if card is None:
                raise AIOperationError("A card in the request was not found.")
            title = operation.title.strip() if operation.title is not None else card["title"]
            details = operation.details.strip() if operation.details is not None else card["details"]
            db.execute(
                "UPDATE cards SET title = ?, details = ?, updated_at = ? WHERE id = ?",
                (title, details, now, operation.card_id),
            )
        elif isinstance(operation, MoveCardOperation):
            _move_card(db, operation.card_id, operation.column_id, operation.position)
        elif isinstance(operation, DeleteCardOperation):
            card = db.execute("SELECT column_id FROM cards WHERE id = ?", (operation.card_id,)).fetchone()
            if card is None:
                raise AIOperationError("A card in the request was not found.")
            column_id = card["column_id"]
            db.execute("DELETE FROM cards WHERE id = ?", (operation.card_id,))
            for index, row in enumerate(db.execute("SELECT id FROM cards WHERE column_id = ? ORDER BY position", (column_id,)).fetchall()):
                db.execute("UPDATE cards SET position = ? WHERE id = ?", (index, row["id"]))


def _messages(username: str, board: dict, request: AIChatRequest) -> list[dict[str, str]]:
    system = (
        "You are a project management assistant. Return only the requested JSON schema. "
        "Write a complete assistant_message in 1-3 concise sentences. End it with a period; "
        "never end with a colon, comma, or unfinished phrase. "
        "You may use only the supported board operations: rename_column, create_card, "
        "edit_card, move_card, and delete_card. Never invent IDs; use IDs from the board. "
        "Do not claim an operation succeeded unless you include it in operations. "
        f"The current user is {username}. Current canonical board JSON: {json.dumps(board, separators=(',', ':'))}"
    )
    messages = [{"role": "system", "content": system}]
    messages.extend(message.model_dump() for message in request.history)
    messages.append({"role": "user", "content": request.message})
    return messages


def answer_board_request(db, username: str, request: AIChatRequest) -> AIResponse:
    board = public_board(db, username)
    raw = ask_structured(_messages(username, board, request), AI_RESPONSE_SCHEMA)
    try:
        return TypeAdapter(AIResponse).validate_json(raw)
    except (ValidationError, ValueError):
        raise OpenRouterError("OpenRouter returned an invalid board response.") from None


def apply_ai_response(db, username: str, response: AIResponse) -> dict | None:
    if not response.operations:
        return None
    _validate_operations(db, username, response.operations)
    _apply_operations(db, username, response.operations)
    return public_board(db, username)


def _partial_assistant_message(raw: str) -> str:
    match = re.search(r'"assistant_message"\s*:\s*"', raw)
    if match is None:
        return ""
    start = match.end()
    escaped = False
    end = len(raw)
    for index in range(start, len(raw)):
        character = raw[index]
        if escaped:
            escaped = False
        elif character == "\\":
            escaped = True
        elif character == '"':
            end = index
            break
    content = raw[start:end]
    try:
        return json.loads(f'"{content}"')
    except json.JSONDecodeError:
        if content.endswith("\\"):
            content = content[:-1]
        try:
            return json.loads(f'"{content}"')
        except json.JSONDecodeError:
            return ""


def stream_board_request(username: str, request: AIChatRequest):
    with connection() as db:
        board = public_board(db, username)
    raw = ""
    visible = ""
    for fragment in stream_structured(_messages(username, board, request), AI_RESPONSE_SCHEMA):
        raw += fragment
        partial = _partial_assistant_message(raw)
        if partial.startswith(visible) and len(partial) > len(visible):
            delta = partial[len(visible):]
            visible = partial
            yield ("delta", delta)
    try:
        response = TypeAdapter(AIResponse).validate_json(raw)
    except (ValidationError, ValueError):
        raise OpenRouterError("OpenRouter returned an invalid board response.") from None
    with connection() as db:
        board_changed = apply_ai_response(db, username, response)
    yield ("done", response, board_changed)
