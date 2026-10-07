"""Recepción de Telegram por long-polling (getUpdates) para cuando NO hay webhook.

Sin webhook el bot no recibía nada. El worker sólo arranca si el token existe y Telegram no tiene un
webhook configurado (si lo tuviera, getUpdates daría conflicto). Un candado de archivo evita duplicados
entre procesos. Se desactiva con TELEGRAM_POLLING=0.
"""

import logging
import os
import tempfile

logger = logging.getLogger(__name__)

_state = {'running': False}
_LOCK_PATH = os.path.join(tempfile.gettempdir(), 'moscowle_telegram_polling.lock')


def status():
    return {'polling': _state['running']}


def _acquire_lock():
    try:
        import fcntl

        handle = open(_LOCK_PATH, 'w')
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return handle
    except Exception:
        return None


def start(app):
    if _state['running'] or os.environ.get('TELEGRAM_POLLING', '1') == '0' or app.config.get('TESTING'):
        return False
    token = app.config.get('TELEGRAM_BOT_TOKEN')
    if not token:
        return False
    lock = _acquire_lock()
    if lock is None:
        return False
    import eventlet

    def _loop():
        from app.services.telegram_bot_service import _tg_request, handle_webhook_update

        _state['running'] = True
        offset = None
        try:
            with app.app_context():
                info = _tg_request('getWebhookInfo', None, token) or {}
                if (info.get('result') or {}).get('url'):
                    logger.info('Telegram: hay webhook activo, no se usa polling')
                    return
            logger.info('Telegram: iniciando long-polling (sin webhook)')
            while True:
                try:
                    with app.app_context():
                        payload = {'timeout': 25, 'allowed_updates': ['message', 'callback_query']}
                        if offset is not None:
                            payload['offset'] = offset
                        data = _tg_request('getUpdates', payload, token) or {}
                        for update in data.get('result') or []:
                            offset = update['update_id'] + 1
                            try:
                                handle_webhook_update(update)
                            except Exception:
                                logger.exception('Error procesando update %s', update.get('update_id'))
                    eventlet.sleep(0.2)
                except Exception:
                    logger.debug('getUpdates falló; reintento', exc_info=True)
                    eventlet.sleep(5)
        finally:
            _state['running'] = False
            lock.close()

    eventlet.spawn(_loop)
    return True
