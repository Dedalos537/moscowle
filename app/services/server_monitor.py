"""Estado del servidor para el panel del administrador. SOLO LECTURA.

Lee métricas de `/proc` y del sistema de archivos, y el estado de una lista FIJA de servicios con
`systemctl is-active` (sin argumentos que vengan del usuario). No ejecuta acciones sobre el sistema: para
administrar el servidor está Cockpit, que tiene su propio inicio de sesión.
"""

import logging
import os
import shutil
import subprocess
import time
from datetime import UTC, datetime, timedelta

from flask import current_app

from app.extensions import db

logger = logging.getLogger(__name__)

# Servicios que la app necesita (nombre de la unidad systemd → etiqueta legible).
SERVICES = {
    'moscowle': 'Backend (Flask)',
    'nginx': 'Servidor web (nginx)',
    'cups': 'Impresión (CUPS)',
    'mysql': 'Base de datos (MySQL)',
    'cloudflared': 'Túnel Cloudflare',
    'ollama': 'IA local (Ollama)',
}
RETENTION_DAYS = 7


def _now():
    return datetime.now(UTC).replace(tzinfo=None)


def _read(path):
    try:
        with open(path) as fh:
            return fh.read()
    except OSError:
        return ''


def _cpu_times():
    line = _read('/proc/stat').splitlines()[0] if _read('/proc/stat') else ''
    parts = [int(x) for x in line.split()[1:]] if line.startswith('cpu ') else []
    if len(parts) < 4:
        return None
    idle = parts[3] + (parts[4] if len(parts) > 4 else 0)
    return idle, sum(parts)


def cpu_percent(interval=0.25):
    a = _cpu_times()
    if a is None:
        return None
    time.sleep(interval)
    b = _cpu_times()
    if b is None or b[1] == a[1]:
        return None
    return round(100.0 * (1 - (b[0] - a[0]) / (b[1] - a[1])), 1)


def memory():
    info = {}
    for line in _read('/proc/meminfo').splitlines():
        key, _, rest = line.partition(':')
        try:
            info[key] = int(rest.strip().split()[0]) * 1024
        except (ValueError, IndexError):
            continue
    total, avail = info.get('MemTotal'), info.get('MemAvailable')
    if not total or avail is None:
        return None
    swap_total, swap_free = info.get('SwapTotal', 0), info.get('SwapFree', 0)
    return {
        'total': total,
        'used': total - avail,
        'pct': round(100.0 * (total - avail) / total, 1),
        'swap_total': swap_total,
        'swap_used': swap_total - swap_free,
    }


def disks():
    out = []
    seen = set()
    for label, path in (('Sistema', '/'), ('Drive', current_app.config.get('DRIVE_ROOT') or current_app.instance_path)):
        try:
            usage = shutil.disk_usage(path)
        except OSError:
            continue
        key = (usage.total, usage.free)
        if key in seen:
            continue
        seen.add(key)
        out.append(
            {
                'label': label,
                'total': usage.total,
                'used': usage.used,
                'pct': round(100.0 * usage.used / usage.total, 1),
            }
        )
    return out


def uptime_seconds():
    raw = _read('/proc/uptime').split()
    return int(float(raw[0])) if raw else None


def app_process():
    status = _read(f'/proc/{os.getpid()}/status')
    rss = next((int(line.split()[1]) * 1024 for line in status.splitlines() if line.startswith('VmRSS:')), None)
    threads = next((int(line.split()[1]) for line in status.splitlines() if line.startswith('Threads:')), None)
    return {'pid': os.getpid(), 'rss': rss, 'threads': threads}


def services():
    systemctl = shutil.which('systemctl')
    result = []
    for unit, label in SERVICES.items():
        state = 'unknown'
        if systemctl:
            try:
                proc = subprocess.run(  # noqa: S603 - binario resuelto con which y unidad de una lista fija
                    [systemctl, 'is-active', unit], capture_output=True, text=True, timeout=5, check=False
                )
                state = (proc.stdout or '').strip() or 'unknown'
            except Exception:
                state = 'unknown'
        result.append({'unit': unit, 'label': label, 'state': state})
    return result


def app_checks():
    """Piezas de la app: base de datos, WhatsApp, Telegram, correo y SMS."""
    checks = []
    try:
        db.session.execute(db.text('SELECT 1'))
        checks.append({'name': 'Base de datos', 'ok': True, 'detail': 'Responde'})
    except Exception as exc:
        db.session.rollback()
        checks.append({'name': 'Base de datos', 'ok': False, 'detail': str(exc)[:120]})
    try:
        from app.services.whatsapp_service import whatsapp_service

        st = whatsapp_service.status()
        checks.append(
            {
                'name': 'WhatsApp',
                'ok': bool(st.get('connected')),
                'detail': 'Conectado' if st.get('connected') else 'Sin conexión',
            }
        )
    except Exception:
        checks.append({'name': 'WhatsApp', 'ok': False, 'detail': 'No disponible'})
    cfg = current_app.config
    checks.append(
        {
            'name': 'Telegram',
            'ok': bool(cfg.get('TELEGRAM_BOT_TOKEN')),
            'detail': 'Configurado' if cfg.get('TELEGRAM_BOT_TOKEN') else 'Sin token',
        }
    )
    mail_ok = bool(cfg.get('MAIL_USERNAME') and cfg.get('MAIL_PASSWORD'))
    checks.append({'name': 'Correo', 'ok': mail_ok, 'detail': 'Configurado' if mail_ok else 'Sin cuenta'})
    sms_ok = bool(os.getenv('SMS_GATEWAY_TOKEN'))
    checks.append({'name': 'SMS', 'ok': sms_ok, 'detail': 'Configurado' if sms_ok else 'Sin token'})
    return checks


def snapshot_now():
    """Estado completo en este momento."""
    load = _read('/proc/loadavg').split()
    return {
        'at': _now().isoformat() + 'Z',
        'host': os.uname().nodename,
        'cpu': {'pct': cpu_percent(), 'cores': os.cpu_count(), 'load': [float(x) for x in load[:3]] if load else None},
        'memory': memory(),
        'disks': disks(),
        'uptime': uptime_seconds(),
        'process': app_process(),
        'services': services(),
        'checks': app_checks(),
        'cockpit_url': current_app.config.get('COCKPIT_URL') or None,
    }


def record():
    """Guarda una foto en la BD y borra las de más de 7 días (lo llama el scheduler)."""
    from app.models.server_snapshot import ServerSnapshot

    data = snapshot_now()
    mem, disk = data['memory'] or {}, (data['disks'] or [{}])[0]
    down = [s['unit'] for s in data['services'] if s['state'] not in ('active', 'unknown')]
    db.session.add(
        ServerSnapshot(
            cpu_pct=data['cpu']['pct'],
            load1=(data['cpu']['load'] or [None])[0],
            mem_pct=mem.get('pct'),
            disk_pct=disk.get('pct'),
            app_rss_mb=round(data['process']['rss'] / 1024**2, 1) if data['process']['rss'] else None,
            services_down=','.join(down)[:255] or None,
        )
    )
    ServerSnapshot.query.filter(ServerSnapshot.taken_at < _now() - timedelta(days=RETENTION_DAYS)).delete()
    db.session.commit()


def history(hours=24):
    from app.models.server_snapshot import ServerSnapshot

    hours = max(1, min(int(hours), 24 * RETENTION_DAYS))
    rows = (
        ServerSnapshot.query.filter(ServerSnapshot.taken_at >= _now() - timedelta(hours=hours))
        .order_by(ServerSnapshot.taken_at.asc())
        .limit(2100)
        .all()
    )
    return [r.to_dict() for r in rows]
