"""Vinculacion de Telegram: solo un usuario AUTENTICADO en el panel puede ligar un
chat (POST /telegram/link con JWT). El comando /link dentro del bot no puede
autovincular: antes validaba el codigo contra la fila del propio chat y dejaba
admin_user_id = id de la tabla telegram_users (no de User)."""

import random

import pytest

from app.models.telegram_user import TelegramUser
from app.services import telegram_bot_service as tb


@pytest.fixture
def bot(app, monkeypatch):
    sent = []
    app.config['TELEGRAM_BOT_TOKEN'] = 'test-token'
    monkeypatch.setattr(tb, 'send_telegram_message', lambda chat_id, text, *a, **k: sent.append((chat_id, text)))
    monkeypatch.setattr(tb, 'send_typing_action', lambda *a, **k: None)
    monkeypatch.setattr(tb, '_bot_enabled', lambda: True)
    return sent


def _update(chat_id, text):
    return {'message': {'chat': {'id': chat_id}, 'from': {'id': chat_id, 'first_name': 'X'}, 'text': text}}


def test_stranger_cannot_self_link_with_own_code(session, bot):
    chat_id = random.randint(10**9, 10**10)
    tb.handle_webhook_update(_update(chat_id, '/start'))
    row = TelegramUser.query.filter_by(telegram_chat_id=chat_id).one()
    code = row.link_code
    assert code

    tb.handle_webhook_update(_update(chat_id, f'/link {code}'))

    session.expire_all()
    row = TelegramUser.query.filter_by(telegram_chat_id=chat_id).one()
    assert row.is_linked is False
    assert row.admin_user_id is None


def test_link_command_points_to_panel(session, bot):
    chat_id = random.randint(10**9, 10**10)
    tb.handle_webhook_update(_update(chat_id, '/start'))
    code = TelegramUser.query.filter_by(telegram_chat_id=chat_id).one().link_code
    bot.clear()
    tb.handle_webhook_update(_update(chat_id, f'/link {code}'))
    assert bot and 'panel' in bot[-1][1].lower()


def test_unlinked_chat_cannot_run_tools(session, bot, monkeypatch):
    chat_id = random.randint(10**9, 10**10)
    tb.handle_webhook_update(_update(chat_id, '/start'))
    monkeypatch.setattr(
        tb, 'process_text_message', lambda *a, **k: pytest.fail('un chat sin vincular llego al asistente')
    )
    tb.handle_webhook_update(_update(chat_id, 'lista los pacientes'))
