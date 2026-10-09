import os

from flask import Blueprint, abort, current_app, send_from_directory

from app.auth_compat import login_required

uploads_bp = Blueprint('uploads', __name__)


def _is_allowed(filename):
    from app.services import attachments

    ext = attachments.ext_of(filename)
    return ext in current_app.config.get('ALLOWED_UPLOAD_EXTENSIONS', set()) or ext in attachments.ALLOWED


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

    from app.services import attachments

    ext = attachments.ext_of(filename)
    response = send_from_directory(
        upload_dir,
        filename,
        as_attachment=ext not in attachments.INLINE,
        download_name=attachments.display_name(os.path.basename(filename)),
        conditional=True,
    )
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Content-Security-Policy'] = "default-src 'none'; img-src 'self' data:; media-src 'self'; sandbox"
    return response
