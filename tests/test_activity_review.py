"""PRP 012: revisión de actividad por usuario (pendiente y hecho), solo admin."""

import uuid
from datetime import datetime, timedelta
from types import SimpleNamespace

from flask_jwt_extended import create_access_token

from app.extensions import db
from app.models import Appointment, Payment, User
from app.models.activity_event import ActivityEvent
from app.services import activity_review as act


def _user(role, **kw):
    tag = uuid.uuid4().hex[:8]
    kw.setdefault('email', f'{tag}@gmail.com')
    u = User(username=f'{role[:3]}{tag}', password='x', role=role, **kw)
    db.session.add(u)
    db.session.commit()
    return u


def _h(u):
    return {'Authorization': 'Bearer ' + create_access_token(identity=str(u.id))}


def test_only_admin_sees_activity(client, app):
    assert client.get('/admin/api/activity/users', headers=_h(_user('terapista'))).status_code == 403
    assert client.get('/admin/api/activity/users', headers=_h(_user('supervisor'))).status_code == 403
    assert client.get('/admin/api/activity/users', headers=_h(_user('admin'))).status_code == 200


def test_past_unclosed_session_is_pending_until_closed(app):
    ther, pat = _user('terapista'), _user('jugador')
    a = Appointment(
        therapist_id=ther.id,
        patient_id=pat.id,
        title='Terapia',
        start_time=datetime.utcnow() - timedelta(days=2),
        status='scheduled',
    )
    db.session.add(a)
    db.session.commit()
    keys = {p['key']: p for p in act.pending_for(ther)}
    assert keys['sessions_unclosed']['count'] == 1 and keys['sessions_unclosed']['days'] >= 2
    assert act.pending_counts()[ther.id]['high'] >= 1
    a.status = 'completed'
    a.notes = 'Avanzó en atención sostenida.'
    db.session.commit()
    assert 'sessions_unclosed' not in {p['key'] for p in act.pending_for(ther)}


def test_patient_without_real_email_shows_incomplete_profile(app):
    pat = _user('jugador', email=f'noemail_{uuid.uuid4().hex[:8]}@local')
    item = next(p for p in act.pending_for(pat) if p['key'] == 'profile')
    assert 'sin correo real' in item['label']


def test_timeline_joins_sources_and_events(app, client):
    admin = _user('admin')
    pat = _user('jugador')
    db.session.add(
        Payment(patient_id=pat.id, amount=150, method='Yape', date=datetime.utcnow(), created_by_id=admin.id)
    )
    db.session.add(ActivityEvent(user_id=admin.id, action='contracts.updated', summary='Editó contrato #7'))
    db.session.commit()
    data = client.get(f'/admin/api/activity/users/{admin.id}/timeline', headers=_h(admin)).get_json()
    summaries = [e['summary'] for e in data['events']]
    assert any('Registró un pago de S/ 150.00' in s for s in summaries) and 'Editó contrato #7' in summaries
    # Ver el detalle deja rastro (quién miró a quién).
    client.get(f'/admin/api/activity/users/{pat.id}', headers=_h(admin))
    assert ActivityEvent.query.filter_by(user_id=admin.id, action='activity.viewed', entity_id=pat.id).count() == 1


def test_only_whitelisted_writes_are_recorded_and_never_the_body(app):
    admin = _user('admin')

    def req(method, path, rule):
        return SimpleNamespace(
            method=method,
            path=path,
            url_rule=SimpleNamespace(rule=rule),
            view_args={'contract_id': 9},
            headers={},
            remote_addr='192.168.122.1',
            get_json=lambda **k: {'secret': 'no'},
        )

    ok = SimpleNamespace(status_code=200)
    act.maybe_record_request(
        req('PUT', '/admin/api/contracts/9', '/admin/api/contracts/<int:contract_id>'), ok, admin.id
    )
    act.maybe_record_request(req('POST', '/mcp/chat/stream', '/mcp/chat/stream'), ok, admin.id)  # no está en la lista
    act.maybe_record_request(
        req('GET', '/admin/api/contracts/9', '/admin/api/contracts/<int:contract_id>'), ok, admin.id
    )
    act.maybe_record_request(
        req('PUT', '/admin/api/contracts/9', '/admin/api/contracts/<int:contract_id>'),
        SimpleNamespace(status_code=400),
        admin.id,
    )
    rows = ActivityEvent.query.filter_by(user_id=admin.id).all()
    assert [(r.action, r.entity_id) for r in rows] == [('contracts.updated', 9)]
    assert 'secret' not in (rows[0].summary or '') and rows[0].summary == 'Editó contrato #9'


def test_revoke_sessions_and_retention(app):
    from app.models import UserSession

    admin, ther = _user('admin'), _user('terapista')
    db.session.add(
        UserSession(
            user_id=ther.id,
            access_jti=uuid.uuid4().hex,
            refresh_jti=uuid.uuid4().hex,
            expires_at=datetime.utcnow() + timedelta(days=1),
        )
    )
    db.session.commit()
    assert act.revoke_sessions(ther, admin.id) == 1 and act.sessions_of(ther) == []
    old = ActivityEvent(user_id=admin.id, action='x.updated', created_at=datetime.utcnow() - timedelta(days=200))
    db.session.add(old)
    db.session.commit()
    old_id = old.id  # tras borrar, la instancia queda expirada: se guarda el id antes
    assert act.purge_old() >= 1
    db.session.expire_all()
    assert db.session.get(ActivityEvent, old_id) is None
