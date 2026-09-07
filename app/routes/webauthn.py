import json
import logging

from flask import Blueprint, jsonify, request
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt_identity,
    jwt_required,
    set_access_cookies,
    set_refresh_cookies,
)
from flask_wtf.csrf import generate_csrf

from app.extensions import db
from app.models.user import User
from app.models.webauthn import WebAuthnCredential
from app.routes.auth import _auto_start_session, _record_session
from app.services import webauthn_service

webauthn_bp = Blueprint('webauthn', __name__, url_prefix='/api/auth/webauthn')

logger = logging.getLogger('app.webauthn')


@webauthn_bp.after_request
def _no_store(response):
    response.headers['Cache-Control'] = 'no-store, max-age=0'
    return response


def _current_identity():
    identity = get_jwt_identity()
    if not identity:
        return None
    try:
        return db.session.get(User, int(identity))
    except (TypeError, ValueError):
        return None


@webauthn_bp.route('/register/options', methods=['POST'])
@jwt_required()
def webauthn_register_options():
    user = _current_identity()
    if not user:
        return jsonify({'success': False, 'error': 'Usuario no encontrado'}), 404
    try:
        options = webauthn_service.registration_options(user)
        return jsonify({'success': True, 'options': json.loads(options)})
    except Exception as exc:
        logger.warning(f'webauthn register options failed: {exc}')
        return jsonify({'success': False, 'error': 'No se pudo iniciar el registro'}), 500


@webauthn_bp.route('/register/verify', methods=['POST'])
@jwt_required()
def webauthn_register_verify():
    user = _current_identity()
    if not user:
        return jsonify({'success': False, 'error': 'Usuario no encontrado'}), 404
    data = request.get_json(silent=True) or {}
    cred_id, error = webauthn_service.verify_registration(user, data)
    if error:
        return jsonify({'success': False, 'error': error}), 400
    return jsonify({'success': True, 'credential_id': cred_id})


@webauthn_bp.route('/login/options', methods=['POST'])
def webauthn_login_options():
    data = request.get_json(silent=True) or {}
    user = webauthn_service.find_user_by_identifier(data.get('identifier'))
    if not user or not user.is_active:
        return jsonify({'success': False, 'error': 'Usuario no encontrado'}), 404
    options = webauthn_service.authentication_options(user)
    if options is None:
        return jsonify({'success': False, 'error': 'Este usuario no tiene huella registrada'}), 404
    return jsonify({'success': True, 'options': json.loads(options)})


@webauthn_bp.route('/login/verify', methods=['POST'])
def webauthn_login_verify():
    data = request.get_json(silent=True) or {}
    identifier = data.get('identifier')
    user = webauthn_service.find_user_by_identifier(identifier)
    if not user or not user.is_active:
        return jsonify({'success': False, 'error': 'Usuario no encontrado'}), 404
    user, error = webauthn_service.verify_authentication(user, data)
    if error:
        return jsonify({'success': False, 'error': error}), 401
    _auto_start_session(user)
    access_token = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))
    _record_session(user, access_token, refresh_token)
    csrf_token = generate_csrf()
    response = jsonify(
        {
            'success': True,
            'csrf_token': csrf_token,
            'access_token': access_token,
            'user': {
                'id': user.id,
                'email': user.email,
                'username': user.username,
                'role': user.role,
                'login_code': user.login_code,
                'timezone': getattr(user, 'timezone', None) or 'America/Lima',
            },
        }
    )
    set_access_cookies(response, access_token)
    set_refresh_cookies(response, refresh_token)
    return response


@webauthn_bp.route('/credentials', methods=['GET'])
@jwt_required()
def webauthn_credentials():
    user = _current_identity()
    if not user:
        return jsonify({'success': False, 'error': 'Usuario no encontrado'}), 404
    creds = WebAuthnCredential.query.filter_by(user_id=user.id, is_active=True).all()
    return jsonify(
        {
            'success': True,
            'credentials': [
                {
                    'id': c.id,
                    'device_name': c.device_name,
                    'created_at': c.created_at.isoformat() if c.created_at else None,
                }
                for c in creds
            ],
        }
    )


@webauthn_bp.route('/credentials/<int:credential_id>', methods=['DELETE'])
@jwt_required()
def webauthn_delete_credential(credential_id):
    user = _current_identity()
    if not user:
        return jsonify({'success': False, 'error': 'Usuario no encontrado'}), 404
    cred = WebAuthnCredential.query.filter_by(id=credential_id, user_id=user.id).first()
    if not cred:
        return jsonify({'success': False, 'error': 'Dispositivo no encontrado'}), 404
    cred.is_active = False
    db.session.commit()
    return jsonify({'success': True})
