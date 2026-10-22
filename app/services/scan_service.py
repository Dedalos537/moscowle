"""Escaneo al drive (Epson L4150 del host) — cliente del servicio `deploy/scanner/moscowle_scand.py`.

El escáner lo ve el host (SANE + airscan, por WSD). VM-APP le pide páginas por HTTP a 192.168.122.1:8631 con un
token (`SCAN_SERVER_URL`, `SCAN_TOKEN`). Las páginas se guardan como borrador en `.uploads/` del drive hasta que
el usuario las junta en un PDF (o guarda la imagen) en la carpeta que eligió; los borradores viejos se limpian solos.
"""

import io
import json
import os
import re
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime
from pathlib import Path

from app.extensions import db
from app.services import drive_service as drive
from app.services.print_service import _gateway

RESOLUTIONS = (150, 200, 300, 600)
MODES = ('Color', 'Gray')
# Mismo catálogo que el servicio del host (deploy/scanner/moscowle_scand.py): caben en el vidrio de la L4150.
SIZES = ('A4', 'Carta', 'Oficio', 'A5', 'B5', 'A6', 'full')
MAX_PAGES = 30
DRAFT_TTL = 6 * 3600
_ID = re.compile(r'^[a-f0-9]{16}$')


class ScanError(drive.DriveError):
    pass


def _server():
    url = (os.environ.get('SCAN_SERVER_URL') or '').rstrip('/')
    if url:
        return url
    gw = _gateway()
    return f'http://{gw}:8631' if gw else ''


def configured():
    return bool(os.environ.get('SCAN_TOKEN') and _server())


def _call(method, path, body=None, timeout=30):
    if not configured():
        raise ScanError('El escáner no está instalado. En el host: setup_scanner.sh (ver deploy/scanner).', 503)
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(  # noqa: S310 - servidor interno configurado por el admin
        _server() + path,
        data=data,
        method=method,
        headers={'X-Scan-Token': os.environ['SCAN_TOKEN'], 'Content-Type': 'application/json'},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            return resp.read(), resp.headers.get('Content-Type', '')
    except urllib.error.HTTPError as exc:
        try:
            msg = json.loads(exc.read() or b'{}').get('error')
        except ValueError:
            msg = None
        raise ScanError(
            msg or f'El servicio de escaneo respondió {exc.code}.', 409 if exc.code == 409 else 502
        ) from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise ScanError(
            'No se pudo conectar con el escáner del host. ¿Está encendido el servicio moscowle-scand?', 503
        ) from exc


def status():
    if not configured():
        return {'available': False, 'devices': [], 'help': 'Falta instalar el servicio de escaneo en el host.'}
    try:
        raw, _ = _call('GET', '/status', timeout=60)
        info = json.loads(raw or b'{}')
    except ScanError as exc:
        return {'available': False, 'devices': [], 'help': str(exc)}
    devs = info.get('devices') or []
    return {
        'available': bool(devs),
        'devices': devs,
        'help': None
        if devs
        else 'El host no encuentra el escáner: revisa que la impresora esté encendida y en la red.',
        'resolutions': list(RESOLUTIONS),
        'modes': list(MODES),
        'sizes': list(SIZES),
    }


_where_cache = {'at': 0.0, 'data': None}
WHERE_TTL = 30


def where(force=False):
    """Dónde está el host y la Epson ahora (lo responde el servicio del host por virbr0, que no cambia de IP).

    None si el servicio no está instalado o no responde: quien llama cae a los nombres .local.
    """
    now = time.time()
    if not force and _where_cache['data'] is not None and now - _where_cache['at'] < WHERE_TTL:
        return _where_cache['data']
    try:
        raw, _ = _call('GET', '/where', timeout=6)
        data = json.loads(raw or b'{}')
    except (ScanError, ValueError):
        data = None
    _where_cache.update(at=now, data=data)
    return data


def printer_state():
    """Estado de la Epson según el host (IP, si responde, último cambio de IP)."""
    try:
        raw, _ = _call('GET', '/printer', timeout=15)
        return json.loads(raw or b'{}')
    except (ScanError, ValueError):
        return None


def repair_printer():
    """Pide al servicio del host que busque la IP actual de la Epson y repunte CUPS (acción fija, sin comandos libres)."""
    # Por debajo del corte del túnel de Cloudflare (~100 s): así llega el error real y no «error de conexión».
    raw, _ = _call('POST', '/printer/repair', {}, timeout=75)
    return json.loads(raw or b'{}')


# ── borradores (páginas escaneadas que aún no se guardan) ────────────────────
def _drafts() -> Path:
    d = drive.root() / '.uploads' / 'scans'
    d.mkdir(parents=True, exist_ok=True)
    return d


def _draft(scan_id) -> Path:
    if not scan_id or not _ID.match(str(scan_id)):
        raise ScanError('Escaneo no válido', 404)
    d = _drafts() / scan_id
    if not d.is_dir():
        raise ScanError('Ese escaneo ya no existe: vuelve a empezar.', 404)
    return d


def _pages(d: Path):
    return sorted(d.glob('page-*.jpg'), key=lambda p: int(p.stem.split('-')[1]))


def cleanup(now=None):
    limit = (now or time.time()) - DRAFT_TTL
    for d in _drafts().iterdir():
        try:
            if d.stat().st_mtime < limit:
                for f in d.iterdir():
                    f.unlink()
                d.rmdir()
        except OSError:
            continue


def scan_page(scan_id=None, resolution=200, mode='Color', size='A4'):
    """Escanea una página y la agrega al borrador (crea uno nuevo si no hay `scan_id`)."""
    resolution = int(resolution or 200)
    size = size or 'A4'
    if resolution not in RESOLUTIONS or mode not in MODES or size not in SIZES:
        raise ScanError('Opciones de escaneo no válidas.', 400)
    if scan_id:
        d = _draft(scan_id)
    else:
        cleanup()
        scan_id = uuid.uuid4().hex[:16]
        d = _drafts() / scan_id
        d.mkdir()
    pages = _pages(d)
    if len(pages) >= MAX_PAGES:
        raise ScanError(f'Máximo {MAX_PAGES} páginas por documento.', 400)
    data, ctype = _call('POST', '/scan', {'resolution': resolution, 'mode': mode, 'size': size}, timeout=200)
    if not data or 'image' not in ctype:
        raise ScanError('El escáner no devolvió una imagen.', 502)
    drive.ensure_space(len(data))
    n = (int(pages[-1].stem.split('-')[1]) + 1) if pages else 1
    (d / f'page-{n}.jpg').write_bytes(data)
    (d / 'meta.json').write_text(json.dumps({'resolution': resolution, 'mode': mode}))
    return describe(scan_id)


def describe(scan_id):
    d = _draft(scan_id)
    return {
        'scan_id': scan_id,
        'pages': [{'n': int(p.stem.split('-')[1]), 'size': p.stat().st_size} for p in _pages(d)],
    }


def page_path(scan_id, n) -> Path:
    p = _draft(scan_id) / f'page-{int(n)}.jpg'
    if not p.is_file():
        raise ScanError('Página no encontrada', 404)
    return p


def remove_page(scan_id, n):
    page_path(scan_id, n).unlink()
    return describe(scan_id)


def discard(scan_id):
    d = _draft(scan_id)
    for f in d.iterdir():
        f.unlink()
    d.rmdir()


def finish(scan_id, folder='', name='', fmt='pdf'):
    """Junta las páginas en un PDF (o guarda la imagen si es una sola y pidió JPG) en la carpeta del drive."""
    from PIL import Image

    d = _draft(scan_id)
    pages = _pages(d)
    if not pages:
        raise ScanError('No hay páginas escaneadas.', 400)
    base = (name or '').strip() or f'Escaneo {datetime.now().strftime("%Y-%m-%d %H.%M")}'
    base = re.sub(r'\.(pdf|jpe?g)$', '', base, flags=re.I)
    if fmt == 'jpg':
        if len(pages) != 1:
            raise ScanError('Para varias páginas guarda en PDF.', 400)
        entry = drive.save_bytes(folder, f'{base}.jpg', pages[0].read_bytes())
    else:
        meta = json.loads((d / 'meta.json').read_text()) if (d / 'meta.json').exists() else {}
        dpi = int(meta.get('resolution') or 200)
        images = [Image.open(p).convert('RGB') for p in pages]
        buf = io.BytesIO()
        images[0].save(buf, 'PDF', save_all=True, append_images=images[1:], resolution=float(dpi))
        for im in images:
            im.close()
        entry = drive.save_bytes(folder, f'{base}.pdf', buf.getvalue())
    discard(scan_id)
    return entry


# ── avisos de la impresora a los admins (PRP 014) ────────────────────────────
_CHANGE_KEY = 'printer.last_change_at'
_OFFLINE_KEY = 'printer.offline_notified'


def _setting(key):
    from app.models.system_setting import SystemSetting

    row = db.session.get(SystemSetting, key)
    return row.value if row else None


def _set_setting(key, value):
    from app.models.system_setting import SystemSetting

    row = db.session.get(SystemSetting, key) or SystemSetting(key=key)
    row.value = value
    db.session.add(row)
    db.session.commit()


def _notify_admins(title, message, priority):
    from app.models.user import User
    from app.services.notification_service import NotificationService

    service = NotificationService()
    for admin in User.query.filter_by(role='admin', is_active=True).all():
        service.notify_user(
            user_id=admin.id,
            message=message,
            title=title,
            link='/admin/drive',
            category='system',
            priority=priority,
            icon=['fas', 'print'],
        )


def check_printer():
    """Lo corre el scheduler: avisa una vez cuando la Epson cambió de IP (y ya se reconectó) o se fue del WiFi."""
    if not configured():
        return
    state = printer_state()
    if state is None:
        return
    change = state.get('last_change') or {}
    at = str(change.get('at') or '')
    if at and at != (_setting(_CHANGE_KEY) or ''):
        _set_setting(_CHANGE_KEY, at)
        _notify_admins(
            'La impresora cambió de IP',
            f'La Epson pasó de {change.get("from")} a {change.get("to")}: impresora y escáner ya se reconectaron solos.',
            'normal',
        )
    offline_notified = _setting(_OFFLINE_KEY) == '1'
    if not state.get('reachable') and not offline_notified:
        _set_setting(_OFFLINE_KEY, '1')
        _notify_admins(
            'La impresora no está en la red',
            'La Epson se desconectó del WiFi del centro. En la impresora presiona el botón de Wi-Fi para '
            'reconectarla; luego, en el Drive, «Reconectar impresora y escáner».',
            'high',
        )
    elif state.get('reachable') and offline_notified:
        _set_setting(_OFFLINE_KEY, '0')
