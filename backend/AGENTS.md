# Backend guidance

The backend is a Python 3.13 FastAPI application managed with `uv`. Application code lives in `app/`, static files in `app/static/`, and pytest tests in `tests/`.

Run commands from `backend/`:

- `uv sync` installs locked runtime and development dependencies.
- `uv run pytest` runs backend tests.
- `uv run uvicorn app.main:app --reload` starts the development server.

Keep API routes under `/api` so static frontend routing cannot shadow them. Keep endpoint models typed, business logic small, and tests deterministic. Do not expose secrets in code, responses, logs, or fixtures.
