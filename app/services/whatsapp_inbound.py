"""Mensajes que escriben las personas al número de WhatsApp del centro: buzón en vivo para el panel.

El bot NO responde solo en WhatsApp (es el número real del centro y no hay forma segura de saber con quién habla):
cada mensaje queda guardado, avisa a administración y un administrador contesta desde el panel.
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
    return saved


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
