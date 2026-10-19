#!/usr/bin/env python3
"""Servicio de escaneo del host para Moscowle (solo biblioteca estándar).

El backend vive en VM-APP y el escáner (Epson L4150, por WSD/eSCL con sane-airscan) lo ve el host. Este servicio
escucha SOLO en la red interna de libvirt (192.168.122.1) y exige un token: VM-APP le pide una página y recibe un
JPEG. Igual que CUPS para imprimir, pero para escanear.

  GET  /status            → {"devices": [...], "device": "..."}
  POST /scan {resolution, mode} → image/jpeg   (resolution: 150|200|300|600; mode: Color|Gray)
"""

import hmac
import json
import os
import re
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BIND = os.environ.get('SCAND_BIND', '192.168.122.1')
PORT = int(os.environ.get('SCAND_PORT', '8631'))
TOKEN = os.environ.get('SCAND_TOKEN', '')
FIXED_DEVICE = os.environ.get('SCAN_DEVICE', '').strip()
RESOLUTIONS = (150, 200, 300, 600)
MODES = ('Color', 'Gray')

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


def scan(resolution, mode):
    dev = pick_device()
    if not dev:
        raise RuntimeError('No se encontró el escáner: revisa que la impresora esté encendida y en la red.')
    cmd = ['scanimage', '-d', dev, '--format=jpeg', '--resolution', str(resolution), '--mode', mode]
    res = subprocess.run(cmd, capture_output=True, timeout=180)
    if res.returncode != 0 or not res.stdout:
        _cache['at'] = 0.0  # la IP del escáner pudo cambiar: se vuelve a buscar
        err = res.stderr.decode('utf-8', 'replace').strip().splitlines()[-1:] or ['sin detalle']
        raise RuntimeError(f'El escáner no respondió ({err[0][:160]}).')
    return res.stdout


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
        return self._json(404, {'error': 'ruta'})

    def do_POST(self):  # noqa: N802
        if not self._authorized():
            return self._json(401, {'error': 'token'})
        if self.path != '/scan':
            return self._json(404, {'error': 'ruta'})
        length = min(int(self.headers.get('Content-Length') or 0), 4096)
        try:
            opts = json.loads(self.rfile.read(length) or b'{}')
        except ValueError:
            opts = {}
        resolution = int(opts.get('resolution') or 200)
        mode = opts.get('mode') or 'Color'
        if resolution not in RESOLUTIONS or mode not in MODES:
            return self._json(400, {'error': 'Opciones de escaneo no válidas.'})
        if not _lock.acquire(blocking=False):
            return self._json(409, {'error': 'El escáner está ocupado con otra página. Espera unos segundos.'})
        try:
            data = scan(resolution, mode)
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
    ThreadingHTTPServer((BIND, PORT), Handler).serve_forever()
