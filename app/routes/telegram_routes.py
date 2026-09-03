import hmac
import logging
import os
import time

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app import db
from app.models.bot_config import BotConfig
from app.models.faq import Faq
from app.models.telegram_user import TelegramUser

logger = logging.getLogger('app.telegram')

telegram_bp = Blueprint('telegram', __name__, url_prefix='/api/telegram')

# Track processed update_ids to prevent duplicate processing (max 1000 entries)
_processed_updates: dict[int, float] = {}
_MAX_PROCESSED = 1000


def _cleanup_old_updates():
    """Remove entries older than 5 minutes."""
    now = time.time()
    cutoff = now - 300
    to_remove = [uid for uid, ts in _processed_updates.items() if ts < cutoff]
    for uid in to_remove:
        del _processed_updates[uid]


def _is_duplicate(update_id: int) -> bool:
    """Check if this update was already processed."""
    _cleanup_old_updates()
    if update_id in _processed_updates:
        return True
    _processed_updates[update_id] = time.time()
    if len(_processed_updates) > _MAX_PROCESSED:
        _cleanup_old_updates()
    return False


@telegram_bp.route('/webhook', methods=['POST'])
def webhook():
    """Handle incoming Telegram updates (webhook mode).

    Responds immediately (200) and processes the message in a background thread
    to avoid Telegram's 30-second timeout.
    """
    secret = current_app.config.get('TELEGRAM_WEBHOOK_SECRET')
    if secret:
        sig = request.headers.get('X-Telegram-Bot-Api-Secret-Token', '')
        if not hmac.compare_digest(sig, secret):
            return jsonify({'error': 'forbidden'}), 403

    update = request.get_json(silent=True)
    if not update:
        return jsonify({'error': 'bad request'}), 400

    update_id = update.get('update_id')
    if update_id and _is_duplicate(update_id):
        logger.debug(f'Duplicate update_id {update_id}, skipping')
        return jsonify({'status': 'ok'}), 200

    # Process in background green thread to avoid Telegram 30s timeout
    import eventlet
    from flask import current_app as _app

    app_ref = _app._get_current_object()

    def _process_bg():
        try:
            logger.info(f'BG: Processing update_id={update_id}')
            with app_ref.app_context():
                from app.services.telegram_bot_service import handle_webhook_update

                handle_webhook_update(update)
                logger.info(f'BG: Done processing update_id={update_id}')
        except Exception as e:
            logger.error(f'Webhook processing error: {e}', exc_info=True)

    eventlet.spawn(_process_bg)

    return jsonify({'status': 'ok'}), 200


@telegram_bp.route('/link', methods=['POST'])
@jwt_required()
def link_account():
    """Link a Telegram account using a 6-character code."""
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    code = (data.get('code') or '').strip().upper()

    if not code or len(code) != 6:
        return jsonify({'error': 'Código inválido (6 caracteres requeridos)'}), 400

    tg_user = TelegramUser.query.filter_by(link_code=code, is_linked=False).first()
    if not tg_user:
        return jsonify({'error': 'Código no encontrado o ya utilizado'}), 404

    if not tg_user.is_link_code_valid(code):
        return jsonify({'error': 'Código expirado. Pide uno nuevo con /start en el bot.'}), 400

    tg_user.admin_user_id = user_id
    tg_user.is_linked = True
    tg_user.link_code = None
    tg_user.link_code_expires_at = None
    db.session.commit()

    from app.services.telegram_bot_service import send_telegram_message

    bot_token = current_app.config.get('TELEGRAM_BOT_TOKEN')
    send_telegram_message(
        tg_user.telegram_chat_id,
        '✅ *¡Cuenta vinculada!*\n\nYa puedes interactuar con el sistema desde Telegram.',
        bot_token,
    )

    return jsonify({'status': 'linked', 'telegram_chat_id': tg_user.telegram_chat_id})


@telegram_bp.route('/status', methods=['GET'])
@jwt_required()
def get_status():
    """Get Telegram link status for the current user."""
    user_id = int(get_jwt_identity())
    tg_users = TelegramUser.query.filter_by(admin_user_id=user_id, is_active=True).all()

    return jsonify(
        {
            'linked_accounts': [
                {
                    'telegram_chat_id': tu.telegram_chat_id,
                    'telegram_username': tu.telegram_username,
                    'telegram_first_name': tu.telegram_first_name,
                    'is_linked': tu.is_linked,
                    'notifications_enabled': tu.notifications_enabled,
                    'linked_at': tu.created_at.isoformat() if tu.created_at else None,
                    'last_interaction': tu.last_interaction_at.isoformat() if tu.last_interaction_at else None,
                }
                for tu in tg_users
            ]
        }
    )


@telegram_bp.route('/unlink', methods=['POST'])
@jwt_required()
def unlink_account():
    """Unlink a Telegram account."""
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    chat_id = data.get('telegram_chat_id')

    if not chat_id:
        return jsonify({'error': 'telegram_chat_id requerido'}), 400

    tg_user = TelegramUser.query.filter_by(admin_user_id=user_id, telegram_chat_id=chat_id).first()

    if not tg_user:
        return jsonify({'error': 'No encontrado'}), 404

    tg_user.is_linked = False
    tg_user.admin_user_id = None
    db.session.commit()

    return jsonify({'status': 'unlinked'})


@telegram_bp.route('/notifications/toggle', methods=['POST'])
@jwt_required()
def toggle_notifications():
    """Enable/disable Telegram notifications."""
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    chat_id = data.get('telegram_chat_id')
    enabled = data.get('enabled', True)

    tg_user = TelegramUser.query.filter_by(admin_user_id=user_id, telegram_chat_id=chat_id, is_linked=True).first()

    if not tg_user:
        return jsonify({'error': 'No encontrado'}), 404

    tg_user.notifications_enabled = bool(enabled)
    db.session.commit()

    return jsonify({'status': 'updated', 'notifications_enabled': tg_user.notifications_enabled})


@telegram_bp.route('/dashboard', methods=['GET'])
@jwt_required()
def get_bot_dashboard():
    """Unified dashboard: bot config + channels + recent conversations + activity."""
    data = {}

    # ── Bot config ────────────────────────────────────────────────────
    bot_token_full = current_app.config.get('TELEGRAM_BOT_TOKEN', '')
    bot_token_masked = f'{bot_token_full[:8]}...{bot_token_full[-4:]}' if len(bot_token_full) > 12 else '—'
    # Prefer persisted BotConfig, fall back to env defaults
    try:
        bot_cfg = BotConfig.get_or_create()
        bot_name = bot_cfg.bot_name or os.getenv('TELEGRAM_BOT_NAME', 'Diego')
        bot_emoji = bot_cfg.bot_emoji or os.getenv('TELEGRAM_BOT_EMOJI', '\U0001f99c')
        persona_msg = bot_cfg.persona_message or os.getenv('TELEGRAM_PERSONA_MESSAGE', '')
        system_prompt = bot_cfg.system_prompt or os.getenv('TELEGRAM_SYSTEM_PROMPT', '')
    except Exception:
        bot_cfg = None
        bot_name = os.getenv('TELEGRAM_BOT_NAME', 'Diego')
        bot_emoji = os.getenv('TELEGRAM_BOT_EMOJI', '\U0001f99c')
        persona_msg = os.getenv('TELEGRAM_PERSONA_MESSAGE', '')
        system_prompt = os.getenv('TELEGRAM_SYSTEM_PROMPT', '')
    is_active = bool(bot_token_full)
    webhook_url = os.getenv('TELEGRAM_WEBHOOK_URL', '')
    webhook_secret = os.getenv('TELEGRAM_WEBHOOK_SECRET', '')

    data['bot'] = {
        'name': bot_name,
        'emoji': bot_emoji,
        'is_active': is_active,
        'bot_token_masked': bot_token_masked,
        'persona_message': persona_msg,
        'system_prompt': system_prompt,
        'webhook_url': webhook_url,
        'webhook_secret': webhook_secret,
    }

    if bot_cfg is not None:
        data['bot']['config'] = {
            'auto_faq_enabled': bot_cfg.auto_faq_enabled,
            'auto_faq_threshold': bot_cfg.auto_faq_threshold,
            'mcp_prompt_enabled': bot_cfg.mcp_prompt_enabled,
            'notify_supervision_enabled': bot_cfg.notify_supervision_enabled,
            'intervention_enabled': bot_cfg.intervention_enabled,
        }
        data['bot']['proposed_faq_count'] = Faq.query.filter_by(status='proposed').count()
        data['bot']['faq_count'] = Faq.query.filter_by(status='active', is_active=True).count()

    # ── Channels ──────────────────────────────────────────────────────
    tg_accounts = TelegramUser.query.filter_by(is_active=True).all()
    linked = [t for t in tg_accounts if t.is_linked]
    tg_status = {
        'active': is_active and len(linked) > 0,
        'linked_count': len(linked),
        'total_accounts': len(tg_accounts),
        'accounts': [
            {
                'chat_id': t.telegram_chat_id,
                'username': t.telegram_username,
                'first_name': t.telegram_first_name,
                'is_linked': t.is_linked,
                'notifications_enabled': t.notifications_enabled,
                'last_interaction': t.last_interaction_at.isoformat() if t.last_interaction_at else None,
            }
            for t in tg_accounts[:20]
        ],
    }

    data['channels'] = {
        'web': {'active': True, 'label': 'Chat Web', 'icon': 'globe'},
        'telegram': tg_status,
        'whatsapp': {'active': False, 'label': 'WhatsApp (Baileys)', 'icon': 'whatsapp', 'status': 'coming_soon'},
        'instagram': {'active': False, 'label': 'Instagram DMs', 'icon': 'instagram', 'status': 'coming_soon'},
    }

    # ── Recent conversations (last 10 per channel) ───────────────────
    conversations = []

    # Telegram conversations
    for t in linked:
        last = t.last_interaction_at.isoformat() if t.last_interaction_at else None
        conversations.append(
            {
                'channel': 'telegram',
                'chat_id': t.telegram_chat_id,
                'contact': t.telegram_username or t.telegram_first_name or f'Chat #{t.telegram_chat_id}',
                'last_message': None,
                'timestamp': last,
                'unread': 0,
                'status': 'active',
            }
        )

    # Contact messages (web form)
    try:
        from app.models import ContactMessage

        recent_contacts = ContactMessage.query.order_by(ContactMessage.created_at.desc()).limit(10).all()
        for cm in recent_contacts:
            first = cm.first_name or ''
            last = cm.last_name or ''
            name = f'{first} {last}'.strip() or cm.email or 'Anónimo'
            conversations.append(
                {
                    'channel': 'web',
                    'chat_id': cm.id,
                    'contact': name,
                    'last_message': (cm.message[:120] + '…') if cm.message and len(cm.message) > 120 else cm.message,
                    'timestamp': cm.created_at.isoformat() if cm.created_at else None,
                    'unread': 0 if cm.status == 'read' else 1,
                    'status': cm.status,
                }
            )
    except Exception as exc:
        logger.debug(f'Could not load contact messages: {exc}')

    # Sort by timestamp desc
    conversations.sort(key=lambda c: c['timestamp'] or '', reverse=True)
    data['conversations'] = conversations[:30]

    # ── Activity (last 10) ───────────────────────────────────────────
    activity = []

    # Recent telegram interactions
    for t in linked:
        if t.last_interaction_at:
            activity.append(
                {
                    'type': 'telegram',
                    'title': f'@{t.telegram_username or t.telegram_first_name or "Usuario"}',
                    'message': f'Interacción con el bot (vinculado: {"sí" if t.is_linked else "no"})',
                    'timestamp': t.last_interaction_at.isoformat(),
                }
            )

    # Recent payments
    try:
        from app.models import Appointment, Payment, User

        recent_payments = Payment.query.order_by(Payment.id.desc()).limit(5).all()
        for p in recent_payments:
            patient = User.query.get(p.patient_id) if p.patient_id else None
            activity.append(
                {
                    'type': 'api',
                    'title': f'Pago S/{getattr(p, "amount", 0)}',
                    'message': f'{getattr(p, "method", "")} — {patient.username if patient else "paciente desconocido"}',
                    'timestamp': (p.date.isoformat() if getattr(p, 'date', None) else ''),
                }
            )

        recent_sessions = Appointment.query.order_by(Appointment.id.desc()).limit(5).all()
        for s in recent_sessions:
            activity.append(
                {
                    'type': 'api',
                    'title': f'Sesión #{s.id}',
                    'message': 'Sesión terapéutica',
                    'timestamp': s.start_time.isoformat() if s.start_time else '',
                }
            )
    except Exception as exc:
        logger.debug(f'Could not load activity data: {exc}')

    activity.sort(key=lambda a: a['timestamp'] or '', reverse=True)
    data['activity'] = activity[:20]

    return jsonify(data)


# ────────────────────────────────────────────────────────────────────────
# Chasqui Bot Config
# ────────────────────────────────────────────────────────────────────────
@telegram_bp.route('/config', methods=['GET', 'PUT'])
@jwt_required()
def bot_config_endpoint():
    """Get or update the bot's persisted configuration (persona, prompt, toggles)."""
    cfg = BotConfig.get_or_create()

    if request.method == 'GET':
        return jsonify(cfg.to_dict())

    data = request.get_json(silent=True) or {}
    if 'bot_name' in data:
        cfg.bot_name = str(data['bot_name'])[:120]
    if 'bot_emoji' in data:
        cfg.bot_emoji = str(data['bot_emoji'])[:16]
    if 'persona_message' in data:
        cfg.persona_message = data['persona_message']
    if 'system_prompt' in data:
        cfg.system_prompt = data['system_prompt']
    for key in ('auto_faq_enabled', 'mcp_prompt_enabled', 'notify_supervision_enabled', 'intervention_enabled'):
        if key in data:
            setattr(cfg, key, bool(data[key]))
    if 'auto_faq_threshold' in data:
        from contextlib import suppress

        with suppress(TypeError, ValueError):
            cfg.auto_faq_threshold = max(1, int(data['auto_faq_threshold']))
    db.session.commit()
    return jsonify({'status': 'ok', 'config': cfg.to_dict()})


# ────────────────────────────────────────────────────────────────────────
# Chasqui FAQ (CRUD + auto-growth)
# ────────────────────────────────────────────────────────────────────────
@telegram_bp.route('/faq', methods=['GET', 'POST'])
@jwt_required()
def faq_list():
    cfg = BotConfig.get_or_create()
    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        question = (data.get('question') or '').strip()
        answer = (data.get('answer') or '').strip()
        if not question or not answer:
            return jsonify({'error': 'question y answer son obligatorios'}), 400
        faq = Faq(
            question=question,
            answer=answer,
            category=(data.get('category') or 'general'),
            keywords=data.get('keywords') or '',
            is_active=bool(data.get('is_active', True)),
            source='manual',
            status='active',
        )
        db.session.add(faq)
        db.session.commit()
        return jsonify({'status': 'ok', 'faq': faq.to_dict()}), 201

    category = request.args.get('category')
    q = Faq.query.filter(Faq.status == 'active')
    if category:
        q = q.filter_by(category=category)
    faqs = q.order_by(Faq.usage_count.desc(), Faq.id.desc()).all()
    return jsonify([f.to_dict() for f in faqs])


@telegram_bp.route('/faq/proposed', methods=['GET'])
@jwt_required()
def faq_proposed():
    """Pending auto-proposed FAQs (repeated unanswered questions) for approval."""
    faqs = Faq.query.filter_by(status='proposed').order_by(Faq.usage_count.desc()).all()
    return jsonify([f.to_dict() for f in faqs])


@telegram_bp.route('/faq/autogrow', methods=['POST'])
@jwt_required()
def faq_autogrow():
    """Manually trigger auto-growth: promote repeated unanswered questions to proposed FAQs."""
    from app.services.faq_service import auto_propose_faq

    created = auto_propose_faq()
    return jsonify({'status': 'ok', 'proposed': created})


@telegram_bp.route('/faq/search', methods=['POST'])
@jwt_required()
def faq_search():
    from app.services.faq_service import match_faq

    data = request.get_json(silent=True) or {}
    query = data.get('query') or ''
    limit = data.get('limit', 5)
    matches = match_faq(query, limit=int(limit))
    return jsonify([{'id': m['id'], 'score': m['score'], 'faq': m['faq'].to_dict()} for m in matches])


@telegram_bp.route('/faq/<int:faq_id>', methods=['PUT', 'DELETE'])
@jwt_required()
def faq_item(faq_id):
    faq = Faq.query.get(faq_id)
    if not faq:
        return jsonify({'error': 'FAQ no encontrada'}), 404

    if request.method == 'DELETE':
        db.session.delete(faq)
        db.session.commit()
        return jsonify({'status': 'ok'})

    data = request.get_json(silent=True) or {}
    if 'question' in data:
        faq.question = data['question']
    if 'answer' in data:
        faq.answer = data['answer']
    if 'category' in data:
        faq.category = data['category'] or 'general'
    if 'keywords' in data:
        faq.keywords = data['keywords']
    if 'is_active' in data:
        faq.is_active = bool(data['is_active'])
    if data.get('approve'):
        # Approve a proposed (auto) FAQ -> make it active
        faq.status = 'active'
        faq.is_active = True
        faq.source = 'auto'
    db.session.commit()
    return jsonify({'status': 'ok', 'faq': faq.to_dict()})


# ────────────────────────────────────────────────────────────────────────
# Chasqui Webhook
# ────────────────────────────────────────────────────────────────────────
@telegram_bp.route('/webhook/status', methods=['GET'])
@jwt_required()
def webhook_status():
    try:
        from app.services.telegram_bot_service import _tg_request

        token = current_app.config.get('TELEGRAM_BOT_TOKEN')
        if not token:
            return jsonify({'ok': False, 'error': 'TELEGRAM_BOT_TOKEN no configurado', 'active': False})
        info = _tg_request('getWebhookInfo', None, token)
        result = info.get('result', {})
        return jsonify(
            {
                'ok': info.get('ok'),
                'active': bool(result.get('url')),
                'url': result.get('url'),
                'pending_update_count': result.get('pending_update_count', 0),
                'last_error_message': result.get('last_error_message'),
                'last_error_date': result.get('last_error_date'),
                'max_connections': result.get('max_connections'),
                'raw': result,
            }
        )
    except Exception as e:
        logger.error(f'webhook status error: {e}')
        return jsonify({'ok': False, 'error': str(e), 'active': False})


@telegram_bp.route('/webhook/setup', methods=['POST'])
@jwt_required()
def webhook_setup():
    data = request.get_json(silent=True) or {}
    url = (data.get('url') or '').strip()
    secret = data.get('secret_token') or ''
    from app.services.telegram_bot_service import _tg_request

    token = current_app.config.get('TELEGRAM_BOT_TOKEN')
    if not token:
        return jsonify({'ok': False, 'error': 'TELEGRAM_BOT_TOKEN no configurado'})
    if not url:
        return jsonify({'ok': False, 'error': 'url requerida'}), 400

    payload = {'url': url}
    if secret:
        payload['secret_token'] = secret
    try:
        result = _tg_request('setWebhook', payload, token)
        if secret:
            os.environ['TELEGRAM_WEBHOOK_SECRET'] = secret
        return jsonify({'ok': result.get('ok'), 'description': result.get('description'), 'result': result})
    except Exception as e:
        logger.error(f'webhook setup error: {e}')
        return jsonify({'ok': False, 'error': str(e)})


@telegram_bp.route('/webhook', methods=['DELETE'])
@jwt_required()
def webhook_delete():
    from app.services.telegram_bot_service import _tg_request

    token = current_app.config.get('TELEGRAM_BOT_TOKEN')
    if not token:
        return jsonify({'ok': False, 'error': 'TELEGRAM_BOT_TOKEN no configurado'})
    try:
        result = _tg_request('deleteWebhook', None, token)
        return jsonify({'ok': result.get('ok'), 'result': result})
    except Exception as e:
        logger.error(f'webhook delete error: {e}')
        return jsonify({'ok': False, 'error': str(e)})


# ────────────────────────────────────────────────────────────────────────
# Chasqui Test message
# ────────────────────────────────────────────────────────────────────────
@telegram_bp.route('/test', methods=['POST'])
@jwt_required()
def send_test():
    data = request.get_json(silent=True) or {}
    chat_id = data.get('chat_id')
    text = (data.get('text') or '').strip()
    if not chat_id or not text:
        return jsonify({'error': 'chat_id y text son obligatorios'}), 400

    from app.services.telegram_bot_service import send_telegram_message

    token = current_app.config.get('TELEGRAM_BOT_TOKEN')
    ok = send_telegram_message(int(chat_id), text, token)
    if ok:
        return jsonify({'status': 'sent', 'message': 'Mensaje de prueba enviado'})
    return jsonify(
        {'error': 'No se pudo enviar el mensaje (revisa el chat_id y que el usuario haya iniciado el bot)'}
    ), 400


# ────────────────────────────────────────────────────────────────────────
# Chasqui Intervention: admin replies from the panel as the bot
# ────────────────────────────────────────────────────────────────────────
@telegram_bp.route('/reply', methods=['POST'])
@jwt_required()
def bot_reply():
    """Admin intervention: send a message to a Telegram chat directly from the panel."""
    data = request.get_json(silent=True) or {}
    chat_id = data.get('chat_id')
    text = (data.get('text') or '').strip()
    if not chat_id or not text:
        return jsonify({'error': 'chat_id y text son obligatorios'}), 400

    from app.services.telegram_bot_service import send_telegram_message

    token = current_app.config.get('TELEGRAM_BOT_TOKEN')
    ok = send_telegram_message(int(chat_id), text, token)
    if ok:
        return jsonify({'status': 'sent', 'message': 'Mensaje enviado como el bot'})
    return jsonify({'error': 'No se pudo enviar (revisa que el chat exista y haya iniciado el bot)'}), 400
