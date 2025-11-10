#!/usr/bin/env bash
set -euo pipefail

# wait-for-db_init.sh
# Wait for MySQL to be reachable and for the db initialization to have created the expected tables.
# It checks that the configured database exists and that the `roles` table is present.

DB_HOST="${DB_HOST:-localhost}"
DB_USER="${DB_USER:-root}"
DB_PASSWORD="${DB_PASSWORD:-Rucula_530}"
DB_NAME="${DB_NAME:-Moscowle_Complete}"
MAX_RETRIES=${MAX_RETRIES:-60}
SLEEP_SECONDS=${SLEEP_SECONDS:-2}

echo "⏳ Waiting for MySQL at ${DB_HOST} (DB: ${DB_NAME})"

retries=0
while [ "$retries" -lt "$MAX_RETRIES" ]; do
  # First, test basic connectivity
  if mysql -h"$DB_HOST" -u"$DB_USER" -p"$DB_PASSWORD" -e "SELECT 1;" >/dev/null 2>&1; then
    echo "✔ MySQL reachable"

    # Check database exists and the 'roles' table is present
    if mysql -h"$DB_HOST" -u"$DB_USER" -p"$DB_PASSWORD" -sN -e "USE ${DB_NAME}; SHOW TABLES LIKE 'roles';" 2>/dev/null | grep -q "roles"; then
      echo "✔ '${DB_NAME}.roles' exists — assuming db_init finished"
      exit 0
    else
      echo "  - DB reachable but '${DB_NAME}.roles' not found yet"
    fi
  else
    echo "  - MySQL not reachable yet (attempt $((retries+1))/${MAX_RETRIES})"
  fi

  retries=$((retries+1))
  sleep "$SLEEP_SECONDS"
done

echo "❌ Timeout waiting for db_init to finish after ${MAX_RETRIES} attempts" >&2
exit 1
