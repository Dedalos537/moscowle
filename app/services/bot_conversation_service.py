"""Historial de conversaciones del bot: registrar, listar, responder como persona y tomar el control."""

import logging
import re
from datetime import UTC, datetime

from app.extensions import db
from app.models.bot_conversation import BotConversation, BotMessage
from app.services import live_sync

logger = logging.getLogger('app.bot_conversations')

MAX_TEXT = 4000


def _now():
    return datetime.now(UTC).replace(tzinfo=None)


def normalize_key(channel, chat_key):
    value = str(chat_key or '').strip()
    return re.sub(r'\D', '', value) if channel == 'whatsapp' else value


def get_or_create(channel, chat_key, contact_name=None, contact_handle=None, user_id=None):
    key = normalize_key(channel, chat_key)
    conv = BotConversation.query.filter_by(channel=channel, chat_key=key).first()
    if conv is None:
        conv = BotConversation(channel=channel, chat_key=key)
        db.session.add(conv)
    if contact_name and not conv.contact_name:
        conv.contact_name = contact_name[:160]
    if contact_handle:
        conv.contact_handle = contact_handle[:160]
    if user_id and not conv.user_id:
        conv.user_id = user_id
    return conv


def log_message(
    channel,
    chat_key,
    direction,
    text,
    sender,
    *,
    kind='text',
    contact_name=None,
    contact_handle=None,
    user_id=None,
    admin_id=None,
    status='sent',
    error=None,
):
    """Guarda un mensaje y actualiza la conversación. Devuelve el BotMessage, o None si no se pudo (nunca lanza)."""
    try:
        text = (text or '').strip()
        if not text:
            return None
        conv = get_or_create(channel, chat_key, contact_name, contact_handle, user_id)
        msg = BotMessage(
            direction=direction,
            sender=sender,
            kind=kind,
            text=text[:MAX_TEXT],
            admin_id=admin_id,
            status=status,
            error=(error or None) and str(error)[:255],
        )
        conv.messages.append(msg)
        conv.last_message_at = _now()
        conv.last_preview = text[:200]
        if direction == 'in':
            conv.unread_count = (conv.unread_count or 0) + 1
        db.session.commit()
        return msg
    except Exception:
        db.session.rollback()
        logger.exception('No se pudo registrar el mensaje de %s/%s', channel, chat_key)
        return None


def is_taken_over(channel, chat_key):
    conv = BotConversation.query.filter_by(channel=channel, chat_key=normalize_key(channel, chat_key)).first()
    return bool(conv and conv.human_takeover)


def set_takeover(conv, enabled, admin_id=None):
    conv.human_takeover = bool(enabled)
    conv.taken_by_id = admin_id if enabled else None
    db.session.commit()
    live_sync.bump('conversations')
    return conv


def mark_read(conv):
    if conv.unread_count:
        conv.unread_count = 0
        db.session.commit()


def list_conversations(channel=None, query=None, limit=60):
    q = BotConversation.query
    if channel:
        q = q.filter(BotConversation.channel == channel)
    if query:
        like = f'%{query.strip()}%'
        q = q.filter(
            db.or_(
                BotConversation.contact_name.ilike(like),
                BotConversation.contact_handle.ilike(like),
                BotConversation.chat_key.ilike(like),
                BotConversation.last_preview.ilike(like),
            )
        )
    return q.order_by(BotConversation.last_message_at.desc()).limit(max(1, min(limit, 200))).all()


def thread(conv, after_id=None, limit=200):
    q = conv.messages
    if after_id:
        q = q.filter(BotMessage.id > after_id)
        return q.order_by(BotMessage.id.asc()).limit(limit).all()
    # Sin cursor: los últimos `limit` mensajes, en orden cronológico.
    rows = q.order_by(BotMessage.id.desc()).limit(limit).all()
    return list(reversed(rows))


def send_as_admin(conv, text, admin):
    """Envía `text` a la persona por su canal. Devuelve (mensaje, error). El intento queda registrado siempre."""
    text = (text or '').strip()
    if not text:
        return None, 'El mensaje está vacío'
    if len(text) > MAX_TEXT:
        return None, f'Máximo {MAX_TEXT} caracteres'

    error = None
    try:
        if conv.channel == 'telegram':
            from flask import current_app

            from app.services.telegram_bot_service import send_telegram_message

            ok = send_telegram_message(
                int(conv.chat_key), text, current_app.config.get('TELEGRAM_BOT_TOKEN'), parse_mode=None, log=False
            )
            if not ok:
                error = 'Telegram no entregó el mensaje (¿la persona inició el bot?)'
        elif conv.channel == 'whatsapp':
            from app.services.whatsapp_service import WhatsAppBridgeError, whatsapp_service

            try:
                whatsapp_service.send_message(conv.chat_key, text)
            except WhatsAppBridgeError as exc:
                error = str(exc)
        else:
            error = 'Este canal no admite respuestas desde el panel'
    except Exception as exc:
        logger.exception('Error enviando como admin a %s/%s', conv.channel, conv.chat_key)
        error = str(exc)[:200]

    msg = log_message(
        conv.channel,
        conv.chat_key,
        'out',
        text,
        'admin',
        admin_id=getattr(admin, 'id', None),
        status='failed' if error else 'sent',
        error=error,
    )
    return msg, error
