#!/bin/sh
set -e
echo "Running migrations..."
alembic upgrade head
PORT="${PORT:-8742}"
echo "Starting API on 0.0.0.0:${PORT}"
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT}"
