"""Estado del servidor para el panel del administrador. SOLO LECTURA.

Lee métricas de `/proc` y del sistema de archivos, y el estado de una lista FIJA de servicios. No ejecuta
acciones sobre el sistema: para administrar el servidor está Cockpit, que tiene su propio inicio de sesión.

Topología (PRP 006): el backend corre en VM-APP; nginx, CUPS, cloudflared, Ollama y el servicio del escáner viven
en el HOST (192.168.122.1) y MySQL en VM-DB. Antes se preguntaba a `systemctl` de VM-APP por todos y salían
«Detenido» aunque funcionaran. Ahora cada servicio se comprueba donde está, por la red y con tiempos cortos.
"""

import logging
import os
import shutil
import socket
import subprocess
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

from flask import current_app

from app.extensions import db

logger = logging.getLogger(__name__)

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


def _host():
    """El host visto desde VM-APP (puerta de enlace de libvirt); si no se puede leer, la IP LAN del host."""
    from app.services.print_service import _gateway

    return os.environ.get('MONITOR_HOST') or _gateway() or '192.168.1.249'


def _tcp(host, port, timeout=2.0):
    with socket.create_connection((host, int(port)), timeout=timeout):
        return True


def _http(url, timeout=4.0):
    # User-Agent de navegador: Cloudflare filtra con 403 los agentes «raros» (pasaba con la sonda del túnel).
    req = urllib.request.Request(  # noqa: S310 - URLs fijas
        url, headers={'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) MoscowleMonitor/1.0', 'Accept': '*/*'}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - URLs fijas internas
            return resp.status
    except urllib.error.HTTPError as exc:
        return exc.code


def _systemd(unit):
    systemctl = shutil.which('systemctl')
    if not systemctl:
        return None
    proc = subprocess.run(  # noqa: S603 - binario resuelto con which y unidad de una lista fija
        [systemctl, 'is-active', unit], capture_output=True, text=True, timeout=5, check=False
    )
    return (proc.stdout or '').strip() or 'unknown'


def _check_backend():
    state = _systemd('moscowle')
    # Si systemd no responde, este mismo proceso es la prueba de que el backend está arriba.
    return ('active' if state in (None, 'unknown') else state), f'PID {os.getpid()}'


def _check_nginx():
    host = _host()
    for target in (host, os.environ.get('HOST_LAN_IP', '192.168.1.249')):
        try:
            code = _http(f'http://{target}/app/', timeout=3)
            return ('active' if code < 500 else 'failed'), f'{target}:80 → HTTP {code}'
        except Exception as exc:  # noqa: BLE001 - se prueba la siguiente dirección del host
            logger.debug('nginx no responde en %s: %s', target, exc)
    return 'inactive', f'{host}:80 sin respuesta'


def _check_cups():
    host = _host()
    try:
        _tcp(host, 631)
        return 'active', f'{host}:631'
    except Exception:
        return 'inactive', f'{host}:631 sin respuesta'


def _check_mysql():
    from sqlalchemy.engine import make_url

    try:
        url = make_url(current_app.config.get('SQLALCHEMY_DATABASE_URI') or '')
        where = f'{url.host or "local"}:{url.port or 3306}' if url.drivername.startswith('mysql') else url.drivername
    except Exception:
        where = 'base de datos'
    try:
        db.session.execute(db.text('SELECT 1'))
        return 'active', where
    except Exception as exc:
        db.session.rollback()
        return 'failed', f'{where}: {str(exc)[:80]}'


def _check_tunnel():
    """De ida y vuelta por Cloudflare: si el dominio público devuelve la hora de Moscowle, el túnel funciona.

    Un 403/429 lo pone Cloudflare (no llegó al backend): no prueba que el túnel ande, así que no cuenta como activo.
    """
    base = (current_app.config.get('PUBLIC_API_URL') or 'https://api-centrojuanpabloii.online').rstrip('/')
    try:
        code = _http(base + '/api/time', timeout=6)
    except Exception as exc:
        return 'inactive', f'Sin respuesta pública ({type(exc).__name__})'
    host = base.split('//')[-1]
    if code == 200:
        return 'active', f'{host} → HTTP 200'
    if code in (401, 403, 429):
        return 'degraded', f'{host} → HTTP {code}: Cloudflare filtró la sonda (el sitio puede estar bien)'
    return 'failed', f'{host} → HTTP {code}'


def _check_ollama():
    from app.services.llm_client import _ollama_host

    url = _ollama_host()
    try:
        code = _http(url + '/api/tags', timeout=4)
        return ('active' if code == 200 else 'failed'), url.split('//')[-1]
    except Exception:
        return 'inactive', f'{url.split("//")[-1]} sin respuesta'


def _check_opencode(inst):
    from app.services import opencode_client as oc

    if not oc.configured(inst):
        return 'off', 'No instalado'
    if oc.blocked(inst):
        return 'degraded', 'En pausa (cuota o fallo); vuelve solo'
    return ('active', oc.base_url(inst).split('//')[-1]) if oc.ping(inst) else ('inactive', 'Sin respuesta')


def _check_scand():
    from app.services import scan_service

    if not scan_service.configured():
        return 'off', 'No instalado'
    server = scan_service._server().split('//')[-1]
    host, _, port = server.partition(':')
    try:
        _tcp(host, port or 8631)
        return 'active', server
    except Exception:
        return 'inactive', f'{server} sin respuesta'


# (clave, etiqueta, dónde vive, comprobación). Lista FIJA: nada viene del usuario.
SERVICES = (
    ('moscowle', 'Backend (Flask)', 'VM-APP', _check_backend),
    ('nginx', 'Servidor web (nginx)', 'Host', _check_nginx),
    ('cups', 'Impresión (CUPS)', 'Host', _check_cups),
    ('mysql', 'Base de datos (MySQL)', 'VM-DB', _check_mysql),
    ('cloudflared', 'Túnel Cloudflare', 'Host', _check_tunnel),
    ('ollama', 'IA local (Ollama)', 'Host', _check_ollama),
    ('opencode', 'Asistente MiMo (opencode)', 'VM-APP', lambda: _check_opencode('chat')),
    ('opencode-dev', 'Modo desarrollador (opencode)', 'VM-APP', lambda: _check_opencode('dev')),
    ('moscowle-scand', 'Escáner e impresora (servicio)', 'Host', _check_scand),
)
_CACHE_SECONDS = 30
_cache: dict = {'at': 0.0, 'rows': None}
_cache_lock = threading.Lock()


def services(force=False):
    """Estado de cada servicio comprobado donde vive (en paralelo, con caché de 30 s: el panel pide cada 10 s)."""
    with _cache_lock:
        if not force and _cache['rows'] is not None and time.time() - _cache['at'] < _CACHE_SECONDS:
            return _cache['rows']
    app = current_app._get_current_object()

    def run(item):
        unit, label, where, check = item
        t0 = time.time()
        with app.app_context():
            try:
                state, detail = check()
            except Exception as exc:  # noqa: BLE001 - un servicio que falla no rompe el panel
                state, detail = 'unknown', str(exc)[:80]
        return {
            'unit': unit,
            'label': label,
            'where': where,
            'state': state,
            'detail': detail,
            'ms': int((time.time() - t0) * 1000),
        }

    with ThreadPoolExecutor(max_workers=len(SERVICES)) as pool:
        rows = list(pool.map(run, SERVICES))
    with _cache_lock:
        _cache.update(at=time.time(), rows=rows)
    return rows


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
        'grafana_url': os.environ.get('GRAFANA_URL') or None,
        'history_max_hours': 24 * 30 if prometheus_available() else 24 * RETENTION_DAYS,
    }


def record():
    """Guarda una foto en la BD y borra las de más de 7 días (lo llama el scheduler)."""
    from app.models.server_snapshot import ServerSnapshot

    data = snapshot_now()
    mem, disk = data['memory'] or {}, (data['disks'] or [{}])[0]
    down = [s['unit'] for s in data['services'] if s['state'] not in ('active', 'unknown', 'off', 'degraded')]
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
    """Historial para las gráficas: de Prometheus si está (hasta 30 días); si no, de la tabla local (7 días)."""
    from app.models.server_snapshot import ServerSnapshot

    if prometheus_available():
        try:
            return prometheus_history(max(1, min(int(hours), 24 * 30)))
        except Exception as exc:  # noqa: BLE001 - si Prometheus no responde, se usa la tabla local
            logger.warning('Prometheus no respondió, uso el historial local: %s', exc)
    hours = max(1, min(int(hours), 24 * RETENTION_DAYS))
    rows = (
        ServerSnapshot.query.filter(ServerSnapshot.taken_at >= _now() - timedelta(hours=hours))
        .order_by(ServerSnapshot.taken_at.asc())
        .limit(2100)
        .all()
    )
    return [r.to_dict() for r in rows]


# ── Prometheus (PRP 010) ─────────────────────────────────────────────────────
SEVERITY_ES = {'critical': 'Crítico', 'warning': 'Atención', 'info': 'Aviso'}


def notify_alerts(alerts):
    """Avisos de Alertmanager → notificación a cada admin (y Telegram según sus preferencias)."""
    from app.models import User
    from app.services.notification_service import NotificationService

    admins = [u.id for u in User.query.filter(User.role == 'admin', User.is_active.isnot(False))]
    svc = NotificationService()
    sent = 0
    for alert in alerts[:20]:
        labels = alert.get('labels') or {}
        ann = alert.get('annotations') or {}
        resolved = alert.get('status') == 'resolved'
        severity = labels.get('severity', 'warning')
        title = ('✅ Resuelto: ' if resolved else '🚨 ') + (ann.get('summary') or labels.get('alertname') or 'Alerta')
        body = ann.get('description') or ''
        for uid in admins:
            svc.notify_user(
                uid,
                body or title,
                title=title,
                notif_type='success' if resolved else ('error' if severity == 'critical' else 'warning'),
                link='/admin/settings?section=backend',
                category='system',
                priority='high' if resolved else ('urgent' if severity == 'critical' else 'high'),
                metadata_json={'alertname': labels.get('alertname'), 'severity': severity, 'resolved': resolved},
            )
            sent += 1
    return sent


def _prom_url():
    return (os.environ.get('PROMETHEUS_URL') or '').rstrip('/')


def prometheus_available():
    return bool(_prom_url())


def _prom_range(query, start, end, step):
    import json
    from urllib.parse import urlencode

    url = f'{_prom_url()}/api/v1/query_range?' + urlencode(
        {'query': query, 'start': f'{start:.0f}', 'end': f'{end:.0f}', 'step': f'{step}s'}
    )
    req = urllib.request.Request(url, headers={'User-Agent': 'moscowle-monitor'})  # noqa: S310 - URL interna fija
    with urllib.request.urlopen(req, timeout=8) as resp:  # noqa: S310
        data = json.loads(resp.read())
    return data.get('data', {}).get('result', [])


PROM_QUERIES = {
    'cpu_pct': '100 - avg(rate(node_cpu_seconds_total{mode="idle",instance="vm-app"}[5m])) * 100',
    'mem_pct': '(1 - node_memory_MemAvailable_bytes{instance="vm-app"} / node_memory_MemTotal_bytes{instance="vm-app"}) * 100',
    'disk_pct': '(1 - node_filesystem_avail_bytes{instance="vm-app",mountpoint="/"} '
    '/ node_filesystem_size_bytes{instance="vm-app",mountpoint="/"}) * 100',
    'load1': 'node_load1{instance="vm-app"}',
    'app_rss_mb': 'moscowle_process_resident_memory_bytes / 1048576',
}


def prometheus_history(hours):
    """Mismo formato que `ServerSnapshot.to_dict()`, pero desde Prometheus (hasta 30 días)."""
    end = time.time()
    start = end - hours * 3600
    step = max(60, int(hours * 3600 / 600))  # ~600 puntos por serie
    points: dict = {}
    for key, query in PROM_QUERIES.items():
        for series in _prom_range(query, start, end, step)[:1]:
            for ts, val in series.get('values', []):
                row = points.setdefault(int(float(ts)), {'services_down': []})
                try:
                    row[key] = round(float(val), 1)
                except ValueError:
                    row[key] = None
    for series in _prom_range('probe_success == 0', start, end, step):
        name = (series.get('metric') or {}).get('service') or (series.get('metric') or {}).get('instance', '?')
        for ts, _ in series.get('values', []):
            points.setdefault(int(float(ts)), {'services_down': []})['services_down'].append(name)
    out = []
    for ts in sorted(points):
        row = points[ts]
        out.append(
            {
                'taken_at': datetime.fromtimestamp(ts, UTC).replace(tzinfo=None).isoformat() + 'Z',
                'cpu_pct': row.get('cpu_pct'),
                'load1': row.get('load1'),
                'mem_pct': row.get('mem_pct'),
                'disk_pct': row.get('disk_pct'),
                'app_rss_mb': row.get('app_rss_mb'),
                'services_down': sorted(set(row['services_down'])),
            }
        )
    return out
