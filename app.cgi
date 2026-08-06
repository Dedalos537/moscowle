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
import sys

UPSTREAM_HOST = '127.0.0.1'
UPSTREAM_PORT = int(os.environ.get('UPSTREAM_PORT', '8765'))
TIMEOUT = 600  # SSE / LLM largos
PUBLIC_HOST = 'backend.centrojuanpabloii.com'

# Headers hop-by-hop que no deben reenviarse
HOP_BY_HOP = {
    'connection', 'keep-alive', 'proxy-authenticate', 'proxy-authorization',
    'te', 'trailer', 'transfer-encoding', 'upgrade',
}


def _write(data: bytes):
    sys.stdout.buffer.write(data)
    sys.stdout.buffer.flush()


def main():
    method = os.environ.get('REQUEST_METHOD', 'GET') or 'GET'
    path_info = os.environ.get('PATH_INFO', '') or '/'
    if not path_info.startswith('/'):
        path_info = '/' + path_info
    query = os.environ.get('QUERY_STRING', '') or ''
    path = path_info + ('?' + query if query else '')

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
