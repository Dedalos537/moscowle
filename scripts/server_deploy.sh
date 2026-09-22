#!/usr/bin/env bash
# Auto-deploy script run by the /api/deploy/webhook endpoint on the Ubuntu server.
#
#   ./server_deploy.sh [--backend] [--frontend /tmp/frontend.tar.gz]
#
set -u

DEPLOY_ROOT="/home/diego/moscowle_ia"
# Flask serves the SPA from here -> public at api-centrojuanpabloii.online/app/
SPA_FRONTEND_ROOT="${DEPLOY_ROOT}/edysync/dist/edysync/browser"
# nginx fallback (LAN) -> http://192.168.1.41/app/
NGINX_FRONTEND_ROOT="/var/www/moscowle/app"
OBSIDIAN_DIR="${DEPLOY_ROOT}/docs/obsidian_graph/Deployments"
LOG_FILE="${DEPLOY_ROOT}/logs/auto_deploy.log"
SUDO_CMD=""

if command -v sudo >/dev/null 2>&1; then
  SUDO_CMD="sudo"
fi

mkdir -p "$(dirname "$LOG_FILE")" "$OBSIDIAN_DIR"

log() {
  echo "[$(date -u '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

BACKEND=0
FRONTEND_TAR=""

while [ $# -gt 0 ]; do
  case "$1" in
    --backend) BACKEND=1; shift ;;
    --frontend) FRONTEND_TAR="${2:-}"; shift 2 ;;
    *) shift ;;
  esac
done

log "=== deploy start (backend=$BACKEND frontend=${FRONTEND_TAR:-none}) ==="

FAILED=0

if [ "$BACKEND" = "1" ]; then
  log "Pulling origin/main..."
  if cd "$DEPLOY_ROOT" && git fetch origin main 2>>"$LOG_FILE" && git reset --hard origin/main 2>>"$LOG_FILE"; then
    log "git reset to $(git rev-parse --short HEAD)"
    log "Scheduling moscowle restart (detached systemd-run)..."
    # The deploy script runs inside the moscowle service cgroup; a direct
    # restart would kill this script mid-run. systemd-run spawns a transient
    # unit outside that cgroup, so we survive the restart.
    if ${SUDO_CMD} -n systemd-run --collect --unit="moscowle-restart-$(date +%s)" \
        /bin/systemctl restart moscowle >>"$LOG_FILE" 2>&1; then
      log "moscowle restart scheduled"
    else
      log "ERROR: systemd-run restart scheduling failed"
      FAILED=1
    fi
  else
    log "ERROR: git pull failed"
    FAILED=1
  fi
fi

if [ -n "$FRONTEND_TAR" ] && [ -f "$FRONTEND_TAR" ]; then
  STAGE="/tmp/frontend_deploy_stage"
  rm -rf "$STAGE"
  mkdir -p "$STAGE"
  if tar -xzf "$FRONTEND_TAR" -C "$STAGE"; then
    log "Extracted frontend dist (stage)"
    for target in "$SPA_FRONTEND_ROOT" "$NGINX_FRONTEND_ROOT"; do
      mkdir -p "$target"
      if rsync -a --delete "$STAGE/" "$target/"; then
        log "Frontend synced to $target"
      else
        log "ERROR: rsync frontend failed -> $target"
        FAILED=1
      fi
    done
    if ${SUDO_CMD} -n /usr/bin/systemctl reload nginx >>"$LOG_FILE" 2>&1; then
      log "nginx reloaded"
    else
      log "ERROR: nginx reload failed"
      FAILED=1
    fi
  else
    log "ERROR: tar extraction failed"
    FAILED=1
  fi
  rm -rf "$STAGE" "$FRONTEND_TAR"
fi

# Write Obsidian deploy record
OBS_NOTE="${OBSIDIAN_DIR}/deploy-$(date -u '+%Y-%m-%d-%H%M').md"
{
  echo "---"
  echo "title: Deploy $(date -u '+%Y-%m-%d %H:%M')"
  echo "tags: [deploy]"
  echo "created: $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  echo "---"
  echo ""
  echo "# Deploy $(date -u '+%Y-%m-%d %H:%M')"
  echo ""
  echo "- **Backend**: $(test "$BACKEND" = '1' && echo 'Sí' || echo 'No')"
  echo "- **Frontend**: $(test -n "$FRONTEND_TAR" && echo 'Sí' || echo 'No')"
  if [ "$BACKEND" = "1" ]; then
    echo "- **Commit server**: \`$(cd "$DEPLOY_ROOT" && git rev-parse --short HEAD 2>/dev/null || echo 'n/a')\`"
  fi
  echo "- **Resultado**: $(test "$FAILED" = '0' && echo 'OK' || echo 'FALLO')"
  echo ""
  echo "Ver también: [[DEPLOY_FLOW]]"
} >> "$OBS_NOTE"
log "Obsidian note: $OBS_NOTE"

log "=== deploy end (status=$FAILED) ==="
exit $FAILED
