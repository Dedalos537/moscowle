#!/usr/bin/env bash
set -euo pipefail

# restore_backup.sh — Restore a database backup from the backups/ directory.
# Usage: ./scripts/restore_backup.sh [backup_file.sqlite]
# If no argument given, lists available backups.

BACKUP_DIR="${BACKUP_DIR:-$(dirname "$0")/../backups}"
PROJECT_DIR="$(dirname "$0")/.."

mkdir -p "$BACKUP_DIR"

if [ $# -eq 0 ]; then
    echo "Available backups:"
    ls -lh "$BACKUP_DIR"/*.sqlite 2>/dev/null || echo "  (no .sqlite backups found in $BACKUP_DIR)"
    echo ""
    echo "Usage: $0 <backup_file>"
    exit 1
fi

BACKUP_FILE="$1"
if [ ! -f "$BACKUP_FILE" ]; then
    if [ -f "$BACKUP_DIR/$BACKUP_FILE" ]; then
        BACKUP_FILE="$BACKUP_DIR/$BACKUP_FILE"
    else
        echo "Error: backup file not found: $BACKUP_FILE"
        echo "Looked in: $BACKUP_DIR"
        exit 1
    fi
fi

# Detect database type from .env
DB_URL="${DATABASE_URL:-$(grep -i '^DATABASE_URL=' "$PROJECT_DIR/.env" 2>/dev/null | cut -d= -f2-)}"

if echo "$DB_URL" | grep -qi "sqlite"; then
    DB_PATH="${DB_URL#sqlite:///}"
    DB_PATH="${DB_PATH#sqlite://}"
    if [ -z "$DB_PATH" ]; then
        DB_PATH="$PROJECT_DIR/instance/moscowle.db"
    fi
    echo "Stopping application (if running)..."
    # Attempt graceful stop
    pkill -f "python.*wsgi.py" 2>/dev/null || true
    sleep 1
    
    echo "Restoring SQLite database..."
    cp "$BACKUP_FILE" "$DB_PATH"
    echo "Restored: $DB_PATH from $BACKUP_FILE"
elif echo "$DB_URL" | grep -qi "postgres"; then
    echo "Restoring PostgreSQL database..."
    echo "Ensure DATABASE_URL is set correctly in .env"
    echo "Command: pg_restore -d \"$DB_URL\" \"$BACKUP_FILE\""
    pg_restore --clean --if-exists -d "$DB_URL" "$BACKUP_FILE"
    echo "PostgreSQL restore complete."
else
    echo "Unsupported database URL: $DB_URL"
    echo "Manual restore required."
    exit 1
fi

echo "Done."
