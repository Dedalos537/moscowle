# NTP / Time Sync (Guía rápida)

Propósito: asegurar que los servidores (cPanel/hosting) tengan la hora sincronizada correctamente; la app usa timestamps para reports, logs y tokens.

Recomendación general:
- En servidores Linux, usar `chrony` o `ntpd` para sincronización continua. `chrony` es recomendado en entornos modernos.
- Para cPanel/WHM en CentOS/AlmaLinux, instala y habilita `chrony` o `ntpd` según política del proveedor.

Ejemplos (CentOS/AlmaLinux/Rocky):

Usando `chrony`:

```bash
# Instalar
sudo yum install -y chrony
# Habilitar y arrancar
sudo systemctl enable --now chronyd
# Verificar sincronización
chronyc tracking
chronyc sources -v
```

Usando `ntpd`:

```bash
# Instalar
sudo yum install -y ntp
# Habilitar y arrancar
sudo systemctl enable --now ntpd
# Forzar sincronización inicial (si es necesario)
sudo ntpdate pool.ntp.org
# Verificar
ntpq -pn
```

Configuración en cPanel:
- cPanel normalmente corre sobre RHEL/CentOS compatible; usar `yum` para instalar `chrony` y habilitar servicio.
- Asegúrate de que el firewall permita salida/entrada al puerto UDP 123 para los servidores NTP.

Comprobación desde la app / CI:
- Añadimos `scripts/check_ntp.py` que consulta `pool.ntp.org` (por defecto) y compara la hora local. Útil para etapas de despliegue y checks en CI.

Uso del script (desde el virtualenv del proyecto):

```bash
# Ejecutar check rápido
/Users/apple/Documents/moscowle_ia_mvp/venv/bin/python scripts/check_ntp.py --server pool.ntp.org --threshold-seconds 5
```

Interpretación de códigos de salida:
- `0` → OK (offset <= threshold)
- `2` → Skew mayor que threshold
- `1` → Error al consultar NTP o falta de dependencia

Notas operativas:
- No intentes ajustar la hora del sistema desde la app: requiere privilegios de root. Usa los servicios del sistema (`chrony`/`ntpd`) para mantener la hora.
- Si usas múltiples réplicas, asegúrate de que todas estén sincronizadas para evitar inconsistencias en logs, JWT expirations y auditoría.

