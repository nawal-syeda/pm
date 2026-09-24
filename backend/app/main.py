import os
import secrets
import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Cookie, Depends, FastAPI, HTTPException, Response
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response as StarletteResponse, StreamingResponse
from starlette.staticfiles import StaticFiles
from starlette.types import Scope

from app.database import connection, new_id, public_board, utc_now
from app.ai_board import (
    AIChatRequest,
    AIOperationError,
    answer_board_request,
    apply_ai_response,
    stream_board_request,
)
from app.openrouter import MODEL, OpenRouterError, ask_two_plus_two

@asynccontextmanager
async def lifespan(_app: FastAPI):
    with connection():
        pass
    yield


app = FastAPI(title="Project Management MVP", lifespan=lifespan)

STATIC_DIR = Path(
    os.environ.get("PM_STATIC_DIR", Path(__file__).resolve().parent / "static")
).resolve()
SESSION_COOKIE = "pm_session"
sessions: dict[str, str] = {}


class LoginRequest(BaseModel):
    username: str
    password: str


class ColumnUpdate(BaseModel):
    title: str = Field(min_length=1)


class CardCreate(BaseModel):
    title: str = Field(min_length=1)
    details: str = ""


class CardUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1)
    details: str | None = None


class CardMove(BaseModel):
    column_id: str
    position: int = Field(default=0, ge=0)


def require_user(
    session_id: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> str:
    username = sessions.get(session_id or "")
    if username is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return username


class FrontendFiles(StaticFiles):
    async def get_response(self, path: str, scope: Scope) -> StarletteResponse:
        try:
            response = await super().get_response(path, scope)
        except StarletteHTTPException as error:
            if error.status_code == 404 and not Path(path).suffix:
                return await super().get_response("index.html", scope)
            raise
        if response.status_code == 404 and not Path(path).suffix:
            return await super().get_response("index.html", scope)
        return response


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/example")
def example(_username: Annotated[str, Depends(require_user)]) -> dict[str, str]:
    return {"message": "Hello from FastAPI"}


@app.post("/api/ai/diagnostic")
def ai_diagnostic(
    _username: Annotated[str, Depends(require_user)],
) -> dict[str, str]:
    try:
        return {"model": MODEL, "answer": ask_two_plus_two()}
    except OpenRouterError as error:
        raise HTTPException(status_code=503, detail=str(error)) from None


@app.post("/api/ai/chat")
def ai_chat(
    request: AIChatRequest,
    username: Annotated[str, Depends(require_user)],
) -> dict:
    try:
        with connection() as db:
            ai_response = answer_board_request(db, username, request)
        with connection() as db:
            board = apply_ai_response(db, username, ai_response)
            return {
                "assistant_message": ai_response.assistant_message,
                "board_changed": board is not None,
                "board": board,
            }
    except AIOperationError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None
    except OpenRouterError as error:
        raise HTTPException(status_code=503, detail=str(error)) from None


@app.post("/api/ai/chat/stream")
def ai_chat_stream(
    request: AIChatRequest,
    username: Annotated[str, Depends(require_user)],
) -> StreamingResponse:
    def events():
        try:
            for event in stream_board_request(username, request):
                if event[0] == "delta":
                    yield f"data: {json.dumps({'type': 'delta', 'content': event[1]})}\n\n"
                else:
                    response, board = event[1], event[2]
                    yield f"data: {json.dumps({'type': 'done', 'assistant_message': response.assistant_message, 'board_changed': board is not None, 'board': board})}\n\n"
        except (AIOperationError, OpenRouterError) as error:
            yield f"data: {json.dumps({'type': 'error', 'detail': str(error)})}\n\n"

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/board")
def get_board(username: Annotated[str, Depends(require_user)]) -> dict:
    with connection() as db:
        return public_board(db, username)


def owned_card(db, username: str, card_id: str):
    return db.execute(
        'SELECT cards.* FROM cards JOIN "columns" ON "columns".id = cards.column_id JOIN boards ON boards.id = "columns".board_id JOIN users ON users.id = boards.user_id WHERE cards.id = ? AND users.username = ?',
        (card_id, username),
    ).fetchone()


@app.patch("/api/board/columns/{column_id}")
def rename_column(
    column_id: str,
    payload: ColumnUpdate,
    username: Annotated[str, Depends(require_user)],
) -> dict:
    with connection() as db:
        result = db.execute(
            'UPDATE "columns" SET title = ?, updated_at = ? WHERE id = ? AND board_id IN (SELECT boards.id FROM boards JOIN users ON users.id = boards.user_id WHERE users.username = ?)',
            (payload.title.strip(), utc_now(), column_id, username),
        )
        if result.rowcount != 1 or not payload.title.strip():
            raise HTTPException(status_code=404, detail="Column not found")
        return public_board(db, username)


@app.post("/api/board/columns/{column_id}/cards")
def create_card(
    column_id: str,
    payload: CardCreate,
    username: Annotated[str, Depends(require_user)],
) -> dict:
    with connection() as db:
        column = db.execute(
            'SELECT "columns".* FROM "columns" JOIN boards ON boards.id = "columns".board_id JOIN users ON users.id = boards.user_id WHERE "columns".id = ? AND users.username = ?',
            (column_id, username),
        ).fetchone()
        if column is None or not payload.title.strip():
            raise HTTPException(status_code=404, detail="Column not found")
        position = db.execute("SELECT COUNT(*) AS count FROM cards WHERE column_id = ?", (column_id,)).fetchone()["count"]
        now = utc_now()
        db.execute(
            "INSERT INTO cards (id, column_id, title, details, position, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (new_id("card"), column_id, payload.title.strip(), payload.details.strip(), position, now, now),
        )
        return public_board(db, username)


@app.patch("/api/board/cards/{card_id}")
def update_card(
    card_id: str,
    payload: CardUpdate,
    username: Annotated[str, Depends(require_user)],
) -> dict:
    if payload.title is None and payload.details is None:
        raise HTTPException(status_code=422, detail="At least one card field is required")
    with connection() as db:
        card = owned_card(db, username, card_id)
        if card is None:
            raise HTTPException(status_code=404, detail="Card not found")
        title = payload.title.strip() if payload.title is not None else card["title"]
        if not title:
            raise HTTPException(status_code=422, detail="Card title cannot be empty")
        details = payload.details if payload.details is not None else card["details"]
        db.execute(
            "UPDATE cards SET title = ?, details = ?, updated_at = ? WHERE id = ?",
            (title, details.strip(), utc_now(), card_id),
        )
        return public_board(db, username)


@app.post("/api/board/cards/{card_id}/move")
def move_card(
    card_id: str,
    payload: CardMove,
    username: Annotated[str, Depends(require_user)],
) -> dict:
    with connection() as db:
        card = owned_card(db, username, card_id)
        target = db.execute(
            'SELECT "columns".* FROM "columns" JOIN boards ON boards.id = "columns".board_id JOIN users ON users.id = boards.user_id WHERE "columns".id = ? AND users.username = ?',
            (payload.column_id, username),
        ).fetchone()
        if card is None or target is None:
            raise HTTPException(status_code=404, detail="Card or target column not found")
        source_id = card["column_id"]
        target_cards = [row["id"] for row in db.execute("SELECT id FROM cards WHERE column_id = ? ORDER BY position", (payload.column_id,)).fetchall() if row["id"] != card_id]
        insert_at = min(payload.position, len(target_cards))
        target_cards.insert(insert_at, card_id)
        db.execute("UPDATE cards SET position = position + 1000000 WHERE column_id IN (?, ?)", (source_id, payload.column_id))
        staging_position = db.execute(
            "SELECT COALESCE(MAX(position), 0) + 1 FROM cards WHERE column_id = ?",
            (payload.column_id,),
        ).fetchone()[0]
        db.execute(
            "UPDATE cards SET column_id = ?, position = ?, updated_at = ? WHERE id = ?",
            (payload.column_id, staging_position, utc_now(), card_id),
        )
        for position, moved_id in enumerate(target_cards):
            db.execute("UPDATE cards SET position = ? WHERE id = ?", (position, moved_id))
        if source_id != payload.column_id:
            for position, row in enumerate(db.execute("SELECT id FROM cards WHERE column_id = ? AND id != ? ORDER BY position", (source_id, card_id)).fetchall()):
                db.execute("UPDATE cards SET position = ? WHERE id = ?", (position, row["id"]))
        return public_board(db, username)


@app.delete("/api/board/cards/{card_id}")
def delete_card(
    card_id: str,
    username: Annotated[str, Depends(require_user)],
) -> dict:
    with connection() as db:
        card = owned_card(db, username, card_id)
        if card is None:
            raise HTTPException(status_code=404, detail="Card not found")
        column_id = card["column_id"]
        db.execute("DELETE FROM cards WHERE id = ?", (card_id,))
        for position, row in enumerate(db.execute("SELECT id FROM cards WHERE column_id = ? ORDER BY position", (column_id,)).fetchall()):
            db.execute("UPDATE cards SET position = ? WHERE id = ?", (position, row["id"]))
        return public_board(db, username)


@app.post("/api/auth/login")
def login(credentials: LoginRequest, response: Response) -> dict[str, str]:
    if credentials.username != "user" or credentials.password != "password":
        raise HTTPException(status_code=401, detail="Invalid username or password")

    session_id = secrets.token_urlsafe(32)
    sessions[session_id] = credentials.username
    response.set_cookie(
        key=SESSION_COOKIE,
        value=session_id,
        httponly=True,
        samesite="lax",
        secure=False,
    )
    return {"username": credentials.username}


@app.get("/api/auth/session")
def current_session(
    username: Annotated[str, Depends(require_user)],
) -> dict[str, str]:
    return {"username": username}


@app.post("/api/auth/logout")
def logout(
    response: Response,
    session_id: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> dict[str, str]:
    if session_id is not None:
        sessions.pop(session_id, None)
    response.delete_cookie(key=SESSION_COOKIE, httponly=True, samesite="lax")
    return {"message": "Logged out"}


app.mount("/", FrontendFiles(directory=STATIC_DIR, html=True), name="frontend")
