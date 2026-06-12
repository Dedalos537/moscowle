#!/usr/bin/env bash
# install-hooks.sh — Installs git hooks for commit message validation
set -euo pipefail

HOOKS_DIR="$(git rev-parse --git-dir)/hooks"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Installing git hooks..."

# commit-msg hook
cat > "$HOOKS_DIR/commit-msg" << 'HOOK'
#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT=$(git rev-parse --show-toplevel)
exec "$REPO_ROOT/scripts/validate-commit.sh" "$1"
HOOK
chmod +x "$HOOKS_DIR/commit-msg"

echo "✅ commit-msg hook installed at $HOOKS_DIR/commit-msg"
echo "Run 'git commit' to test."
