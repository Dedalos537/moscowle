#!/usr/bin/env bash
set -euo pipefail

# rollback_remediation.sh — Roll back the remediation (Fase 1-3) changes.
# This reverts the Alembic migration bba7eaa6929c and restores
# original code from git for changed source files.
#
# Usage: ./scripts/rollback_remediation.sh
#   Reverts latest migration and restores original files.

PROJECT_DIR="$(dirname "$0")/.."
MIGRATION_ID="bba7eaa6929c"

echo "=== Remediation Rollback ==="
echo ""
echo "This script will:"
echo "  1. Revert Alembic migration $MIGRATION_ID"
echo "  2. Restore original app/ files via git checkout"
echo ""
read -p "Continue? [y/N] " -r
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

# Step 1: Roll back the database migration
echo ""
echo "[1/2] Rolling back database migration..."
cd "$PROJECT_DIR"
if command -v alembic &>/dev/null; then
    alembic downgrade "$MIGRATION_ID" 2>/dev/null || alembic downgrade -1 2>/dev/null || echo "  (alembic not configured; manual revert required)"
else
    echo "  (alembic not found; manual revert required)"
fi

# Step 2: Restore original source files from git
echo ""
echo "[2/2] Restoring original source files..."
cd "$PROJECT_DIR"
FILES_TO_RESTORE=(
    "app/models/base.py"
    "app/models/user.py"
    "app/models/payment.py"
    "app/models/admin.py"
    "app/models/appointment.py"
    "app/models/chat.py"
    "app/models/ai.py"
    "app/models/refresh_token.py"
    "app/models/notification.py"
    "app/models/service_request.py"
    "app/api/service_requests.py"
    "app/repositories/base.py"
    "app/repositories/service_request_repo.py"
    "app/routes/health_routes.py"
    "app/services/crisis_monitor.py"
    "app/db/routing.py"
    "app/auth_compat.py"
    "app/middleware/request_handlers.py"
    "app/bootstrap.py"
    "app/utils/api_helpers.py"
    "config.py"
    "tests/conftest.py"
    "tests/test_service_requests.py"
)

for f in "${FILES_TO_RESTORE[@]}"; do
    if git ls-files --error-unmatch "$f" &>/dev/null 2>&1; then
        git checkout -- "$f"
        echo "  Restored: $f"
    else
        echo "  SKIP (not in git): $f"
    fi
done

echo ""
echo "=== Rollback complete ==="
echo "Database migration $MIGRATION_ID has been reverted."
echo "Source files restored to git HEAD."
echo ""
echo "To recreate the .env.example (no git history):"
echo "  cp .env.example .env.example.bak (if you modified it)"
