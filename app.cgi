#!/usr/bin/python3
"""Relay CGI fino -> gunicorn persistente (127.0.0.1:8765).

mod_proxy [P] NO esta disponible en este hosting (Apache responde 500
"proxy flag requires mod_proxy"), asi que Apache rutea a este script
(mod_cgi, que SI funciona) y este reenvia a la app persistente.

Ventajas vs el app.cgi antiguo (que booteaba Flask por request):
  - No importa Flask ni nada de la app: solo stdlib (http.client).
  - Boot por request ~50-150ms en vez de ~6s.
  - El servidor persistente ya tiene el pool de DB, cache, socketio y SSE.

Protocolo CGI: env vars HTTP_* + PATH_INFO + QUERY_STRING + body en stdin;
la respuesta va a stdout con "Status: N reason" y luego las cabeceras.
Se reenvian X-Forwarded-* para que ProxyFix (server_local.py) genere URLs
externas correctas y preserve la IP real del cliente.
"""
import http.client
import os
import socket
import subprocess
import sys
import time

UPSTREAM_HOST = '127.0.0.1'
UPSTREAM_PORT = int(os.environ.get('UPSTREAM_PORT', '8765'))
TIMEOUT = 600  # SSE / LLM largos
PUBLIC_HOST = 'backend.centrojuanpabloii.com'

# Headers hop-by-hop que no deben reenviarse
HOP_BY_HOP = {
    'connection', 'keep-alive', 'proxy-authenticate', 'proxy-authorization',
    'te', 'trailer', 'transfer-encoding', 'upgrade',
}

# ── Server control paths (bypass Gunicorn) ──
RESTART_PATH = '/api/server/restart'
STATUS_PATH = '/api/server/status'
RESTART_SECRET = os.environ.get('RESTART_SECRET', 'moscowle-restart-2026')
BASE = '/home/centroju/moscowle'
PY = '/home/centroju/virtualenv/moscowle/3.11/bin/python'
PORT = 8765


def _write(data: bytes):
    sys.stdout.buffer.write(data)
    sys.stdout.buffer.flush()


def _json_response(status_code, body_dict):
    """Write a JSON CGI response."""
    import json
    payload = json.dumps(body_dict).encode('utf-8')
    reason = {200: 'OK', 403: 'Forbidden', 502: 'Bad Gateway'}.get(status_code, 'OK')
    _write(('Status: %d %s\r\n' % (status_code, reason)).encode('latin1'))
    _write(('Content-Type: application/json; charset=utf-8\r\n').encode('latin1'))
    _write(('Content-Length: %d\r\n' % len(payload)).encode('latin1'))
    _write(b'Access-Control-Allow-Origin: https://moscowle.centrojuanpabloii.com\r\n')
    _write(b'Access-Control-Allow-Credentials: true\r\n')
    _write(b'Access-Control-Allow-Methods: GET, POST, OPTIONS\r\n')
    _write(b'Access-Control-Allow-Headers: Content-Type, Authorization, X-Restart-Secret\r\n')
    _write(b'\r\n')
    _write(payload)


def _server_alive():
    try:
        s = socket.create_connection((UPSTREAM_HOST, PORT), timeout=3)
        s.close()
        return True
    except Exception:
        return False


def _restart_server():
    """Kill old gunicorn, start fresh via ensure_local pattern."""
    try:
        subprocess.call(
            ['pkill', '-f', 'gunicorn.*8765'],
            stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL
        )
    except Exception:
        pass
    time.sleep(1)

    logs = os.path.join(BASE, 'logs')
    os.makedirs(logs, exist_ok=True)

    _clean_env = {k: v for k, v in os.environ.items() if not k.startswith('HTTP_')}
    for _v in ('SCRIPT_NAME', 'SCRIPT_FILENAME', 'SCRIPT_URL', 'REDIRECT_URL',
               'REQUEST_METHOD', 'QUERY_STRING', 'REDIRECT_STATUS'):
        _clean_env.pop(_v, None)

    with open(os.path.join(logs, 'local_server.log'), 'ab') as f:
        p = subprocess.Popen(
            [PY, '-m', 'gunicorn',
             '--worker-class', 'eventlet',
             '--workers', '1',
             '--bind', '127.0.0.1:%d' % PORT,
             '--timeout', '300',
             '--graceful-timeout', '30',
             '--max-requests', '1000',
             '--max-requests-jitter', '200',
             '--access-logformat', '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(M)s',
             '--error-logfile', os.path.join(logs, 'gunicorn_err.log'),
             '--access-logfile', os.path.join(logs, 'gunicorn_acc.log'),
             'server_local:application'],
            cwd=BASE,
            stdin=subprocess.DEVNULL,
            stdout=f,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            env=_clean_env,
        )

    # Wait up to 30s for startup
    for _ in range(30):
        if _server_alive():
            return True
        time.sleep(1)
    return False


def main():
    method = os.environ.get('REQUEST_METHOD', 'GET') or 'GET'
    path_info = os.environ.get('PATH_INFO', '') or '/'
    if not path_info.startswith('/'):
        path_info = '/' + path_info
    query = os.environ.get('QUERY_STRING', '') or ''
    path = path_info + ('?' + query if query else '')

    # ── Server control endpoints (no Gunicorn needed) ──
    # Handle OPTIONS preflight for CORS
    if path_info in (RESTART_PATH, STATUS_PATH) and method == 'OPTIONS':
        _json_response(200, {'status': 'ok'})
        return

    if path_info == RESTART_PATH and method == 'POST':
        # Verify secret token from header
        secret = os.environ.get('HTTP_X_RESTART_SECRET', '')
        if secret != RESTART_SECRET:
            _json_response(403, {'error': 'Invalid secret'})
            return
        alive_before = _server_alive()
        if alive_before:
            _json_response(200, {'status': 'already_running', 'message': 'Backend ya está activo'})
            return
        started = _restart_server()
        if started:
            _json_response(200, {'status': 'started', 'message': 'Backend iniciado correctamente'})
        else:
            _json_response(502, {'status': 'failed', 'message': 'No se pudo iniciar el backend en 30s'})
        return

    if path_info == STATUS_PATH and method == 'GET':
        alive = _server_alive()
        _json_response(200, {
            'status': 'running' if alive else 'stopped',
            'host': UPSTREAM_HOST,
            'port': PORT,
        })
        return

    # ── Normal relay to Gunicorn ──
    # Cabeceras desde el entorno CGI (HTTP_*)
    headers = {}
    for key, value in os.environ.items():
        if key.startswith('HTTP_'):
            hname = key[5:].replace('_', '-')
            headers[hname] = value

    ctype = os.environ.get('CONTENT_TYPE')
    if ctype:
        headers['Content-Type'] = ctype

    length = int(os.environ.get('CONTENT_LENGTH') or 0)
    body = sys.stdin.buffer.read(length) if length > 0 else None

    # Headers X-Forwarded para ProxyFix
    scheme = 'https'
    if os.environ.get('HTTPS') not in ('on', '1', 'yes') and os.environ.get('SERVER_PORT') != '443':
        scheme = 'http'
    headers['X-Forwarded-For'] = os.environ.get('REMOTE_ADDR', '')
    headers['X-Forwarded-Proto'] = scheme
    headers['X-Forwarded-Host'] = os.environ.get('HTTP_HOST', PUBLIC_HOST)
    # Host = dominio publico para url_for/_external correctos
    headers['Host'] = PUBLIC_HOST
    headers.pop('Connection', None)
    headers.pop('Proxy-Connection', None)

    conn = http.client.HTTPConnection(UPSTREAM_HOST, UPSTREAM_PORT, timeout=TIMEOUT)
    try:
        conn.request(method, path, body=body, headers=headers)
        resp = conn.getresponse()
    except Exception as e:  # servidor persistente caido
        _write(b'Status: 502 Bad Gateway\r\nContent-Type: text/plain; charset=utf-8\r\n\r\n')
        _write(('Upstream (127.0.0.1:%d) no disponible: %r' % (UPSTREAM_PORT, e)).encode('utf-8'))
        return

    reason = resp.reason or ''
    _write(('Status: %d %s\r\n' % (resp.status, reason)).encode('latin1'))

    for k, v in resp.getheaders():
        if k.lower() in HOP_BY_HOP:
            continue
        # Proteger contra header injection
        if '\r' in k or '\n' in k or '\r' in v or '\n' in v:
            continue
        _write(('%s: %s\r\n' % (k, v)).encode('latin1'))
    _write(b'\r\n')

    # Stream del body (clave para SSE /mcp/chat/stream)
    while True:
        chunk = resp.read(65536)
        if not chunk:
            break
        _write(chunk)

    conn.close()
    sys.stdout.buffer.flush()
    os._exit(0)


if __name__ == '__main__':
    main()
