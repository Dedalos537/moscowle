#!/usr/bin/env bash
# PRP 010 — Prometheus + Alertmanager + blackbox + node_exporter + Grafana en el HOST (no en VM-APP).
# Una sola vez (es idempotente: si se repite, actualiza la configuración y conserva claves y datos):
#   curl -fsSL https://raw.githubusercontent.com/Dedalos537/moscowle/main/deploy/observability/setup_observability.sh | sudo bash
# Después, en VM-APP y en VM-DB: setup_vm_exporter.sh (ver el final de este script).
set -euo pipefail
umask 022  # archivos de configuración legibles por los servicios; las claves se crean aparte con umask 077
RAW=https://raw.githubusercontent.com/Dedalos537/moscowle/main/deploy/observability
VM_APP=192.168.122.10
VM_KEY=/home/diego/.ssh/id_ed25519_vm
[ "$(id -u)" -eq 0 ] || { echo "Córrelo con sudo."; exit 1; }

echo "== Memoria libre antes: $(free -m | awk '/Mem:/{print $7}') MB"
avail=$(free -m | awk '/Mem:/{print $7}')
if [ "$avail" -lt 700 ]; then
  echo "AVISO: quedan menos de 700 MB libres. Se instala igual con límites de memoria, pero revisa el PRP 010 (Fase 0)."
fi

# 1) Paquetes oficiales de Ubuntu + Grafana desde su repositorio firmado.
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq prometheus prometheus-alertmanager prometheus-node-exporter prometheus-blackbox-exporter \
  curl gpg >/dev/null
if ! command -v grafana-server >/dev/null && [ ! -x /usr/share/grafana/bin/grafana ]; then
  install -d -m 0755 /etc/apt/keyrings
  curl -fsSL https://apt.grafana.com/gpg.key | gpg --dearmor --yes -o /etc/apt/keyrings/grafana.gpg
  echo "deb [signed-by=/etc/apt/keyrings/grafana.gpg] https://apt.grafana.com stable main" > /etc/apt/sources.list.d/grafana.list
  apt-get update -qq
  apt-get install -y -qq grafana >/dev/null
fi

# 2) Configuración del repo.
fetch() { curl -fsSL "$RAW/$1" -o "$2"; }
install -d -m 0755 /etc/prometheus/rules
fetch prometheus.yml /etc/prometheus/prometheus.yml
fetch rules.yml /etc/prometheus/rules/moscowle.yml
fetch alertmanager.yml /etc/prometheus/alertmanager.yml
fetch blackbox.yml /etc/prometheus/blackbox.yml

# 3) Claves compartidas con Moscowle (se generan una vez; nunca se imprimen).
gen() { head -c 32 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | head -c 40; }
for f in moscowle_metrics.token alert_webhook.token; do
  [ -s "/etc/prometheus/$f" ] || (umask 077; gen > "/etc/prometheus/$f")
  chown root:prometheus "/etc/prometheus/$f"; chmod 640 "/etc/prometheus/$f"
done

# 4) Direcciones internas y retención (todo por /etc/default de cada paquete).
#    Prometheus usa 9095: el 9090 es de Cockpit en este host (escucha en todas las interfaces).
cat > /etc/default/prometheus <<'EOF'
ARGS="--web.listen-address=192.168.122.1:9095 --storage.tsdb.retention.time=30d --storage.tsdb.retention.size=2GB"
EOF
cat > /etc/default/prometheus-alertmanager <<'EOF'
ARGS="--web.listen-address=127.0.0.1:9093 --cluster.listen-address="
EOF
cat > /etc/default/prometheus-node-exporter <<'EOF'
ARGS="--web.listen-address=127.0.0.1:9100 --collector.systemd"
EOF
cat > /etc/default/prometheus-blackbox-exporter <<'EOF'
ARGS="--web.listen-address=127.0.0.1:9115 --config.file=/etc/prometheus/blackbox.yml"
EOF

# 5) Límites de memoria: nunca le quitan RAM a Ollama ni a las VMs.
limit() {
  install -d "/etc/systemd/system/$1.service.d"
  printf '[Service]\nMemoryMax=%s\nMemoryHigh=%s\n' "$2" "$3" > "/etc/systemd/system/$1.service.d/moscowle-limits.conf"
}
limit prometheus 300M 250M
# Escucha en virbr0 (192.168.122.1): debe arrancar después de libvirt, que crea esa red.
printf '[Unit]\nAfter=libvirtd.service network-online.target\nWants=network-online.target\n' \
  > /etc/systemd/system/prometheus.service.d/after-libvirt.conf
limit prometheus-alertmanager 64M 48M
limit prometheus-node-exporter 64M 48M
limit prometheus-blackbox-exporter 64M 48M
limit grafana-server 512M 400M  # su primer arranque migra la base y pasa de 300 MB

# 6) Grafana: solo en la LAN, sin registro ni anónimos; datasource y tablero desde archivos.
LAN_IP=$(ip -4 route get 1.1.1.1 | awk '{for(i=1;i<=NF;i++) if($i=="src") print $(i+1)}')
[ -s /etc/grafana/admin.pass ] || (umask 077; gen > /etc/grafana/admin.pass)
chown root:grafana /etc/grafana/admin.pass; chmod 640 /etc/grafana/admin.pass
install -d "/etc/systemd/system/grafana-server.service.d"
cat > /etc/systemd/system/grafana-server.service.d/moscowle.conf <<EOF
[Service]
Environment=GF_SERVER_HTTP_ADDR=$LAN_IP
Environment=GF_SERVER_HTTP_PORT=3000
Environment=GF_SECURITY_ADMIN_USER=admin
Environment=GF_SECURITY_ADMIN_PASSWORD__FILE=/etc/grafana/admin.pass
Environment=GF_USERS_ALLOW_SIGN_UP=false
Environment=GF_AUTH_ANONYMOUS_ENABLED=false
Environment=GF_ANALYTICS_REPORTING_ENABLED=false
Environment=GF_ANALYTICS_CHECK_FOR_UPDATES=false
Environment=GF_DATE_FORMATS_DEFAULT_TIMEZONE=America/Lima
EOF
install -d /etc/grafana/provisioning/datasources /etc/grafana/provisioning/dashboards /var/lib/grafana/dashboards/moscowle
fetch grafana/datasource.yml /etc/grafana/provisioning/datasources/moscowle.yml
fetch grafana/dashboards.yml /etc/grafana/provisioning/dashboards/moscowle.yml
fetch dashboards/moscowle-overview.json /var/lib/grafana/dashboards/moscowle/moscowle-overview.json
# Tablero comunitario «Node Exporter Full» (grafana.com, id 1860) para el detalle de cada máquina.
if curl -fsSL -m 60 https://grafana.com/api/dashboards/1860/revisions/latest/download -o /tmp/node-full.json; then
  sed 's/\${DS_PROMETHEUS}/prometheus/g' /tmp/node-full.json > /var/lib/grafana/dashboards/moscowle/node-exporter-full.json
  rm -f /tmp/node-full.json
fi
chown -R grafana:grafana /var/lib/grafana/dashboards
# Grafana corre como su usuario: debe poder leer su aprovisionamiento (antes quedaba 600 root y no arrancaba).
chown root:grafana /etc/grafana/provisioning/datasources/moscowle.yml /etc/grafana/provisioning/dashboards/moscowle.yml
chmod 644 /etc/grafana/provisioning/datasources/moscowle.yml /etc/grafana/provisioning/dashboards/moscowle.yml

# 7) Firewall: Grafana solo desde la LAN; Prometheus solo desde VM-APP (para las gráficas del panel).
if command -v ufw >/dev/null && ufw status | grep -q active; then
  LAN_NET=$(echo "$LAN_IP" | awk -F. '{print $1"."$2"."$3".0/24"}')
  ufw allow from "$LAN_NET" to any port 3000 proto tcp comment 'Grafana LAN' >/dev/null
  ufw allow in on virbr0 from "$VM_APP" to any port 9095 proto tcp comment 'Prometheus para Moscowle' >/dev/null
fi

# 8) Arrancar.
systemctl daemon-reload
for s in prometheus prometheus-alertmanager prometheus-node-exporter prometheus-blackbox-exporter grafana-server; do
  systemctl enable "$s" >/dev/null 2>&1 || true
  systemctl restart "$s"
done
sleep 5

# 9) Pasar URLs y claves al .env de Moscowle en VM-APP y reiniciar el backend.
METRICS=$(cat /etc/prometheus/moscowle_metrics.token)
ALERTS=$(cat /etc/prometheus/alert_webhook.token)
if [ -f "$VM_KEY" ]; then
  # -n: sin esto, ssh se «come» el resto de este script (llega por la misma entrada con curl | bash).
  sudo -u diego ssh -n -i "$VM_KEY" -o StrictHostKeyChecking=accept-new "diego@$VM_APP" \
    "cd /home/diego/moscowle_ia && sed -i '/^METRICS_TOKEN=/d; /^ALERT_WEBHOOK_TOKEN=/d; /^PROMETHEUS_URL=/d; /^GRAFANA_URL=/d' .env && \
     printf 'METRICS_TOKEN=%s\nALERT_WEBHOOK_TOKEN=%s\nPROMETHEUS_URL=http://192.168.122.1:9095\nGRAFANA_URL=http://%s:3000\n' '$METRICS' '$ALERTS' '$LAN_IP' >> .env && \
     chmod 600 .env && sudo systemctl restart moscowle && echo 'VM-APP: .env actualizado y backend reiniciado'"
else
  echo "No encontré $VM_KEY: agrega a mano en VM-APP (.env) METRICS_TOKEN, ALERT_WEBHOOK_TOKEN (en /etc/prometheus/*.token),"
  echo "PROMETHEUS_URL=http://192.168.122.1:9095 y GRAFANA_URL=http://$LAN_IP:3000"
fi

# 10) Comprobaciones.
sleep 8
echo "== Servicios (si alguno no está «active»: journalctl -u NOMBRE -n 30):"
for s in prometheus prometheus-alertmanager prometheus-node-exporter prometheus-blackbox-exporter grafana-server; do
  printf '  %-32s %s\n' "$s" "$(systemctl is-active "$s")"
done
echo "== Objetivos de Prometheus (up=1 bien):"
curl -s "http://192.168.122.1:9095/api/v1/query?query=up" | python3 -c '
import json,sys
for r in json.load(sys.stdin)["data"]["result"]:
    m=r["metric"]; print("   ", m.get("job"), m.get("instance"), "→", r["value"][1])' || true
printf '== Grafana %s:3000 → HTTP %s\n' "$LAN_IP" "$(curl -s -o /dev/null -w '%{http_code}' "http://$LAN_IP:3000/api/health" || true)"
echo "== Memoria libre después: $(free -m | awk '/Mem:/{print $7}') MB"
echo
echo "Listo. Grafana: http://$LAN_IP:3000 (usuario admin; contraseña: sudo cat /etc/grafana/admin.pass)"
echo "Falta en VM-APP y en VM-DB (una vez en cada una):"
echo "  curl -fsSL $RAW/setup_vm_exporter.sh | sudo bash"
