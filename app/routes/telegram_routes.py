import hmac
import logging
import time

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app import db
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

    def _process_bg():
        with current_app.app_context():
            try:
                from app.services.telegram_bot_service import handle_webhook_update

                handle_webhook_update(update)
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
