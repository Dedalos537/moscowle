#!/usr/bin/env bash
set -euo pipefail

echo "🚦 Backend entrypoint starting — will wait for DB init before launching app"

if [ -f "/app/wait_for_db_init.py" ]; then
  echo "Running Python wait script /app/wait_for_db_init.py"
  python /app/wait_for_db_init.py
  rc=$?
  if [ $rc -ne 0 ]; then
    echo "❌ wait_for_db_init.py exited with code $rc" >&2
    exit $rc
  fi
else
  echo "⚠️ /app/wait_for_db_init.py not found — continuing without wait"
fi

echo "✅ DB init check passed — launching command"

# Exec the container CMD (uvicorn) as PID 1
exec "$@"
