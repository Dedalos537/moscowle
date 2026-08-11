import http.client
import json
import logging
import tempfile
from datetime import UTC, datetime

from flask import current_app

logger = logging.getLogger('app.telegram')

# In-memory pending confirmations: chat_id -> {data, timestamp}
_pending_confirmations = {}

CONFIRMATION_TTL_SECONDS = 300


def _tg_request(method, data=None, bot_token=None):
    """Send request to Telegram Bot API using stdlib http.client."""
    conn = http.client.HTTPSConnection('api.telegram.org', timeout=30)
    body = json.dumps(data).encode() if data else None
    conn.request(
        'POST',
        f'/bot{bot_token}/{method}',
        body=body,
        headers={'Content-Type': 'application/json'},
    )
    resp = conn.getresponse()
    result = json.loads(resp.read().decode())
    conn.close()
    return result


def send_telegram_message(chat_id, text, bot_token=None, reply_markup=None):
    """Send a text message to a Telegram chat."""
    if not bot_token:
        return None
    payload = {
        'chat_id': chat_id,
        'text': text[:4096],
        'parse_mode': 'Markdown',
    }
    if reply_markup:
        payload['reply_markup'] = reply_markup
    try:
        return _tg_request('sendMessage', payload, bot_token)
    except Exception as e:
        logger.error(f'Telegram sendMessage failed: {e}')
        return None


def send_typing_action(chat_id, bot_token=None):
    """Send typing indicator."""
    if not bot_token:
        return
    try:
        _tg_request('sendChatAction', {'chat_id': chat_id, 'action': 'typing'}, bot_token)
    except Exception:
        pass


def download_telegram_file(file_id, bot_token):
    """Download a file from Telegram and return the local temp path."""
    info = _tg_request('getFile', {'file_id': file_id}, bot_token)
    if not info.get('ok'):
        return None
    file_path = info['result']['file_path']

    conn = http.client.HTTPSConnection('api.telegram.org', timeout=60)
    conn.request('GET', f'/file/bot{bot_token}/{file_path}')
    resp = conn.getresponse()
    data = resp.read()
    conn.close()

    suffix = '.' + file_path.rsplit('.', 1)[-1] if '.' in file_path else '.ogg'
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(data)
        return tmp.name


def process_text_message(chat_id, text, user_id, user_role, mode='grande'):
    """Process a text message through MCP and return the response."""
    from app.services.mcp_service import MCPService

    send_typing_action(chat_id, current_app.config.get('TELEGRAM_BOT_TOKEN'))

    mcp = MCPService()
    result = mcp.process_message(
        message=text,
        user_role=user_role,
        user_id=user_id,
        mode=mode,
    )

    if result.get('requires_confirmation'):
        pending = result.get('pending_tool', {})
        _pending_confirmations[chat_id] = {
            'data': pending,
            'user_id': user_id,
            'user_role': user_role,
            'mode': mode,
            'timestamp': datetime.now(UTC),
        }
        tool_name = pending.get('name', 'unknown')
        tool_args = pending.get('args', {})
        args_preview = json.dumps(tool_args, ensure_ascii=False)[:200]
        return {
            'type': 'confirmation_required',
            'tool_name': tool_name,
            'args_preview': args_preview,
            'response': result.get('response', 'Acción pendiente de confirmación.'),
        }

    return {
        'type': 'response',
        'response': result.get('response', 'Sin respuesta.'),
    }


def process_voice_message(chat_id, file_id, user_id, user_role, mode='grande'):
    """Download voice, transcribe via Groq, then process through MCP."""
    bot_token = current_app.config.get('TELEGRAM_BOT_TOKEN')
    temp_path = download_telegram_file(file_id, bot_token)

    if not temp_path:
        return {'type': 'error', 'response': 'No pude descargar el audio.'}

    try:
        import os

        with open(temp_path, 'rb') as f:
            audio_data = f.read()
        os.unlink(temp_path)

        groq_key = current_app.config.get('GROQ_API_KEY')
        if not groq_key:
            return {'type': 'error', 'response': 'Servicio de transcripción no disponible.'}

        import base64
        import http.client as httplib

        audio_b64 = base64.b64encode(audio_data).decode()
        conn = httplib.HTTPSConnection('api.groq.com', timeout=30)
        conn.request(
            'POST',
            '/openai/v1/audio/transcriptions',
            body=json.dumps(
                {
                    'model': 'whisper-large-v3',
                    'audio': f'data:audio/ogg;base64,{audio_b64}',
                    'response_format': 'text',
                }
            ),
            headers={
                'Authorization': f'Bearer {groq_key}',
                'Content-Type': 'application/json',
            },
        )
        resp = conn.getresponse()
        transcription = resp.read().decode().strip()
        conn.close()

        if not transcription:
            return {'type': 'error', 'response': 'No pude transcribir el audio.'}

        send_telegram_message(
            chat_id,
            f'🎤 *Transcrito:* {transcription}\n\n_Procesando..._',
            bot_token,
        )

        return process_text_message(chat_id, transcription, user_id, user_role, mode)

    except Exception as e:
        logger.error(f'Voice processing error: {e}', exc_info=True)
        try:
            os.unlink(temp_path)
        except Exception:
            pass
        return {'type': 'error', 'response': f'Error procesando audio: {str(e)[:100]}'}


def confirm_pending_operation(chat_id, confirmed=True):
    """Handle confirmation or cancellation of a pending write operation."""
    pending = _pending_confirmations.pop(chat_id, None)
    if not pending:
        return {'type': 'error', 'response': 'No hay operación pendiente.'}

    if not confirmed:
        return {'type': 'response', 'response': '❌ Operación cancelada.'}

    from app.services.mcp_service import MCPService

    mcp = MCPService()
    result = mcp.process_message(
        message='Confirmar operación',
        user_role=pending['user_role'],
        user_id=pending['user_id'],
        mode=pending['mode'],
        confirmed_tool=pending['data'],
    )

    return {
        'type': 'response',
        'response': result.get('response', 'Operación ejecutada.'),
    }


def handle_webhook_update(update):
    """Process a raw Telegram webhook update dict."""
    bot_token = current_app.config.get('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        logger.warning('TELEGRAM_BOT_TOKEN not configured')
        return

    msg = update.get('message') or update.get('edited_message')
    if not msg:
        callback = update.get('callback_query')
        if callback:
            _handle_callback(callback, bot_token)
        return

    chat_id = msg.get('chat', {}).get('id')
    if not chat_id:
        return

    from app import db
    from app.models.telegram_user import TelegramUser

    tg_user = TelegramUser.query.filter_by(telegram_chat_id=chat_id).first()

    if msg.get('text') == '/start':
        _handle_start(chat_id, msg.get('from', {}), tg_user, bot_token)
        return

    if msg.get('text', '').startswith('/link'):
        _handle_link(chat_id, msg['text'], tg_user, bot_token)
        return

    if msg.get('text') == '/unlink':
        _handle_unlink(chat_id, tg_user, bot_token)
        return

    if msg.get('text') == '/status':
        _handle_status(chat_id, tg_user, bot_token)
        return

    if msg.get('text') == '/help':
        _handle_help(chat_id, bot_token)
        return

    if not tg_user or not tg_user.is_linked:
        send_telegram_message(
            chat_id,
            '⚠️ Tu cuenta no está vinculada.\nUsa /start para vincular.',
            bot_token,
        )
        return

    tg_user.last_interaction_at = datetime.now(UTC)
    db.session.commit()

    if msg.get('voice') or msg.get('audio'):
        result = process_voice_message(
            chat_id,
            msg['voice']['file_id'] if msg.get('voice') else msg['audio']['file_id'],
            tg_user.admin_user_id,
            'admin',
        )
    elif msg.get('text'):
        text = msg['text']
        if chat_id in _pending_confirmations:
            if text.lower() in ('si', 'sí', 'yes', 'confirmar', 'confirm', 'ok'):
                result = confirm_pending_operation(chat_id, confirmed=True)
            elif text.lower() in ('no', 'cancelar', 'cancel'):
                result = confirm_pending_operation(chat_id, confirmed=False)
            else:
                result = process_text_message(chat_id, text, tg_user.admin_user_id, 'admin')
        else:
            result = process_text_message(chat_id, text, tg_user.admin_user_id, 'admin')
    else:
        return

    response_text = result.get('response', 'Sin respuesta.')

    if result.get('type') == 'confirmation_required':
        tool_name = result.get('tool_name', 'unknown')
        args_preview = result.get('args_preview', '')
        confirmation_msg = (
            f'⚠️ *Confirmación requerida*\n\n'
            f'*Operación:* {tool_name}\n'
            f'*Detalles:* {args_preview}\n\n'
            f'¿Deseas ejecutar esta operación?\n'
            f'Responde *sí* o *no*.'
        )
        send_telegram_message(chat_id, confirmation_msg, bot_token)
    elif len(response_text) > 4000:
        for i in range(0, len(response_text), 4000):
            send_telegram_message(chat_id, response_text[i : i + 4000], bot_token)
    else:
        send_telegram_message(chat_id, response_text, bot_token)


def _handle_start(chat_id, from_user, tg_user, bot_token):
    from app import db
    from app.models.telegram_user import TelegramUser

    if tg_user and tg_user.is_linked:
        send_telegram_message(
            chat_id,
            '✅ Tu cuenta ya está vinculada.\nEnvíame un mensaje para interactuar.\n\nUsa /help para ver comandos.',
            bot_token,
        )
        return

    if not tg_user:
        tg_user = TelegramUser(
            telegram_chat_id=chat_id,
            telegram_user_id=from_user.get('id'),
            telegram_username=from_user.get('username'),
            telegram_first_name=from_user.get('first_name'),
        )
        db.session.add(tg_user)

    link_code = tg_user.generate_link_code()
    db.session.commit()

    send_telegram_message(
        chat_id,
        f'👋 *Bienvenido!*\n\n'
        f'Para vincular tu Telegram a tu cuenta de admin:\n\n'
        f'1. Inicia sesión en el panel de admin\n'
        f'2. Ve a *Configuración > Integración Telegram*\n'
        f'3. Ingresa este código: `{link_code}`\n\n'
        f'⏰ El código expira en 10 minutos.\n'
        f'Usa /link <código> si ya tienes uno.',
        bot_token,
        reply_markup={'remove_keyboard': True},
    )


def _handle_link(chat_id, text, tg_user, bot_token):
    from app import db
    from app.models.telegram_user import TelegramUser

    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        send_telegram_message(chat_id, 'Uso: /link <código-de-6-caracteres>', bot_token)
        return

    code = parts[1].strip().upper()

    if not tg_user:
        send_telegram_message(chat_id, 'Usa /start primero para generar un código.', bot_token)
        return

    if tg_user.is_link_code_valid(code):
        admin_user = TelegramUser.query.filter_by(link_code=code, is_linked=False).first()

        if not admin_user:
            send_telegram_message(chat_id, '❌ Código inválido. Intenta de nuevo.', bot_token)
            return

        tg_user.admin_user_id = admin_user.admin_user_id or admin_user.id
        tg_user.is_linked = True
        tg_user.link_code = None
        tg_user.link_code_expires_at = None
        db.session.commit()

        send_telegram_message(
            chat_id,
            '✅ *¡Cuenta vinculada!*\n\n'
            'Puedes:\n'
            '• Enviar mensajes de texto para consultar datos\n'
            '• Enviar mensajes de voz para comandos por voz\n'
            '• Recibir notificaciones\n\n'
            'Usa /help para ver comandos.',
            bot_token,
        )
    else:
        send_telegram_message(
            chat_id,
            '❌ Código expirado o inválido.\nUsa /start para generar uno nuevo.',
            bot_token,
        )


def _handle_unlink(chat_id, tg_user, bot_token):
    from app import db

    if not tg_user or not tg_user.is_linked:
        send_telegram_message(chat_id, 'No hay cuenta vinculada.', bot_token)
        return

    tg_user.is_linked = False
    tg_user.admin_user_id = None
    db.session.commit()

    send_telegram_message(chat_id, '🔗 Cuenta desvinculada.', bot_token)


def _handle_status(chat_id, tg_user, bot_token):
    if not tg_user or not tg_user.is_linked:
        send_telegram_message(chat_id, '⚠️ No hay cuenta vinculada.', bot_token)
        return

    last = tg_user.last_interaction_at
    last_str = last.strftime('%d/%m/%Y %H:%M') if last else 'Nunca'

    send_telegram_message(
        chat_id,
        f'📊 *Estado*\n\n'
        f'Vinculado: ✅\n'
        f'Usuario: @{tg_user.telegram_username or "N/A"}\n'
        f'Última interacción: {last_str}\n'
        f'Notificaciones: {"Activadas" if tg_user.notifications_enabled else "Desactivadas"}',
        bot_token,
    )


def _handle_help(chat_id, bot_token):
    send_telegram_message(
        chat_id,
        '🤖 *Comandos disponibles:*\n\n'
        '/start — Vincular cuenta\n'
        '/link <código> — Vincular con código\n'
        '/unlink — Desvincular cuenta\n'
        '/status — Ver estado\n'
        '/help — Esta ayuda\n\n'
        '*Uso general:*\n'
        '• Escribe un mensaje para interactuar con el sistema\n'
        '• Envía audio para comandos por voz\n'
        '• Puedes registrar pagos, consultar pacientes, etc.\n\n'
        '*Ejemplos:*\n'
        '• "¿Cuántos pacientes hay?"\n'
        '• "Registrar pago de Juan Pérez 200 soles"\n'
        '• "Resumen financiero de mayo"',
        bot_token,
    )


def _handle_callback(callback, bot_token):
    """Handle inline keyboard callback queries."""
    data = callback.get('data', '')
    chat_id = callback.get('from', {}).get('id')
    callback_id = callback.get('id')

    if not chat_id:
        return

    if data == 'confirm_yes':
        result = confirm_pending_operation(chat_id, confirmed=True)
    elif data == 'confirm_no':
        result = confirm_pending_operation(chat_id, confirmed=False)
    else:
        return

    _tg_request('answerCallbackQuery', {'callback_query_id': callback_id}, bot_token)

    response_text = result.get('response', 'Sin respuesta.')
    send_telegram_message(chat_id, response_text, bot_token)


def send_notification_to_telegram(user_id, title, message, priority='normal'):
    """Forward an in-app notification to all linked Telegram accounts of a user."""
    from app.models.telegram_user import TelegramUser

    bot_token = current_app.config.get('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        return

    priority_emoji = {'high': '🔴', 'medium': '🟡', 'normal': '🟢'}.get(priority, '⚪')

    tg_users = TelegramUser.query.filter_by(
        admin_user_id=user_id,
        is_linked=True,
        is_active=True,
        notifications_enabled=True,
    ).all()

    for tu in tg_users:
        send_telegram_message(
            tu.telegram_chat_id,
            f'{priority_emoji} *{title or "Notificación"}*\n\n{message}',
            bot_token,
        )
        tu.last_interaction_at = datetime.now(UTC)

    from app import db

    db.session.commit()
