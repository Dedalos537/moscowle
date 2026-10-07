"""Conversaciones del bot en vivo (ver el hilo, responder como persona, tomar el control) y versiones de configuración."""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.extensions import db
from app.models import BotConfig, BotConversation
from app.services import bot_conversation_service as conversations
from app.services import live_sync
from app.utils.decorators import admin_required, admin_write_required

bot_conv_bp = Blueprint('bot_conversations', __name__, url_prefix='/api/bot')
live_bp = Blueprint('live_sync', __name__, url_prefix='/api/live')

LIVE_SCOPES = ('bot_config', 'faq', 'channels', 'conversations')


def _conversation_or_404(cid):
    conv = db.session.get(BotConversation, cid)
    if not conv:
        return None, (jsonify({'error': 'Conversación no encontrada'}), 404)
    return conv, None


@bot_conv_bp.route('/conversations', methods=['GET'])
@jwt_required()
@admin_required
def list_conversations():
    channel = request.args.get('channel') or None
    if channel not in (None, 'telegram', 'whatsapp', 'web'):
        return jsonify({'error': 'Canal inválido'}), 400
    rows = conversations.list_conversations(channel, request.args.get('q'), int(request.args.get('limit', 60) or 60))
    last = db.session.query(db.func.max(conversations.BotMessage.id)).scalar() or 0
    return jsonify(
        {
            'conversations': [c.to_dict() for c in rows],
            'latest_message_id': last,
            'unread_total': sum(c.unread_count or 0 for c in rows),
        }
    )


@bot_conv_bp.route('/conversations/<int:cid>/messages', methods=['GET'])
@jwt_required()
@admin_required
def get_thread(cid):
    conv, err = _conversation_or_404(cid)
    if err:
        return err
    after_id = request.args.get('after_id', type=int)
    rows = conversations.thread(conv, after_id=after_id)
    if request.args.get('mark_read') in ('1', 'true'):
        conversations.mark_read(conv)
    return jsonify({'conversation': conv.to_dict(), 'messages': [m.to_dict() for m in rows]})


@bot_conv_bp.route('/conversations/<int:cid>/messages', methods=['POST'])
@jwt_required()
@admin_write_required
def reply(cid):
    conv, err = _conversation_or_404(cid)
    if err:
        return err
    if not BotConfig.get_or_create().intervention_enabled:
        return jsonify({'error': 'La intervención manual está desactivada en la configuración del bot'}), 403
    data = request.get_json(silent=True) or {}
    from app.models import User

    admin = db.session.get(User, int(get_jwt_identity()))
    msg, error = conversations.send_as_admin(conv, data.get('text'), admin)
    live_sync.bump('conversations')
    if error:
        return jsonify({'error': error, 'message': msg.to_dict() if msg else None}), 502 if msg else 400
    return jsonify({'status': 'sent', 'message': msg.to_dict()}), 201


@bot_conv_bp.route('/conversations/<int:cid>/takeover', methods=['POST'])
@jwt_required()
@admin_write_required
def takeover(cid):
    conv, err = _conversation_or_404(cid)
    if err:
        return err
    if not BotConfig.get_or_create().intervention_enabled:
        return jsonify({'error': 'La intervención manual está desactivada en la configuración del bot'}), 403
    enabled = bool((request.get_json(silent=True) or {}).get('enabled'))
    conversations.set_takeover(conv, enabled, admin_id=int(get_jwt_identity()))
    return jsonify({'conversation': conv.to_dict()})


@live_bp.route('/versions', methods=['GET'])
@jwt_required()
def versions():
    """Versión actual de cada ámbito pedido. Las pantallas abiertas comparan y se recargan si cambió."""
    from app.models import User

    user = db.session.get(User, int(get_jwt_identity()))
    wanted = [s for s in (request.args.get('scopes') or '').split(',') if s]
    out = {}
    staff = bool(user and user.role in ('admin', 'supervisor'))
    plain = [s for s in wanted if s in LIVE_SCOPES and staff]
    out.update(live_sync.versions(plain))
    if 'notif_prefs' in wanted and user:  # preferencias propias: cada usuario ve solo su contador
        out['notif_prefs'] = live_sync.versions([f'notif_prefs:{user.id}'])[f'notif_prefs:{user.id}']
    return jsonify(out)
