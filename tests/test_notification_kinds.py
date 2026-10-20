"""PRP 011 · E2: cada notificación lleva su tipo y cómo mostrarse (badge, toast, snackbar, banner, modal, push)."""

import uuid

from flask_jwt_extended import create_access_token

from app.extensions import db
from app.models import User
from app.services import notification_kinds as nk


def _user(role='admin'):
    tag = uuid.uuid4().hex[:8]
    u = User(username=f'{role[:3]}{tag}', email=f'{tag}@nk.test', password='x', role=role)
    db.session.add(u)
    db.session.commit()
    return u


def test_kind_is_inferred_from_the_old_event_types():
    assert nk.resolve_kind(event_type='message') == 'message.new'
    assert nk.resolve_kind(event_type='sla_breach') == 'sla.breach'
    assert nk.resolve_kind(category='system', metadata={'alertname': 'ServicioCaido'}) == 'server.alert'
    assert nk.resolve_kind(kind='crisis.alert', event_type='message') == 'crisis.alert'  # el explícito gana
    assert nk.resolve_kind(event_type='algo_nuevo') == 'legacy'


def test_presentation_follows_the_matrix_and_priority():
    assert nk.presentation_for('message.new') == ['badge', 'snackbar', 'push']
    assert 'modal' in nk.presentation_for('security.event')
    assert nk.presentation_for('legacy', 'urgent') == ['badge', 'banner', 'push']  # urgente sube de nivel
    assert nk.presentation_for('legacy', 'high') == ['badge', 'toast']
    resolved = nk.presentation_for('server.alert', 'urgent', resolved=True)
    assert 'banner' not in resolved and 'toast' in resolved  # «resuelto» avisa sin alarmar
    assert nk.presentation_for('action.confirmed') == ['toast']  # sin badge: no es algo pendiente


def test_every_kind_uses_known_presentations():
    for kind, spec in nk.KINDS.items():
        assert set(spec['presentation']) <= set(nk.PRESENTATIONS), kind


def test_socket_event_carries_kind_presentation_and_action(app, monkeypatch):
    from app.services import notification_service as ns

    sent = []
    monkeypatch.setattr(ns.socketio, 'emit', lambda name, data, room=None: sent.append((name, data, room)))
    u = _user()
    ns.NotificationService().notify_user(
        u.id,
        'Juan te escribió',
        title='Nuevo mensaje',
        category='message',
        link='/admin/messages',
        event_type='message',
        event_kwargs={'sender_id': 7},
        skip_telegram=True,
    )
    name, data, room = sent[-1]
    assert name == 'notification:new' and room == f'user_{u.id}'
    assert data['kind'] == 'message.new' and data['presentation'] == ['badge', 'snackbar', 'push']
    assert data['action'] == {'label': 'Abrir chat', 'link': '/admin/messages'}


def test_groups_api_and_catalog_expose_the_kind(app, client, monkeypatch):
    from app.services import notification_service as ns

    monkeypatch.setattr(ns.socketio, 'emit', lambda *a, **k: None)
    u = _user()
    ns.NotificationService().create_notification(
        u.id,
        'Servidor caído',
        category='system',
        priority='urgent',
        kind='server.alert',
        metadata_json={'alertname': 'ServicioCriticoCaido'},
    )
    headers = {'Authorization': 'Bearer ' + create_access_token(identity=str(u.id))}
    groups = client.get('/api/notifications/groups', headers=headers).get_json()
    g = next(x for x in groups if x['kind'] == 'server.alert')
    assert 'banner' in g['presentation']
    cat = client.get('/api/notifications/kinds', headers=headers).get_json()
    assert 'message.new' in cat['kinds'] and 'modal' in cat['presentations']
