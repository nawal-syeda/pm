"""Validated, atomic AI operations for the current user's board."""

import json
import re
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

from app import board as board_ops
from app.board import Details, Title, owned_card, owned_column
from app.database import connection, public_board
from app.openrouter import OpenRouterError, ask_structured, stream_structured


class ChatMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class RenameColumnOperation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["rename_column"]
    column_id: str = Field(min_length=1)
    title: Title = Field(max_length=200)


class CreateCardOperation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["create_card"]
    column_id: str = Field(min_length=1)
    title: Title = Field(max_length=300)
    details: Details = Field(default="", max_length=4000)


class EditCardOperation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["edit_card"]
    card_id: str = Field(min_length=1)
    title: Title | None = Field(default=None, max_length=300)
    details: Details | None = Field(default=None, max_length=4000)


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


def _validate_operations(db, username: str, operations: list[AIOperation]) -> None:
    for operation in operations:
        if isinstance(operation, RenameColumnOperation):
            if owned_column(db, username, operation.column_id) is None:
                raise AIOperationError("A column in the request was not found.")
        elif isinstance(operation, CreateCardOperation):
            if owned_column(db, username, operation.column_id) is None:
                raise AIOperationError("A target column in the request was not found.")
        elif isinstance(operation, EditCardOperation):
            if owned_card(db, username, operation.card_id) is None:
                raise AIOperationError("A card in the request was not found.")
            if operation.title is None and operation.details is None:
                raise AIOperationError("Card edits must include a title or details.")
        elif isinstance(operation, MoveCardOperation):
            if owned_card(db, username, operation.card_id) is None or owned_column(db, username, operation.column_id) is None:
                raise AIOperationError("A card or target column in the request was not found.")
        elif isinstance(operation, DeleteCardOperation):
            if owned_card(db, username, operation.card_id) is None:
                raise AIOperationError("A card in the request was not found.")


def _apply_operations(db, operations: list[AIOperation]) -> None:
    """Applies a validated batch. Earlier operations can invalidate later ones
    (deleting a card the next operation edits), so a missing row aborts the batch
    and the caller's transaction rolls the whole thing back."""
    for operation in operations:
        try:
            if isinstance(operation, RenameColumnOperation):
                board_ops.rename_column(db, operation.column_id, operation.title)
            elif isinstance(operation, CreateCardOperation):
                board_ops.create_card(db, operation.column_id, operation.title, operation.details)
            elif isinstance(operation, EditCardOperation):
                board_ops.update_card(db, operation.card_id, operation.title, operation.details)
            elif isinstance(operation, MoveCardOperation):
                board_ops.move_card(db, operation.card_id, operation.column_id, operation.position)
            elif isinstance(operation, DeleteCardOperation):
                board_ops.delete_card(db, operation.card_id)
        except LookupError:
            raise AIOperationError("A card in the request was not found.") from None


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
    _apply_operations(db, response.operations)
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
    # One connection for the whole exchange, so the board the model reasoned
    # about is the same board the operations are applied to.
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
        updated_board = apply_ai_response(db, username, response)
    yield ("done", response, updated_board)
