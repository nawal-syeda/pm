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

The app is available at <http://localhost:8000>. Check backend health at <http://localhost:8000/api/health>.

## Test the backend

```sh
cd backend
uv sync
uv run pytest
```

