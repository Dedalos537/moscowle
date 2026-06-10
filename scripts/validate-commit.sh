#!/usr/bin/env bash
# validate-commit.sh — Validates git commit messages follow project convention
# Usage: validate-commit.sh <commit-msg-file>
# Hook: .git/hooks/commit-msg

set -euo pipefail

MSG_FILE="${1:-/dev/stdin}"
MSG=$(cat "$MSG_FILE")

# Strip comments (lines starting with #)
MSG=$(echo "$MSG" | sed '/^#/d' | sed '/^$/d' | head -1)

if [ -z "$MSG" ]; then
    echo "❌ ERROR: Commit message is empty"
    exit 1
fi

# Pattern: <type>(<scope>): <description>
# Types: feat, fix, refactor, test, docs, chore, spec, prp, plan
# Scope: lowercase alphanumeric + hyphens
PATTERN='^(feat|fix|refactor|test|docs|chore|spec|prp|plan|debug)\([a-z][a-z0-9-]*\): .+$'

if ! echo "$MSG" | grep -qE "$PATTERN"; then
    echo "❌ ERROR: Commit message format invalid"
    echo ""
    echo "Expected format: <type>(<scope>): <description>"
    echo "Example:         feat(auth): implementar login OAuth Google"
    echo ""
    echo "Valid types: feat, fix, refactor, test, docs, chore, spec, prp, plan, debug"
    echo "Scope examples: api, models, auth, ui, db, ci, monitor, chat, payment, report"
    echo ""
    echo "Received: $MSG"
    exit 1
fi

echo "✅ Commit message válido: $MSG"
exit 0
