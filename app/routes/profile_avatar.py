"""Foto de perfil de cualquier usuario autenticado (admin, supervisor, terapeuta, paciente)."""

import io
import logging
import os

from flask import Blueprint, current_app, jsonify, request, send_file
from flask_jwt_extended import get_jwt_identity, jwt_required
from PIL import Image, ImageOps, UnidentifiedImageError

from app.extensions import db
from app.models import User

avatar_bp = Blueprint('profile_avatar', __name__, url_prefix='/api/profile')
logger = logging.getLogger('app.avatar')

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_PIXELS = 24_000_000  # evita "bombas" de descompresión
ALLOWED_FORMATS = {'JPEG', 'PNG', 'WEBP'}
AVATAR_SIZE = 256


def _avatar_dir():
    path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'avatars')
    os.makedirs(path, exist_ok=True)
    return path


def _avatar_path(user_id):
    return os.path.join(_avatar_dir(), f'{int(user_id)}.jpg')


def _current_user():
    identity = get_jwt_identity()
    return db.session.get(User, int(identity)) if identity else None


def avatar_url(user_id, path=None):
    """URL con versión (mtime) para que el navegador no muestre la foto anterior tras cambiarla."""
    path = path or _avatar_path(user_id)
    if not os.path.exists(path):
        return None
    return f'/api/profile/avatar/{int(user_id)}?v={int(os.path.getmtime(path))}'


@avatar_bp.route('/avatar', methods=['POST'])
@jwt_required()
def upload_avatar():
    user = _current_user()
    if not user or not user.is_active:
        return jsonify({'success': False, 'message': 'Usuario no encontrado'}), 401
    file = request.files.get('file')
    if not file:
        return jsonify({'success': False, 'message': 'Selecciona una imagen'}), 400
    raw = file.read(MAX_UPLOAD_BYTES + 1)
    if len(raw) > MAX_UPLOAD_BYTES:
        return jsonify({'success': False, 'message': 'La imagen supera 5 MB'}), 413
    try:
        Image.MAX_IMAGE_PIXELS = MAX_PIXELS
        img = Image.open(io.BytesIO(raw))
        if img.format not in ALLOWED_FORMATS:
            return jsonify({'success': False, 'message': 'Usa una imagen JPG, PNG o WebP'}), 400
        img = ImageOps.exif_transpose(img).convert('RGB')
        img = ImageOps.fit(img, (AVATAR_SIZE, AVATAR_SIZE), Image.LANCZOS)
        out = io.BytesIO()
        img.save(out, 'JPEG', quality=86, optimize=True)
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError, ValueError):
        return jsonify({'success': False, 'message': 'No se pudo leer la imagen'}), 400
    path = _avatar_path(user.id)
    with open(path, 'wb') as fh:
        fh.write(out.getvalue())
    user.avatar = avatar_url(user.id, path)
    db.session.commit()
    return jsonify({'success': True, 'avatar': user.avatar})


@avatar_bp.route('/avatar', methods=['DELETE'])
@jwt_required()
def delete_avatar():
    user = _current_user()
    if not user:
        return jsonify({'success': False, 'message': 'Usuario no encontrado'}), 401
    path = _avatar_path(user.id)
    if os.path.exists(path):
        os.remove(path)
    user.avatar = None
    db.session.commit()
    return jsonify({'success': True, 'avatar': None})


@avatar_bp.route('/avatar/<int:user_id>', methods=['GET'])
@jwt_required()
def get_avatar(user_id):
    path = _avatar_path(user_id)
    if not os.path.exists(path):
        return jsonify({'success': False, 'message': 'Sin foto'}), 404
    resp = send_file(path, mimetype='image/jpeg', conditional=True, max_age=0)
    # La URL lleva ?v=<mtime>: puede cachearse sin riesgo de ver una foto vieja.
    resp.headers['Cache-Control'] = 'private, max-age=86400' if request.args.get('v') else 'private, no-cache'
    return resp
