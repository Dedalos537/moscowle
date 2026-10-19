#!/usr/bin/env bash
# PRP 009 — instala opencode como servicio en VM-APP. Se corre UNA vez, a mano:
#   sudo bash /home/diego/moscowle_ia/deploy/opencode/setup_opencode.sh
# Es idempotente: volver a correrlo actualiza binario y unidades sin cambiar las claves.
set -euo pipefail

REPO=/home/diego/moscowle_ia
APP_ENV=$REPO/.env
HERE=$(cd "$(dirname "$0")" && pwd)

[ "$(id -u)" -eq 0 ] || { echo "Córrelo con sudo."; exit 1; }

# 1) Binario: el que instaló diego (~/.opencode/bin) u otro en el PATH.
SRC=""
for c in /home/diego/.opencode/bin/opencode "$(command -v opencode || true)"; do
  [ -n "$c" ] && [ -x "$c" ] && SRC=$c && break
done
[ -n "$SRC" ] || { echo "No encuentro opencode. Instálalo como diego: curl -fsSL https://opencode.ai/install | bash"; exit 1; }
install -m 0755 "$SRC" /usr/local/bin/opencode
echo "opencode $(/usr/local/bin/opencode --version) → /usr/local/bin/opencode"

# 2) Usuarios de sistema sin shell ni sudo.
for u in opencode opencode-dev; do
  id "$u" >/dev/null 2>&1 || useradd --system --no-create-home --shell /usr/sbin/nologin "$u"
done

# 3) Carpetas.
install -d -o opencode -g opencode -m 0750 /srv/opencode/chat /srv/opencode/chat/home /srv/opencode/chat/sandbox
install -d -o opencode-dev -g opencode-dev -m 0750 /srv/opencode/dev /srv/opencode/dev/home
install -o opencode -g opencode -m 0644 "$HERE/AGENTS.md" /srv/opencode/chat/sandbox/AGENTS.md

# 4) Modo desarrollador: lectura del repo con ACL; el .env queda fuera (600 de diego, sin ACL).
if command -v setfacl >/dev/null 2>&1; then
  setfacl -m u:opencode-dev:x /home/diego
  setfacl -R -m u:opencode-dev:rX "$REPO"
  setfacl -R -d -m u:opencode-dev:rX "$REPO"
else
  echo "Falta setfacl (apt install acl): el modo desarrollador no podrá leer el repo."
fi
for f in "$APP_ENV" "$REPO"/.deploy_cpanel.env "$REPO"/*.pem; do
  [ -e "$f" ] || continue
  chmod 600 "$f"
  command -v setfacl >/dev/null 2>&1 && setfacl -b "$f"
done
sudo -u opencode-dev env HOME=/srv/opencode/dev/home git config --global --add safe.directory "$REPO" || true

# 5) Claves (se generan una vez; nunca se imprimen).
gen() { head -c 32 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | head -c 40; }
for pair in "/etc/opencode-moscowle.env:OPENCODE_URL:OPENCODE_PASSWORD:4096" \
            "/etc/opencode-moscowle-dev.env:OPENCODE_DEV_URL:OPENCODE_DEV_PASSWORD:4097"; do
  IFS=: read -r file url_var pass_var port <<<"$pair"
  if [ ! -s "$file" ]; then
    umask 077
    printf 'OPENCODE_SERVER_PASSWORD=%s\n' "$(gen)" > "$file"
  fi
  chmod 600 "$file"; chown root:root "$file"
  pass=$(sed -n 's/^OPENCODE_SERVER_PASSWORD=//p' "$file")
  # .env de Moscowle: misma clave, para que Flask hable con el servicio.
  touch "$APP_ENV"
  sed -i "/^${url_var}=/d; /^${pass_var}=/d" "$APP_ENV"
  printf '%s=http://127.0.0.1:%s\n%s=%s\n' "$url_var" "$port" "$pass_var" "$pass" >> "$APP_ENV"
done
chown diego:diego "$APP_ENV"; chmod 600 "$APP_ENV"

# 6) Servicios.
install -m 0644 "$HERE/opencode-moscowle.service" /etc/systemd/system/opencode-moscowle.service
install -m 0644 "$HERE/opencode-moscowle-dev.service" /etc/systemd/system/opencode-moscowle-dev.service
systemctl daemon-reload
systemctl enable --now opencode-moscowle opencode-moscowle-dev
systemctl restart opencode-moscowle opencode-moscowle-dev
systemctl restart moscowle

# 7) Comprobaciones.
sleep 4
for port in 4096 4097; do
  code=$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:$port/doc" || true)
  echo "puerto $port sin clave → HTTP $code (esperado 401)"
done
ss -ltnp | grep -E ':409[67]\b' || true
echo "Listo. Activa el asistente en Visor de funcionamiento → LLM → «Asistente con MiMo»."
