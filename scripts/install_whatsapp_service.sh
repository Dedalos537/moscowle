#!/usr/bin/env bash
# Instala el servicio systemd del puente de WhatsApp.
# Necesita sudo: systemctl install escribe en /etc/systemd/system.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UNIT="$REPO/app/whatsapp_bridge/moscowle-whatsapp.service"
NODE_BIN="${NODE_BIN:-$(command -v node || echo /home/diego/.nvm/versions/node/v20.20.2/bin/node)}"

if ! command -v systemctl >/dev/null 2>&1; then
  echo "Este servidor no usa systemd. Ejecuta el puente a mano:"
  echo "  cd $REPO/app/whatsapp_bridge && node index.js"
  exit 0
fi

echo "Instalando el servicio desde $UNIT"
sudo cp "$UNIT" /etc/systemd/system/moscowle-whatsapp.service
sudo systemctl daemon-reload
sudo systemctl enable moscowle-whatsapp
sudo systemctl restart moscowle-whatsapp

echo
echo "Estado:"
sudo systemctl status moscowle-whatsapp --no-pager -n 5
echo
echo "El QR aparece en el log:"
echo "  journalctl -u moscowle-whatsapp -f"
