#!/home/centroju/virtualenv/moscowle/3.11/bin/python
"""Servidor persistente local del backend Moscowle — alcanzado por Apache.

backend.centrojuanpabloii.com --[mod_cgi app.cgi relay]--> 127.0.0.1:8765 (este proceso)

mod_proxy [P] NO existe en este hosting (Apache 500), asi que el relay
app.cgi (stdlib, boot ~50-150ms) reenvia cada request a este proceso.

Un solo boot -> respuestas en ms. Sirve HTTP + Socket.IO websocket (eventlet) —
la MISMA config que corria en Railway: gunicorn --worker-class eventlet
--workers 1 (ver Dockerfile).

Arranque (lo hace ensure_local.py):
    gunicorn -k eventlet -w 1 -b 127.0.0.1:8765 server_local:application
"""

import eventlet

eventlet.monkey_patch()  # antes de importar la app (igual que server.py)

import logging
import os
import sys

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

BASE = '/home/centroju/moscowle'
if BASE not in sys.path:
    sys.path.insert(0, BASE)
site = os.path.join('/home/centroju/virtualenv/moscowle/3.11', 'lib', 'python3.11', 'site-packages')
if os.path.isdir(site) and site not in sys.path:
    sys.path.insert(0, site)

try:
    from dotenv import load_dotenv

    load_dotenv(os.path.join(BASE, '.env'), override=False)
except Exception:
    pass

# Modo LEAN: boot ligero (salta flasgger/celery/scheduler APScheduler/ollama/
# sentry/create_all/migraciones). El scheduler pasa a cron, la DB ya existe.
os.environ['MOSCOWLE_LEAN'] = '1'

from app import create_app_lite

application = create_app_lite()

# El relay app.cgi setea X-Forwarded-Proto/Host/For (IP real del cliente).
# Sin ProxyFix los url_for(_external=True) generarian http://127.0.0.1:8765/...
# y el rate-limiter veria 127.0.0.1 para todos.
from werkzeug.middleware.proxy_fix import ProxyFix

application.wsgi_app = ProxyFix(application.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)
