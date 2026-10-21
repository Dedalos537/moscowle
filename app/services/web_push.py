"""Web Push sin dependencias nuevas: cifrado aes128gcm (RFC 8291) y firma VAPID (RFC 8292) con `cryptography`.

- Las claves VAPID salen de `VAPID_PRIVATE_KEY` (base64url de los 32 bytes privados) o, si no está, se generan
  una vez y se guardan en `system_setting` para que todos los procesos usen las mismas.
- `notify_user` envía en segundo plano a todas las suscripciones del usuario; las que el servicio de push da por
  vencidas (404/410) se borran.
"""

import base64
import json
import os
import threading
import time
from datetime import datetime
from urllib.parse import urlparse

import requests
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from flask import current_app

from app.extensions import db

_SETTING_KEY = 'webpush.vapid_private'
_RECORD_SIZE = 4096
_lock = threading.Lock()
_cache: dict = {}  # 'key': clave privada VAPID ya cargada


def b64u(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip('=')


def b64u_decode(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + '=' * (-len(text) % 4))


def _public_bytes(key) -> bytes:
    return key.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)


def _private_from_b64(text: str):
    return ec.derive_private_key(int.from_bytes(b64u_decode(text), 'big'), ec.SECP256R1())


def _vapid_key():
    """Clave privada VAPID (P-256), estable entre reinicios y procesos."""
    if 'key' in _cache:
        return _cache['key']
    with _lock:
        if 'key' in _cache:
            return _cache['key']
        configured = current_app.config.get('VAPID_PRIVATE_KEY') or os.getenv('VAPID_PRIVATE_KEY')
        if configured:
            _cache['key'] = _private_from_b64(configured.strip())
            return _cache['key']
        from app.models.system_setting import SystemSetting

        row = db.session.get(SystemSetting, _SETTING_KEY)
        if row is None or not row.value:
            key = ec.generate_private_key(ec.SECP256R1())
            raw = key.private_numbers().private_value.to_bytes(32, 'big')
            row = row or SystemSetting(key=_SETTING_KEY)
            row.value = b64u(raw)
            db.session.add(row)
            db.session.commit()
        _cache['key'] = _private_from_b64(row.value)
        return _cache['key']


def public_key() -> str:
    """Clave pública VAPID en base64url (applicationServerKey del navegador)."""
    return b64u(_public_bytes(_vapid_key()))


def _vapid_header(endpoint: str, key, subject: str) -> str:
    url = urlparse(endpoint)
    header = b64u(json.dumps({'typ': 'JWT', 'alg': 'ES256'}, separators=(',', ':')).encode())
    claims = {'aud': f'{url.scheme}://{url.netloc}', 'exp': int(time.time()) + 12 * 3600, 'sub': subject}
    body = b64u(json.dumps(claims, separators=(',', ':')).encode())
    signing_input = f'{header}.{body}'.encode()
    r, s = decode_dss_signature(key.sign(signing_input, ec.ECDSA(hashes.SHA256())))
    signature = r.to_bytes(32, 'big') + s.to_bytes(32, 'big')
    return f'vapid t={header}.{body}.{b64u(signature)}, k={b64u(_public_bytes(key))}'


def encrypt(payload: bytes, p256dh: str, auth: str, *, salt: bytes | None = None, server_key=None) -> bytes:
    """Cuerpo cifrado aes128gcm para la suscripción (un solo registro)."""
    ua_public = b64u_decode(p256dh)
    auth_secret = b64u_decode(auth)
    server_key = server_key or ec.generate_private_key(ec.SECP256R1())
    as_public = _public_bytes(server_key)
    shared = server_key.exchange(ec.ECDH(), ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), ua_public))
    ikm = HKDF(
        algorithm=hashes.SHA256(), length=32, salt=auth_secret, info=b'WebPush: info\x00' + ua_public + as_public
    ).derive(shared)
    salt = salt or os.urandom(16)
    cek = HKDF(algorithm=hashes.SHA256(), length=16, salt=salt, info=b'Content-Encoding: aes128gcm\x00').derive(ikm)
    nonce = HKDF(algorithm=hashes.SHA256(), length=12, salt=salt, info=b'Content-Encoding: nonce\x00').derive(ikm)
    ciphertext = AESGCM(cek).encrypt(nonce, payload + b'\x02', None)
    header = salt + _RECORD_SIZE.to_bytes(4, 'big') + bytes([len(as_public)]) + as_public
    return header + ciphertext


def send(subscription: dict, data: dict, key, subject: str, urgency: str = 'normal') -> int:
    """Envía un aviso a una suscripción; devuelve el código HTTP del servicio de push."""
    body = encrypt(json.dumps(data, ensure_ascii=False).encode(), subscription['p256dh'], subscription['auth'])
    headers = {
        'Content-Encoding': 'aes128gcm',
        'Content-Type': 'application/octet-stream',
        'TTL': '86400',
        'Urgency': urgency,
        'Authorization': _vapid_header(subscription['endpoint'], key, subject),
    }
    resp = requests.post(subscription['endpoint'], data=body, headers=headers, timeout=10)
    return resp.status_code


def notify_user(user_id: int, data: dict, urgency: str = 'normal') -> None:
    """Aviso a todos los navegadores suscritos del usuario, sin frenar la petición que lo origina."""
    from app.models.push_subscription import PushSubscription

    subs = [
        {'id': s.id, 'endpoint': s.endpoint, 'p256dh': s.p256dh, 'auth': s.auth}
        for s in PushSubscription.query.filter_by(user_id=user_id).all()
    ]
    if not subs:
        return
    key = _vapid_key()
    subject = current_app.config.get('VAPID_SUBJECT', 'mailto:info@centrojuanpabloii.com')
    app = current_app._get_current_object()

    def run():
        dead, ok = [], []
        for sub in subs:
            try:
                code = send(sub, data, key, subject, urgency)
            except Exception as exc:  # noqa: BLE001 - un navegador caído no frena a los demás
                app.logger.debug(f'web push fallo de red: {exc}')
                continue
            if code in (404, 410):
                dead.append(sub['id'])
            elif code < 300:
                ok.append(sub['id'])
            else:
                app.logger.warning(f'web push {code} para la suscripción {sub["id"]}')
        if not (dead or ok):
            return
        with app.app_context():
            try:
                if dead:
                    PushSubscription.query.filter(PushSubscription.id.in_(dead)).delete(synchronize_session=False)
                if ok:
                    PushSubscription.query.filter(PushSubscription.id.in_(ok)).update(
                        {'last_ok_at': datetime.utcnow()}, synchronize_session=False
                    )
                db.session.commit()
            except Exception:  # noqa: BLE001
                db.session.rollback()

    threading.Thread(target=run, name='web-push', daemon=True).start()
