#!/usr/bin/env bash
set -euo pipefail

echo "🚦 Backend entrypoint starting — will wait for DB init before launching app"

# If the wait script exists, run it
if [ -x "/app/wait-for-db_init.sh" ]; then
  /app/wait-for-db_init.sh
else
  echo "⚠️ wait-for-db_init.sh not found or not executable — continuing"
fi

echo "✅ DB init check passed — launching command"

# Exec the container CMD (uvicorn) as PID 1
exec "$@"
