#!/usr/bin/env python3
"""Servicio del host para Moscowle: escaneo y reconexión de la impresora (solo biblioteca estándar).

El backend vive en VM-APP y el escáner (Epson L4150, por WSD/eSCL con sane-airscan) lo ve el host. Este servicio
escucha SOLO en la red interna de libvirt (192.168.122.1) y exige un token: VM-APP le pide una página y recibe un
JPEG. Igual que CUPS para imprimir, pero para escanear.

  GET  /status            → {"devices": [...], "device": "..."}
  POST /scan {resolution, mode} → image/jpeg   (resolution: 150|200|300|600; mode: Color|Gray)
  GET  /printer           → {"name", "uri", "ip", "reachable"}
  POST /printer/repair    → busca la IP actual de la Epson en la red y repunta CUPS (lpadmin), nada más.

La impresora cambia de IP por DHCP y CUPS la seguía buscando en la vieja. Un vigilante revisa cada 10 min que
responda en su puerto 9100 y, si no, la repunta solo. Es una acción fija: no ejecuta comandos que lleguen de fuera.
"""

import hmac
import json
import os
import re
import socket
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BIND = os.environ.get('SCAND_BIND', '192.168.122.1')
PORT = int(os.environ.get('SCAND_PORT', '8631'))
TOKEN = os.environ.get('SCAND_TOKEN', '')
FIXED_DEVICE = os.environ.get('SCAN_DEVICE', '').strip()
RESOLUTIONS = (150, 200, 300, 600)
PRINTER = os.environ.get('PRINTER_NAME', 'Epson_L4150')
_SAFE_PRINTER = re.compile(r'^[A-Za-z0-9_.@-]{1,127}$')
WATCH_EVERY = int(os.environ.get('PRINTER_WATCH_SECONDS', '600'))
MODES = ('Color', 'Gray')
# Tamaños en mm (ancho, alto) que caben en el vidrio de la L4150 (216 × 297 mm). None = todo el vidrio.
SIZES = {
    'full': None,
    'A4': (210, 297),
    'Carta': (216, 279),
    'Oficio': (216, 297),  # el vidrio llega a 297 mm: un oficio (330/356 mm) queda recortado al largo del vidrio
    'A5': (148, 210),
    'B5': (176, 250),
    'A6': (105, 148),
}

_lock = threading.Lock()
_cache = {'at': 0.0, 'devices': []}


def devices(force=False):
    if not force and time.time() - _cache['at'] < 600 and _cache['devices']:
        return _cache['devices']
    try:
        out = subprocess.run(['scanimage', '-L'], capture_output=True, text=True, timeout=40).stdout
    except (OSError, subprocess.TimeoutExpired):
        out = ''
    found = [{'name': m.group(1), 'label': m.group(2)} for m in re.finditer(r"device `([^']+)' is a (.+)", out)]
    _cache.update(at=time.time(), devices=found)
    return found


def pick_device():
    if FIXED_DEVICE:
        return FIXED_DEVICE
    devs = devices() or devices(force=True)
    return devs[0]['name'] if devs else None


def scan(resolution, mode, size='full'):
    dev = pick_device()
    if not dev:
        raise RuntimeError('No se encontró el escáner: revisa que la impresora esté encendida y en la red.')
    cmd = ['scanimage', '-d', dev, '--format=jpeg', '--resolution', str(resolution), '--mode', mode]
    if SIZES.get(size):
        w, h = SIZES[size]
        cmd += ['-l', '0', '-t', '0', '-x', str(w), '-y', str(h)]
    res = subprocess.run(cmd, capture_output=True, timeout=180)
    if res.returncode != 0 or not res.stdout:
        _cache['at'] = 0.0  # la IP del escáner pudo cambiar: se vuelve a buscar
        err = res.stderr.decode('utf-8', 'replace').strip().splitlines()[-1:] or ['sin detalle']
        raise RuntimeError(f'El escáner no respondió ({err[0][:160]}).')
    return res.stdout


# ── impresora: repuntar CUPS cuando la Epson cambia de IP ────────────────────
_IP_RE = re.compile(r'(?:ip=|net:)(\d{1,3}(?:\.\d{1,3}){3})')
_printer_lock = threading.Lock()


def _reachable(ip, port=9100, timeout=3):
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True
    except OSError:
        return False


def printer_uri():
    try:
        out = subprocess.run(['lpstat', '-v', PRINTER], capture_output=True, text=True, timeout=15).stdout
    except (OSError, subprocess.TimeoutExpired):
        return None
    m = re.search(r':\s*(\S+)\s*$', out.strip())
    return m.group(1) if m else None


def _ip_of(uri):
    m = re.search(r'//(\d{1,3}(?:\.\d{1,3}){3})', uri or '')
    return m.group(1) if m else None


def discover_ip():
    """IP actual de la Epson según el descubrimiento de SANE (epsonds/airscan la anuncian)."""
    for dev in devices(force=True):
        m = _IP_RE.search(dev['name'] + ' ' + dev['label'])
        if m and 'epson' in (dev['name'] + dev['label']).lower():
            return m.group(1)
    return None


def printer_info():
    uri = printer_uri()
    ip = _ip_of(uri)
    return {'name': PRINTER, 'uri': uri, 'ip': ip, 'reachable': bool(ip and _reachable(ip))}


def repair_printer():
    if not _SAFE_PRINTER.match(PRINTER):
        raise RuntimeError('Nombre de impresora no válido.')
    with _printer_lock:
        before = printer_info()
        if before['reachable']:
            return {
                **before,
                'changed': False,
                'message': 'La impresora ya responde en su IP: no hacía falta cambiar nada.',
            }
        ip = discover_ip()
        if not ip:
            raise RuntimeError('No encontré la Epson en la red: revisa que esté encendida y conectada al WiFi.')
        if not _reachable(ip):
            raise RuntimeError(f'La Epson aparece en {ip} pero no acepta trabajos en el puerto 9100.')
        uri = f'socket://{ip}:9100'
        for cmd in (['lpadmin', '-p', PRINTER, '-v', uri], ['cupsenable', PRINTER], ['cupsaccept', PRINTER]):
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if res.returncode != 0:
                raise RuntimeError(f'CUPS no aceptó el cambio ({(res.stderr or res.stdout).strip()[:160]}).')
        print(f'impresora {PRINTER}: {before["uri"]} → {uri}', flush=True)
        return {
            **printer_info(),
            'changed': True,
            'old_uri': before['uri'],
            'message': f'Impresora reconectada en {ip}.',
        }


def _watch_printer():
    while True:
        time.sleep(WATCH_EVERY)
        try:
            if not printer_info()['reachable']:
                repair_printer()
        except Exception as exc:  # noqa: BLE001 - el vigilante nunca se cae
            print(f'vigilante de impresora: {exc}', flush=True)


class Handler(BaseHTTPRequestHandler):
    server_version = 'moscowle-scand/1'

    def _authorized(self):
        got = self.headers.get('X-Scan-Token', '')
        return bool(TOKEN) and hmac.compare_digest(got, TOKEN)

    def _json(self, code, data):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802
        if not self._authorized():
            return self._json(401, {'error': 'token'})
        if self.path == '/status':
            devs = devices(force='refresh' in self.headers.get('X-Scan-Refresh', ''))
            return self._json(200, {'devices': devs, 'device': FIXED_DEVICE or (devs[0]['name'] if devs else None)})
        if self.path == '/printer':
            return self._json(200, printer_info())
        return self._json(404, {'error': 'ruta'})

    def do_POST(self):  # noqa: N802
        if not self._authorized():
            return self._json(401, {'error': 'token'})
        if self.path == '/printer/repair':
            try:
                return self._json(200, repair_printer())
            except (RuntimeError, subprocess.TimeoutExpired) as exc:
                return self._json(502, {'error': str(exc)})
        if self.path != '/scan':
            return self._json(404, {'error': 'ruta'})
        length = min(int(self.headers.get('Content-Length') or 0), 4096)
        try:
            opts = json.loads(self.rfile.read(length) or b'{}')
        except ValueError:
            opts = {}
        resolution = int(opts.get('resolution') or 200)
        size = opts.get('size') or 'full'
        mode = opts.get('mode') or 'Color'
        if resolution not in RESOLUTIONS or mode not in MODES or size not in SIZES:
            return self._json(400, {'error': 'Opciones de escaneo no válidas.'})
        if not _lock.acquire(blocking=False):
            return self._json(409, {'error': 'El escáner está ocupado con otra página. Espera unos segundos.'})
        try:
            data = scan(resolution, mode, size)
        except (RuntimeError, subprocess.TimeoutExpired) as exc:
            return self._json(502, {'error': str(exc)})
        finally:
            _lock.release()
        self.send_response(200)
        self.send_header('Content-Type', 'image/jpeg')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):
        print(f'{self.address_string()} {fmt % args}', flush=True)


if __name__ == '__main__':
    if not TOKEN:
        raise SystemExit('Falta SCAND_TOKEN')
    if WATCH_EVERY > 0:
        threading.Thread(target=_watch_printer, daemon=True).start()
    ThreadingHTTPServer((BIND, PORT), Handler).serve_forever()
