import json
import os
import secrets
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Cookie, Depends, FastAPI, HTTPException, Response
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response as StarletteResponse, StreamingResponse
from starlette.staticfiles import StaticFiles
from starlette.types import Scope

from app import board as board_ops
from app.board import Details, Title, owned_card, owned_column
from app.database import connection, initialise, public_board
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
    initialise()
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
    title: Title


class CardCreate(BaseModel):
    title: Title
    details: Details = ""


class CardUpdate(BaseModel):
    title: Title | None = None
    details: Details | None = None


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
    """Serves the exported Next.js site, falling back to index.html for SPA routes.

    Only unknown /api paths reach this mount, because the real API routes are
    matched first. They are refused here so they fail as a JSON 404 rather than
    being answered with the SPA shell or the exported 404.html page.
    """

    def _is_spa_route(self, path: str) -> bool:
        return not Path(path).suffix

    def _is_api_path(self, path: str) -> bool:
        # Starlette hands this an OS-native relative path, so it is separated by
        # backslashes on Windows and slashes elsewhere. Path.parts handles both.
        parts = Path(path).parts
        return bool(parts) and parts[0] == "api"

    async def get_response(self, path: str, scope: Scope) -> StarletteResponse:
        if self._is_api_path(path):
            raise StarletteHTTPException(status_code=404, detail="Not Found")
        try:
            response = await super().get_response(path, scope)
        except StarletteHTTPException as error:
            if error.status_code == 404 and self._is_spa_route(path):
                return await super().get_response("index.html", scope)
            raise
        if response.status_code == 404 and self._is_spa_route(path):
            return await super().get_response("index.html", scope)
        return response


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


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
    def event(payload: dict) -> str:
        return f"data: {json.dumps(payload)}\n\n"

    def events():
        try:
            for message in stream_board_request(username, request):
                if message[0] == "delta":
                    yield event({"type": "delta", "content": message[1]})
                else:
                    response, board = message[1], message[2]
                    yield event(
                        {
                            "type": "done",
                            "assistant_message": response.assistant_message,
                            "board_changed": board is not None,
                            "board": board,
                        }
                    )
        except (AIOperationError, OpenRouterError) as error:
            yield event({"type": "error", "detail": str(error)})
        except Exception:
            # The response has already started, so this is the only way to tell
            # the browser that the stream failed instead of silently truncating.
            yield event({"type": "error", "detail": "The AI request failed unexpectedly."})

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/board")
def get_board(username: Annotated[str, Depends(require_user)]) -> dict:
    with connection() as db:
        return public_board(db, username)


@app.patch("/api/board/columns/{column_id}")
def rename_column(
    column_id: str,
    payload: ColumnUpdate,
    username: Annotated[str, Depends(require_user)],
) -> dict:
    with connection() as db:
        if owned_column(db, username, column_id) is None:
            raise HTTPException(status_code=404, detail="Column not found")
        board_ops.rename_column(db, column_id, payload.title)
        return public_board(db, username)


@app.post("/api/board/columns/{column_id}/cards")
def create_card(
    column_id: str,
    payload: CardCreate,
    username: Annotated[str, Depends(require_user)],
) -> dict:
    with connection() as db:
        if owned_column(db, username, column_id) is None:
            raise HTTPException(status_code=404, detail="Column not found")
        board_ops.create_card(db, column_id, payload.title, payload.details)
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
        if owned_card(db, username, card_id) is None:
            raise HTTPException(status_code=404, detail="Card not found")
        board_ops.update_card(db, card_id, payload.title, payload.details)
        return public_board(db, username)


@app.post("/api/board/cards/{card_id}/move")
def move_card(
    card_id: str,
    payload: CardMove,
    username: Annotated[str, Depends(require_user)],
) -> dict:
    with connection() as db:
        if owned_card(db, username, card_id) is None or owned_column(db, username, payload.column_id) is None:
            raise HTTPException(status_code=404, detail="Card or target column not found")
        board_ops.move_card(db, card_id, payload.column_id, payload.position)
        return public_board(db, username)


@app.delete("/api/board/cards/{card_id}")
def delete_card(
    card_id: str,
    username: Annotated[str, Depends(require_user)],
) -> dict:
    with connection() as db:
        if owned_card(db, username, card_id) is None:
            raise HTTPException(status_code=404, detail="Card not found")
        board_ops.delete_card(db, card_id)
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
