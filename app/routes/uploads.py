import os

from flask import Blueprint, abort, current_app, send_from_directory
from app.auth_compat import login_required

uploads_bp = Blueprint('uploads', __name__)


def _is_allowed(filename):
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    return ext in current_app.config.get('ALLOWED_UPLOAD_EXTENSIONS', set())


@uploads_bp.route('/uploads/<path:filename>')
@login_required
def protected_file(filename):
    upload_dir = current_app.config.get('UPLOAD_FOLDER')
    if not upload_dir:
        abort(404)

    safe_path = os.path.normpath(os.path.join(upload_dir, filename))
    if not safe_path.startswith(os.path.abspath(upload_dir)):
        abort(403)

    if not _is_allowed(filename):
        abort(403)

    if not os.path.exists(safe_path):
        abort(404)

    return send_from_directory(upload_dir, filename, as_attachment=False)
