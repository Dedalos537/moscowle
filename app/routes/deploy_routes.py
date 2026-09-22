"""Auto-deploy webhook for the Ubuntu server.

GitHub Actions (cloud runner) cannot reach the LAN server directly, so we use
the public tunnel (api-centrojuanpabloii.online -> 127.0.0.1:5000). The deploy
workflows POST here; this endpoint relays the work to a local script that:

  - backend : git pull (reset --hard origin/main) + systemctl restart moscowle
  - frontend: extract the uploaded Angular dist tar into /var/www/moscowle/app
              + systemctl reload nginx
  - obsidian: write a deploy record under docs/obsidian_graph/Deployments/
"""

import os
import subprocess
import threading

from flask import Blueprint, current_app, jsonify, request

from app.extensions import csrf

deploy_bp = Blueprint('deploy', __name__, url_prefix='/api')

DEPLOY_ROOT = '/home/diego/moscowle_ia'
DEPLOY_SCRIPT = os.path.join(DEPLOY_ROOT, 'scripts', 'server_deploy.sh')
OBSIDIAN_DIR = os.path.join(DEPLOY_ROOT, 'docs', 'obsidian_graph', 'Deployments')
TAR_STAGING = '/tmp/frontend_deploy.tar.gz'  # noqa: S108 - internal staging only

csrf.exempt(deploy_bp)


def _token_ok():
    expected = os.environ.get('DEPLOY_WEBHOOK_TOKEN') or current_app.config.get('DEPLOY_WEBHOOK_TOKEN', '')
    provided = request.headers.get('X-Deploy-Token', '')
    return bool(expected) and provided == expected


@deploy_bp.route('/deploy/webhook', methods=['POST'])
def deploy_webhook():
    if not _token_ok():
        return jsonify({'success': False, 'error': 'Token de deploy invalido'}), 401

    backend = request.form.get('backend', 'false').lower() in ('1', 'true', 'yes', 'on')
    frontend_file = request.files.get('frontend')

    if not backend and not frontend_file:
        return jsonify({'success': False, 'error': 'Nada que desplegar (backend/frontend ausente)'}), 400

    args = [DEPLOY_SCRIPT]
    if backend:
        args.append('--backend')
    if frontend_file:
        frontend_file.save(TAR_STAGING)
        args.extend(['--frontend', TAR_STAGING])

    def _run():
        env = dict(os.environ)
        try:
            # args is a fixed list of flags + server paths; no user-controlled values
            _ = subprocess.Popen(  # noqa: S603
                args,
                cwd=DEPLOY_ROOT,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        except Exception as exc:
            current_app.logger.error(f'deploy webhook spawn error: {exc}')

    threading.Thread(target=_run, daemon=True).start()
    current_app.logger.info(f'  Deploy triggered: backend={backend} frontend={bool(frontend_file)}')
    return jsonify({'success': True, 'message': 'Deploy en progreso'}), 202
