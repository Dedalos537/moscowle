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
import ipaddress
import json
import os
import re
import socket
import subprocess
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BIND = os.environ.get('SCAND_BIND', '192.168.122.1')
PORT = int(os.environ.get('SCAND_PORT', '8631'))
TOKEN = os.environ.get('SCAND_TOKEN', '')
FIXED_DEVICE = os.environ.get('SCAN_DEVICE', '').strip()
RESOLUTIONS = (150, 200, 300, 600)
PRINTER = os.environ.get('PRINTER_NAME', 'Epson_L4150')
_SAFE_PRINTER = re.compile(r'^[A-Za-z0-9_.@-]{1,127}$')
WATCH_EVERY = int(os.environ.get('PRINTER_WATCH_SECONDS', '600'))
# Identidad de la Epson (MAC, nombre mDNS, última IP): sobrevive a reinicios (StateDirectory del servicio).
STATE_DIR = os.environ.get('STATE_DIRECTORY') or os.environ.get('SCAND_STATE_DIR', '/var/lib/moscowle-scand')
IDENTITY_FILE = os.path.join(STATE_DIR, 'epson.json')
# Servicios del host que se abren desde el Monitor: puerto y esquema (se comprueban en el momento).
HOST_SERVICES = {'cockpit': (9090, 'https'), 'grafana': (3000, 'http'), 'app': (80, 'http')}
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
        out = subprocess.run(['scanimage', '-L'], capture_output=True, text=True, timeout=40, check=False).stdout  # noqa: S603, S607 - comandos fijos del sistema (sane/cups), sin entrada libre
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
    res = subprocess.run(cmd, capture_output=True, timeout=180, check=False)  # noqa: S603, S607 - comandos fijos del sistema (sane/cups), sin entrada libre
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
        out = subprocess.run(['lpstat', '-v', PRINTER], capture_output=True, text=True, timeout=15, check=False).stdout  # noqa: S603, S607 - comandos fijos del sistema (sane/cups), sin entrada libre
    except (OSError, subprocess.TimeoutExpired):
        return None
    m = re.search(r':\s*(\S+)\s*$', out.strip())
    return m.group(1) if m else None


def _ip_of(uri):
    m = re.search(r'//(\d{1,3}(?:\.\d{1,3}){3})', uri or '')
    return m.group(1) if m else None


def _lan_ip():
    """IP actual del host en la LAN (la de la ruta por defecto). La pone el router por DHCP y puede cambiar."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(('1.1.1.1', 80))  # UDP: no envía nada, solo elige la interfaz de salida
            return s.getsockname()[0]
    except OSError:
        return None


def _lan_network():
    """Red /24 de la LAN del host, p. ej. 192.168.1.0/24."""
    ip = _lan_ip()
    return ipaddress.ip_network(f'{ip}/24', strict=False) if ip else None


def _load_identity():
    try:
        with open(IDENTITY_FILE, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _save_identity(data):
    try:
        os.makedirs(STATE_DIR, exist_ok=True)
        tmp = IDENTITY_FILE + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(data, f)
        os.replace(tmp, IDENTITY_FILE)
    except OSError as exc:
        print(f'no se pudo guardar la identidad de la Epson: {exc}', flush=True)


def _mac_of(ip):
    """MAC de una IP de la LAN según la tabla de vecinos (se llena al conectarse, p. ej. en el barrido)."""
    try:
        out = subprocess.run(['ip', 'neigh', 'show', ip], capture_output=True, text=True, timeout=5, check=False).stdout  # noqa: S603, S607 - comando fijo del sistema
    except (OSError, subprocess.TimeoutExpired):
        return None
    m = re.search(r'lladdr ([0-9a-f]{2}(?::[0-9a-f]{2}){5})', out.lower())
    return m.group(1) if m else None


def _mdns_epsons():
    """Epson que se anuncian por mDNS con impresión directa (puerto 9100): [(nombre, host.local, ip)]."""
    try:
        out = subprocess.run(  # noqa: S603 - comando fijo del sistema
            ['avahi-browse', '-rpt', '_pdl-datastream._tcp'],  # noqa: S607
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        ).stdout
    except (OSError, subprocess.TimeoutExpired):
        return []
    found = []
    for line in out.splitlines():
        parts = line.split(';')
        # =;iface;IPv4;nombre;tipo;dominio;host.local;ip;puerto;txt
        if len(parts) >= 9 and parts[0] == '=' and parts[2] == 'IPv4' and 'epson' in parts[3].lower():
            found.append((parts[3].replace('\\032', ' '), parts[6], parts[7]))
    return found


def _is_epson(ip):
    """La Epson responde su página de configuración web con «EPSON» en el contenido."""
    try:
        with urllib.request.urlopen(f'http://{ip}/', timeout=2) as resp:  # noqa: S310 - IP de la LAN
            return b'epson' in resp.read(65536).lower()
    except Exception:  # noqa: BLE001 - cualquier fallo: no es la Epson
        return False


def _sweep_9100():
    """IPs de la LAN que aceptan impresión directa (puerto 9100), probadas en paralelo (~3 s)."""
    net = _lan_network()
    if net is None:
        return []
    hosts = [str(h) for h in net.hosts()]
    with ThreadPoolExecutor(max_workers=64) as pool:
        return [ip for ip, ok in zip(hosts, pool.map(lambda h: _reachable(h, timeout=0.6), hosts), strict=True) if ok]


def _found(ip, via, mdns=None):
    ident = _load_identity()
    return {'ip': ip, 'mac': _mac_of(ip) or ident.get('mac'), 'mdns': mdns or ident.get('mdns'), 'via': via}


def discover():
    """Dónde está la Epson ahora. Por quién es, no por su IP: mDNS → su MAC guardada → su página web → SANE."""
    ident = _load_identity()
    known_mac = ident.get('mac')
    for _name, host, ip in _mdns_epsons():
        mac = _mac_of(ip)
        if known_mac and mac and mac != known_mac:
            continue  # otra Epson en la red: no es la nuestra
        return _found(ip, 'mdns', host)
    candidates = _sweep_9100()
    if known_mac:
        for ip in candidates:
            if _mac_of(ip) == known_mac:
                return _found(ip, 'mac')
    for ip in candidates:
        if _is_epson(ip):
            return _found(ip, 'web')
    if len(candidates) == 1:
        return _found(candidates[0], 'unica')
    for dev in devices(force=True):
        m = _IP_RE.search(dev['name'] + ' ' + dev['label'])
        if m and 'epson' in (dev['name'] + dev['label']).lower():
            return _found(m.group(1), 'sane')
    return None


def discover_ip():
    found = discover()
    return found['ip'] if found else None


def _resolves(host):
    try:
        socket.gethostbyname(host)
        return True
    except OSError:
        return False


def _host_of(uri):
    m = re.search(r'//([^:/]+)', uri or '')
    return m.group(1) if m else None


def printer_info():
    uri = printer_uri()
    host = _host_of(uri)
    ident = _load_identity()
    return {
        'name': PRINTER,
        'uri': uri,
        'ip': _ip_of(uri) or ident.get('ip'),
        'host': host,
        'by_name': bool(host and not _ip_of(uri)),
        'reachable': bool(host and _reachable(host)),
        'mac': ident.get('mac'),
        'mdns': ident.get('mdns'),
        'last_change': ident.get('last_change'),
    }


def _point_cups(uri):
    for cmd in (['lpadmin', '-p', PRINTER, '-v', uri], ['cupsenable', PRINTER], ['cupsaccept', PRINTER]):
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=False)  # noqa: S603, S607 - comandos fijos de CUPS
        if res.returncode != 0:
            raise RuntimeError(f'CUPS no aceptó el cambio ({(res.stderr or res.stdout).strip()[:160]}).')


def repair_printer(wait=0):
    """Encuentra la Epson por quién es y deja CUPS apuntando a ella (por nombre si se puede), y el escáner igual.

    `wait`: segundos que se espera si el vigilante ya está en eso.
    """
    if not _SAFE_PRINTER.match(PRINTER):
        raise RuntimeError('Nombre de impresora no válido.')
    got = _printer_lock.acquire(timeout=wait) if wait else _printer_lock.acquire(blocking=False)
    if not got:
        raise BusyError('Ya estoy reconectando la impresora: espera unos segundos y vuelve a intentar.')
    try:
        before = printer_info()
        ident = _load_identity()
        if not ident.get('mdns') and before['ip']:
            # Aprende su nombre .local aunque nunca se haya perdido, para dejar CUPS apuntando por nombre.
            ident['mdns'] = next((h for _n, h, mip in _mdns_epsons() if mip == before['ip']), None)
        named = ident.get('mdns') and _resolves(ident['mdns'])
        if before['reachable'] and (before['by_name'] or not named):
            return {
                **before,
                'changed': False,
                'message': 'La impresora y el escáner ya responden: no hacía falta cambiar nada.',
            }
        found = None if before['reachable'] else discover()
        if before['reachable']:
            found = {'ip': before['ip'], 'mac': _mac_of(before['ip']) or ident.get('mac'), 'mdns': ident.get('mdns')}
        if not found:
            net = _lan_network()
            raise RuntimeError(
                f'La Epson no está en la red del centro ({net or "LAN"}): se desconectó del WiFi. En la impresora '
                'presiona el botón de Wi-Fi (o imprime la hoja de estado de red) y vuelve a conectarla; '
                'luego reintenta.'
            )
        ip = found['ip']
        if not _reachable(ip):
            raise RuntimeError(f'La Epson aparece en {ip} pero no acepta trabajos en el puerto 9100.')
        # Por nombre (mDNS) CUPS la vuelve a encontrar en cada trabajo aunque cambie de IP; si el host no resuelve
        # .local, queda por IP y el vigilante la repunta.
        target = found.get('mdns') if found.get('mdns') and _resolves(found['mdns']) else ip
        uri = f'socket://{target}:9100'
        if uri != before['uri']:
            _point_cups(uri)
        _cache['at'] = 0.0  # el escáner es el mismo equipo: que lo vuelva a buscar en su nueva dirección
        change = None
        if before['ip'] and before['ip'] != ip:
            change = {'from': before['ip'], 'to': ip, 'at': time.time()}
        _save_identity(
            {
                **ident,
                'ip': ip,
                'mac': found.get('mac') or ident.get('mac'),
                'mdns': found.get('mdns') or ident.get('mdns'),
                'last_change': change or ident.get('last_change'),
            }
        )
        print(f'impresora {PRINTER}: {before["uri"]} → {uri}', flush=True)
        where = f'{found["mdns"]} ({ip})' if target != ip else ip
        return {
            **printer_info(),
            'changed': True,
            'old_uri': before['uri'],
            'message': f'Impresora y escáner reconectados en {where}.',
        }
    finally:
        _printer_lock.release()


def where():
    """Dónde está todo ahora: IP del host en la LAN, su nombre .local, servicios y la Epson."""
    ip = _lan_ip()
    host = socket.gethostname()
    services = {
        name: {'port': port, 'scheme': scheme, 'up': bool(ip and _reachable(ip, port, timeout=1))}
        for name, (port, scheme) in HOST_SERVICES.items()
    }
    return {
        'host': {'lan_ip': ip, 'mdns': f'{host}.local', 'name': host},
        'services': services,
        'epson': printer_info(),
    }


class BusyError(RuntimeError):
    pass


def _watch_printer():
    """Cada WATCH_EVERY: si la Epson no responde (o aún va por IP y ya se puede por nombre), la reconecta."""
    while True:
        time.sleep(WATCH_EVERY)
        try:
            info = printer_info()
            if not info['reachable'] or not info['by_name']:
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
        if self.path == '/where':
            return self._json(200, where())
        return self._json(404, {'error': 'ruta'})

    def do_POST(self):  # noqa: N802
        if not self._authorized():
            return self._json(401, {'error': 'token'})
        if self.path == '/printer/repair':
            try:
                return self._json(200, repair_printer(wait=20))
            except BusyError as exc:
                return self._json(409, {'error': str(exc)})
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
