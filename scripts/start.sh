#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
IMAGE_NAME="pm-mvp:local"
CONTAINER_NAME="pm-mvp"
DATA_VOLUME_NAME="pm-mvp-data"

docker build --tag "$IMAGE_NAME" "$PROJECT_ROOT"

if docker container inspect "$CONTAINER_NAME" >/dev/null 2>&1; then
  docker container rm --force "$CONTAINER_NAME" >/dev/null
fi

if [ -f "$PROJECT_ROOT/.env" ]; then
  docker run --detach \
    --name "$CONTAINER_NAME" \
    --publish 8000:8000 \
    --volume "$DATA_VOLUME_NAME:/app/backend/data" \
    --env-file "$PROJECT_ROOT/.env" \
    "$IMAGE_NAME"
else
  docker run --detach \
    --name "$CONTAINER_NAME" \
    --publish 8000:8000 \
    --volume "$DATA_VOLUME_NAME:/app/backend/data" \
    "$IMAGE_NAME"
fi

ready=false
attempt=0
while [ "$attempt" -lt 30 ]; do
  if docker exec "$CONTAINER_NAME" python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health')" >/dev/null 2>&1; then
    ready=true
    break
  fi
  attempt=$((attempt + 1))
  sleep 1
done

if [ "$ready" != true ]; then
  echo "Container started, but the API did not become ready within 30 seconds." >&2
  exit 1
fi

echo "Project Management MVP is running at http://localhost:8000"
