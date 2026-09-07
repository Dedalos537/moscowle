import base64
import hashlib
import json
import os

import cbor2
import pytest
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from flask import g

from app.extensions import bcrypt
from app.models import User
from app.models.webauthn import WebAuthnCredential


def _b64url(b):
    return base64.urlsafe_b64encode(b).rstrip(b'=').decode()


def _b64url_bytes(s):
    pad = '=' * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


def _make_registration_credential(app, challenge, key):
    rp_id = app.config.get('WEBAUTHN_RP_ID', 'localhost')
    origin = app.config.get('WEBAUTHN_ORIGINS')
    origin = origin[0] if isinstance(origin, list) else origin
    rp_hash = hashlib.sha256(rp_id.encode()).digest()
    pub = key.public_key().public_numbers()
    pub_cbor = cbor2.dumps({1: 2, 3: -7, -1: 1, -2: pub.x.to_bytes(32, 'big'), -3: pub.y.to_bytes(32, 'big')})
    cred_id = os.urandom(32)
    cd = json.dumps(
        {'type': 'webauthn.create', 'challenge': challenge, 'origin': origin, 'crossOrigin': False},
        separators=(',', ':'),
    ).encode()
    auth_data = (
        rp_hash
        + bytes([0x41])
        + (0).to_bytes(4, 'big')
        + (0).to_bytes(16, 'big')
        + len(cred_id).to_bytes(2, 'big')
        + cred_id
        + pub_cbor
    )
    att = cbor2.dumps({'fmt': 'none', 'attStmt': {}, 'authData': auth_data})
    return {
        'id': _b64url(cred_id),
        'rawId': _b64url(cred_id),
        'type': 'public-key',
        'response': {'clientDataJSON': _b64url(cd), 'attestationObject': _b64url(att)},
        'clientExtensionResults': {},
    }, cred_id


def _make_authentication_credential(app, challenge, key, cred_id, rp_hash, sign_count=1):
    origin = app.config.get('WEBAUTHN_ORIGINS')
    origin = origin[0] if isinstance(origin, list) else origin
    cd = json.dumps(
        {'type': 'webauthn.get', 'challenge': challenge, 'origin': origin, 'crossOrigin': False}, separators=(',', ':')
    ).encode()
    sig_auth_data = rp_hash + bytes([0x05]) + sign_count.to_bytes(4, 'big')
    sig = key.sign(sig_auth_data + hashlib.sha256(cd).digest(), ec.ECDSA(hashes.SHA256()))
    return {
        'id': _b64url(cred_id),
        'rawId': _b64url(cred_id),
        'type': 'public-key',
        'response': {
            'clientDataJSON': _b64url(cd),
            'authenticatorData': _b64url(sig_auth_data),
            'signature': _b64url(sig),
            'userHandle': None,
        },
    }


@pytest.fixture(autouse=True)
def _reset_flask_login_user(app):
    g.pop('_login_user', None)
    g.pop('current_user', None)
    yield
    g.pop('_login_user', None)
    g.pop('current_user', None)


@pytest.fixture
def webauthn_staff(session):
    for user in User.query.filter(User.email.ilike('%@wf.test')).all():
        WebAuthnCredential.query.filter_by(user_id=user.id).delete()
    User.query.filter(User.email.ilike('%@wf.test')).delete()
    session.flush()
    user = User(
        username='Staff Huella',
        email='staff@wf.test',
        password=bcrypt.generate_password_hash('secret123').decode('utf-8'),
        role='admin',
    )
    session.add(user)
    session.commit()
    return user


def _auth_client(client, email, password):
    resp = client.post(
        '/api/login',
        content_type='application/json',
        data=json.dumps({'email': email, 'password': password}),
    )
    assert resp.status_code == 200
    return client


def test_register_options_requires_jwt(client):
    resp = client.post('/api/auth/webauthn/register/options', json={})
    assert resp.status_code in (401, 422)


def test_register_options_with_jwt(client, webauthn_staff):
    _auth_client(client, 'staff@wf.test', 'secret123')
    resp = client.post('/api/auth/webauthn/register/options', json={})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['success'] is True
    assert data['options']['challenge']
    assert data['options']['user']['name'] == 'staff@wf.test'


def test_login_options_unknown_identifier(client):
    resp = client.post(
        '/api/auth/webauthn/login/options',
        json={'identifier': 'noexiste@wf.test'},
    )
    assert resp.status_code == 404


def test_login_options_user_without_credentials(client, webauthn_staff):
    resp = client.post(
        '/api/auth/webauthn/login/options',
        json={'identifier': 'staff@wf.test'},
    )
    assert resp.status_code == 404
    assert 'huella' in resp.get_json()['error']


def test_login_options_with_credential(session, client, webauthn_staff):
    session.add(
        WebAuthnCredential(
            user_id=webauthn_staff.id,
            credential_id='Y3JlZGRpZA',
            public_key='cHVia2V5',
            sign_count=0,
            device_name='Test',
        )
    )
    session.commit()
    resp = client.post(
        '/api/auth/webauthn/login/options',
        json={'identifier': 'staff@wf.test'},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['success'] is True
    assert data['options']['allowCredentials'][0]['id'] == 'Y3JlZGRpZA'


def test_register_verify_invalid_credential(client, webauthn_staff):
    _auth_client(client, 'staff@wf.test', 'secret123')
    client.post('/api/auth/webauthn/register/options', json={})
    resp = client.post(
        '/api/auth/webauthn/register/verify',
        json={'credential': {'response': {'clientDataJSON': 'abc'}}},
    )
    assert resp.status_code == 400
    assert 'error' in resp.get_json()


def test_login_verify_invalid_credential(session, client, webauthn_staff):
    session.add(
        WebAuthnCredential(
            user_id=webauthn_staff.id,
            credential_id='Y3JlZGR2ZXI',
            public_key='cHVia2V5',
            sign_count=0,
            device_name='Test',
        )
    )
    session.commit()
    client.post(
        '/api/auth/webauthn/login/options',
        json={'identifier': 'staff@wf.test'},
    )
    resp = client.post(
        '/api/auth/webauthn/login/verify',
        json={
            'identifier': 'staff@wf.test',
            'credential': {'response': {'clientDataJSON': 'abc'}},
        },
    )
    assert resp.status_code == 401
    assert 'error' in resp.get_json()


def test_credentials_list_and_delete(client, webauthn_staff):
    _auth_client(client, 'staff@wf.test', 'secret123')
    resp = client.get('/api/auth/webauthn/credentials')
    assert resp.status_code == 200
    assert resp.get_json()['credentials'] == []
    assert resp.headers.get('Cache-Control') == 'no-store, max-age=0'
    resp = client.delete('/api/auth/webauthn/credentials/999')
    assert resp.status_code == 404


def test_webauthn_register_and_login_full_flow(app, client, webauthn_staff):
    rp_hash = hashlib.sha256(app.config.get('WEBAUTHN_RP_ID', 'localhost').encode()).digest()
    key = ec.generate_private_key(ec.SECP256R1())
    _auth_client(client, 'staff@wf.test', 'secret123')

    resp = client.post('/api/auth/webauthn/register/options', json={})
    assert resp.status_code == 200
    challenge = resp.get_json()['options']['challenge']

    credential, cred_id = _make_registration_credential(app, challenge, key)
    resp = client.post(
        '/api/auth/webauthn/register/verify',
        json={
            'credential': credential,
            'device_name': 'Samsung Galaxy',
        },
    )
    assert resp.status_code == 200, resp.get_json()
    assert resp.get_json()['credential_id'] == _b64url(cred_id)
    assert WebAuthnCredential.query.filter_by(user_id=webauthn_staff.id, is_active=True).count() == 1

    resp = client.post('/api/auth/webauthn/login/options', json={'identifier': 'staff@wf.test'})
    assert resp.status_code == 200
    login_challenge = resp.get_json()['options']['challenge']
    assert resp.get_json()['options']['allowCredentials'][0]['id'] == _b64url(cred_id)

    login_credential = _make_authentication_credential(app, login_challenge, key, cred_id, rp_hash)
    resp = client.post(
        '/api/auth/webauthn/login/verify',
        json={
            'identifier': 'staff@wf.test',
            'credential': login_credential,
        },
    )
    assert resp.status_code == 200, resp.get_json()
    data = resp.get_json()
    assert data['success'] is True
    assert data['user']['email'] == 'staff@wf.test'
    assert data['access_token']

    cred = WebAuthnCredential.query.filter_by(credential_id=_b64url(cred_id)).first()
    assert cred.sign_count == 1
    assert cred.aaguid == '00000000-0000-0000-0000-000000000000'
