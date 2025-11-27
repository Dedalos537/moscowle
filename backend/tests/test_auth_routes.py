import json

from app.extensions import db
from app.models.user import User


def create_user(db, email: str, password: str, role_id: int = None):
    user = User(email=email, role_id=role_id or None)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user


def test_login_endpoint(client, db, app):
    # create a normal user
    create_user(db, 'normal@example.com', 'normalpass', role_id=2)

    resp = client.post('/api/auth/login', json={'email': 'normal@example.com', 'password': 'normalpass'})
    assert resp.status_code == 200
    body = resp.get_json()
    assert 'access_token' in body
    assert 'user' in body
    assert body['user']['email'] == 'normal@example.com'


def test_register_requires_admin_and_allows_creation(client, db, app):
    # create admin user (role_id == 1)
    admin = create_user(db, 'admin@example.com', 'adminpass', role_id=1)

    # login admin to get token
    login = client.post('/api/auth/login', json={'email': 'admin@example.com', 'password': 'adminpass'})
    assert login.status_code == 200
    token = login.get_json()['access_token']

    # register a new user via admin token
    headers = {'Authorization': f'Bearer {token}'}
    payload = {'email': 'newuser@example.com', 'password': 'newpassword', 'role': 'therapist'}
    reg = client.post('/api/auth/register', json=payload, headers=headers)
    assert reg.status_code == 201
    body = reg.get_json()
    assert body['user']['email'] == 'newuser@example.com'


def test_register_forbidden_for_non_admin(client, db, app):
    # create non-admin user
    create_user(db, 'user2@example.com', 'user2pass', role_id=2)

    login = client.post('/api/auth/login', json={'email': 'user2@example.com', 'password': 'user2pass'})
    assert login.status_code == 200
    token = login.get_json()['access_token']

    headers = {'Authorization': f'Bearer {token}'}
    payload = {'email': 'forbid@example.com', 'password': 'pw123456', 'role': 'therapist'}
    reg = client.post('/api/auth/register', json=payload, headers=headers)
    assert reg.status_code == 403
