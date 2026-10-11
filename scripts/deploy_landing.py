"""Publica la landing (landing/) en centrojuanpabloii.com por FTP.

Uso:
    python scripts/deploy_landing.py --preview --from-ci   # vista previa en centrojuanpabloii.com/nuevo/
    python scripts/deploy_landing.py --root --from-ci      # reemplaza la landing de la raíz del dominio
    python scripts/deploy_landing.py --rollback            # vuelve a poner la landing anterior en la raíz
    --build en vez de --from-ci compila aquí (necesita Node 22).

Sube primero los archivos con hash y al final index.html, que es el que los referencia: si la conexión se corta a
mitad, el sitio sigue sirviendo la versión anterior. En la raíz no borra nada (public_html también aloja el
subdominio de la plataforma y la landing anterior), así que volver atrás es solo restaurar su index.html.

La contraseña FTP sale de FTP_PASS o de .deploy_cpanel.env (ignorado por git), igual que deploy_cpanel.py, y nunca
se imprime.
"""

import contextlib
import ftplib
import io
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import deploy_cpanel as cp  # noqa: E402 - reutiliza credenciales y utilidades FTP

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LANDING_DIR = PROJECT_ROOT / 'landing'
LEGACY_DIR = PROJECT_ROOT / 'backups' / 'landing_legacy_2026-10-10'
REMOTE = {'root': '/public_html', 'preview': '/public_html/nuevo'}
BASE = {'root': '/', 'preview': '/nuevo/'}
ARTIFACT_DIR = {'root': 'landing-root', 'preview': 'landing-preview'}


def fetch_ci(target):
    """Bundle de la landing del último CI exitoso de main (requiere `gh` autenticado)."""
    list_cmd = ['gh', 'run', 'list', '--branch', 'main', '--workflow', 'ci.yml', '--status', 'success']
    list_cmd += ['--limit', '1', '--json', 'databaseId', '-q', '.[0].databaseId']
    run_id = subprocess.run(list_cmd, cwd=PROJECT_ROOT, capture_output=True, text=True, check=True).stdout.strip()  # noqa: S603
    if not run_id:
        raise SystemExit('No hay un CI exitoso en main con la landing.')
    tmp = Path(tempfile.mkdtemp(prefix='landing-'))
    subprocess.run(['gh', 'run', 'download', run_id, '--name', 'landing-cpanel', '--dir', str(tmp)], check=True)  # noqa: S603, S607
    dist = tmp / ARTIFACT_DIR[target]
    print(f'Bundle del CI {run_id}: {dist}')
    return dist


def build_local(target):
    env = {**os.environ, 'LANDING_BASE': BASE[target]}
    subprocess.run(['npm', 'run', 'build'], cwd=LANDING_DIR, env=env, check=True)  # noqa: S603, S607
    out = Path(tempfile.mkdtemp(prefix='landing-')) / 'dist'
    shutil.copytree(LANDING_DIR / 'dist', out)
    return out


def check_bundle(dist, target):
    index = dist / 'index.html'
    if not index.is_file():
        raise SystemExit(f'Falta index.html en {dist}')
    html = index.read_text(encoding='utf-8')
    expected = f'src="{BASE[target]}assets/'
    if expected not in html:
        raise SystemExit(f'El bundle no es para {BASE[target]} (no encuentro {expected}). Compílalo con LANDING_BASE.')


def upload(dist, remote_dir, connect, prune):
    files = sorted(p for p in dist.rglob('*') if p.is_file())
    index = dist / 'index.html'
    ordered = [p for p in files if p != index] + [index]
    state = {'ftp': connect()}

    def put(path):
        rel = path.relative_to(dist).as_posix()
        remote = f'{remote_dir}/{rel}'
        for attempt in range(1, 5):
            try:
                cp.mkdir_p(state['ftp'], remote.rsplit('/', 1)[0])
                with open(path, 'rb') as fh:
                    state['ftp'].storbinary(f'STOR {remote}', fh)
                return
            except Exception as e:  # noqa: BLE001 - reintento con reconexión
                print(f'  reintento {attempt} {rel}: {e}')
                with contextlib.suppress(Exception):
                    state['ftp'].close()
                time.sleep(2 * attempt)
                with contextlib.suppress(Exception):
                    state['ftp'] = connect()
        raise SystemExit(f'No se pudo subir {rel}. index.html no se tocó: el sitio sigue con la versión anterior.')

    for path in ordered:
        put(path)
    print(f'  Subidos {len(ordered)} archivos a {remote_dir}')
    if prune:
        cp.delete_old_hashed_files(state['ftp'], f'{remote_dir}/assets', keep={p.name for p in files})
    with contextlib.suppress(Exception):
        state['ftp'].quit()


def rollback(connect):
    index = LEGACY_DIR / 'index.html'
    if not index.is_file():
        raise SystemExit(f'No encuentro el respaldo en {LEGACY_DIR}')
    ftp = connect()
    ftp.storbinary(f'STOR {REMOTE["root"]}/index.html', io.BytesIO(index.read_bytes()))
    with contextlib.suppress(Exception):
        ftp.quit()
    print('Landing anterior restaurada en la raíz (sus archivos nunca se borraron).')


def main():
    args = set(sys.argv[1:])
    password = cp._load_password()
    if not password:
        raise SystemExit('Falta la contraseña FTP (FTP_PASS o .deploy_cpanel.env).')

    def connect():
        conn = ftplib.FTP_TLS(cp.FTP_HOST, timeout=60)  # noqa: S321 - FTPS explícito con prot_p()
        conn.login(cp.FTP_USER, password)
        conn.prot_p()
        return conn

    if '--rollback' in args:
        rollback(connect)
        return

    target = 'root' if '--root' in args else 'preview'
    dist = build_local(target) if '--build' in args else fetch_ci(target)
    check_bundle(dist, target)
    print(f'Publicando la landing en {REMOTE[target]} ...')
    # En /nuevo/ la carpeta es solo de la landing: se limpian los archivos viejos. En la raíz no se borra nada.
    upload(dist, REMOTE[target], connect, prune=(target == 'preview'))
    print('Listo: https://centrojuanpabloii.com' + BASE[target])


if __name__ == '__main__':
    main()
