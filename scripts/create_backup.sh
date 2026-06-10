#!/usr/bin/env bash
set -euo pipefail

# create_backup.sh — Create a timestamped backup of the database.
# Usage: ./scripts/create_backup.sh
#   Creates backups/YYYY-MM-DD_HHMMSS.sqlite (for SQLite) or
#   a pg_dump (for PostgreSQL).

BACKUP_DIR="${BACKUP_DIR:-$(dirname "$0")/../backups}"
PROJECT_DIR="$(dirname "$0")/.."
TIMESTAMP="$(date +%Y-%m-%d_%H%M%S)"
DB_URL="${DATABASE_URL:-$(grep -i '^DATABASE_URL=' "$PROJECT_DIR/.env" 2>/dev/null | cut -d= -f2-)}"

mkdir -p "$BACKUP_DIR"

if echo "$DB_URL" | grep -qi "sqlite"; then
    DB_PATH="${DB_URL#sqlite:///}"
    DB_PATH="${DB_PATH#sqlite://}"
    if [ -z "$DB_PATH" ]; then
        DB_PATH="$PROJECT_DIR/instance/moscowle.db"
    fi
    BACKUP_FILE="$BACKUP_DIR/${TIMESTAMP}.sqlite"
    sqlite3 "$DB_PATH" ".backup '$BACKUP_FILE'"
    echo "Backup created: $BACKUP_FILE ($(du -h "$BACKUP_FILE" | cut -f1))"
elif echo "$DB_URL" | grep -qi "postgres"; then
    BACKUP_FILE="$BACKUP_DIR/${TIMESTAMP}.dump"
    pg_dump --no-owner --no-acl -d "$DB_URL" -f "$BACKUP_FILE"
    echo "Backup created: $BACKUP_FILE ($(du -h "$BACKUP_FILE" | cut -f1))"
else
    echo "Warning: unknown DATABASE_URL ($DB_URL); trying SQLite default..."
    DB_PATH="$PROJECT_DIR/instance/moscowle.db"
    if [ -f "$DB_PATH" ]; then
        BACKUP_FILE="$BACKUP_DIR/${TIMESTAMP}.sqlite"
        sqlite3 "$DB_PATH" ".backup '$BACKUP_FILE'"
        echo "Backup created: $BACKUP_FILE"
    else
        echo "No database file found at $DB_PATH"
        exit 1
    fi
fi
