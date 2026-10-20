#!/usr/bin/env bash
# PRP 010 — node_exporter en una VM (y mysqld_exporter si es VM-DB). Una vez en VM-APP y otra en VM-DB:
#   curl -fsSL https://raw.githubusercontent.com/Dedalos537/moscowle/main/deploy/observability/setup_vm_exporter.sh | sudo bash
# Escucha solo en la IP de la VM en la red interna (192.168.122.x); el único que lo lee es Prometheus del host.
set -euo pipefail
[ "$(id -u)" -eq 0 ] || { echo "Córrelo con sudo."; exit 1; }
HOST_IP=192.168.122.1
# Se corre DENTRO de VM-APP o VM-DB. En el host (tiene virbr0) dejaría node_exporter en otra dirección.
if ip link show virbr0 >/dev/null 2>&1; then
  echo "Esto es el HOST, no una VM. Entra primero a la VM:"
  echo "  ssh -i ~/.ssh/id_ed25519_vm diego@192.168.122.10   (VM-APP)"
  echo "  ssh -i ~/.ssh/id_ed25519_vm diego@192.168.122.20   (VM-DB)"
  exit 1
fi
VM_IP=$(ip -4 route get "$HOST_IP" | awk '{for(i=1;i<=NF;i++) if($i=="src") print $(i+1)}')
[ -n "$VM_IP" ] || { echo "No pude saber la IP interna de esta VM."; exit 1; }
echo "== VM $(hostname) en $VM_IP"

export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq prometheus-node-exporter >/dev/null
cat > /etc/default/prometheus-node-exporter <<EOF
ARGS="--web.listen-address=$VM_IP:9100 --collector.systemd"
EOF
install -d /etc/systemd/system/prometheus-node-exporter.service.d
printf '[Service]\nMemoryMax=64M\nMemoryHigh=48M\n' > /etc/systemd/system/prometheus-node-exporter.service.d/moscowle-limits.conf

if command -v ufw >/dev/null && ufw status | grep -q active; then
  ufw allow from "$HOST_IP" to any port 9100 proto tcp comment 'node_exporter para Prometheus' >/dev/null
fi

# VM-DB: exportador de MySQL con un usuario de solo lectura (contraseña generada, nunca se imprime).
# Sin tubería con grep -q: con «set -o pipefail», grep corta la lectura, systemctl recibe SIGPIPE y la condición
# daba falso aunque MySQL estuviera instalado (por eso no se instalaba el exportador en VM-DB).
UNITS=$(systemctl list-unit-files --type=service --no-legend 2>/dev/null || true)
if [[ "$UNITS" =~ (^|$'\n')(mysql|mariadb)\.service ]] || command -v mysqld >/dev/null 2>&1; then
  apt-get install -y -qq prometheus-mysqld-exporter >/dev/null
  CNF=/etc/prometheus/mysqld-exporter.cnf
  install -d -m 0755 /etc/prometheus
  if [ ! -s "$CNF" ]; then
    PASS=$(head -c 32 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | head -c 32)
    mysql -uroot <<SQL
CREATE USER IF NOT EXISTS 'exporter'@'localhost' IDENTIFIED BY '$PASS' WITH MAX_USER_CONNECTIONS 3;
ALTER USER 'exporter'@'localhost' IDENTIFIED BY '$PASS';
GRANT PROCESS, REPLICATION CLIENT, SELECT ON *.* TO 'exporter'@'localhost';
FLUSH PRIVILEGES;
SQL
    (umask 077; printf '[client]\nuser=exporter\npassword=%s\nhost=localhost\n' "$PASS" > "$CNF")
  fi
  chown root:prometheus "$CNF"; chmod 640 "$CNF"
  cat > /etc/default/prometheus-mysqld-exporter <<EOF
ARGS="--web.listen-address=$VM_IP:9104 --config.my-cnf=$CNF"
EOF
  install -d /etc/systemd/system/prometheus-mysqld-exporter.service.d
  printf '[Service]\nMemoryMax=64M\nMemoryHigh=48M\n' > /etc/systemd/system/prometheus-mysqld-exporter.service.d/moscowle-limits.conf
  if command -v ufw >/dev/null && ufw status | grep -q active; then
    ufw allow from "$HOST_IP" to any port 9104 proto tcp comment 'mysqld_exporter para Prometheus' >/dev/null
  fi
  systemctl daemon-reload
  systemctl enable prometheus-mysqld-exporter >/dev/null 2>&1 || true
  systemctl restart prometheus-mysqld-exporter
fi

systemctl daemon-reload
systemctl enable prometheus-node-exporter >/dev/null 2>&1 || true
systemctl restart prometheus-node-exporter
sleep 2
printf 'node_exporter  %s → %s\n' "$VM_IP:9100" "$(curl -s -o /dev/null -w '%{http_code}' "http://$VM_IP:9100/metrics")"
if systemctl is-active --quiet prometheus-mysqld-exporter 2>/dev/null; then
  printf 'mysqld_exporter %s → mysql_up=%s\n' "$VM_IP:9104" "$(curl -s "http://$VM_IP:9104/metrics" | awk '/^mysql_up /{print $2}')"
fi
echo "Listo. En unos 30 s Prometheus del host empieza a leer esta VM."
