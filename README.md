# Project Management MVP

## Prerequisites

- Docker
- `uv` and Python 3.13 or newer for backend development
- Node.js and npm for frontend development

Create a root `.env` file when environment variables are needed. It is ignored by Git and passed to the container by the start scripts.

## Run locally

On Windows:

```powershell
./scripts/start.ps1
./scripts/stop.ps1
```

On macOS or Linux:

```sh
./scripts/start.sh
./scripts/stop.sh
```

The Kanban app is available at <http://localhost:8000>. FastAPI serves the statically exported Next.js frontend and the API from the same container. Check backend health at <http://localhost:8000/api/health>.

Sign in with:

- Username: `user`
- Password: `password`

Sessions are stored in memory for the local MVP, so restarting the container signs the user out.

## Test the backend

```sh
cd backend
uv sync
uv run pytest
```

## Test the frontend

```sh
cd frontend
npm ci
npm run lint
npm run test:unit
npm run build
npm run test:e2e
```
