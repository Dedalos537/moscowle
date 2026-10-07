from unittest.mock import patch

from app.extensions import db
from app.models.bot_conversation import BotConversation
from app.models.faq import Faq
from app.services import automation_settings, website_faq_sync
from app.services import bot_conversation_service as convs

JS = (
    'h.jsx("h3",{children:"Nuestra Misión"}),h.jsx("p",{className:"x leading-relaxed mb-6",children:"'
    + 'Brindar una educación integral e inclusiva para personas con habilidades diferentes. ' * 2
    + '"}),title:"Horario",content:`Lun - Vie: 8:00 AM - 7:00 PM`,description:"Sáb: 8:00 AM"'
)


def test_extract_reads_mission_and_schedule():
    questions = {q: a for q, a, _ in website_faq_sync.extract(JS)}
    assert '¿Cuál es el horario de atención?' in questions
    assert 'Lun - Vie' in questions['¿Cuál es el horario de atención?']


def test_sync_is_idempotent_and_updates(app):
    with (
        patch.object(website_faq_sync, '_fetch', side_effect=['<script src="/a.js"></script>', JS]),
        patch.object(website_faq_sync, 'get_url', return_value='https://x.test'),
    ):
        first = website_faq_sync.sync()
    assert first['ok'] and first['created'] >= 1
    with (
        patch.object(website_faq_sync, '_fetch', side_effect=['<script src="/a.js"></script>', JS]),
        patch.object(website_faq_sync, 'get_url', return_value='https://x.test'),
    ):
        second = website_faq_sync.sync()
    assert second['created'] == 0 and second['updated'] == 0
    assert Faq.query.filter_by(source='website').count() == first['created']


def test_sync_ignores_foreign_scripts():
    html = '<script src="https://evil.test/a.js"></script><script src="/ok.js"></script>'
    assert website_faq_sync._bundles(html, 'https://x.test') == ['https://x.test/ok.js']


def test_sync_reports_error_without_raising(app):
    with patch.object(website_faq_sync, '_fetch', side_effect=RuntimeError('caída')):
        out = website_faq_sync.sync()
    assert out['ok'] is False and 'caída' in out['error']


def test_web_channel_logs_and_normalizes_email(app):
    msg = convs.log_message(
        'web', ' Ana@Mail.com ', 'in', 'Hola', 'contact', contact_name='Ana', contact_handle='ana@mail.com'
    )
    assert msg is not None
    conv = BotConversation.query.filter_by(channel='web', chat_key='ana@mail.com').first()
    assert conv is not None and conv.unread_count >= 1


def test_automation_modes(app):
    automation_settings.update({'mode': 'off'})
    assert automation_settings.allows(1, 'sessions', 'whatsapp')[0] is False
    automation_settings.update({'mode': 'all'})
    assert automation_settings.allows(1, 'sessions', 'whatsapp')[0] is True
    db.session.rollback()


def test_whatsapp_bot_answers_from_faq_and_greets(app):
    from app.services import whatsapp_inbound

    faq = Faq(
        question='¿Aceptan seguro Rímac?',
        answer='Sí, aceptamos Rímac',
        category='x',
        keywords='seguro rimac',
        is_active=True,
        source='manual',
        status='active',
    )
    db.session.add(faq)
    db.session.commit()
    try:
        text, solved = whatsapp_inbound.compose_reply('aceptan seguro rimac?')
        assert solved and 'Rímac' in text
    finally:
        db.session.delete(faq)
        db.session.commit()
    greeting, solved = whatsapp_inbound.compose_reply('hola')
    assert solved and 'asistente virtual' in greeting
    fallback, solved = whatsapp_inbound.compose_reply(
        'necesito cambiar la dirección de facturación de mi contrato anterior'
    )
    assert not solved and 'persona del centro' in fallback


def test_whatsapp_bot_respects_takeover_and_switch(app):
    from app.services import whatsapp_inbound

    convs.log_message('whatsapp', '51999000111', 'in', 'hola', 'contact')
    conv = BotConversation.query.filter_by(channel='whatsapp', chat_key='51999000111').first()
    automation_settings.update({'mode': 'all', 'whatsapp_bot': True})
    assert whatsapp_inbound._bot_allowed(conv) is True
    conv.human_takeover = True
    assert whatsapp_inbound._bot_allowed(conv) is False
    conv.human_takeover = False
    automation_settings.update({'whatsapp_bot': False})
    assert whatsapp_inbound._bot_allowed(conv) is False
    automation_settings.update({'whatsapp_bot': True})
    db.session.rollback()
