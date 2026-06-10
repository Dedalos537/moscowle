#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-./backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DB_URL="${SQLALCHEMY_DATABASE_URI:-}"

if [ -z "$DB_URL" ]; then
  if [ -f .env ]; then
    source .env
    DB_URL="${SQLALCHEMY_DATABASE_URI:-}"
  fi
fi

if [ -z "$DB_URL" ]; then
  echo "ERROR: SQLALCHEMY_DATABASE_URI not set"
  exit 1
fi

# Parse MySQL URI: mysql+pymysql://user:password@host:port/dbname
if [[ "$DB_URL" =~ mysql\+pymysql://([^:]+):([^@]+)@([^:/]+):?([0-9]*)/(.+) ]]; then
  DB_USER="${BASH_REMATCH[1]}"
  DB_PASS="${BASH_REMATCH[2]}"
  DB_HOST="${BASH_REMATCH[3]}"
  DB_PORT="${BASH_REMATCH[4]:-3306}"
  DB_NAME="${BASH_REMATCH[5]}"

  mkdir -p "$BACKUP_DIR"

  echo "=== Backing up $DB_NAME @ $DB_HOST:$DB_PORT ==="
  mysqldump \
    --user="$DB_USER" \
    --password="$DB_PASS" \
    --host="$DB_HOST" \
    --port="$DB_PORT" \
    --single-transaction \
    --routines \
    --triggers \
    --events \
    --hex-blob \
    --skip-lock-tables \
    "$DB_NAME" \
    | gzip > "$BACKUP_DIR/${DB_NAME}_${TIMESTAMP}.sql.gz"

  echo "Backup saved: $BACKUP_DIR/${DB_NAME}_${TIMESTAMP}.sql.gz ($(du -h "$BACKUP_DIR/${DB_NAME}_${TIMESTAMP}.sql.gz" | cut -f1))"
else
  echo "ERROR: Unsupported DB_URL or not MySQL"
  exit 1
fi
