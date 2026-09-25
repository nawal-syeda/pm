# Backend guidance

The backend is a Python 3.13 FastAPI application managed with `uv`. Application code lives in `app/`, static files in `app/static/`, and pytest tests in `tests/`.

Run commands from `backend/`:

- `uv sync` installs locked runtime and development dependencies.
- `uv run pytest` runs backend tests.
- `uv run uvicorn app.main:app --reload` starts the development server.

Keep API routes under `/api` so static frontend routing cannot shadow them. Keep endpoint models typed, business logic small, and tests deterministic. Do not expose secrets in code, responses, logs, or fixtures.

Board mutations live in `app/board.py` and are shared by the HTTP endpoints and the AI operations in `app/ai_board.py`, so both paths behave identically. Callers check ownership first; the operations assume it. Titles and details are validated and stripped by the `Title` and `Details` request types rather than by hand.

`app/database.py` creates the schema and seeds the default board in `initialise()`, which runs once at startup. Per-request connections only open the file.

Authentication currently validates the fixed MVP credentials and stores opaque session IDs in process memory. The `pm_session` cookie is `HttpOnly` and `SameSite=Lax`. Keep `/api/health` public and require the session dependency for user data and future AI routes.
