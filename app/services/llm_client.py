import logging
import os
import time
from datetime import UTC, datetime

logger = logging.getLogger('app.llm')

# Rate-limit provider failure notifications (max 1 per 15 min)
_provider_failure_last_sent = {}
_PROVIDER_FAILURE_COOLDOWN = 900  # seconds

# Circuit breaker: skip providers that recently failed (invalid key, auth, etc.)
_provider_cooldowns = {}
_PROVIDER_COOLDOWN_SECONDS = 600  # 10 min

# ─── Provider configuration ────────────────────────────────────────────────

GLM_BASE_URL = 'https://integrate.api.nvidia.com/v1'
GLM_MODEL = 'z-ai/glm-5.2'

GROQ_MODELS = ['llama-3.3-70b-versatile', 'llama-3.1-8b-instant']
GEMINI_MODEL = 'gemini-2.0-flash'
OLLAMA_MODEL_DEFAULT = 'llama3.1:8b'

_RATE_LIMIT_RETRIES = 2
_RATE_LIMIT_BACKOFF = 2.0

# Provider order. Groq first (fast + free tier) unless overridden via LLM_PROVIDER.
_DEFAULT_PROVIDER_ORDER = ['groq', 'glm', 'gemini', 'ollama']


def _is_rate_limit(exc):
    """Detect 429 / rate-limit errors from any provider client."""
    code = getattr(exc, 'status_code', None) or getattr(exc, 'code', None)
    if code == 429:
        return True
    text = str(exc).lower()
    return any(k in text for k in ('rate limit', 'rate_limit', 'too many requests', '429'))


def _is_auth_error(exc):
    """Detect invalid-key / auth errors (401, 403, or 400 mentioning the API key)."""
    code = getattr(exc, 'status_code', None) or getattr(exc, 'code', None)
    if code in (401, 403):
        return True
    text = str(exc).lower()
    if code == 400 and any(k in text for k in ('api key', 'apikey', 'key not', 'invalid key')):
        return True
    return any(k in text for k in ('invalid api key', 'authentication', 'unauthorized', 'api key not valid'))


def _provider_blocked(name):
    """True if provider is in cooldown and should be skipped this round."""
    return time.time() < _provider_cooldowns.get(name, 0)


def _block_provider(name, exc=None):
    """Put provider in cooldown (e.g. after an invalid key error)."""
    _provider_cooldowns[name] = time.time() + _PROVIDER_COOLDOWN_SECONDS
    logger.warning(f'Provider {name} blocked for {_PROVIDER_COOLDOWN_SECONDS}s: {exc}')


def _provider_order():
    """Return the provider chain order, honoring LLM_PROVIDER override."""
    order = list(_DEFAULT_PROVIDER_ORDER)
    try:
        from flask import current_app

        pref = os.environ.get('LLM_PROVIDER') or current_app.config.get('LLM_PROVIDER')
    except Exception:
        pref = os.environ.get('LLM_PROVIDER')
    if pref:
        pref = pref.lower()
        if pref in order:
            order.remove(pref)
            order.insert(0, pref)
    return order


_PROVIDER_DISPLAY = {'groq': 'Groq', 'glm': 'GLM-5.2', 'gemini': 'Gemini', 'ollama': 'Ollama'}


def _provider_display(name):
    return _PROVIDER_DISPLAY.get(name, name)


def _chat_with_retry(call, retries=_RATE_LIMIT_RETRIES, backoff=_RATE_LIMIT_BACKOFF):
    """Execute a chat completion call, retrying on rate-limit (429)."""
    attempt = 0
    while True:
        try:
            return call()
        except Exception as e:
            if _is_rate_limit(e) and attempt < retries:
                attempt += 1
                logger.info(f'Rate limit hit, retrying in {backoff * attempt:.1f}s (attempt {attempt})')
                time.sleep(backoff * attempt)
                continue
            raise


# ─── Client cache (one per provider) ───────────────────────────────────────

_clients = {}


def get_glm_client():
    """NVIDIA NIM OpenAI-compatible client via openai library."""
    if 'glm' in _clients:
        return _clients['glm']
    try:
        from openai import OpenAI

        api_key = os.environ.get('GLM_API_KEY')
        if not api_key:
            try:
                from flask import current_app
                api_key = current_app.config.get('GLM_API_KEY')
            except Exception:
                pass
        if not api_key:
            logger.warning('GLM_API_KEY not set in environment or config')
            return None
        logger.info(f'Creating GLM client: base_url={GLM_BASE_URL}, key_len={len(api_key)}')
        client = OpenAI(base_url=GLM_BASE_URL, api_key=api_key)
        _clients['glm'] = client
        return client
    except ImportError:
        logger.error('openai library not installed — pip install openai')
        return None
    except Exception as e:
        logger.error(f'Failed to create GLM client: {e}', exc_info=True)
        return None


def get_groq_client():
    if 'groq' in _clients:
        return _clients['groq']
    try:
        from groq import Groq

        api_key = os.environ.get('GROQ_API_KEY')
        if not api_key:
            try:
                from flask import current_app
                api_key = current_app.config.get('GROQ_API_KEY')
            except Exception:
                pass
        if not api_key:
            return None
        client = Groq(api_key=api_key)
        _clients['groq'] = client
        return client
    except ImportError:
        return None
    except Exception as e:
        logger.error(f'Failed to create Groq client: {e}')
        return None


def get_gemini_model():
    if 'gemini' in _clients:
        return _clients['gemini']
    try:
        import google.generativeai as genai

        api_key = os.environ.get('GEMINI_API_KEY')
        if not api_key:
            try:
                from flask import current_app
                api_key = current_app.config.get('GEMINI_API_KEY')
            except Exception:
                pass
        if not api_key:
            return None
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(GEMINI_MODEL)
        _clients['gemini'] = model
        return model
    except ImportError:
        return None
    except Exception as e:
        logger.error(f'Failed to create Gemini model: {e}')
        return None


def get_ollama_client():
    if 'ollama' in _clients:
        return _clients['ollama']
    try:
        from ollama import Client

        host = os.environ.get('OLLAMA_HOST', 'http://127.0.0.1:11434')
        client = Client(host=host)
        client.list()
        _clients['ollama'] = client
        return client
    except ImportError:
        return None
    except Exception:
        return None


def reset_clients():
    """Reset cached clients and circuit breaker (useful after key rotation)."""
    _clients.clear()
    _provider_cooldowns.clear()


def _notify_provider_failure(errors):
    """Send Telegram notification when all LLM providers fail. Rate-limited."""
    now = datetime.now(UTC).timestamp()
    last = _provider_failure_last_sent.get('all_failed', 0)
    if now - last < _PROVIDER_FAILURE_COOLDOWN:
        return
    _provider_failure_last_sent['all_failed'] = now

    error_summary = '; '.join(errors[:5])
    logger.error(f'ALL LLM PROVIDERS FAILED: {error_summary}')

    try:
        from flask import current_app

        bot_token = current_app.config.get('TELEGRAM_BOT_TOKEN')
        if not bot_token:
            return

        from app.models.telegram_user import TelegramUser
        from app.services.telegram_bot_service import send_telegram_message

        tg_users = TelegramUser.query.filter_by(
            is_linked=True, is_active=True, notifications_enabled=True
        ).all()

        msg = (
            '🔴 *Alerta: Proveedores IA fuera de línea*\n\n'
            f'📅 {datetime.now(UTC).strftime("%d/%m/%Y %H:%M")} UTC\n'
            f'❌ {len(errors)} errores detectados\n\n'
            f'*Detalle:*\n```\n{error_summary[:500]}\n```\n\n'
            '_Revisa las API keys en Configuración del Sistema._'
        )

        for tu in tg_users:
            send_telegram_message(tu.telegram_chat_id, msg, bot_token)
    except Exception as e:
        logger.warning(f'Could not send provider failure notification: {e}')


def _notify_provider_error(provider_name, error_msg):
    """Notify about a single provider failure. Rate-limited per provider."""
    now = datetime.now(UTC).timestamp()
    last = _provider_failure_last_sent.get(provider_name, 0)
    if now - last < _PROVIDER_FAILURE_COOLDOWN:
        return
    _provider_failure_last_sent[provider_name] = now
    logger.warning(f'Provider {provider_name} failed: {error_msg}')

    try:
        from flask import current_app

        bot_token = current_app.config.get('TELEGRAM_BOT_TOKEN')
        if not bot_token:
            return

        from app.models.telegram_user import TelegramUser
        from app.services.telegram_bot_service import send_telegram_message

        tg_users = TelegramUser.query.filter_by(
            is_linked=True, is_active=True, notifications_enabled=True
        ).all()

        msg = (
            f'⚠️ *Proveedor {provider_name} caído*\n\n'
            f'📅 {datetime.now(UTC).strftime("%d/%m/%Y %H:%M")} UTC\n'
            f'❌ Error: {str(error_msg)[:300]}\n\n'
            '_Se intentarán otros proveedores automáticamente._'
        )

        for tu in tg_users:
            send_telegram_message(tu.telegram_chat_id, msg, bot_token)
    except Exception:
        pass


# ─── Unified chat completion ───────────────────────────────────────────────


def llm_chat(messages, model=None, temperature=0.3, max_tokens=4096):
    """
    Send chat completion through provider chain: Groq → GLM-5.2 → Gemini → Ollama
    (order configurable via LLM_PROVIDER). Providers with invalid keys are
    temporarily blocked to avoid wasting time on every call.
    Returns (content: str, provider: str) or raises RuntimeError.
    """
    errors = []
    logger.info(f'llm_chat called: {len(messages)} messages, providers in order: {_provider_order()}')

    for name in _provider_order():
        if _provider_blocked(name):
            errors.append(f'{name}: blocked (cooldown)')
            continue
        try:
            if name == 'groq':
                content = _try_groq(messages, model, temperature, max_tokens)
            elif name == 'glm':
                content = _try_glm(messages, model, temperature, max_tokens)
            elif name == 'gemini':
                content = _try_gemini(messages, temperature, max_tokens)
            elif name == 'ollama':
                content = _try_ollama(messages, temperature)
            else:
                continue
            if content is not None and content.strip():
                logger.info(f'{name} success: {len(content)} chars')
                return content, name
            errors.append(f'{name}: empty response')
        except Exception as e:
            errors.append(f'{name}: {e}')
            logger.warning(f'{name} failed: {e}')
            _notify_provider_error(_provider_display(name), e)
            if _is_auth_error(e):
                _block_provider(name, e)

    _notify_provider_failure(errors)
    raise RuntimeError(f'All LLM providers failed: {"; ".join(errors)}')


def _try_glm(messages, model, temperature, max_tokens):
    glm = get_glm_client()
    if not glm:
        return None
    use_model = model or GLM_MODEL
    response = _chat_with_retry(
        lambda: glm.chat.completions.create(
            model=use_model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
    )
    return response.choices[0].message.content or None


def _try_groq(messages, model, temperature, max_tokens):
    groq = get_groq_client()
    if not groq:
        return None
    last_exc = None
    for gm in GROQ_MODELS:
        try:
            response = _chat_with_retry(
                lambda: groq.chat.completions.create(
                    model=gm,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
            )
            content = response.choices[0].message.content or ''
            if content.strip():
                return content
        except Exception as e:
            last_exc = e
            logger.warning(f'Groq {gm} failed: {e}')
    if last_exc is not None:
        raise last_exc
    return None


def _try_gemini(messages, temperature, max_tokens):
    gemini = get_gemini_model()
    if not gemini:
        return None
    flat = '\n'.join(f'[{m["role"]}] {m["content"]}' for m in messages)
    resp = gemini.generate_content(flat)
    return resp.text or None


def _try_ollama(messages, temperature):
    ollama = get_ollama_client()
    if not ollama:
        return None
    ollama_model = os.environ.get('OLLAMA_MODEL', OLLAMA_MODEL_DEFAULT)
    resp = ollama.chat(model=ollama_model, messages=messages, options={'temperature': temperature})
    return resp.get('message', {}).get('content', '') or None


def llm_chat_stream(messages, model=None, temperature=0.3, max_tokens=4096):
    """
    Stream chat completion. Yields text chunks.
    Tries Groq first, then GLM-5.2, then Gemini, then Ollama.
    """
    logger.info(f'llm_chat_stream called: {len(messages)} messages, order: {_provider_order()}')

    for name in _provider_order():
        if _provider_blocked(name):
            continue
        try:
            if name == 'groq':
                done = yield from _stream_groq(messages, model, temperature, max_tokens)
            elif name == 'glm':
                done = yield from _stream_glm(messages, model, temperature, max_tokens)
            elif name == 'gemini':
                done = yield from _stream_gemini(messages, temperature, max_tokens)
            elif name == 'ollama':
                done = yield from _stream_ollama(messages, temperature)
            else:
                continue
            if done:
                return
        except Exception as e:
            logger.warning(f'{name} stream failed: {e}')
            _notify_provider_error(f'{_provider_display(name)}-stream', e)
            if _is_auth_error(e):
                _block_provider(name, e)

    logger.error('All LLM providers failed in llm_chat_stream')
    _notify_provider_failure(['All providers exhausted in stream mode'])
    yield 'Error: todos los proveedores de IA fallaron. Verifica las API keys en Configuracion del Sistema.'


def _stream_glm(messages, model, temperature, max_tokens):
    glm = get_glm_client()
    if not glm:
        return False
    use_model = model or GLM_MODEL
    stream = _chat_with_retry(
        lambda: glm.chat.completions.create(
            model=use_model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True,
        )
    )
    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content
    return True


def _stream_groq(messages, model, temperature, max_tokens):
    groq = get_groq_client()
    if not groq:
        return False
    last_exc = None
    for gm in GROQ_MODELS:
        try:
            logger.info(f'Trying Groq stream with {gm}')
            stream = _chat_with_retry(
                lambda: groq.chat.completions.create(
                    model=gm,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    stream=True,
                )
            )
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
            logger.info(f'Groq stream {gm} succeeded')
            return True
        except Exception as e:
            last_exc = e
            logger.warning(f'Groq stream {gm} failed: {e}')
    if last_exc is not None:
        raise last_exc
    return False


def _stream_gemini(messages, temperature, max_tokens):
    gemini = get_gemini_model()
    if not gemini:
        return False
    response = gemini.generate_content(
        messages[-1]['content'] if messages else '',
        generation_config={'temperature': temperature, 'max_output_tokens': max_tokens},
        stream=True,
    )
    for chunk in response:
        if chunk.text:
            yield chunk.text
    return True


def _stream_ollama(messages, temperature):
    ollama = get_ollama_client()
    if not ollama:
        return False
    ollama_model = os.environ.get('OLLAMA_MODEL', OLLAMA_MODEL_DEFAULT)
    resp = ollama.chat(model=ollama_model, messages=messages, options={'temperature': temperature})
    content = resp.get('message', {}).get('content', '')
    if content:
        yield content
    return True


# ─── Legacy helpers (used by enhanced_llm_service_v5, _shared, etc.) ───────


def llm_fallback_chain(system_prompt, msg):
    """
    Legacy fallback chain function matching the old _llm_fallback_chain interface.
    Returns response text string.
    """
    messages = [
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': msg},
    ]
    try:
        content, _provider = llm_chat(messages, temperature=0.3, max_tokens=2000)
        return content
    except RuntimeError as e:
        logger.error(f'All providers failed in fallback chain: {e}')
        _notify_provider_failure(['Fallback chain: ' + str(e)[:200]])
        return 'Lo siento, no pude conectar con ningun proveedor de IA. Verifica las API keys o la conexion a Internet.'
