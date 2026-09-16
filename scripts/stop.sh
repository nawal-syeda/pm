#!/usr/bin/env sh
set -eu

CONTAINER_NAME="pm-mvp"

if docker container inspect "$CONTAINER_NAME" >/dev/null 2>&1; then
  docker container rm --force "$CONTAINER_NAME" >/dev/null
  echo "Project Management MVP stopped."
else
  echo "Project Management MVP is not running."
fi

