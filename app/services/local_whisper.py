"""
Servicio de transcripción local usando faster-whisper.
Funciona sin API keys — corre en CPU en el servidor Ubuntu.
"""

import gc
import logging
import os
import tempfile

logger = logging.getLogger(__name__)

_model = None
_model_name = None


def _get_model(model_size='small'):
    """Lazy-load del modelo whisper (se carga una vez y se reutiliza)."""
    global _model, _model_name

    if _model is not None and _model_name == model_size:
        return _model

    try:
        from faster_whisper import WhisperModel

        logger.info(f'Cargando modelo faster-whisper: {model_size}')
        _model = WhisperModel(model_size, device='cpu', compute_type='int8')
        _model_name = model_size
        logger.info(f'Modelo faster-whisper cargado: {model_size}')
        return _model
    except Exception as e:
        logger.error(f'Error cargando faster-whisper: {e}')
        raise


def transcribe_local(audio_path, language='es', model_size='small'):
    """
    Transcribe audio usando faster-whisper local.

    Args:
        audio_path: Ruta al archivo de audio
        language: Código de idioma (default 'es' = español)
        model_size: Tamaño del modelo ('tiny', 'base', 'small', 'medium')

    Returns:
        dict con keys: text, duration, language
    """
    if not os.path.exists(audio_path):
        raise ValueError(f'Archivo de audio no encontrado: {audio_path}')

    model = _get_model(model_size)

    try:
        logger.info(f'Transcribiendo audio: {audio_path}')
        segments, info = model.transcribe(
            audio_path,
            language=language,
            beam_size=5,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500),
        )

        text_parts = []
        for segment in segments:
            text_parts.append(segment.text.strip())

        transcript_text = ' '.join(text_parts)
        duration = info.duration if hasattr(info, 'duration') else 0
        detected_lang = info.language if hasattr(info, 'language') else language

        logger.info(f'Audio transcrito: {len(transcript_text)} caracteres, duración={duration}s')

        return {
            'text': transcript_text,
            'duration': int(duration) if duration else 0,
            'language': detected_lang,
        }

    except Exception as e:
        logger.error(f'Error en transcripción local: {e}')
        raise ValueError(f'Error al transcribir el audio: {str(e)}')

    finally:
        gc.collect()


def transcribe_telegram_voice(audio_bytes, filename='voice.ogg'):
    """
    Transcribe bytes de audio de Telegram.

    Args:
        audio_bytes: Bytes del archivo de audio
        filename: Nombre del archivo (para detectar formato)

    Returns:
        dict con keys: text, duration, language
    """
    suffix = os.path.splitext(filename)[1] or '.ogg'

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        return transcribe_local(tmp_path)
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
