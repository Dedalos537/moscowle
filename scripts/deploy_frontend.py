"""Deploy frontend build to cPanel via FTP.

Usage:
    python scripts/deploy_frontend.py

Alternative: push to main branch of Dedalos537/moscowle_ia
with changes under edysync/ to trigger GitHub Actions workflow.
"""

import ftplib
import os
import re

FTP_HOST = 'ftp.centrojuanpabloii.com'
FTP_USER = 'centroju'
FTP_PASS = '+LC6OXpm0dq6@4'
REMOTE_DIR = '/public_html/moscowle.centrojuanpabloii.com'
LOCAL_DIR = 'edysync/dist/edysync/browser'


def bust_index_cache(ftp, remote_dir):
    """Add ?v=<timestamp> to JS/CSS references in index.html on the server
    so CDN/proxy never serves a stale index.html."""
    import io

    try:
        ftp.cwd(remote_dir)
        buf = io.BytesIO()
        ftp.retrbinary('RETR index.html', buf.write)
        html = buf.getvalue().decode('utf-8')
    except Exception as e:
        print(f'  WARN: Could not read index.html: {e}')
        return

    ts = str(int(__import__('time').time()))
    # Add ?v=TIMESTAMP to .js and .css references that don't already have it
    new_html = re.sub(r'((?:src|href)="[^"]*\.(?:js|css))(?!.*\?v=)', rf'\1?v={ts}"', html)
    if new_html != html:
        try:
            ftp.storbinary('STOR index.html', io.BytesIO(new_html.encode('utf-8')))
            print(f'  OK  index.html (cache-bust ?v={ts})')
        except Exception as e:
            print(f'  WARN: Could not update index.html: {e}')


def delete_old_hashed_files(ftp, remote_dir):
    """Delete old hashed JS/CSS files (e.g. main-XXXX.js, styles-XXXX.css)
    before uploading new build. Keeps index.html and assets/."""
    try:
        ftp.cwd(remote_dir)
        entries = []
        ftp.retrlines('LIST', entries.append)
    except Exception as e:
        print(f'  WARN: Could not list remote dir: {e}')
        return

    # Pattern: files like main-ABC123.js, styles-ABC123.css, polyfills-ABC123.js
    hash_pattern = re.compile(r'^-.*\s+([\w]+-[A-Z0-9]{6,}\.(?:js|css|js\.map|css\.map))\s*$')
    deleted = 0
    for entry in entries:
        m = hash_pattern.search(entry)
        if m:
            filename = m.group(1)
            try:
                ftp.delete(filename)
                print(f'  DEL {filename}')
                deleted += 1
            except Exception as e:
                print(f'  WARN Could not delete {filename}: {e}')
    if deleted:
        print(f'  Cleaned {deleted} old hashed file(s)')


def upload_dir(ftp, local, remote):
    ftp.cwd('/')
    for root, dirs, files in os.walk(local):
        rel = os.path.relpath(root, local)
        rem = os.path.join(remote, rel).replace('\\', '/') if rel != '.' else remote
        ftp.cwd('/')
        for part in rem.split('/'):
            if not part:
                continue
            try:
                ftp.cwd(part)
            except:
                ftp.mkd(part)
                ftp.cwd(part)
        for f in files:
            local_path = os.path.join(root, f)
            remote_path = os.path.join(rem, f).replace('\\', '/')
            try:
                with open(local_path, 'rb') as fh:
                    ftp.storbinary(f'STOR {remote_path}', fh)
                print(f'  OK  {remote_path}')
            except Exception as e:
                print(f'  FAIL {remote_path}: {e}')


if __name__ == '__main__':
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    local_dir = os.path.join(script_dir, LOCAL_DIR)

    print(f'Connecting to {FTP_HOST}...')
    ftp = ftplib.FTP(FTP_HOST)
    ftp.login(FTP_USER, FTP_PASS)

    print('Cleaning old hashed files...')
    delete_old_hashed_files(ftp, REMOTE_DIR)

    print('Uploading...')
    upload_dir(ftp, local_dir, REMOTE_DIR)

    print('Busting index.html cache...')
    bust_index_cache(ftp, REMOTE_DIR)

    ftp.quit()
    print('Done!')
