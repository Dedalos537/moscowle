#!/home/centroju/virtualenv/moscowle/3.11/bin/python
"""Ejecuta una tarea programada por nombre desde cron.

Como el scheduler APScheduler de la app ya NO corre en el servidor persistente
(modo LEAN), el cron llama a este script una vez por job:

    python run_task.py <nombre_de_funcion>

Boote la app en modo lean (sin flasgger/celery/scheduler/ollama/sentry/
create_all), crea el contexto de app, y llama tasks.<nombre>(app).
"""

import os
import sys
import traceback

BASE = '/home/centroju/moscowle'
if BASE not in sys.path:
    sys.path.insert(0, BASE)
site = os.path.join('/home/centroju/virtualenv/moscowle/3.11', 'lib', 'python3.11', 'site-packages')
if os.path.isdir(site) and site not in sys.path:
    sys.path.insert(0, site)

os.environ['FLASK_ENV'] = 'production'
os.environ['MOSCOWLE_LEAN'] = '1'

try:
    from dotenv import load_dotenv

    load_dotenv(os.path.join(BASE, '.env'), override=False)
except Exception:
    pass

from app import create_app, tasks


def main():
    task_name = sys.argv[1] if len(sys.argv) > 1 else ''
    func = getattr(tasks, task_name, None)
    if not func:
        print('Tarea no encontrada: %r' % task_name)
        sys.exit(2)

    app = create_app()
    try:
        with app.app_context():
            func(app)
        print('OK %s' % task_name)
    except Exception:
        print('ERROR en %s' % task_name)
        traceback.print_exc()
        sys.exit(1)
    os._exit(0)


if __name__ == '__main__':
    main()
