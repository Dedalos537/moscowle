"""
WSGI de entrada para cPanel / CloudLinux Python Selector (Passenger).

Arranca la app Flask Moscowle desde el Application root
(/home/centroju/moscowle). Detecta el virtualenv creado por
CloudLinux y, si faltan las dependencias, hace un bootstrap
(una sola vez) con pip para auto-instalar requirements.txt.
"""

import os
import subprocess
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Ruta del virtualenv de CloudLinux (usa ~/virtualenv/<app>/<ver>)
HOME = os.environ.get('HOME', '')
VENV = None
for candidate in (
    os.path.join(HOME, 'virtualenv', 'moscowle', '3.11'),
    '/home/centroju/virtualenv/moscowle/3.11',
):
    if os.path.isdir(candidate):
        VENV = candidate
        break

if VENV:
    site = os.path.join(VENV, 'lib', 'python3.11', 'site-packages')
    if os.path.isdir(site) and site not in sys.path:
        sys.path.insert(0, site)

    # Bootstrap: instalar dependencias si faltan (una sola vez).
    # El primer Restart de cPanel tarda (pip instala); los siguientes van directos.
    if not os.path.exists(os.path.join(site, 'flask')):
        log = os.path.join(BASE_DIR, 'logs', 'bootstrap.log')
        os.makedirs(os.path.dirname(log), exist_ok=True)
        req = os.path.join(BASE_DIR, 'requirements.txt')

        # Wheels offline subidos por FTP (respaldo si PyPI no es alcanzable)
        wh_dir = os.path.join(BASE_DIR, 'wheelhouse')
        wh_tgz = wh_dir + '.tar.gz'
        if os.path.exists(wh_tgz) and not os.path.isdir(wh_dir):
            try:
                import tarfile

                with tarfile.open(wh_tgz) as tf:
                    tf.extractall(BASE_DIR)
            except Exception:
                pass
        install_cmd = [sys.executable, '-m', 'pip', 'install', '--quiet', '-r', req]
        if os.path.isdir(wh_dir):
            install_cmd = [
                sys.executable,
                '-m',
                'pip',
                'install',
                '--quiet',
                '--no-index',
                '--find-links=' + wh_dir,
                '-r',
                req,
            ]

        try:
            with open(log, 'w') as f:
                f.write('Bootstrap iniciado…\n')
                p = subprocess.run(
                    [sys.executable, '-m', 'pip', 'install', '--quiet', '--upgrade', 'pip', 'setuptools', 'wheel'],
                    capture_output=True,
                    text=True,
                    timeout=600,
                )
                f.write('pip upgrade rc=%s\n%s\n%s\n' % (p.returncode, p.stdout, p.stderr))
                p = subprocess.run(
                    install_cmd,
                    capture_output=True,
                    text=True,
                    timeout=1800,
                )
                f.write(
                    'pip install rc=%s (cmd=%s)\n%s\n%s\n' % (p.returncode, ' '.join(install_cmd), p.stdout, p.stderr)
                )
        except Exception as e:
            with open(log, 'a') as f:
                f.write('ERROR: %r\n' % (e,))
            sys.path = [pth for pth in sys.path if pth != site]
            raise
        if p.returncode != 0:
            sys.path = [pth for pth in sys.path if pth != site]
            raise RuntimeError('pip install falló (ver %s)' % log)

# ── Crear la aplicación ──
from app import create_app

application = create_app()

# restart marker
