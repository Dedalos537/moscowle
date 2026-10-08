"""Deploy backend + frontend to cPanel via FTP.

Usage:
    python scripts/deploy_cpanel.py              # Deploy everything
    python scripts/deploy_cpanel.py --backend    # Backend only
    python scripts/deploy_cpanel.py --frontend   # Frontend only
    python scripts/deploy_cpanel.py --dry-run    # Preview what would be uploaded
    python scripts/deploy_cpanel.py --build      # Compila Angular (ng build) antes de subir el frontend
    python scripts/deploy_cpanel.py --no-build   # Frontend: sube el dist/ actual (debe tener base href /)
    python scripts/deploy_cpanel.py --from-ci    # Frontend: descarga el build de la CI (main) en vez de compilar aquí
    python scripts/deploy_cpanel.py --all        # --build + todo: lo mismo que hace el pipeline, en un comando

La contrasena FTP se toma de (en este orden): variable FTP_PASS, archivo local `.deploy_cpanel.env`
(ignorado por git, linea FTP_PASS=...) o se pide por teclado sin mostrarla.

Structure on cPanel:
    /moscowle/                    <- Backend (Flask + Python)
        passenger_wsgi.py
        app/
        config.py
        server.py
        requirements.txt
        .env
        migrations/
        ...
    /public_html/moscowle.centrojuanpabloii.com/  <- Frontend (Angular)
        index.html
        assets/
        ...
"""

import contextlib
import ftplib
import getpass
import io
import os
import re
import subprocess
import sys
import time
from pathlib import Path

# ─── FTP Config ───
# La contrasena NO va en el codigo: se pasa por entorno (FTP_PASS=... python scripts/deploy_cpanel.py).
FTP_HOST = os.environ.get('FTP_HOST', 'ftp.centrojuanpabloii.com')
FTP_USER = os.environ.get('FTP_USER', 'centroju')
FTP_PASS = os.environ.get('FTP_PASS', '')


def _load_password():
    """FTP_PASS del entorno, de .deploy_cpanel.env (gitignored) o por teclado. Nunca se imprime."""
    if FTP_PASS:
        return FTP_PASS
    env_file = Path(__file__).resolve().parent.parent / '.deploy_cpanel.env'
    if env_file.is_file():
        for line in env_file.read_text().splitlines():
            key, _, value = line.partition('=')
            if key.strip() == 'FTP_PASS' and value.strip():
                return value.strip().strip('"\'')
    return getpass.getpass('Contrasena FTP (no se muestra): ') if sys.stdin.isatty() else ''


def fetch_ci_frontend():
    """Descarga el bundle 'frontend-cpanel' del último CI exitoso de main (requiere `gh` autenticado).

    Útil cuando la máquina local no tiene memoria para compilar Angular.
    """
    import shutil
    import tempfile

    list_cmd = ['gh', 'run', 'list', '--branch', 'main', '--workflow', 'ci.yml', '--status', 'success']
    list_cmd += ['--limit', '1', '--json', 'databaseId', '-q', '.[0].databaseId']
    out = subprocess.run(list_cmd, cwd=PROJECT_ROOT, capture_output=True, text=True, check=True)  # noqa: S603
    run_id = out.stdout.strip()
    if not run_id:
        raise SystemExit('No hay un CI exitoso en main con el bundle de cPanel.')
    tmp = Path(tempfile.mkdtemp(prefix='cpanel-'))
    download_cmd = ['gh', 'run', 'download', run_id, '--name', 'frontend-cpanel', '--dir', str(tmp)]
    subprocess.run(download_cmd, cwd=PROJECT_ROOT, check=True)  # noqa: S603
    if not (tmp / 'index.html').exists() or '<base href="/">' not in (tmp / 'index.html').read_text():
        raise SystemExit('El bundle descargado no tiene el base href de cPanel.')
    if LOCAL_FRONTEND_DIR.exists():
        shutil.rmtree(LOCAL_FRONTEND_DIR)
    LOCAL_FRONTEND_DIR.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(tmp, LOCAL_FRONTEND_DIR)
    shutil.rmtree(tmp, ignore_errors=True)
    print(f'Bundle del CI {run_id} listo en {LOCAL_FRONTEND_DIR}')


def build_frontend():
    print('Compilando Angular (produccion, base href / para cPanel)...')
    subprocess.run(['npx', 'ng', 'build', '--base-href', '/'], cwd=PROJECT_ROOT / 'edysync', check=True)  # noqa: S607


# ─── Remote paths ───
REMOTE_BACKEND_DIR = '/moscowle'
REMOTE_FRONTEND_DIR = '/public_html/moscowle.centrojuanpabloii.com'

# ─── Local paths ───
PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOCAL_FRONTEND_DIR = PROJECT_ROOT / 'edysync' / 'dist' / 'edysync' / 'browser'

# ─── Files/folders to EXCLUDE from backend upload ───
BACKEND_EXCLUDE = {
    '.git',
    '.github',
    '__pycache__',
    '.pytest_cache',
    '.ruff_cache',
    '.venv',
    'venv',
    'node_modules',
    '.opencode',
    '.cache',
    'edysync',
    'design',
    'docs',
    'features',
    'tests',
    'graphify-out',
    'sprinbootbackend',
    'railway_deploy',
    'docker',
    'PRPs',
    '.coverage',
    '.DS_Store',
    '.gitattributes',
    '.gitignore',
    '.pre-commit-config.yaml',
    '.pre-commit-hooks.yaml',
    'docker-compose.yml',
    'docker-compose.dev.yml',
    'docker-compose.override.yml.example',
    'Dockerfile',
    'Dockerfile.dev',
    'Dockerfile.frontend.dev',
    'Makefile',
    'README.md',
    'CONTRIBUTING.md',
    'documento_proyecto.md',
    'generar_docx.py',
    'moscowle_production.sql',
    'package-lock.json',
    'pyproject.toml',
    'pytest.ini',
    'runtime.txt',
    'railway.json',
    'run_dev.py',
    'run_gunicorn.py',
    'run.py',
    'seed_docker.py',
    'start_server.py',
    'start.sh',
    'dev.sh',
    'logs',
    'uploads',
    'instance',
}

# ─── Backend files/dirs to INCLUDE ───
BACKEND_INCLUDE = {
    'app',
    'migrations',
    'scripts',
    'config.py',
    'server.py',
    'wsgi.py',
    'apply_itil_columns.py',
    'requirements.txt',
}

# ─── Passenger WSGI template ───
PASSENGER_WSGI = '''"""Passenger WSGI entry point for cPanel."""
import os
import sys

# Add project root to Python path
sys.path.insert(0, os.path.dirname(__file__))

# Set environment
os.environ.setdefault('FLASK_ENV', 'production')

# Create Flask application
from app import create_app
application = create_app()
'''


def should_include_backend(path: str) -> bool:
    """Check if a file/dir should be included in backend upload."""
    parts = Path(path).parts
    if not parts:
        return False
    # Exclude known unwanted directories
    for part in parts:
        if part in BACKEND_EXCLUDE:
            return False
    # Include if top-level matches BACKEND_INCLUDE or is inside an included dir
    top = parts[0]
    return top in BACKEND_INCLUDE


def delete_old_hashed_files(ftp: ftplib.FTP, remote_dir: str, keep=frozenset()):
    """Borra los JS/CSS con hash de builds anteriores (nunca los que están en `keep`, los del build nuevo)."""
    try:
        ftp.cwd(remote_dir)
        entries = []
        ftp.retrlines('LIST', entries.append)
    except Exception:
        return

    hash_pattern = re.compile(r'^-.*\s+([\w]+-[A-Z0-9]{6,}\.(?:js|css|js\.map|css\.map))\s*$')
    deleted = 0
    for entry in entries:
        m = hash_pattern.search(entry)
        if m:
            filename = m.group(1)
            if filename in keep:
                continue
            try:
                ftp.delete(filename)
                deleted += 1
            except Exception:  # noqa: S110 - mejor esfuerzo, se ignora a proposito
                pass
    if deleted:
        print(f'  Cleaned {deleted} old hashed file(s)')


def bust_index_cache(ftp: ftplib.FTP, remote_dir: str):
    """Add ?v=<timestamp> to JS/CSS references in index.html."""
    try:
        ftp.cwd(remote_dir)
        buf = io.BytesIO()
        ftp.retrbinary('RETR index.html', buf.write)
        html = buf.getvalue().decode('utf-8')
    except Exception:
        return

    ts = str(int(time.time()))
    new_html = re.sub(r'((?:src|href)="[^"]*\.(?:js|css))(?!.*\?v=)', rf'\1?v={ts}"', html)
    if new_html != html:
        try:
            ftp.storbinary('STOR index.html', io.BytesIO(new_html.encode('utf-8')))
            print(f'  index.html cache-bust ?v={ts}')
        except Exception:  # noqa: S110 - mejor esfuerzo, se ignora a proposito
            pass


def mkdir_p(ftp: ftplib.FTP, remote_path: str):
    """Create remote directory recursively."""
    ftp.cwd('/')
    for part in remote_path.split('/'):
        if not part:
            continue
        try:
            ftp.cwd(part)
        except ftplib.error_perm:
            try:
                ftp.mkd(part)
                ftp.cwd(part)
            except ftplib.error_perm:
                pass


def upload_dir(ftp: ftplib.FTP, local: str, remote: str, filter_fn=None):
    """Upload a local directory to remote via FTP."""
    uploaded = 0
    skipped = 0

    for root, dirs, files in os.walk(local):
        rel = os.path.relpath(root, local)
        rem = os.path.join(remote, rel).replace('\\', '/') if rel != '.' else remote

        # Create remote directory
        mkdir_p(ftp, rem)

        # Filter directories in-place to skip excluded ones
        if filter_fn:
            dirs[:] = [d for d in dirs if filter_fn(os.path.join(rel, d))]

        for f in files:
            local_path = os.path.join(root, f)
            remote_path = os.path.join(rem, f).replace('\\', '/')

            if filter_fn and not filter_fn(os.path.join(rel, f)):
                skipped += 1
                continue

            try:
                with open(local_path, 'rb') as fh:
                    ftp.storbinary(f'STOR {remote_path}', fh)
                uploaded += 1
            except Exception as e:
                print(f'  FAIL {remote_path}: {e}')

    return uploaded, skipped


def create_passenger_wsgi(ftp: ftplib.FTP):
    """Upload passenger_wsgi.py to the backend root."""
    mkdir_p(ftp, REMOTE_BACKEND_DIR)
    ftp.storbinary('STOR passenger_wsgi.py', io.BytesIO(PASSENGER_WSGI.encode('utf-8')))
    print(f'  OK  {REMOTE_BACKEND_DIR}/passenger_wsgi.py')


def upload_env_production(ftp: ftplib.FTP):
    """Upload .env.production as .env to the backend root."""
    env_src = PROJECT_ROOT / '.env.production'
    if not env_src.exists():
        print(f'  WARN  {env_src} not found, skipping .env upload')
        return
    with open(env_src, 'rb') as f:
        ftp.storbinary('STOR .env', f)
    print(f'  OK  {REMOTE_BACKEND_DIR}/.env (from .env.production)')


def deploy_backend(ftp: ftplib.FTP, dry_run=False):
    """Deploy backend code to cPanel."""
    print('\n=== BACKEND ===')
    print(f'  Local:  {PROJECT_ROOT}')
    print(f'  Remote: {REMOTE_BACKEND_DIR}')

    if dry_run:
        count = 0
        for root, _dirs, files in os.walk(PROJECT_ROOT):
            rel = os.path.relpath(root, PROJECT_ROOT)
            if rel == '.':
                rel = ''
            for f in files:
                path = os.path.join(rel, f)
                if should_include_backend(path):
                    count += 1
                    print(f'  WOULD UPLOAD: {path}')
        print(f'  Total: {count} files')
        return

    # Create passenger_wsgi.py
    create_passenger_wsgi(ftp)

    # Upload .env.production as .env
    upload_env_production(ftp)

    # Upload backend files
    uploaded, skipped = upload_dir(ftp, str(PROJECT_ROOT), REMOTE_BACKEND_DIR, should_include_backend)
    print(f'  Uploaded: {uploaded} files, skipped: {skipped}')


def deploy_frontend(ftp: ftplib.FTP, dry_run=False, connect=None):
    """Sube el build al cPanel sin dejar el sitio roto en ningún momento.

    Orden: (1) archivos nuevos con hash, con reintento y reconexión; (2) index.html al final, que es el que apunta a
    ellos; (3) recién entonces se borran los archivos viejos. Antes se borraba primero: si la conexión FTPS se caía a
    mitad, el sitio quedaba pidiendo archivos que ya no existían.
    """
    print('\n=== FRONTEND ===')
    print(f'  Local:  {LOCAL_FRONTEND_DIR}')
    print(f'  Remote: {REMOTE_FRONTEND_DIR}')

    if not LOCAL_FRONTEND_DIR.exists():
        print(f'  ERROR: Frontend build not found at {LOCAL_FRONTEND_DIR}')
        print('  Run "npx ng build" first.')
        return False

    files = sorted(p for p in LOCAL_FRONTEND_DIR.rglob('*') if p.is_file())
    if dry_run:
        print(f'  Total: {len(files)} files')
        return True

    index = LOCAL_FRONTEND_DIR / 'index.html'
    ordered = [p for p in files if p != index] + ([index] if index.exists() else [])
    state = {'ftp': ftp}

    def put(path):
        rel = path.relative_to(LOCAL_FRONTEND_DIR).as_posix()
        remote = f'{REMOTE_FRONTEND_DIR}/{rel}'
        for attempt in range(1, 5):
            try:
                mkdir_p(state['ftp'], remote.rsplit('/', 1)[0])
                with open(path, 'rb') as fh:
                    state['ftp'].storbinary(f'STOR {remote}', fh)
                return True
            except Exception as e:
                print(f'  reintento {attempt} {rel}: {e}')
                if connect is None:
                    break
                with contextlib.suppress(Exception):
                    state['ftp'].close()
                time.sleep(2 * attempt)
                with contextlib.suppress(Exception):
                    state['ftp'] = connect()
        return False

    uploaded = 0
    for path in ordered[:-1] if index.exists() else ordered:
        if not put(path):
            print(
                f'  ERROR: no se pudo subir {path.name}. Se detiene SIN tocar index.html: el sitio sigue con la versión anterior.'
            )
            return False
        uploaded += 1
    if index.exists() and not put(index):
        print('  ERROR: no se pudo subir index.html. El sitio sigue con la versión anterior.')
        return False
    print(f'  Uploaded: {uploaded + 1} files')

    bust_index_cache(state['ftp'], REMOTE_FRONTEND_DIR)
    delete_old_hashed_files(state['ftp'], REMOTE_FRONTEND_DIR, keep={p.name for p in files})
    return True


def main():
    dry_run = '--dry-run' in sys.argv
    backend_only = '--backend' in sys.argv
    frontend_only = '--frontend' in sys.argv

    if backend_only and frontend_only:
        print('ERROR: Use --backend OR --frontend, not both.')
        sys.exit(1)

    do_backend = not frontend_only
    do_frontend = not backend_only

    password = _load_password()
    if not password:
        print('ERROR: falta la contrasena FTP (variable FTP_PASS o archivo .deploy_cpanel.env).')
        sys.exit(1)

    # El dist por defecto usa base /app/ (nginx de Ubuntu); en cPanel cuelga de la raiz, asi que siempre se recompila.
    if do_frontend and not dry_run:
        if '--no-build' in sys.argv:
            # Sube el build que ya está en dist/, pero solo si es uno para cPanel (base href en la raíz).
            index = LOCAL_FRONTEND_DIR / 'index.html'
            if not index.exists() or '<base href="/">' not in index.read_text(encoding='utf-8'):
                raise SystemExit('dist/ no es un build para cPanel (falta <base href="/">). Usa --from-ci o compila.')
        elif '--from-ci' in sys.argv:
            fetch_ci_frontend()
        else:
            build_frontend()

    print(f'Connecting to {FTP_HOST}...')

    # FTPS: con FTP plano la contrasena viaja en claro.
    def connect():
        conn = ftplib.FTP_TLS(FTP_HOST, timeout=60)  # noqa: S321 - FTPS explicito (TLS) con prot_p()
        conn.login(FTP_USER, password)
        conn.prot_p()
        return conn

    ftp = connect()
    print('Connected!')

    if do_backend:
        deploy_backend(ftp, dry_run)

    if do_frontend and not deploy_frontend(ftp, dry_run, connect=connect):
        sys.exit(1)

    with contextlib.suppress(Exception):
        ftp.quit()
    print('\nDone!')


if __name__ == '__main__':
    main()
