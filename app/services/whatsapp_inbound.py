"""Mensajes que escriben las personas al número de WhatsApp del centro: buzón en vivo para el panel.

Cada mensaje queda guardado y avisa a administración. El bot (Chasqui) contesta solo con información pública:
las FAQ del centro y un saludo; nunca ejecuta herramientas ni toca datos de pacientes, porque por este número
escribe cualquiera. Se calla si un administrador tomó la conversación o respondió hace poco, si el bot o este
canal están apagados, o si ya contestó muchas veces en la última hora (evita bucles con otros bots).
"""

import logging

from app.extensions import db
from app.services import bot_conversation_service as conversations
from app.services import live_sync

logger = logging.getLogger('app.whatsapp_inbound')


def _known_user(phone):
    """Usuario de la plataforma cuyo teléfono coincide con el número (últimos 9 dígitos), si es uno solo."""
    from app.models.user import User

    tail = phone[-9:]
    if len(tail) < 9:
        return None
    digits_only = User.phone
    for ch in (' ', '-', '+', '(', ')', '.'):
        digits_only = db.func.replace(digits_only, ch, '')
    matches = User.query.filter(User.phone.isnot(None), digits_only.like(f'%{tail}')).limit(2).all()
    return matches[0] if len(matches) == 1 else None


def handle_incoming(msg):
    """Procesa un evento `incoming` del puente (con app context ya activo)."""
    phone = conversations.normalize_key('whatsapp', msg.get('phone'))
    text = (msg.get('text') or '').strip()
    if not phone or not text:
        return None
    user = _known_user(phone)
    name = msg.get('name') or (user.username if user else None)
    saved = conversations.log_message(
        'whatsapp',
        phone,
        'in',
        text,
        'contact',
        kind=msg.get('kind') or 'text',
        contact_name=name,
        contact_handle=f'+{phone}',
        user_id=user.id if user else None,
    )
    if saved is None:
        return None
    live_sync.bump('conversations')
    _notify_staff(name or f'+{phone}', text)
    try:
        _auto_reply(phone, text, name)
    except Exception:
        db.session.rollback()
        logger.exception('El bot no pudo contestar en WhatsApp')
    return saved


MAX_BOT_REPLIES_PER_HOUR = 8
HUMAN_QUIET_MINUTES = 30
GREETINGS = (
    'hola',
    'buenas',
    'buenos',
    'buen dia',
    'buen día',
    'saludos',
    'hello',
    'hi',
    'info',
    'informacion',
    'información',
)


def _bot_allowed(conv):
    from datetime import datetime, timedelta

    from app.models.bot_config import BotConfig
    from app.models.bot_conversation import BotMessage
    from app.services import automation_settings

    if not BotConfig.get_or_create().enabled or not automation_settings.get()['whatsapp_bot']:
        return False
    if conv is None or conv.human_takeover:
        return False
    now = datetime.utcnow()
    recent_admin = (
        BotMessage.query.filter(
            BotMessage.conversation_id == conv.id,
            BotMessage.sender == 'admin',
            BotMessage.created_at >= now - timedelta(minutes=HUMAN_QUIET_MINUTES),
        ).first()
        is not None
    )
    if recent_admin:
        return False
    bot_replies = BotMessage.query.filter(
        BotMessage.conversation_id == conv.id,
        BotMessage.sender == 'bot',
        BotMessage.created_at >= now - timedelta(hours=1),
    ).count()
    return bot_replies < MAX_BOT_REPLIES_PER_HOUR


def compose_reply(text):
    """Respuesta pública para `text`, o (None, False) si no hay nada que decir. Devuelve (texto, resuelta)."""
    from app.models.faq import Faq
    from app.services.faq_service import match_faq, record_usage
    from app.services.telegram_bot_service import _bot_identity, _bot_persona

    name, emoji = _bot_identity()
    lowered = text.lower().strip()
    matches = match_faq(text, limit=1)
    if matches and matches[0]['score'] >= 4:
        faq = matches[0]['faq']
        record_usage([faq.id])
        return faq.answer, True
    if any(lowered.startswith(g) or lowered == g for g in GREETINGS) or len(lowered) < 12:
        topics = [
            f.question
            for f in Faq.query.filter_by(is_active=True, status='active').order_by(Faq.usage_count.desc()).limit(5)
        ]
        intro = _bot_persona() or f'¡Hola! Soy {name} {emoji}, asistente virtual del Centro de Terapias Juan Pablo II.'
        body = intro + '\n\n¿En qué puedo ayudarte?'
        if topics:
            body += ' Por ejemplo, puedes preguntarme:\n' + '\n'.join(f'• {t}' for t in topics)
        return body, True
    return (
        'Gracias por escribirnos. No tengo esa información a la mano, pero ya avisé a una persona del centro '
        'para que te responda pronto. 🙏',
        False,
    )


def _auto_reply(phone, text, name):
    from app.models.bot_conversation import BotConversation
    from app.services.faq_service import note_unanswered
    from app.services.whatsapp_service import WhatsAppBridgeError, whatsapp_service

    conv = BotConversation.query.filter_by(channel='whatsapp', chat_key=phone).first()
    if not _bot_allowed(conv):
        return
    reply, solved = compose_reply(text)
    if not reply:
        return
    if not solved:
        note_unanswered(text)
    try:
        whatsapp_service.send_message(phone, reply)
        conversations.log_message('whatsapp', phone, 'out', reply, 'bot')
    except WhatsAppBridgeError as exc:
        conversations.log_message('whatsapp', phone, 'out', reply, 'bot', status='failed', error=str(exc))


def _notify_staff(who, text):
    try:
        from app.models.bot_config import BotConfig
        from app.models.user import User
        from app.services.notification_service import NotificationService

        if not BotConfig.get_or_create().notify_supervision_enabled:
            return
        service = NotificationService()
        snippet = ' '.join(text.split())[:120]
        for admin in User.query.filter(User.role.in_(('admin', 'supervisor')), User.is_active.is_(True)).all():
            service.notify_user(
                user_id=admin.id,
                title='Nuevo mensaje de WhatsApp',
                message=f'{who}: {snippet}',
                notif_type='info',
                link='/app/admin/settings?section=bot',
                category='contact',
                priority='normal',
                icon='comments',
                event_type='bot_whatsapp_in',
                event_kwargs={'scope': 'whatsapp'},
                skip_telegram=True,
            )
    except Exception:
        db.session.rollback()
        logger.exception('No se pudo avisar del mensaje entrante de WhatsApp')


def make_handler(app):
    def handler(msg):
        with app.app_context():
            try:
                handle_incoming(msg)
            finally:
                db.session.remove()

    return handler
