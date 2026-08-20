import http.client
import json
import logging
import re
import tempfile
from datetime import UTC, datetime

from flask import current_app

logger = logging.getLogger('app.telegram')

CONFIRMATION_TTL_SECONDS = 300

# Bot personality
BOT_NAME = 'Chasqui'
BOT_EMOJI = '🦜'


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


def send_telegram_message(chat_id, text, bot_token=None, reply_markup=None, parse_mode='Markdown'):
    """Send a text message to a Telegram chat and return the message_id."""
    if not bot_token:
        return None
    payload = {
        'chat_id': chat_id,
        'text': text[:4096],
        'parse_mode': parse_mode,
    }
    if reply_markup:
        payload['reply_markup'] = reply_markup
    try:
        result = _tg_request('sendMessage', payload, bot_token)
        return result.get('result', {}).get('message_id')
    except Exception as e:
        logger.error(f'Telegram sendMessage failed: {e}')
        return None


def edit_telegram_message(chat_id, message_id, text, bot_token=None, parse_mode='Markdown'):
    """Edit an existing message."""
    if not bot_token or not message_id:
        return False
    data = {
        'chat_id': chat_id,
        'message_id': message_id,
        'text': text,
        'parse_mode': parse_mode,
    }
    try:
        result = _tg_request('editMessageText', data, bot_token)
        return result.get('ok', False)
    except Exception:
        return False


def send_typing_action(chat_id, bot_token=None):
    """Send typing indicator."""
    if not bot_token:
        return
    try:
        _tg_request('sendChatAction', {'chat_id': chat_id, 'action': 'typing'}, bot_token)
    except Exception:
        pass


def _get_tg_user(chat_id):
    from app.models.telegram_user import TelegramUser

    return TelegramUser.query.filter_by(telegram_chat_id=chat_id).first()


def _load_pending_confirmation(chat_id):
    """Load a pending confirmation from DB, expiring stale entries."""
    from datetime import UTC as _UTC

    tu = _get_tg_user(chat_id)
    if not tu or not tu.pending_confirmation:
        return None
    if tu.pending_confirmation_expires_at:
        exp = tu.pending_confirmation_expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=_UTC)
        if datetime.now(UTC) > exp:
            tu.pending_confirmation = None
            tu.pending_confirmation_expires_at = None
            tu.awaiting_patient_name = None
            db_commit()
            return None
    return tu.pending_confirmation


def _store_pending_confirmation(chat_id, data):
    from datetime import timedelta as _td

    from app import db

    tu = _get_tg_user(chat_id)
    if not tu:
        return
    tu.pending_confirmation = data
    tu.pending_confirmation_expires_at = datetime.now(UTC) + _td(seconds=CONFIRMATION_TTL_SECONDS)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()


def _clear_pending_confirmation(chat_id):
    tu = _get_tg_user(chat_id)
    if not tu:
        return
    tu.pending_confirmation = None
    tu.pending_confirmation_expires_at = None
    tu.awaiting_patient_name = None
    db_commit()


def _store_awaiting_name(chat_id, data):
    tu = _get_tg_user(chat_id)
    if not tu:
        return
    tu.awaiting_patient_name = data
    db_commit()


def _load_awaiting_name(chat_id):
    tu = _get_tg_user(chat_id)
    if not tu:
        return None
    return tu.awaiting_patient_name


def _pop_awaiting_name(chat_id):
    tu = _get_tg_user(chat_id)
    if not tu:
        return None
    data = tu.awaiting_patient_name
    tu.awaiting_patient_name = None
    db_commit()
    return data


def db_commit():
    from app import db

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()


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


def _parse_telegram_ocr(text):
    """Parse Tesseract OCR text to extract payment voucher data."""
    result = {'amount': None, 'method': None, 'patient_name': None, 'date': None, 'transaction_id': None}

    # Extract amount (S/, S/., soles, or plain numbers) - more flexible patterns
    amount_patterns = [
        r'S/\.?\s*(\d+(?:[.,]\d{1,2})?)',
        r'soles\s*(\d+(?:[.,]\d{1,2})?)',
        r'monto[:\s]*(\d+(?:[.,]\d{1,2})?)',
        r'total[:\s]*(\d+(?:[.,]\d{1,2})?)',
        r'(\d+(?:[.,]\d{1,2})?)\s*(?:soles|PEN|S/)',
        r'enviado[:\s]*(\d+(?:[.,]\d{1,2})?)',
        r'recibido[:\s]*(\d+(?:[.,]\d{1,2})?)',
        r'importe[:\s]*(\d+(?:[.,]\d{1,2})?)',
        r'pago[:\s]*(\d+(?:[.,]\d{1,2})?)',
        r'(\d+(?:[.,]\d{1,2})?)\s*S/',
        r'(\d{2,6}(?:\.\d{2})?)\b',
    ]
    for pattern in amount_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                # Handle comma as decimal separator (common in Peru)
                amount_str = match.group(1).replace(',', '.')
                amount = float(amount_str)
                # Sanity check: amount should be between 0.01 and 1000000
                if 0.01 <= amount <= 1000000:
                    result['amount'] = amount
                    break
            except ValueError:
                continue

    # Detect payment method
    text_lower = text.lower()
    if 'yape' in text_lower:
        result['method'] = 'Yape'
    elif 'plin' in text_lower:
        result['method'] = 'Plin'
    elif 'transfer' in text_lower or 'transferencia' in text_lower:
        result['method'] = 'Transferencia'
    elif 'efectivo' in text_lower or 'cash' in text_lower:
        result['method'] = 'Efectivo'
    elif 'tarjeta' in text_lower or 'card' in text_lower:
        result['method'] = 'Tarjeta'

    # Extract date - more formats for Peruvian apps
    date_patterns = [
        r'(\d{2}/\d{2}/\d{4})',
        r'(\d{4}-\d{2}-\d{2})',
        r'(\d{2}-\d{2}-\d{4})',
        r'(\d{1,2}\s+(?:de\s+)?(?:ene|feb|mar|abr|may|jun|jul|ago|sep|oct|nov|dic)[a-z]*\.?\s+(?:de\s+)?\d{4})',
        r'(\d{1,2}\s+(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+(?:de\s+)?\d{4})',
        r'(\d{2}\.\d{2}\.\d{4})',
        r'(\d{2}\s+\d{2}\s+\d{4})',
    ]
    for pattern in date_patterns:
        match = re.search(pattern, text)
        if match:
            result['date'] = match.group(1)
            break

    # Extract transaction ID / operation number
    tx_patterns = [
        r'(?:operaci[oó]n|n[uú]mero|ref|codigo)[:\s]*(\w{6,})',
        r'(\d{8,12})',
    ]
    for pattern in tx_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result['transaction_id'] = match.group(1)
            break

    return result


def process_text_message(chat_id, text, user_id, user_role, mode='grande'):
    """Process a text message through MCP and return the response."""
    from app.services.mcp_service import MCPService

    bot_token = current_app.config.get('TELEGRAM_BOT_TOKEN')
    send_typing_action(chat_id, bot_token)

    # Respuestas predefinidas para preguntas comunes
    text_lower = text.lower().strip()
    identity_triggers = [
        'quien eres',
        'quién eres',
        'que eres',
        'qué eres',
        'como te llamas',
        'cómo te llamas',
        'tu nombre',
        'tu nombre',
        'presentate',
        'preséntate',
    ]
    if any(trigger in text_lower for trigger in identity_triggers):
        return {
            'type': 'response',
            'response': 'Soy Diego, tu asistente del Centro Juan Pablo II. 💙',
        }

    # Enviar mensaje de "Procesando..." y editarlo con la respuesta
    processing_msg_id = send_telegram_message(
        chat_id,
        '⏳ *Procesando tu solicitud...*',
        bot_token,
    )

    mcp = MCPService()
    result = mcp.process_message(
        message=text,
        user_role=user_role,
        user_id=user_id,
        mode=mode,
        telegram_mode=True,
    )

    if result.get('requires_confirmation'):
        pending = result.get('pending_tool', {})
        if pending.get('name') == 'register_payment' and not (pending.get('args') or {}).get('receipt_url'):
            response_text = (
                '📎 Para registrar un pago necesito el *voucher* (envíalo como foto). Después lo confirmo contigo.'
            )
            edit_telegram_message(chat_id, processing_msg_id, response_text, bot_token)
            return {
                'type': 'response',
                'response': response_text,
            }
        _store_pending_confirmation(
            chat_id,
            {
                'data': pending,
                'user_id': user_id,
                'user_role': user_role,
                'mode': mode,
            },
        )
        tool_name = pending.get('name', 'unknown')
        tool_args = pending.get('args', {})
        args_preview = json.dumps(tool_args, ensure_ascii=False)[:200]
        response_text = result.get('response', 'Acción pendiente de confirmación.')
        edit_telegram_message(chat_id, processing_msg_id, response_text, bot_token)
        return {
            'type': 'confirmation_required',
            'tool_name': tool_name,
            'args_preview': args_preview,
            'response': response_text,
            'already_sent': True,
        }

    response_text = result.get('response', 'Sin respuesta.')
    edit_telegram_message(chat_id, processing_msg_id, response_text, bot_token)
    return {
        'type': 'response',
        'response': response_text,
        'already_sent': True,
    }


def process_voice_message(chat_id, file_id, user_id, user_role, mode='grande'):
    """Download voice, transcribe locally via faster-whisper, then process through MCP."""
    bot_token = current_app.config.get('TELEGRAM_BOT_TOKEN')
    temp_path = download_telegram_file(file_id, bot_token)

    if not temp_path:
        return {'type': 'error', 'response': 'No pude descargar el audio.'}

    try:
        import os

        with open(temp_path, 'rb') as f:
            audio_data = f.read()
        os.unlink(temp_path)

        # Intentar transcripción local primero (faster-whisper)
        transcription = None
        try:
            from app.services.local_whisper import transcribe_telegram_voice

            result = transcribe_telegram_voice(audio_data, filename='voice.ogg')
            transcription = result.get('text', '').strip()
            logger.info(f'Transcripción local exitosa: {len(transcription)} caracteres')
        except Exception as local_err:
            logger.warning(f'Transcripción local falló, intentando Groq: {local_err}')

        # Fallback a Groq si la local falla
        if not transcription:
            groq_key = current_app.config.get('GROQ_API_KEY')
            if groq_key:
                try:
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
                    logger.info(f'Transcripción Groq exitosa: {len(transcription)} caracteres')
                except Exception as groq_err:
                    logger.error(f'Groq transcription also failed: {groq_err}')

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
    pending_data = _load_pending_confirmation(chat_id)
    if not pending_data:
        return {'type': 'error', 'response': 'No hay operación pendiente.'}

    if not confirmed:
        _clear_pending_confirmation(chat_id)
        return {'type': 'response', 'response': '❌ Operación cancelada.'}

    from app.services.mcp_service import MCPService

    mcp = MCPService()
    result = mcp.process_message(
        message='Confirmar operación',
        user_role=pending_data['user_role'],
        user_id=pending_data['user_id'],
        mode=pending_data['mode'],
        confirmed_tool=pending_data['data'],
    )
    _clear_pending_confirmation(chat_id)

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

    if msg.get('text') == '/help' or msg.get('text') == '/ayuda':
        _handle_help(chat_id, bot_token)
        return

    if msg.get('text') == '/pagos':
        _handle_quick_command(chat_id, tg_user, '¿Cuáles son los últimos 10 pagos registrados?', bot_token)
        return

    if msg.get('text') == '/pacientes':
        _handle_quick_command(chat_id, tg_user, 'Lista los primeros 10 pacientes activos', bot_token)
        return

    if msg.get('text') == '/sesiones':
        _handle_quick_command(chat_id, tg_user, '¿Qué sesiones hay programadas para hoy?', bot_token)
        return

    if msg.get('text') == '/resumen':
        _handle_quick_command(chat_id, tg_user, 'Dame el resumen financiero del mes actual', bot_token)
        return

    if msg.get('text') == '/desactivar_sla':
        _handle_sla_toggle(chat_id, tg_user, False, bot_token)
        return

    if msg.get('text') == '/activar_sla':
        _handle_sla_toggle(chat_id, tg_user, True, bot_token)
        return

    if msg.get('text') == '/notificaciones' or msg.get('text') == '/notifications':
        _handle_notification_toggle(chat_id, tg_user, bot_token)
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
    elif msg.get('photo'):
        photo = msg['photo'][-1]
        caption = msg.get('caption', '')
        result = process_image_message(
            chat_id,
            photo['file_id'],
            tg_user.admin_user_id,
            'admin',
            caption=caption,
        )
    elif msg.get('text'):
        text = msg['text']
        if _load_awaiting_name(chat_id):
            pending_name = _pop_awaiting_name(chat_id)
            patient_name = text.strip()
            confirmation_msg = (
                f'📸 *Confirmar pago:*\n\n'
                f'• Paciente: {patient_name}\n'
                f'• Monto: S/{pending_name.get("amount")}\n'
                f'• Método: {pending_name.get("method", "Efectivo")}\n'
                f'• Fecha: {pending_name.get("payment_date", "No especificada")}\n\n'
                f'¿Registrar este pago?\n'
                f'Responde *sí* o *no*.'
            )
            _store_pending_confirmation(
                chat_id,
                {
                    'data': {
                        'name': 'register_payment',
                        'args': {
                            'patient_name': patient_name,
                            'amount': pending_name.get('amount'),
                            'method': pending_name.get('method', 'Efectivo'),
                            'payment_date': pending_name.get('payment_date'),
                            'receipt_url': pending_name.get('receipt_url'),
                        },
                    },
                    'user_id': tg_user.admin_user_id,
                    'user_role': 'admin',
                    'mode': 'grande',
                },
            )
            send_telegram_message(chat_id, confirmation_msg, bot_token)
            return
        if _load_pending_confirmation(chat_id):
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
    already_sent = result.get('already_sent', False)

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
    elif not already_sent:
        if len(response_text) > 4000:
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
            f'{BOT_EMOJI} ¡Hola de nuevo! Tu cuenta ya está vinculada.\n\n'
            'Envíame un mensaje para interactuar.\n\n'
            'Usa /ayuda para ver todo lo que puedo hacer.',
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
        f'{BOT_EMOJI} *¡Bienvenido a {BOT_NAME}!*\n\n'
        f'Soy tu asistente inteligente para el Centro Juan Pablo II.\n\n'
        f'Para vincular tu cuenta:\n'
        f'1. Inicia sesión en el panel de admin\n'
        f'2. Ve a *Centro de Operaciones > Bot de Telegram*\n'
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
            f'{BOT_EMOJI} *¡Cuenta vinculada!*\n\n'
            'Ya puedes interactuar con el sistema desde Telegram.\n\n'
            'Puedes:\n'
            '• Enviar mensajes de texto para consultar datos\n'
            '• Enviar mensajes de voz para comandos por voz\n'
            '• Enviar fotos de comprobantes para registrar pagos\n'
            '• Recibir notificaciones importantes\n\n'
            'Usa /ayuda para ver todo lo que puedo hacer.',
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

    send_telegram_message(
        chat_id,
        f'{BOT_EMOJI} Cuenta desvinculada.\n\nSi necesitas volver a vincular, usa /start.',
        bot_token,
    )


def _handle_status(chat_id, tg_user, bot_token):
    if not tg_user or not tg_user.is_linked:
        send_telegram_message(chat_id, '⚠️ No hay cuenta vinculada.', bot_token)
        return

    last = tg_user.last_interaction_at
    last_str = last.strftime('%d/%m/%Y %H:%M') if last else 'Nunca'

    send_telegram_message(
        chat_id,
        f'{BOT_EMOJI} *Estado de {BOT_NAME}*\n\n'
        f'Vinculado: ✅\n'
        f'Usuario: @{tg_user.telegram_username or "N/A"}\n'
        f'Última interacción: {last_str}\n'
        f'Notificaciones: {"Activadas" if tg_user.notifications_enabled else "Desactivadas"}',
        bot_token,
    )


def _handle_help(chat_id, bot_token):
    send_telegram_message(
        chat_id,
        f'{BOT_EMOJI} *{BOT_NAME} — Tu asistente inteligente*\n\n'
        '*Comandos:*\n'
        '/start — Vincular cuenta\n'
        '/link <código> — Vincular con código\n'
        '/unlink — Desvincuar cuenta\n'
        '/status — Ver estado\n'
        '/ayuda — Esta ayuda\n'
        '/pagos — Registrar pago rápido\n'
        '/pacientes — Buscar paciente\n'
        '/sesiones — Ver sesiones del día\n'
        '/resumen — Resumen financiero\n'
        '/desactivar_sla — Desactivar monitoreo SLA\n'
        '/activar_sla — Activar monitoreo SLA\n'
        '/notificaciones — Activar/desactivar notificaciones\n\n'
        '*Puedo hacer mucho más:*\n'
        '• 📋 Consultar pacientes, sesiones, pagos\n'
        '• 💰 Registrar pagos (texto o imagen)\n'
        '• 📊 Generar reportes financieros\n'
        '• 🔍 Buscar información específica\n'
        '• 📸 Procesar comprobantes (envía una foto)\n'
        '• 🎤 Escuchar comandos por voz\n\n'
        '*Ejemplos:*\n'
        '• "¿Cuántos pacientes hay?"\n'
        '• "Registrar pago de Juan Pérez 200 soles"\n'
        '• "Resumen financiero de mayo"\n'
        '• "Sesiones pendientes de Carlos"\n'
        '• [Envía una foto de comprobante]\n\n'
        f'_{BOT_EMOJI} Soy como Chasqui, tu mensajero confiable._',
        bot_token,
    )


def _handle_sla_toggle(chat_id, tg_user, enable, bot_token):
    """Handle SLA enable/disable toggle."""
    if not tg_user or not tg_user.is_linked:
        send_telegram_message(
            chat_id,
            '⚠️ Tu cuenta no está vinculada.\nUsa /start para vincular.',
            bot_token,
        )
        return

    # Verificar que sea admin
    from app.models.user import User

    user = User.query.get(tg_user.admin_user_id)
    if not user or user.rol != 'admin':
        send_telegram_message(
            chat_id,
            '🔒 Solo los administradores pueden cambiar esta configuración.',
            bot_token,
        )
        return

    # Actualizar configuración en la tabla de incidentes

    try:
        # Usar una tabla de configuración del sistema o una columna en Incidente
        # Por ahora, usamos una variable de entorno como alternativa rápida

        config_path = '/home/diego/moscowle_ia/.env'

        # Leer archivo actual
        with open(config_path) as f:
            env_content = f.read()

        # Actualizar o agregar SLA_ENABLED
        if 'SLA_ENABLED=' in env_content:
            if enable:
                env_content = env_content.replace('SLA_ENABLED=false', 'SLA_ENABLED=true')
            else:
                env_content = env_content.replace('SLA_ENABLED=true', 'SLA_ENABLED=false')
        else:
            env_content += f'\nSLA_ENABLED={"true" if enable else "false"}\n'

        # Guardar archivo
        with open(config_path, 'w') as f:
            f.write(env_content)

        # Reiniciar servicio para aplicar cambios
        import subprocess

        subprocess.run(
            ['echo', 'Rucula_530', '|', 'sudo', '-S', 'systemctl', 'restart', 'moscowle.service'],
            capture_output=True,
            timeout=10,
        )

        status = 'activado' if enable else 'desactivado'
        emoji = '✅' if enable else '❌'

        send_telegram_message(
            chat_id,
            f'{emoji} *Monitoreo SLA {status}*\n\n'
            f'El sistema {"generará" if enable else "no generará"} incidentes automática por violaciones de SLA.',
            bot_token,
        )

        logger.info(f'SLA monitoring {status} by user {user.id_usuario}')

    except Exception as e:
        logger.error(f'Error toggling SLA: {e}')
        send_telegram_message(
            chat_id,
            '❌ Error al cambiar la configuración de SLA. Intenta de nuevo.',
            bot_token,
        )


def _handle_notification_toggle(chat_id, tg_user, bot_token):
    """Handle /notificaciones command — toggle notifications on/off."""
    if not tg_user or not tg_user.is_linked:
        send_telegram_message(
            chat_id,
            '⚠️ Tu cuenta no está vinculada.\nUsa /start para vincular.',
            bot_token,
        )
        return

    from app import db

    tg_user.notifications_enabled = not tg_user.notifications_enabled
    db.session.commit()

    status = 'activadas' if tg_user.notifications_enabled else 'desactivadas'
    emoji = '🔔' if tg_user.notifications_enabled else '🔕'

    send_telegram_message(
        chat_id,
        f'{emoji} Notificaciones {status}.',
        bot_token,
    )

    logger.info(f'Notifications {"enabled" if tg_user.notifications_enabled else "disabled"} for chat {chat_id}')


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


def _handle_quick_command(chat_id, tg_user, text, bot_token):
    """Process a quick command through MCP."""
    if not tg_user or not tg_user.is_linked:
        send_telegram_message(
            chat_id,
            '⚠️ Tu cuenta no está vinculada.\nUsa /start para vincular.',
            bot_token,
        )
        return

    result = process_text_message(chat_id, text, tg_user.admin_user_id, 'admin')
    response_text = result.get('response', 'Sin respuesta.')

    if len(response_text) > 4000:
        for i in range(0, len(response_text), 4000):
            send_telegram_message(chat_id, response_text[i : i + 4000], bot_token)
    else:
        send_telegram_message(chat_id, response_text, bot_token)


def process_image_message(chat_id, file_id, user_id, user_role, caption=None, mode='grande'):
    """Process an image (voucher/comprobante) through local OCR (Tesseract) and MCP."""
    bot_token = current_app.config.get('TELEGRAM_BOT_TOKEN')
    temp_path = download_telegram_file(file_id, bot_token)

    if not temp_path:
        return {'type': 'error', 'response': 'No pude descargar la imagen.'}

    try:
        import base64
        import os
        import uuid

        with open(temp_path, 'rb') as f:
            image_data = f.read()

        ext = os.path.splitext(temp_path)[1] or '.jpg'
        receipt_name = f'{uuid.uuid4().hex}{ext}'
        voucher_dir = os.path.join(current_app.config.get('UPLOAD_FOLDER', 'uploads'), 'vouchers')
        os.makedirs(voucher_dir, exist_ok=True)
        receipt_path = f'vouchers/{receipt_name}'
        try:
            with open(os.path.join(voucher_dir, receipt_name), 'wb') as f:
                f.write(image_data)
        except Exception:
            receipt_path = None

        os.unlink(temp_path)

        ocr_data = None

        # 0. Si el usuario envió caption con datos, usarlos directamente
        if caption and caption.strip():
            amount_match = re.search(r'(\d+(?:\.\d{1,2})?)', caption)
            if amount_match:
                ocr_data = {
                    'amount': float(amount_match.group(1)),
                    'method': None,
                    'patient_name': None,
                    'date': None,
                    'transaction_id': None,
                }
                caption_lower = caption.lower()
                if 'yape' in caption_lower:
                    ocr_data['method'] = 'Yape'
                elif 'plin' in caption_lower:
                    ocr_data['method'] = 'Plin'
                elif 'transfer' in caption_lower:
                    ocr_data['method'] = 'Transferencia'
                elif 'efectivo' in caption_lower or 'cash' in caption_lower:
                    ocr_data['method'] = 'Efectivo'
                if ocr_data.get('amount'):
                    logger.info(f'Datos extraídos del caption: {ocr_data}')

        # 1. Usar moondream vision (modelo local que SÍ puede leer imágenes)
        if not ocr_data or not ocr_data.get('amount'):
            try:
                import base64 as b64

                import ollama as ollama_lib

                ollama_host = os.environ.get('OLLAMA_HOST', 'http://127.0.0.1:11434')
                client = ollama_lib.Client(host=ollama_host)

                image_b64 = b64.b64encode(image_data).decode()

                prompt = (
                    'Look at this payment receipt image from Peru (Yape, Plin, or bank transfer). '
                    'Extract the following data and respond ONLY with a valid JSON object, no other text:\n'
                    '{"amount": number, "method": "Efectivo|Yape|Transferencia|Plin", '
                    '"patient_name": "name if visible", "date": "YYYY-MM-DD if visible", '
                    '"transaction_id": "operation number if visible"}\n'
                    'If a field is not visible, use null.\n'
                    'IMPORTANT: The amount is the main payment amount shown prominently (e.g. S/225), '
                    'NOT small numbers like security codes or phone digits.'
                )

                response = client.chat(
                    model='moondream:1.8b',
                    messages=[
                        {
                            'role': 'user',
                            'content': prompt,
                            'images': [image_b64],
                        }
                    ],
                    options={'temperature': 0.1, 'num_ctx': 2048},
                )

                content = response.get('message', {}).get('content', '')
                logger.info(f'Moondream vision response: {content[:500]}')

                json_match = re.search(r'\{[^{}]*\}', content)
                if json_match:
                    try:
                        ocr_data = json.loads(json_match.group())
                        if ocr_data.get('amount'):
                            logger.info(f'Moondream vision OCR exitoso: {ocr_data}')
                    except json.JSONDecodeError:
                        logger.warning(f'Could not parse moondream response: {content[:200]}')
            except Exception as moondream_err:
                logger.warning(f'Moondream vision OCR falló: {moondream_err}')

        # 2. Fallback a Tesseract OCR si moondream no funcionó
        if not ocr_data or not ocr_data.get('amount'):
            try:
                import io

                import pytesseract
                from PIL import Image as PilImage
                from PIL import ImageFilter, ImageOps

                img = PilImage.open(io.BytesIO(image_data))

                if img.mode != 'L':
                    img = img.convert('L')

                img = ImageOps.autocontrast(img, cutoff=5)
                img = ImageOps.equalize(img)
                img = img.filter(ImageFilter.SHARPEN)
                img = img.filter(ImageFilter.SHARPEN)

                threshold = 100
                img = img.point(lambda x: 255 if x > threshold else 0, '1')
                img = img.resize((img.width * 3, img.height * 3), PilImage.LANCZOS)

                ocr_text = ''
                for psm in ['--psm 6', '--psm 4', '--psm 3']:
                    try:
                        text = pytesseract.image_to_string(
                            img,
                            lang='spa+eng',
                            config=f'{psm} --oem 3',
                        )
                        if text.strip():
                            ocr_text = text
                            break
                    except Exception as psm_err:
                        logger.debug(f'PSM {psm} failed: {psm_err}')
                        continue

                logger.info(f'Telegram Tesseract OCR: {ocr_text[:300]}')

                ocr_data = _parse_telegram_ocr(ocr_text)
                if ocr_data and ocr_data.get('amount'):
                    logger.info(f'Tesseract OCR exitoso: {ocr_data}')
            except Exception as tess_err:
                logger.warning(f'Tesseract OCR falló: {tess_err}')

        # 3. Fallback a Groq vision si ambos fallaron
        if not ocr_data or not ocr_data.get('amount'):
            groq_key = current_app.config.get('GROQ_API_KEY')
            if groq_key:
                try:
                    image_b64 = base64.b64encode(image_data).decode()
                    import http.client as httplib

                    conn = httplib.HTTPSConnection('api.groq.com', timeout=30)
                    conn.request(
                        'POST',
                        '/openai/v1/chat/completions',
                        body=json.dumps(
                            {
                                'model': 'llama-3.2-90b-vision-preview',
                                'messages': [
                                    {
                                        'role': 'user',
                                        'content': [
                                            {
                                                'type': 'text',
                                                'text': (
                                                    'Extrae los datos de este comprobante de pago. '
                                                    'Responde SOLO con un JSON válido: '
                                                    '{"amount": número, "method": "Efectivo|Yape|Transferencia|Plin", '
                                                    '"patient_name": "nombre si aparece", "date": "YYYY-MM-DD si aparece", '
                                                    '"transaction_id": "número de operación si aparece"}. '
                                                    'Si un dato no se ve, usa null.'
                                                ),
                                            },
                                            {
                                                'type': 'image_url',
                                                'image_url': {'url': f'data:image/jpeg;base64,{image_b64}'},
                                            },
                                        ],
                                    }
                                ],
                                'max_tokens': 500,
                                'temperature': 0.1,
                            }
                        ),
                        headers={
                            'Authorization': f'Bearer {groq_key}',
                            'Content-Type': 'application/json',
                        },
                    )
                    resp = conn.getresponse()
                    result = json.loads(resp.read().decode())
                    conn.close()

                    content = result.get('choices', [{}])[0].get('message', {}).get('content', '')

                    try:
                        json_match = content.replace('```json', '').replace('```', '').strip()
                        ocr_data = json.loads(json_match)
                        logger.info(f'Groq vision OCR exitoso: {ocr_data}')
                    except Exception:
                        logger.warning(f'Could not parse Groq OCR response: {content}')
                except Exception as groq_err:
                    logger.error(f'Groq vision OCR falló: {groq_err}')

        if not ocr_data:
            send_telegram_message(
                chat_id,
                '📸 No pude leer los datos de la imagen.\n\n'
                'Por favor, envía los datos manualmente:\n'
                '• Paciente\n'
                '• Monto\n'
                '• Método de pago\n'
                '• Fecha',
                bot_token,
            )
            return {'type': 'response', 'response': 'OCR no pudo procesar la imagen.'}

        amount = ocr_data.get('amount')
        method = ocr_data.get('method', 'Efectivo')
        patient = ocr_data.get('patient_name', 'No identificado')
        date = ocr_data.get('date', 'No especificada')

        if amount is None:
            send_telegram_message(
                chat_id,
                '📸 *No pude leer el monto* en el comprobante.\n\n'
                'Vuelve a enviar la foto del voucher, o envía el monto y paciente manualmente.',
                bot_token,
            )
            return {'type': 'response', 'response': 'OCR sin monto.'}

        if not patient or patient.lower() in ('no identificado', 'null', 'none', 'desconocido'):
            _store_awaiting_name(
                chat_id,
                {
                    'amount': amount,
                    'method': method,
                    'payment_date': date,
                    'receipt_url': receipt_path,
                },
            )
            send_telegram_message(
                chat_id,
                '📸 *No pude identificar al paciente* en el comprobante.\n\n'
                f'• Monto: S/{amount}\n'
                f'• Método: {method}\n'
                f'• Fecha: {date}\n\n'
                'Escribe el *nombre del paciente* para continuar.',
                bot_token,
            )
            return {'type': 'response', 'response': 'OCR procesado, esperando nombre del paciente.'}

        confirmation_msg = (
            f'📸 *Datos extraídos del comprobante:*\n\n'
            f'• Paciente: {patient}\n'
            f'• Monto: S/{amount}\n'
            f'• Método: {method}\n'
            f'• Fecha: {date}\n\n'
            f'¿Registrar este pago?\n'
            f'Responde *sí* o *no*.'
        )

        _store_pending_confirmation(
            chat_id,
            {
                'data': {
                    'name': 'register_payment',
                    'args': {
                        'patient_name': patient,
                        'amount': amount,
                        'method': method,
                        'payment_date': date,
                        'receipt_url': receipt_path,
                    },
                },
                'user_id': user_id,
                'user_role': user_role,
                'mode': mode,
            },
        )

        send_telegram_message(chat_id, confirmation_msg, bot_token)
        return {'type': 'response', 'response': 'OCR procesado, esperando confirmación.'}

    except Exception as e:
        logger.error(f'Image processing error: {e}', exc_info=True)
        try:
            os.unlink(temp_path)
        except Exception:
            pass
        return {'type': 'error', 'response': f'Error procesando imagen: {str(e)[:100]}'}


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
