#!/usr/bin/env bash
# Instala el servicio de escaneo en el HOST (no en VM-APP). Una sola vez:
#   curl -fsSL https://raw.githubusercontent.com/Dedalos537/moscowle/main/deploy/scanner/setup_scanner.sh | sudo bash
# Idempotente: si se repite, actualiza el servicio y conserva el token.
set -euo pipefail
RAW=https://raw.githubusercontent.com/Dedalos537/moscowle/main/deploy/scanner
VM=192.168.122.10
VM_KEY=/home/diego/.ssh/id_ed25519_vm
[ "$(id -u)" -eq 0 ] || { echo "Córrelo con sudo."; exit 1; }

apt-get install -y -qq sane-utils sane-airscan >/dev/null
id moscowle-scan >/dev/null 2>&1 || useradd --system --no-create-home --shell /usr/sbin/nologin moscowle-scan
getent group scanner >/dev/null && usermod -aG scanner moscowle-scan || true
getent group lpadmin >/dev/null && usermod -aG lpadmin moscowle-scan || true

install -d -m 0755 /opt/moscowle-scand
curl -fsSL "$RAW/moscowle_scand.py" -o /opt/moscowle-scand/moscowle_scand.py
curl -fsSL "$RAW/moscowle-scand.service" -o /etc/systemd/system/moscowle-scand.service
chmod 0644 /opt/moscowle-scand/moscowle_scand.py /etc/systemd/system/moscowle-scand.service

if [ ! -s /etc/moscowle-scand.env ]; then
  umask 077
  printf 'SCAND_TOKEN=%s\n' "$(head -c 32 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | head -c 40)" > /etc/moscowle-scand.env
fi
chown root:moscowle-scan /etc/moscowle-scand.env; chmod 640 /etc/moscowle-scand.env
TOKEN=$(sed -n 's/^SCAND_TOKEN=//p' /etc/moscowle-scand.env)

# Solo VM-APP puede llegar al puerto, y solo por virbr0.
if command -v ufw >/dev/null && ufw status | grep -q active; then
  ufw allow in on virbr0 from "$VM" to any port 8631 proto tcp >/dev/null
fi

systemctl daemon-reload
systemctl enable --now moscowle-scand
systemctl restart moscowle-scand
sleep 2

echo "Buscando el escáner (puede tardar ~20 s)…"
code=$(curl -s -o /tmp/scand-status.json -w '%{http_code}' -H "X-Scan-Token: $TOKEN" http://192.168.122.1:8631/status || true)
echo "Servicio: HTTP $code · $(cat /tmp/scand-status.json 2>/dev/null)"; rm -f /tmp/scand-status.json

# Pasar URL y token al .env de Moscowle en VM-APP (con la llave del host) y reiniciar el backend.
if [ -f "$VM_KEY" ]; then
  sudo -u diego ssh -i "$VM_KEY" -o StrictHostKeyChecking=accept-new "diego@$VM" \
    "cd /home/diego/moscowle_ia && sed -i '/^SCAN_SERVER_URL=/d; /^SCAN_TOKEN=/d' .env && \
     printf 'SCAN_SERVER_URL=http://192.168.122.1:8631\nSCAN_TOKEN=%s\n' '$TOKEN' >> .env && chmod 600 .env && \
     sudo systemctl restart moscowle && echo 'VM-APP: .env actualizado y backend reiniciado'"
else
  echo "No encontré $VM_KEY: agrega a mano en VM-APP (.env): SCAN_SERVER_URL=http://192.168.122.1:8631 y SCAN_TOKEN (en /etc/moscowle-scand.env)."
fi
echo "Impresora: $(curl -s -H "X-Scan-Token: $TOKEN" http://192.168.122.1:8631/printer)"
echo "Listo. En el Drive: «Escanear» y, en Impresiones, «Reconectar impresora» (también se repunta sola cada 10 min)."
