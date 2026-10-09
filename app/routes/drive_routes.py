"""API del drive del administrador (/api/drive). SOLO el rol «admin»: ni supervisores ni otros roles."""

from functools import wraps

from flask import Blueprint, jsonify, request, send_file
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.extensions import db
from app.models import PrintJob, User
from app.services import drive_preview, print_service
from app.services import drive_service as drive

drive_bp = Blueprint('drive', __name__, url_prefix='/api/drive')


def admin_only(fn):
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        user = db.session.get(User, int(get_jwt_identity()))
        if not user or user.role != 'admin' or not user.is_active:
            return jsonify({'error': 'Solo el administrador puede usar el drive'}), 403
        try:
            return fn(*args, **kwargs)
        except drive.DriveError as exc:
            return jsonify({'error': str(exc)}), exc.status

    return wrapper


def _body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def _paths(data):
    paths = data.get('paths')
    if not isinstance(paths, list) or not paths or not all(isinstance(p, str) for p in paths):
        raise drive.DriveError('Elige uno o más elementos')
    if len(paths) > 500:
        raise drive.DriveError('Demasiados elementos a la vez')
    return paths


def _uid():
    return int(get_jwt_identity())


# ── explorar ─────────────────────────────────────────────────────────────────
@drive_bp.route('/list', methods=['GET'])
@admin_only
def list_folder():
    return jsonify(drive.list_dir(request.args.get('path', '')))


@drive_bp.route('/search', methods=['GET'])
@admin_only
def search():
    return jsonify({'entries': drive.search(request.args.get('q', '')), 'usage': drive.usage()})


@drive_bp.route('/recent', methods=['GET'])
@admin_only
def recent():
    return jsonify({'entries': drive.recent(), 'usage': drive.usage()})


@drive_bp.route('/starred', methods=['GET', 'POST'])
@admin_only
def starred():
    if request.method == 'POST':
        data = _body()
        for rel in _paths(data):
            drive.set_starred(rel, bool(data.get('starred', True)))
    return jsonify({'entries': drive.starred_entries(), 'usage': drive.usage()})


@drive_bp.route('/usage', methods=['GET'])
@admin_only
def usage():
    return jsonify(drive.usage())


# ── archivos ─────────────────────────────────────────────────────────────────
@drive_bp.route('/folder', methods=['POST'])
@admin_only
def new_folder():
    data = _body()
    return jsonify(drive.mkdir(data.get('path', ''), data.get('name', ''))), 201


@drive_bp.route('/rename', methods=['POST'])
@admin_only
def rename():
    data = _body()
    return jsonify(drive.rename(data.get('path', ''), data.get('name', '')))


@drive_bp.route('/move', methods=['POST'])
@admin_only
def move():
    data = _body()
    return jsonify({'entries': drive.move(_paths(data), data.get('dest', ''))})


@drive_bp.route('/copy', methods=['POST'])
@admin_only
def copy():
    data = _body()
    return jsonify({'entries': drive.copy(_paths(data), data.get('dest', ''))})


@drive_bp.route('/delete', methods=['POST'])
@admin_only
def delete():
    return jsonify({'trashed': drive.trash(_paths(_body())), 'usage': drive.usage()})


@drive_bp.route('/compress', methods=['POST'])
@admin_only
def compress():
    data = _body()
    return jsonify(drive.compress(_paths(data), data.get('dest', ''), data.get('name') or 'Archivo')), 201


@drive_bp.route('/extract', methods=['POST'])
@admin_only
def extract():
    data = _body()
    return jsonify(drive.extract(data.get('path', ''), data.get('dest'))), 201


# ── papelera ─────────────────────────────────────────────────────────────────
@drive_bp.route('/trash', methods=['GET'])
@admin_only
def trash_list():
    return jsonify({'entries': drive.trash_list(), 'usage': drive.usage()})


@drive_bp.route('/trash/restore', methods=['POST'])
@admin_only
def trash_restore():
    return jsonify({'restored': drive.restore(_body().get('ids') or [])})


@drive_bp.route('/trash/empty', methods=['POST'])
@admin_only
def trash_empty():
    ids = _body().get('ids')
    return jsonify({'purged': drive.purge(ids if isinstance(ids, list) else None), 'usage': drive.usage()})


# ── subida por partes ────────────────────────────────────────────────────────
@drive_bp.route('/upload/init', methods=['POST'])
@admin_only
def upload_init():
    data = _body()
    return jsonify(drive.upload_init(data.get('path', ''), str(data.get('name') or ''), data.get('size') or 0))


@drive_bp.route('/upload/<upload_id>', methods=['PUT'])
@admin_only
def upload_chunk(upload_id):
    received = drive.upload_chunk(
        upload_id, int(request.args.get('offset', 0)), request.stream, int(request.content_length or 0)
    )
    return jsonify({'received': received})


@drive_bp.route('/upload/<upload_id>/complete', methods=['POST'])
@admin_only
def upload_complete(upload_id):
    return jsonify(drive.upload_complete(upload_id)), 201


@drive_bp.route('/upload/<upload_id>', methods=['DELETE'])
@admin_only
def upload_abort(upload_id):
    drive.upload_abort(upload_id)
    return jsonify({'ok': True})


# ── descargar y previsualizar ────────────────────────────────────────────────
@drive_bp.route('/file', methods=['GET'])
@admin_only
def download():
    path = drive.resolve(request.args.get('path', ''))
    if path.is_dir():
        raise drive.DriveError('Para descargar una carpeta, comprímela primero')
    inline = request.args.get('inline') == '1'
    response = send_file(path, as_attachment=not inline, download_name=path.name, conditional=True, max_age=0)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    # Un HTML/SVG subido nunca se ejecuta en el origen de la app.
    response.headers['Content-Security-Policy'] = "default-src 'none'; img-src 'self' data:; style-src 'unsafe-inline'"
    return response


@drive_bp.route('/thumb', methods=['GET'])
@admin_only
def thumb():
    cached = drive_preview.thumbnail(request.args.get('path', ''))
    if cached is None:
        return jsonify({'error': 'Sin miniatura'}), 404
    return send_file(cached, mimetype='image/webp', max_age=3600, conditional=True)


@drive_bp.route('/preview', methods=['GET'])
@admin_only
def preview():
    return jsonify(drive_preview.describe(request.args.get('path', '')))


@drive_bp.route('/preview/pdf', methods=['GET'])
@admin_only
def preview_pdf():
    """PDF convertido con LibreOffice (Word/PowerPoint/Excel) para verlo tal cual."""
    path = drive.resolve(request.args.get('path', ''))
    pdf = drive_preview.office_pdf(path)
    if pdf is None:
        return jsonify({'error': 'No se pudo convertir el documento'}), 404
    return send_file(pdf, mimetype='application/pdf', download_name=path.stem + '.pdf', max_age=0)


# ── impresión ────────────────────────────────────────────────────────────────
@drive_bp.route('/printers', methods=['GET'])
@admin_only
def printers():
    return jsonify(print_service.status())


@drive_bp.route('/print', methods=['POST'])
@admin_only
def print_file():
    data = _body()
    job = print_service.create_job(data.get('path', ''), data, user_id=_uid())
    return jsonify(job.to_dict()), (201 if job.status != 'failed' else 502)


@drive_bp.route('/print/jobs', methods=['GET'])
@admin_only
def print_jobs():
    jobs = PrintJob.query.order_by(PrintJob.created_at.desc()).limit(100).all()
    return jsonify({'jobs': [j.to_dict() for j in jobs]})


@drive_bp.route('/print/jobs/<int:job_id>/cancel', methods=['POST'])
@admin_only
def cancel_print(job_id):
    job = db.session.get(PrintJob, job_id)
    if not job:
        return jsonify({'error': 'Trabajo no encontrado'}), 404
    return jsonify(print_service.cancel(job).to_dict())
