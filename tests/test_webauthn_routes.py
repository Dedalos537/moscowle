import json

import pytest
from flask import g

from app.extensions import bcrypt
from app.models import User
from app.models.webauthn import WebAuthnCredential


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
    resp = client.delete('/api/auth/webauthn/credentials/999')
    assert resp.status_code == 404
