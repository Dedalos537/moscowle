"""Web Push propio (RFC 8291 + RFC 8292) y suscripciones."""

import json
import threading
import uuid

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from flask_jwt_extended import create_access_token

from app.extensions import db
from app.models import User
from app.models.push_subscription import PushSubscription
from app.services import web_push as wp


def _user():
    tag = uuid.uuid4().hex[:8]
    u = User(username=f'u{tag}', email=f'{tag}@gmail.com', password='x', role='terapista')
    db.session.add(u)
    db.session.commit()
    return u


def _h(u):
    return {'Authorization': 'Bearer ' + create_access_token(identity=str(u.id))}


def _browser():
    """Claves como las de un navegador: privada P-256 + secreto de autenticación."""
    key = ec.generate_private_key(ec.SECP256R1())
    pub = key.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    auth = b'0123456789abcdef'
    return key, wp.b64u(pub), wp.b64u(auth)


def _decrypt(body, key, p256dh, auth):
    """Descifra como lo hace el navegador (lado receptor del RFC 8291)."""
    salt, idlen = body[:16], body[20]
    as_public = body[21 : 21 + idlen]
    ua_public = wp.b64u_decode(p256dh)
    shared = key.exchange(ec.ECDH(), ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), as_public))
    ikm = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=wp.b64u_decode(auth),
        info=b'WebPush: info\x00' + ua_public + as_public,
    ).derive(shared)
    cek = HKDF(algorithm=hashes.SHA256(), length=16, salt=salt, info=b'Content-Encoding: aes128gcm\x00').derive(ikm)
    nonce = HKDF(algorithm=hashes.SHA256(), length=12, salt=salt, info=b'Content-Encoding: nonce\x00').derive(ikm)
    plain = AESGCM(cek).decrypt(nonce, body[21 + idlen :], None)
    assert plain.endswith(b'\x02')
    return plain[:-1]


def test_encrypt_roundtrip_like_a_browser():
    key, p256dh, auth = _browser()
    body = wp.encrypt('{"title":"Sesión"}'.encode(), p256dh, auth)
    assert int.from_bytes(body[16:20], 'big') == 4096
    assert _decrypt(body, key, p256dh, auth) == '{"title":"Sesión"}'.encode()


def test_vapid_header_is_a_valid_es256_jwt(app):
    with app.app_context():
        key = wp._vapid_key()
        header = wp._vapid_header('https://fcm.googleapis.com/fcm/send/abc', key, 'mailto:x@y.z')
    token = header.split('t=')[1].split(',')[0]
    h, c, s = token.split('.')
    claims = json.loads(wp.b64u_decode(c))
    assert claims['aud'] == 'https://fcm.googleapis.com' and claims['sub'] == 'mailto:x@y.z'
    raw = wp.b64u_decode(s)
    der = encode_dss_signature(int.from_bytes(raw[:32], 'big'), int.from_bytes(raw[32:], 'big'))
    key.public_key().verify(der, f'{h}.{c}'.encode(), ec.ECDSA(hashes.SHA256()))  # no lanza = firma válida
    assert header.split('k=')[1] == wp.public_key()


def test_subscribe_and_unsubscribe(client, app):
    u = _user()
    _, p256dh, auth = _browser()
    sub = {'endpoint': f'https://push.example/{uuid.uuid4().hex}', 'keys': {'p256dh': p256dh, 'auth': auth}}
    assert client.get('/api/push/vapid-key', headers=_h(u)).get_json()['key']
    assert client.post('/api/push/subscribe', json=sub, headers=_h(u)).status_code == 200
    assert PushSubscription.query.filter_by(endpoint=sub['endpoint'], user_id=u.id).count() == 1
    assert client.post('/api/push/subscribe', json={'endpoint': 'http://inseguro'}, headers=_h(u)).status_code == 400
    client.post('/api/push/unsubscribe', json={'endpoint': sub['endpoint']}, headers=_h(u))
    assert PushSubscription.query.filter_by(endpoint=sub['endpoint']).count() == 0


def test_notify_user_sends_and_drops_gone_subscriptions(app, monkeypatch):
    u = _user()
    _, p256dh, auth = _browser()
    alive = PushSubscription(
        user_id=u.id, endpoint=f'https://push.example/{uuid.uuid4().hex}', p256dh=p256dh, auth=auth
    )
    gone = PushSubscription(user_id=u.id, endpoint=f'https://push.example/{uuid.uuid4().hex}', p256dh=p256dh, auth=auth)
    db.session.add_all([alive, gone])
    db.session.commit()
    gone_id = gone.id
    calls = []

    class _Resp:
        def __init__(self, code):
            self.status_code = code

    def fake_post(url, data, headers, timeout):
        calls.append(headers)
        return _Resp(410 if url == gone.endpoint else 201)

    monkeypatch.setattr(wp.requests, 'post', fake_post)
    started = []
    monkeypatch.setattr(threading.Thread, 'start', lambda self: started.append(self) or self.run())
    wp.notify_user(u.id, {'title': 'Hola', 'body': 'x'})
    assert len(calls) == 2 and all(h['Content-Encoding'] == 'aes128gcm' for h in calls)
    db.session.expire_all()
    assert db.session.get(PushSubscription, gone_id) is None
    assert db.session.get(PushSubscription, alive.id).last_ok_at is not None
