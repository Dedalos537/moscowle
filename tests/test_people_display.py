"""Ajuste del centro «solo códigos» y directorio de personas según el rol."""

import uuid

from flask_jwt_extended import create_access_token

from app.extensions import db
from app.models import User


def _user(role, **kw):
    tag = uuid.uuid4().hex[:8]
    u = User(username=f'{role[:3]}{tag}', email=f'{tag}@ppl.test', password='x', role=role, **kw)
    db.session.add(u)
    db.session.commit()
    return u


def _h(u):
    return {'Authorization': 'Bearer ' + create_access_token(identity=str(u.id))}


def test_only_admin_changes_center_setting(app, client):
    with app.app_context():
        admin, ther = _user('admin'), _user('terapista')
        assert client.get('/api/people/settings', headers=_h(ther)).get_json()['center_code_only'] is False
        r = client.put('/api/people/settings', headers=_h(ther), json={'center_code_only': True})
        assert r.status_code == 403
        r = client.put('/api/people/settings', headers=_h(admin), json={'center_code_only': True})
        assert r.get_json()['center_code_only'] is True
        assert client.get('/api/people/settings', headers=_h(ther)).get_json()['center_code_only'] is True
        client.put('/api/people/settings', headers=_h(admin), json={'center_code_only': False})


def test_directory_is_scoped_by_role(app, client):
    with app.app_context():
        ther = _user('terapista')
        mine = _user('jugador', login_code=uuid.uuid4().hex[:6].upper())
        other = _user('jugador')
        mine.therapists.append(ther)
        db.session.commit()

        ids = {p['id'] for p in client.get('/api/people/directory', headers=_h(ther)).get_json()['people']}
        assert mine.id in ids and ther.id in ids and other.id not in ids
        row = next(
            p for p in client.get('/api/people/directory', headers=_h(ther)).get_json()['people'] if p['id'] == mine.id
        )
        assert row['code'] == mine.login_code

        assert client.get('/api/people/directory', headers=_h(mine)).get_json()['people'] == []
