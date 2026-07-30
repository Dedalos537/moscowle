"""Deploy backend + frontend to cPanel via FTP.

Usage:
    python scripts/deploy_cpanel.py              # Deploy everything
    python scripts/deploy_cpanel.py --backend    # Backend only
    python scripts/deploy_cpanel.py --frontend   # Frontend only
    python scripts/deploy_cpanel.py --dry-run    # Preview what would be uploaded

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

import ftplib
import io
import os
import re
import sys
import time
from pathlib import Path

# ─── FTP Config ───
FTP_HOST = 'ftp.centrojuanpabloii.com'
FTP_USER = 'centroju'
FTP_PASS = '+LC6OXpm0dq6@4'

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


def delete_old_hashed_files(ftp: ftplib.FTP, remote_dir: str):
    """Delete old hashed JS/CSS files before uploading new build."""
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
            try:
                ftp.delete(filename)
                deleted += 1
            except Exception:
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
        except Exception:
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
        for root, dirs, files in os.walk(PROJECT_ROOT):
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


def deploy_frontend(ftp: ftplib.FTP, dry_run=False):
    """Deploy frontend build to cPanel."""
    print('\n=== FRONTEND ===')
    print(f'  Local:  {LOCAL_FRONTEND_DIR}')
    print(f'  Remote: {REMOTE_FRONTEND_DIR}')

    if not LOCAL_FRONTEND_DIR.exists():
        print(f'  ERROR: Frontend build not found at {LOCAL_FRONTEND_DIR}')
        print('  Run "npx ng build" first.')
        return

    if dry_run:
        count = sum(1 for _ in LOCAL_FRONTEND_DIR.rglob('*') if _.is_file())
        print(f'  Total: {count} files')
        return

    # Clean old hashed files
    print('  Cleaning old hashed files...')
    delete_old_hashed_files(ftp, REMOTE_FRONTEND_DIR)

    # Upload
    uploaded, skipped = upload_dir(ftp, str(LOCAL_FRONTEND_DIR), REMOTE_FRONTEND_DIR)
    print(f'  Uploaded: {uploaded} files')

    # Bust index.html cache
    bust_index_cache(ftp, REMOTE_FRONTEND_DIR)


def main():
    dry_run = '--dry-run' in sys.argv
    backend_only = '--backend' in sys.argv
    frontend_only = '--frontend' in sys.argv

    if backend_only and frontend_only:
        print('ERROR: Use --backend OR --frontend, not both.')
        sys.exit(1)

    do_backend = not frontend_only
    do_frontend = not backend_only

    print(f'Connecting to {FTP_HOST}...')
    ftp = ftplib.FTP(FTP_HOST)
    ftp.login(FTP_USER, FTP_PASS)
    print('Connected!')

    if do_backend:
        deploy_backend(ftp, dry_run)

    if do_frontend:
        deploy_frontend(ftp, dry_run)

    ftp.quit()
    print('\nDone!')


if __name__ == '__main__':
    main()
