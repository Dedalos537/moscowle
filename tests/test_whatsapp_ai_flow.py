"""Flujo del bot de WhatsApp: hilo propio, IA pública anclada a las FAQ y asistente para personal verificado."""

import threading
from types import SimpleNamespace
from unittest.mock import patch

from app.extensions import db
from app.models.faq import Faq
from app.services import whatsapp_inbound
from app.services.whatsapp_service import WhatsAppService


def test_incoming_runs_off_the_reader_thread():
    svc = WhatsAppService()
    seen = {}
    done = threading.Event()

    def handler(msg):
        seen['thread'] = threading.current_thread().name
        done.set()

    svc.set_incoming_handler(handler)
    svc._handle({'type': 'incoming', 'phone': '51999', 'text': 'hola'})
    assert done.wait(2)
    assert seen['thread'] == 'wa-incoming'


def _faq():
    faq = Faq(
        question='¿Atienden sábados?',
        answer='Sí, sábados de 8 a 6',
        category='x',
        keywords='sabado',
        is_active=True,
        source='manual',
        status='active',
    )
    db.session.add(faq)
    db.session.commit()
    return faq


def test_public_ai_uses_faq_and_respects_no_se(app):
    faq = _faq()
    try:
        with patch(
            'app.services.llm_client.llm_chat', return_value=('Sí, los sábados atendemos de 8 a 6.', 'ollama')
        ) as chat:
            text, ok = whatsapp_inbound.public_ai_reply('abren el finde?')
        assert ok and 'sábados' in text
        system = chat.call_args[0][0][0]['content']
        assert 'Sí, sábados de 8 a 6' in system  # la IA recibe las FAQ como única fuente
        with patch('app.services.llm_client.llm_chat', return_value=('NO_SE', 'ollama')):
            assert whatsapp_inbound.public_ai_reply('¿cuánto cuesta un auto?') == (None, False)
        with patch('app.services.llm_client.llm_chat', side_effect=RuntimeError('caído')):
            assert whatsapp_inbound.public_ai_reply('hola?') == (None, False)
    finally:
        db.session.delete(faq)
        db.session.commit()


def test_staff_reply_never_runs_writes():
    user = SimpleNamespace(id=1, role='admin')
    pending = {'requires_confirmation': True, 'pending_tool': {'name': 'register_payment'}}
    with patch('app.services.mcp_service.MCPService.process_message', return_value=pending):
        text = whatsapp_inbound.staff_ai_reply(user, 'registra un pago de 50')
    assert 'solo hago consultas' in text
    with patch('app.services.mcp_service.MCPService.process_message', return_value={'response': 'Hay 12 pacientes'}):
        assert whatsapp_inbound.staff_ai_reply(user, '¿cuántos pacientes?') == 'Hay 12 pacientes'


def test_auto_reply_sends_processing_then_answer(app):
    conv = SimpleNamespace(id=1, human_takeover=False)
    sent = []
    with (
        patch.object(whatsapp_inbound, '_bot_allowed', return_value=True),
        patch('app.models.bot_conversation.BotConversation.query') as q,
        patch('app.services.bot_conversation_service.whatsapp_target', return_value=('51999', False)),
        patch.object(whatsapp_inbound, '_send_bot', side_effect=lambda t, lid, text, phone: sent.append(text) or True),
        patch.object(whatsapp_inbound, 'public_ai_reply', return_value=('Respuesta IA', True)),
        patch('app.services.whatsapp_service.whatsapp_service.send_typing'),
    ):
        q.filter_by.return_value.first.return_value = conv
        whatsapp_inbound._auto_reply('51999', 'una pregunta rara que no está en las faq', 'Ana')
    assert sent == [whatsapp_inbound.PROCESSING_TEXT, 'Respuesta IA']
