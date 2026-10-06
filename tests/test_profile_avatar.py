import io
import json

import pytest
from PIL import Image

from app.extensions import bcrypt
from app.models import User


@pytest.fixture(autouse=True)
def _fresh_login_per_request(app, tmp_path):
    """El `g` del app context de sesión cachea el usuario de Flask-Login entre peticiones; se limpia solo aquí."""

    def _clear(exc):
        from flask import g

        g.pop('_login_user', None)

    previous = app.config.get('UPLOAD_FOLDER')
    app.config['UPLOAD_FOLDER'] = str(tmp_path)
    funcs = app.teardown_request_funcs.setdefault(None, [])
    funcs.append(_clear)
    yield
    funcs.remove(_clear)
    app.config['UPLOAD_FOLDER'] = previous


def _user(session, email, role):
    User.query.filter_by(email=email).delete()
    u = User(
        username=email.split('@')[0],
        email=email,
        password=bcrypt.generate_password_hash('secret123').decode(),
        role=role,
    )
    session.add(u)
    session.commit()
    return u


def _login(app, email):
    c = app.test_client()
    r = c.post(
        '/api/login', content_type='application/json', data=json.dumps({'email': email, 'password': 'secret123'})
    )
    assert r.status_code == 200, r.get_data(as_text=True)
    return c


def _png(w=600, h=300, color=(200, 30, 30)):
    buf = io.BytesIO()
    Image.new('RGB', (w, h), color).save(buf, 'PNG')
    buf.seek(0)
    return buf


@pytest.mark.parametrize('role', ['admin', 'terapista', 'jugador', 'supervisor'])
def test_every_role_can_set_and_read_avatar(app, session, role):
    email = f'av-{role}@avatar.test'
    user = _user(session, email, role)
    c = _login(app, email)
    r = c.post('/api/profile/avatar', data={'file': (_png(), 'foto.png')}, content_type='multipart/form-data')
    assert r.status_code == 200, r.get_data(as_text=True)
    url = r.get_json()['avatar']
    assert url.startswith(f'/api/profile/avatar/{user.id}?v=')
    got = c.get(url)
    assert got.status_code == 200 and got.mimetype == 'image/jpeg'
    img = Image.open(io.BytesIO(got.data))
    assert img.size == (256, 256)  # recortada a cuadrado
    assert c.delete('/api/profile/avatar').status_code == 200
    assert c.get(f'/api/profile/avatar/{user.id}').status_code == 404


def test_rejects_non_images_and_oversized(app, session):
    _user(session, 'bad@avatar.test', 'terapista')
    c = _login(app, 'bad@avatar.test')
    r = c.post(
        '/api/profile/avatar',
        data={'file': (io.BytesIO(b'<script>alert(1)</script>'), 'x.png')},
        content_type='multipart/form-data',
    )
    assert r.status_code == 400
    r = c.post(
        '/api/profile/avatar',
        data={'file': (io.BytesIO(b'0' * (5 * 1024 * 1024 + 10)), 'big.png')},
        content_type='multipart/form-data',
    )
    assert r.status_code == 413
    assert c.post('/api/profile/avatar').status_code == 400


def test_avatar_requires_login(app):
    c = app.test_client()
    assert c.get('/api/profile/avatar/1').status_code in (401, 403, 422)
    assert c.post(
        '/api/profile/avatar', data={'file': (_png(), 'a.png')}, content_type='multipart/form-data'
    ).status_code in (401, 403, 422)


@pytest.mark.parametrize('role', ['admin', 'supervisor', 'terapista', 'jugador'])
def test_every_role_can_start_fingerprint_registration(app, session, role):
    email = f'fp-{role}@avatar.test'
    _user(session, email, role)
    c = _login(app, email)
    r = c.post('/api/auth/webauthn/register/options', content_type='application/json', data='{}')
    assert r.status_code == 200, r.get_data(as_text=True)
    assert r.get_json()['options']['challenge']
    assert c.get('/api/auth/webauthn/credentials').status_code == 200
