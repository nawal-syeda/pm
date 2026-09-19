import os
import secrets
from pathlib import Path
from typing import Annotated

from fastapi import Cookie, Depends, FastAPI, HTTPException, Response
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response as StarletteResponse
from starlette.staticfiles import StaticFiles
from starlette.types import Scope

app = FastAPI(title="Project Management MVP")

STATIC_DIR = Path(
    os.environ.get("PM_STATIC_DIR", Path(__file__).resolve().parent / "static")
).resolve()
SESSION_COOKIE = "pm_session"
sessions: dict[str, str] = {}


class LoginRequest(BaseModel):
    username: str
    password: str


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
