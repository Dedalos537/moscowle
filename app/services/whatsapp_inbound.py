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


def _user_by_display_name(name):
    """Usuario activo cuyo nombre coincide exactamente (y es único) con el que muestra WhatsApp.

    Solo sirve para saber a qué teléfono escribirle a un contacto que WhatsApp identifica sin número; el bot solo
    contesta información pública, así que un error aquí no expone datos.
    """
    from app.models.user import User

    name = (name or '').strip().lower()
    if len(name) < 5:
        return None
    rows = User.query.filter(db.func.lower(User.username) == name, User.is_active.is_(True)).limit(2).all()
    return rows[0] if len(rows) == 1 and rows[0].phone else None


def handle_incoming(msg):
    """Procesa un evento `incoming` del puente (con app context ya activo)."""
    phone = conversations.normalize_key('whatsapp', msg.get('phone'))
    text = (msg.get('text') or '').strip()
    if not phone or not text:
        return None
    is_lid = bool(msg.get('lid'))
    user = _user_by_display_name(msg.get('name')) if is_lid else _known_user(phone)
    name = msg.get('name') or (user.username if user else None)
    saved = conversations.log_message(
        'whatsapp',
        phone,
        'in',
        text,
        'contact',
        kind=msg.get('kind') or 'text',
        contact_name=name,
        contact_handle=f'lid:{phone}' if is_lid else f'+{phone}',
        user_id=user.id if user else None,
    )
    if saved is None:
        return None
    live_sync.bump('conversations')
    if is_lid or user is None or user.role not in STAFF_ROLES:
        # Al personal que consulta al bot no se le avisa de sus propios mensajes.
        _notify_staff(name or f'+{phone}', text)
    try:
        # Solo un teléfono real identifica a alguien (WhatsApp lo autentica). Un @lid emparejado por nombre no.
        _auto_reply(phone, text, name, is_lid, verified_user=None if is_lid else user)
    except Exception:
        db.session.rollback()
        logger.exception('El bot no pudo contestar en WhatsApp')
    return saved


MAX_BOT_REPLIES_PER_HOUR = 20
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


def compose_reply(text, allow_fallback=True):
    """Respuesta pública rápida (FAQ o saludo). Devuelve (texto, resuelta).

    Con allow_fallback=False devuelve (None, False) cuando no hay respuesta directa, para que decida la IA.
    """
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
    if not allow_fallback:
        return None, False
    return FALLBACK_TEXT, False


FALLBACK_TEXT = (
    'Gracias por escribirnos. No tengo esa información a la mano, pero ya avisé a una persona del centro '
    'para que te responda pronto. 🙏'
)
PROCESSING_TEXT = '⏳ Un momento, lo estoy revisando…'
NOT_KNOWN = 'NO_SE'


def public_ai_reply(text):
    """Respuesta con IA para el público, anclada SOLO a las FAQ del centro. (texto, resuelta) o (None, False)."""
    from app.models.faq import Faq
    from app.services.llm_client import llm_chat
    from app.services.prompt_builder import bot_identity

    faqs = Faq.query.filter_by(is_active=True, status='active').order_by(Faq.usage_count.desc()).limit(20).all()
    if not faqs:
        return None, False
    name, emoji, _persona = bot_identity()
    knowledge = '\n'.join(f'- P: {f.question}\n  R: {f.answer}' for f in faqs)
    system = (
        f'Eres {name} {emoji}, asistente virtual del Centro de Terapias Juan Pablo II (Piura, Perú) por WhatsApp. '
        'Respondes en español, cálido y breve (1 a 4 líneas). Usa SOLO la información de abajo; no inventes precios, '
        'horarios, nombres ni datos de pacientes. Si la respuesta no está en la información, responde exactamente '
        f'{NOT_KNOWN} y nada más.\n\nINFORMACIÓN DEL CENTRO:\n{knowledge}'
    )
    try:
        content, _provider = llm_chat(
            [{'role': 'system', 'content': system}, {'role': 'user', 'content': text[:600]}],
            temperature=0.2,
            max_tokens=300,
            phase='resume',
        )
    except Exception:
        logger.warning('La IA no respondió para WhatsApp público', exc_info=True)
        return None, False
    content = (content or '').strip()
    if not content or NOT_KNOWN in content.upper() or content.startswith('<function'):
        return None, False
    return content[:1500], True


def staff_ai_reply(user, text):
    """Asistente del ERP (MCP) para un usuario identificado por su teléfono real. Solo consultas.

    Las acciones que modifican datos no se ejecutan por WhatsApp: no hay confirmación segura en este canal.
    """
    from app.services.mcp_service import MCPService

    result = MCPService().process_message(
        message=text, user_role=user.role, user_id=user.id, mode='grande', telegram_mode=True
    )
    if result.get('requires_confirmation'):
        return (
            '✋ Eso modifica datos del sistema. Por seguridad, por WhatsApp solo hago consultas: '
            'confírmalo desde el panel o desde Telegram.'
        )
    return (result.get('response') or '').strip() or None


def _send_bot(target, is_lid, text, phone):
    from app.services.whatsapp_service import WhatsAppBridgeError, whatsapp_service

    try:
        whatsapp_service.send_message(target, text, lid=is_lid)
        conversations.log_message('whatsapp', phone, 'out', text, 'bot')
        return True
    except WhatsAppBridgeError as exc:
        conversations.log_message('whatsapp', phone, 'out', text, 'bot', status='failed', error=str(exc))
        return False


def _auto_reply(phone, text, name, is_lid=False, verified_user=None):
    from app.models.bot_conversation import BotConversation
    from app.services.faq_service import note_unanswered
    from app.services.whatsapp_service import whatsapp_service

    conv = BotConversation.query.filter_by(channel='whatsapp', chat_key=phone).first()
    if not _bot_allowed(conv):
        return
    target, is_lid = conversations.whatsapp_target(conv)
    whatsapp_service.send_typing(target, lid=is_lid)

    staff = verified_user is not None and verified_user.role in STAFF_ROLES
    if not staff:
        reply, _solved = compose_reply(text, allow_fallback=False)
        if reply:
            _send_bot(target, is_lid, reply, phone)
            return

    # Camino lento (IA): primero un aviso, como el «Procesando…» de Telegram.
    if not _send_bot(target, is_lid, PROCESSING_TEXT, phone):
        return
    if staff:
        answer = staff_ai_reply(verified_user, text) or FALLBACK_TEXT
    else:
        answer, solved = public_ai_reply(text)
        if not answer:
            note_unanswered(text)
            answer = FALLBACK_TEXT
    _send_bot(target, is_lid, answer, phone)


STAFF_ROLES = ('admin', 'supervisor', 'terapista')


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
