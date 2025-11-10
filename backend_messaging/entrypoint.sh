#!/bin/bash
set -e
echo "Backend starting"
if [ -f /app/wait_for_db_init.py ]; then
  python /app/wait_for_db_init.py || exit 1
fi
echo "Launching app"
exec "$@"

