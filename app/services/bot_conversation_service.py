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
    if channel == 'whatsapp':
        return re.sub(r'\D', '', value)
    return value.lower() if channel == 'web' else value  # web: el correo identifica a la persona


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
        _push(conv, msg)
        return msg
    except Exception:
        db.session.rollback()
        logger.exception('No se pudo registrar el mensaje de %s/%s', channel, chat_key)
        return None


def _push(conv, msg):
    """Aviso instantáneo a los administradores conectados (Socket.IO); la lectura periódica queda de respaldo."""
    try:
        from app.extensions import socketio

        socketio.emit(
            'bot:message',
            {
                'conversation_id': conv.id,
                'channel': conv.channel,
                'message': msg.to_dict(),
                'conversation': conv.to_dict(),
            },
            room='admins',
        )
        live_sync.bump('conversations')
    except Exception:
        logger.debug('No se pudo emitir bot:message', exc_info=True)


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


def backfill_contact_messages(limit=300):
    """Pasa los mensajes que ya llegaron por el formulario de la página web a la bandeja (una sola vez)."""
    from app.models.chat import ContactMessage
    from app.models.system_setting import SystemSetting

    flag = db.session.get(SystemSetting, 'conversations.web_backfilled')
    if flag is not None:
        return 0
    created = 0
    try:
        rows = ContactMessage.query.order_by(ContactMessage.created_at.asc()).limit(limit).all()
        for cm in rows:
            email = (cm.email or '').strip().lower()
            if not email:
                continue
            conv = get_or_create('web', email, f'{cm.first_name} {cm.last_name}'.strip(), email)
            text = f'[{cm.subject}] {cm.message}' if cm.subject and cm.subject != 'Consulta Web' else cm.message
            msg = BotMessage(
                direction='in',
                sender='contact',
                kind='text',
                text=(text or '')[:MAX_TEXT],
                created_at=cm.created_at or _now(),
            )
            conv.messages.append(msg)
            conv.last_message_at = max(conv.last_message_at or msg.created_at, msg.created_at)
            conv.last_preview = (text or '')[:200]
            if cm.status != 'read':
                conv.unread_count = (conv.unread_count or 0) + 1
            created += 1
        db.session.add(SystemSetting(key='conversations.web_backfilled', value=str(created)))
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception('No se pudieron importar los mensajes de contacto')
    return created


def list_conversations(channel=None, query=None, limit=60):
    if channel in (None, 'web'):
        backfill_contact_messages()
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
        elif conv.channel == 'web':
            from app.services.email_service import EmailService

            last_in = conv.messages.filter(BotMessage.direction == 'in').order_by(BotMessage.id.desc()).first()
            subject = 'Respuesta de Centro Juan Pablo II'
            if last_in and last_in.text.startswith('[') and ']' in last_in.text:
                subject = 'Re: ' + last_in.text[1 : last_in.text.find(']')]
            if not EmailService.send_notification_email(subject, [conv.chat_key], body=text):
                error = 'No se pudo enviar el correo (revisa la cuenta de correo del servidor)'
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
