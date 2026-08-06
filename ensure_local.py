#!/home/centroju/virtualenv/moscowle/3.11/bin/python
"""Guardian del servidor local: si 127.0.0.1:8765 esta muerto, lo levanta.

Lo llaman el cron (cada minuto) y ensure.cgi (bajo demanda).
"""

import os
import socket
import subprocess
import sys
import time

BASE = '/home/centroju/moscowle'
PORT = 8765
PY = '/home/centroju/virtualenv/moscowle/3.11/bin/python'
LOGS = os.path.join(BASE, 'logs')


def log(msg):
    try:
        with open(os.path.join(LOGS, 'ensure_local.log'), 'a') as f:
            f.write('%s %s\n' % (time.strftime('%Y-%m-%d %H:%M:%S'), msg))
    except Exception:
        pass


def alive():
    try:
        s = socket.create_connection(('127.0.0.1', PORT), timeout=3)
        s.close()
        return True
    except Exception:
        return False


if alive():
    sys.exit(0)

log('servidor muerto, levantando...')
try:
    subprocess.call(['pkill', '-f', 'gunicorn.*8765'], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
except Exception:
    pass
time.sleep(1)

os.makedirs(LOGS, exist_ok=True)
# Limpiar variables CGI heredadas (SCRIPT_NAME, etc). Si ensure_local.py fue
# lanzado desde un .cgi (restart.cgi/ensure.cgi), el env trae SCRIPT_NAME y
# gunicorn 21 lo usa como prefijo del path -> IndexError en wsgi.create.
# Tambien evitamos que apunte a un script CGI concreto.
_clean_env = {k: v for k, v in os.environ.items() if not k.startswith('HTTP_')}
for _v in (
    'SCRIPT_NAME',
    'SCRIPT_FILENAME',
    'SCRIPT_URL',
    'REDIRECT_URL',
    'REQUEST_METHOD',
    'QUERY_STRING',
    'REDIRECT_STATUS',
):
    _clean_env.pop(_v, None)
with open(os.path.join(LOGS, 'local_server.log'), 'ab') as f:
    # Reciclaje del worker: en hosting compartido (CloudLinux LVE) la memoria
    # del proceso crece con el uso (cache simple, rate-limit memory, SSE) hasta
    # que el host lo mata con SIGKILL. max-requests recicla el worker antes,
    # liberando la memoria acumulada sin downtime visible (graceful).
    # access-logformat con %(M)s (tiempo de proceso en ms) para monitorear.
    p = subprocess.Popen(
        [
            PY,
            '-m',
            'gunicorn',
            '--worker-class',
            'eventlet',
            '--workers',
            '1',
            '--bind',
            '127.0.0.1:%d' % PORT,
            '--timeout',
            '300',
            '--graceful-timeout',
            '30',
            '--max-requests',
            '1000',
            '--max-requests-jitter',
            '200',
            '--access-logformat',
            '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(M)s',
            '--error-logfile',
            os.path.join(LOGS, 'gunicorn_err.log'),
            '--access-logfile',
            os.path.join(LOGS, 'gunicorn_acc.log'),
            'server_local:application',
        ],
        cwd=BASE,
        stdin=subprocess.DEVNULL,
        stdout=f,
        stderr=subprocess.STDOUT,
        start_new_session=True,
        env=_clean_env,
    )
    log('lanzado pid=%d' % p.pid)

for _ in range(60):
    if alive():
        log('escuchando OK en :%d' % PORT)
        sys.exit(0)
    time.sleep(1)
log('NO escucho en 60s — revisar logs/gunicorn_err.log')
