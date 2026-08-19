#!/usr/bin/env python3.11
"""Servidor Ubuntu del backend Moscowle — alcanzado directo por Cloudflare Tunnel.

api-centrojuanpabloii.online --> cloudflared --> 127.0.0.1:5000 (este proceso)

Modo FULL (no LEAN): con socketio, ollama, scheduler, todo activo.
"""

import eventlet

eventlet.monkey_patch()

import logging
import os
import sys

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

BASE = '/home/diego/moscowle_ia'
if BASE not in sys.path:
    sys.path.insert(0, BASE)

try:
    from dotenv import load_dotenv

    load_dotenv(os.path.join(BASE, '.env'), override=False)
except Exception:
    pass

os.environ['FLASK_ENV'] = 'production'

from app import create_app

application = create_app()

from werkzeug.middleware.proxy_fix import ProxyFix

application.wsgi_app = ProxyFix(application.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)

if __name__ == '__main__':
    from app.extensions import socketio

    socketio.run(
        application,
        host='127.0.0.1',
        port=5000,
        debug=False,
        use_reloader=False,
        log_output=True,
    )
