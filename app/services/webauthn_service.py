import os
from datetime import datetime, timedelta
from urllib.parse import urlparse

from flask import current_app, has_request_context, request
from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers import base64url_to_bytes, bytes_to_base64url
from webauthn.helpers.options_to_json import options_to_json
from webauthn.helpers.structs import (
    AttestationConveyancePreference,
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

from app.extensions import db
from app.models.user import User
from app.models.webauthn import WebAuthnChallenge, WebAuthnCredential

CHALLENGE_TTL_SECONDS = 300


def _configured_rp_id():
    return current_app.config.get('WEBAUTHN_RP_ID', 'api-centrojuanpabloii.online')


def _allowed_rp_ids():
    """Dominios que pueden ser RP ID. Un sitio solo puede usar su propio dominio (o un padre) como rpId,
    así que el frontend de cPanel (moscowle.centrojuanpabloii.com) necesita `centrojuanpabloii.com`."""
    extra = current_app.config.get('WEBAUTHN_EXTRA_RP_IDS', ['centrojuanpabloii.com'])
    if isinstance(extra, str):
        extra = [e.strip() for e in extra.split(',') if e.strip()]
    return [_configured_rp_id(), *extra]


def _request_origin():
    """Origen del navegador si su host está bajo un RP ID permitido y usa https; si no, None."""
    origin = (request.headers.get('Origin') or '').strip().rstrip('/')
    parsed = urlparse(origin)
    host = parsed.hostname
    if not host or parsed.scheme != 'https':
        return None, None
    for allowed in _allowed_rp_ids():
        if host == allowed or host.endswith('.' + allowed):
            return origin, allowed
    return None, None


def rp_id():
    _, allowed = _request_origin() if has_request_context() else (None, None)
    return allowed or _configured_rp_id()


def rp_name():
    return current_app.config.get('WEBAUTHN_RP_NAME', 'Centro Juan Pablo II')


def origins():
    value = current_app.config.get('WEBAUTHN_ORIGINS')
    if isinstance(value, str):
        value = [o.strip() for o in value.split(',') if o.strip()]
    result = list(value or [f'https://{_configured_rp_id()}'])
    origin, _ = _request_origin() if has_request_context() else (None, None)
    if origin and origin not in result:
        result.append(origin)
    return result


def default_challenge():
    return os.urandom(32)


def _save_challenge(user_id, challenge_b64, operation):
    WebAuthnChallenge.query.filter(WebAuthnChallenge.expires_at < datetime.utcnow()).delete()
    WebAuthnChallenge.query.filter_by(user_handle=str(user_id), operation=operation).delete()
    db.session.add(
        WebAuthnChallenge(
            challenge=challenge_b64,
            user_handle=str(user_id),
            operation=operation,
            expires_at=datetime.utcnow() + timedelta(seconds=CHALLENGE_TTL_SECONDS),
        )
    )
    db.session.commit()


def _pop_challenge(user_id, operation):
    row = (
        WebAuthnChallenge.query.filter_by(user_handle=str(user_id), operation=operation)
        .order_by(WebAuthnChallenge.id.desc())
        .first()
    )
    if not row:
        return None
    db.session.delete(row)
    db.session.commit()
    return row


def registration_options(user):
    existing = WebAuthnCredential.query.filter_by(user_id=user.id, is_active=True).all()
    options = generate_registration_options(
        rp_id=rp_id(),
        rp_name=rp_name(),
        user_id=str(user.id).encode(),
        user_name=user.email or user.username,
        user_display_name=user.username,
        attestation=AttestationConveyancePreference.NONE,
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.DISCOURAGED,
            user_verification=UserVerificationRequirement.PREFERRED,
        ),
        challenge=default_challenge(),
        exclude_credentials=[PublicKeyCredentialDescriptor(id=base64url_to_bytes(c.credential_id)) for c in existing],
    )
    _save_challenge(user.id, bytes_to_base64url(options.challenge), 'register')
    return options_to_json(options)


def authentication_options(user):
    creds = WebAuthnCredential.query.filter_by(user_id=user.id, is_active=True).all()
    if not creds:
        return None
    options = generate_authentication_options(
        rp_id=rp_id(),
        challenge=default_challenge(),
        user_verification=UserVerificationRequirement.PREFERRED,
        allow_credentials=[PublicKeyCredentialDescriptor(id=base64url_to_bytes(c.credential_id)) for c in creds],
    )
    _save_challenge(user.id, bytes_to_base64url(options.challenge), 'login')
    return options_to_json(options)


def verify_registration(user, payload):
    challenge_row = _pop_challenge(user.id, 'register')
    if not challenge_row:
        return None, 'La solicitud de registro expiró, inténtalo de nuevo.'
    try:
        verification = verify_registration_response(
            credential=payload.get('credential'),
            expected_challenge=base64url_to_bytes(challenge_row.challenge),
            expected_origin=origins(),
            expected_rp_id=rp_id(),
        )
    except Exception as exc:
        db.session.rollback()
        return None, f'Verificación fallida: {exc}'
    cred_id = bytes_to_base64url(verification.credential_id)
    if WebAuthnCredential.query.filter_by(user_id=user.id, credential_id=cred_id).first():
        return None, 'Este dispositivo ya está registrado.'
    db.session.add(
        WebAuthnCredential(
            user_id=user.id,
            credential_id=cred_id,
            public_key=bytes_to_base64url(verification.credential_public_key),
            sign_count=verification.sign_count,
            aaguid=verification.aaguid if verification.aaguid else None,
            device_name=(payload.get('device_name') or 'Dispositivo')[:120],
            transports=(payload.get('transports') if payload.get('transports') else None),
        )
    )
    db.session.commit()
    return cred_id, None


def find_user_by_identifier(identifier):
    ident = (identifier or '').strip()
    if not ident:
        return None
    return User.query.filter(db.or_(User.email.ilike(ident), User.login_code.ilike(ident))).first()


def verify_authentication(user, payload):
    challenge_row = _pop_challenge(user.id, 'login')
    if not challenge_row:
        return None, 'La solicitud de inicio de sesión expiró, inténtalo de nuevo.'
    credential = payload.get('credential')
    if not credential or not isinstance(credential, dict):
        return None, 'Credencial inválida.'
    try:
        raw_id = base64url_to_bytes(credential.get('rawId') or '')
    except Exception:
        return None, 'Credencial inválida.'
    cred_id = bytes_to_base64url(raw_id)
    credential_db = WebAuthnCredential.query.filter_by(user_id=user.id, credential_id=cred_id, is_active=True).first()
    if not credential_db:
        return None, 'Dispositivo no registrado para este usuario.'
    try:
        verification = verify_authentication_response(
            credential=credential,
            expected_challenge=base64url_to_bytes(challenge_row.challenge),
            expected_origin=origins(),
            expected_rp_id=rp_id(),
            credential_public_key=base64url_to_bytes(credential_db.public_key),
            credential_current_sign_count=credential_db.sign_count,
        )
    except Exception as exc:
        db.session.rollback()
        return None, f'Verificación fallida: {exc}'
    credential_db.sign_count = verification.new_sign_count
    credential_db.last_used_at = datetime.utcnow()
    db.session.commit()
    return user, None
