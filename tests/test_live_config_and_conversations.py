"""Configuración que de verdad se aplica y se ve en vivo: notificaciones, canales de aviso, FAQ y conversaciones del bot."""

import uuid

import pytest
from flask_jwt_extended import create_access_token

import app.services.telegram_bot_service as tbs
from app.extensions import db
from app.models import BotConfig, BotConversation, BotMessage, Faq, User
from app.services import channel_settings, faq_service, live_sync
from app.services.notification_service import NotificationService


def _user(role='admin', **kw):
    tag = uuid.uuid4().hex[:8]
    u = User(username=f'{role[:3]}{tag}', email=f'{tag}@live.test', password='x', role=role, **kw)
    db.session.add(u)
    db.session.commit()
    return u


def _h(user):
    return {'Authorization': 'Bearer ' + create_access_token(identity=str(user.id))}


@pytest.fixture
def admin(session):
    return _user('admin')


@pytest.fixture
def cfg(app):
    c = BotConfig.get_or_create()
    saved = {
        k: getattr(c, k)
        for k in (
            'intervention_enabled',
            'auto_faq_enabled',
            'auto_faq_threshold',
            'notify_supervision_enabled',
            'enabled',
        )
    }
    c.intervention_enabled, c.auto_faq_enabled, c.auto_faq_threshold, c.enabled = True, True, 3, True
    db.session.commit()
    yield c
    for k, v in saved.items():
        setattr(c, k, v)
    db.session.commit()


# ───────────────────────── notificaciones: interruptor maestro y categorías
def test_master_toggle_persists_and_is_returned(client, admin):
    h = _h(admin)
    assert (
        client.put('/api/notifications/preferences', json={'notifications_enabled': False}, headers=h).status_code
        == 200
    )
    got = client.get('/api/notifications/preferences', headers=h).get_json()
    assert got['notifications_enabled'] is False
    client.put('/api/notifications/preferences', json={'notifications_enabled': True}, headers=h)
    assert client.get('/api/notifications/preferences', headers=h).get_json()['notifications_enabled'] is True


def test_master_off_blocks_every_notification(app, admin):
    svc = NotificationService()
    svc.update_preferences(admin.id, {'notifications_enabled': False})
    assert svc.notify_user(admin.id, 'hola', title='t', category='system') is None
    assert svc.create_notification(admin.id, 'interno', title='t', category='report') is None
    svc.update_preferences(admin.id, {'notifications_enabled': True})
    assert svc.notify_user(admin.id, 'hola', title='t', category='system') is not None


def test_categories_inherit_their_group_toggle(app, admin):
    svc = NotificationService()
    svc.update_preferences(admin.id, {'activity_enabled': False})
    for category in ('activity', 'message', 'session', 'game', 'audit', 'contact'):
        assert svc.notify_user(admin.id, 'x', title='t', category=category) is None, category
    assert svc.notify_user(admin.id, 'x', title='t', category='payment') is not None


def test_preferences_reject_invalid_values(client, admin):
    h = _h(admin)
    assert client.put('/api/notifications/preferences', json={'debt_enabled': 'no'}, headers=h).status_code == 400
    assert (
        client.put('/api/notifications/preferences', json={'digest_channel': 'palomas'}, headers=h).status_code == 400
    )
    assert (
        client.put('/api/notifications/preferences', json={'digest_channel': 'telegram'}, headers=h).status_code == 200
    )


def test_saving_preferences_bumps_the_users_live_version(client, admin):
    before = live_sync.versions([f'notif_prefs:{admin.id}'])[f'notif_prefs:{admin.id}']
    client.put('/api/notifications/preferences', json={'sound_enabled': False}, headers=_h(admin))
    after = client.get('/api/live/versions?scopes=notif_prefs', headers=_h(admin)).get_json()['notif_prefs']
    assert after == before + 1


# ───────────────────────── versiones en vivo
def test_live_versions_scopes_are_staff_only(client, admin):
    therapist = _user('terapista')
    live_sync.bump('bot_config')
    assert client.get('/api/live/versions?scopes=bot_config', headers=_h(admin)).get_json()['bot_config'] >= 1
    assert 'bot_config' not in client.get('/api/live/versions?scopes=bot_config', headers=_h(therapist)).get_json()


def test_bot_config_write_bumps_version(client, admin, cfg):
    before = live_sync.versions(['bot_config'])['bot_config']
    assert client.put('/api/telegram/config', json={'bot_name': 'Chasqui'}, headers=_h(admin)).status_code == 200
    assert live_sync.versions(['bot_config'])['bot_config'] == before + 1
    client.put('/api/telegram/config', json={'bot_name': '   '}, headers=_h(admin))  # inválido: no cambia versión
    assert live_sync.versions(['bot_config'])['bot_config'] == before + 1


# ───────────────────────── canales de aviso persistentes
def test_channel_settings_persist_in_db_and_can_be_cleared(client, admin):
    h = _h(admin)
    r = client.post(
        '/api/health/notifications/config',
        json={'destination': '+51 921 507 470', 'sms_template': 'Hola {patient_name}, debes S/ {amount:.2f}'},
        headers=h,
    )
    assert r.status_code == 200, r.get_data(as_text=True)
    assert channel_settings.get('destination') == '+51921507470'
    got = client.get('/api/health/notifications/config', headers=h).get_json()
    assert got['destination'] == '+51921507470' and '{amount' in got['sms_template']
    client.post('/api/health/notifications/config', json={'destination': ''}, headers=h)  # antes no se podía vaciar
    assert channel_settings.get('destination') == ''


def test_channel_settings_validation(client, admin):
    h = _h(admin)
    url = '/api/health/notifications/config'
    assert client.post(url, json={'destination': 'abc'}, headers=h).status_code == 400
    assert (
        client.post(url, json={'sms_template': 'Hola {nombre}'}, headers=h).status_code == 400
    )  # variable inexistente
    assert (
        client.post(url, json={'whatsapp_template': '{patient_name.__class__}'}, headers=h).status_code == 400
    )  # inyección
    assert client.post(url, json={'whatsapp_template': 'x' * 1001}, headers=h).status_code == 400
    assert client.post(url, json={'whatsapp_template': 'Hola {patient_name'}, headers=h).status_code == 400


def test_only_admin_can_change_channels(client):
    sup = _user('supervisor')
    assert (
        client.post(
            '/api/health/notifications/config', json={'destination': '+51921507470'}, headers=_h(sup)
        ).status_code
        == 403
    )
    assert client.get('/api/health/notifications/config', headers=_h(sup)).status_code == 200


# ───────────────────────── FAQ automática
def test_faq_is_proposed_as_soon_as_the_threshold_is_reached(app, cfg):
    Faq.query.filter(Faq.source == 'auto_proposed').delete()
    faq_service._unanswered.clear()
    db.session.commit()
    q = 'Hola ¿cuánto cuesta la terapia grupal para niños en la sede norte?'
    before = Faq.query.filter_by(source='auto_proposed').count()
    faq_service.note_unanswered(q)
    faq_service.note_unanswered(q)
    assert Faq.query.filter_by(source='auto_proposed').count() == before  # aún no llega al umbral (3)
    faq_service.note_unanswered(q)
    assert Faq.query.filter_by(source='auto_proposed').count() == before + 1


def test_similar_phrasings_count_together(app, cfg):
    faq_service._unanswered.clear()
    cfg.auto_faq_threshold = 2
    db.session.commit()
    before = Faq.query.filter_by(source='auto_proposed').count()
    faq_service.note_unanswered('cuanto cuesta la terapia de lenguaje para ninos')
    faq_service.note_unanswered('precio terapia de lenguaje ninos cuanto cuesta')
    assert Faq.query.filter_by(source='auto_proposed').count() == before + 1


def test_auto_faq_off_never_proposes(app, cfg):
    faq_service._unanswered.clear()
    cfg.auto_faq_enabled = False
    db.session.commit()
    before = Faq.query.filter_by(source='auto_proposed').count()
    for _ in range(5):
        faq_service.note_unanswered('pregunta que nadie sabe responder sobre horarios especiales')
    assert Faq.query.filter_by(source='auto_proposed').count() == before


def test_unanswered_detection_is_shared_across_channels(app, cfg):
    assert faq_service.looks_unanswered({'response': 'Lo siento, no tengo esa información.'})
    assert not faq_service.looks_unanswered({'response': 'Hay 12 pacientes activos hoy en el centro.'})
    assert not faq_service.looks_unanswered({'response': 'no sé', 'tool_calls': [{'name': 'x'}]})


# ───────────────────────── conversaciones en vivo (Telegram)
@pytest.fixture
def telegram(app, monkeypatch, cfg):
    app.config['TELEGRAM_BOT_TOKEN'] = 'test-token'
    sent = []

    def fake(method, data=None, bot_token=None):
        if method == 'sendMessage':
            sent.append(data)
            return {'result': {'message_id': 100 + len(sent)}}
        return {'result': {}}

    monkeypatch.setattr(tbs, '_tg_request', fake)
    chat = int(uuid.uuid4().int % 10**9) + 10**9
    yield chat, sent
    app.config.pop('TELEGRAM_BOT_TOKEN', None)


def _incoming(chat, text, name='Laura'):
    return {
        'message': {'chat': {'id': chat}, 'from': {'id': chat, 'first_name': name, 'username': 'laura'}, 'text': text}
    }


def test_telegram_messages_are_logged_both_ways(app, telegram):
    chat, sent = telegram
    tbs.handle_webhook_update(_incoming(chat, '/start'))
    conv = BotConversation.query.filter_by(channel='telegram', chat_key=str(chat)).one()
    msgs = conv.messages.order_by(BotMessage.id).all()
    assert [m.direction for m in msgs][:2] == ['in', 'out']
    assert msgs[0].sender == 'contact' and msgs[0].text == '/start'
    assert msgs[1].sender == 'bot'
    assert conv.contact_name == 'Laura' and conv.contact_handle == '@laura' and conv.unread_count >= 1


def test_takeover_silences_the_bot_and_admin_reply_is_delivered(client, app, admin, telegram):
    chat, sent = telegram
    tbs.handle_webhook_update(_incoming(chat, 'hola'))
    conv = BotConversation.query.filter_by(chat_key=str(chat)).one()
    h = _h(admin)
    assert (
        client.post(f'/api/bot/conversations/{conv.id}/takeover', json={'enabled': True}, headers=h).status_code == 200
    )
    sent.clear()
    tbs.handle_webhook_update(_incoming(chat, '¿me ayudas con mi pago?'))
    assert sent == []  # el bot calló
    assert conv.messages.order_by(BotMessage.id.desc()).first().text == '¿me ayudas con mi pago?'

    r = client.post(f'/api/bot/conversations/{conv.id}/messages', json={'text': 'Claro, te ayudo yo.'}, headers=h)
    assert r.status_code == 201 and r.get_json()['message']['sender'] == 'admin'
    assert sent and sent[-1]['text'] == 'Claro, te ayudo yo.' and sent[-1]['chat_id'] == chat

    client.post(f'/api/bot/conversations/{conv.id}/takeover', json={'enabled': False}, headers=h)
    sent.clear()
    tbs.handle_webhook_update(_incoming(chat, '/ayuda'))
    assert sent  # vuelve a contestar el bot


def test_thread_supports_incremental_polling_and_mark_read(client, admin, telegram):
    chat, _ = telegram
    h = _h(admin)
    tbs.handle_webhook_update(_incoming(chat, 'uno'))
    conv = BotConversation.query.filter_by(chat_key=str(chat)).one()
    first = client.get(f'/api/bot/conversations/{conv.id}/messages?mark_read=1', headers=h).get_json()
    last_id = first['messages'][-1]['id']
    tbs.handle_webhook_update(_incoming(chat, 'dos'))
    new = client.get(f'/api/bot/conversations/{conv.id}/messages?after_id={last_id}', headers=h).get_json()
    assert [m['text'] for m in new['messages'] if m['sender'] == 'contact'] == ['dos']
    lst = client.get('/api/bot/conversations', headers=h).get_json()
    assert (
        any(c['id'] == conv.id and c['unread'] >= 1 for c in lst['conversations'])
        and lst['latest_message_id'] >= new['messages'][-1]['id']
    )


def test_intervention_disabled_blocks_replies_and_takeover(client, admin, telegram, cfg):
    chat, _ = telegram
    tbs.handle_webhook_update(_incoming(chat, 'hola'))
    conv = BotConversation.query.filter_by(chat_key=str(chat)).one()
    cfg.intervention_enabled = False
    db.session.commit()
    h = _h(admin)
    assert client.post(f'/api/bot/conversations/{conv.id}/messages', json={'text': 'x'}, headers=h).status_code == 403
    assert (
        client.post(f'/api/bot/conversations/{conv.id}/takeover', json={'enabled': True}, headers=h).status_code == 403
    )


def test_conversations_are_admin_only(client, telegram):
    ther = _user('terapista')
    assert client.get('/api/bot/conversations', headers=_h(ther)).status_code == 403


# ───────────────────────── WhatsApp entrante
def test_whatsapp_incoming_is_logged_and_linked_to_a_known_user(app, admin, cfg, monkeypatch):
    from app.services import whatsapp_inbound

    patient = _user('jugador', phone='+51 987 654 321')
    saved = whatsapp_inbound.handle_incoming(
        {'phone': '51987654321', 'name': 'Mamá de Sofía', 'text': 'Buenos días, ¿hay cupo?', 'kind': 'text'}
    )
    assert saved is not None
    conv = BotConversation.query.filter_by(channel='whatsapp', chat_key='51987654321').one()
    assert conv.user_id == patient.id and conv.contact_name == 'Mamá de Sofía' and conv.unread_count >= 1


def test_whatsapp_admin_reply_goes_through_the_bridge(client, admin, monkeypatch):
    from app.services import whatsapp_inbound
    from app.services.whatsapp_service import whatsapp_service

    whatsapp_inbound.handle_incoming({'phone': '51911222333', 'text': 'hola', 'kind': 'text'})
    conv = BotConversation.query.filter_by(channel='whatsapp', chat_key='51911222333').one()
    calls = []
    monkeypatch.setattr(
        whatsapp_service,
        'send_message',
        lambda phone, text, *a, **k: calls.append((phone, text)) or {'provider_message_id': 'x'},
    )
    r = client.post(
        f'/api/bot/conversations/{conv.id}/messages', json={'text': 'Hola, sí hay cupo.'}, headers=_h(admin)
    )
    assert r.status_code == 201 and calls == [('51911222333', 'Hola, sí hay cupo.')]
