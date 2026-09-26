import json
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

# Local Ollama chain (clase "Claude + MCP"): un modelo RÁPIDO decide la tool
# (ruteo), otro produce la respuesta final, y gemma queda como último recurso.
OLLAMA_MODEL_DEFAULT = os.environ.get('OLLAMA_MODEL', 'gemma2')
OLLAMA_MODEL_ROUTER = os.environ.get('OLLAMA_MODEL_ROUTER', 'qwen2.5:1.5b')
OLLAMA_MODEL_TACTICAL = os.environ.get('OLLAMA_MODEL_TACTICAL', 'openbmb/minicpm5:q4_K_M')
OLLAMA_MODEL_FALLBACK = os.environ.get('OLLAMA_MODEL_FALLBACK', 'gemma3:4b')
OLLAMA_KEEP_ALIVE = os.environ.get('OLLAMA_KEEP_ALIVE', '6m')

# Contexto por fase: ruteo corto (solo necesita decidir), resume más holgado.
OLLAMA_CTX_ROUTE = int(os.environ.get('OLLAMA_CTX_ROUTE', '8192'))
OLLAMA_CTX_TACTICAL = int(os.environ.get('OLLAMA_CTX_TACTICAL', '4096'))

# Fase táctica: MiniCPM responde solo charla corta, sin tools ni tecnicismos.
_TACTICAL_SYSTEM = (
    'Eres Diego, asistente amable del Centro Juan Pablo II (Perú). '
    'Respondes SIEMPRE en español, breve y cálido: 1-3 líneas. '
    'No mencionas herramientas, sistemas ni datos de pacientes. '
    'Solo conversación casual.'
)

_RATE_LIMIT_RETRIES = 2
_RATE_LIMIT_BACKOFF = 2.0

# Provider order. Ollama first (Gemma 4) unless overridden via LLM_PROVIDER.
_DEFAULT_PROVIDER_ORDER = ['ollama', 'groq', 'glm', 'gemini']


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
    """Return the provider slugs in chain order (respects fallback toggle)."""
    return [p['slug'] for p in _configured_providers()]


_PROVIDER_DISPLAY = {'groq': 'Groq', 'glm': 'GLM-5.2', 'gemini': 'Gemini', 'ollama': 'Ollama'}


def _provider_display(name):
    return _PROVIDER_DISPLAY.get(name, name)


# ─── Provider config (persistida en BD: app.models.ai_provider) ────────────

# Cache de providers activos + toggle fallback. Se invalida con reset_clients()
# o invalidate_provider_config() tras cada cambio desde el panel.
_db_config_cache = {'providers': None, 'fallback': True}


def invalidate_provider_config():
    """Fuerza relectura de providers/fallback desde la BD."""
    _reset_provider_config_cache()


def _reset_provider_config_cache():
    _db_config_cache['providers'] = None
    _db_config_cache['fallback'] = True


def _load_db_providers():
    """Return (providers, fallback_enabled) desde la BD, o None si está vacía/rota."""
    if _db_config_cache['providers'] is not None:
        return _db_config_cache['providers'], _db_config_cache['fallback']
    try:
        from app.models.ai_provider import AIProvider, AISettings

        settings = AISettings.get_or_create()
        rows = AIProvider.query.filter_by(is_active=True).order_by(AIProvider.priority.asc(), AIProvider.id.asc()).all()
        if not rows:
            return None
        _db_config_cache['providers'] = [r.to_config_dict() for r in rows]
        _db_config_cache['fallback'] = settings.fallback_enabled
        return _db_config_cache['providers'], _db_config_cache['fallback']
    except Exception as e:
        logger.warning(f'DB provider config unavailable, using env chain: {e}')
        return None


def _configured_providers():
    """Cadena efectiva de providers (dicts). OFF de fallback => solo el primario."""
    db = _load_db_providers()
    if db is not None:
        providers, fallback = db
        if not fallback:
            providers = providers[:1]
        return providers
    return _env_providers()


def _env_providers():
    """Fallback legacy: providers construidos desde variables de entorno."""
    order = list(_DEFAULT_PROVIDER_ORDER)
    try:
        from flask import current_app

        pref = os.environ.get('LLM_PROVIDER') or current_app.config.get('LLM_PROVIDER')
    except Exception:
        pref = os.environ.get('LLM_PROVIDER')
    if pref and pref.lower() in order:
        order.remove(pref.lower())
        order.insert(0, pref.lower())

    def key(env_name, default=''):
        value = os.environ.get(env_name)
        if not value:
            try:
                from flask import current_app

                value = current_app.config.get(env_name)
            except Exception:
                pass
        return value or default

    specs = {
        'ollama': {
            'slug': 'ollama',
            'name': 'Ollama (Local)',
            'provider_type': 'ollama',
            'base_url': None,
            'model': None,
            'api_key': None,
            'is_active': True,
            'priority': 0,
        },
        'groq': {
            'slug': 'groq',
            'name': 'Groq',
            'provider_type': 'groq',
            'base_url': None,
            'model': None,
            'api_key': key('GROQ_API_KEY'),
            'is_active': True,
            'priority': 100,
        },
        'glm': {
            'slug': 'glm',
            'name': 'GLM-5.2 (NVIDIA)',
            'provider_type': 'glm',
            'base_url': GLM_BASE_URL,
            'model': GLM_MODEL,
            'api_key': key('GLM_API_KEY'),
            'is_active': True,
            'priority': 200,
        },
        'gemini': {
            'slug': 'gemini',
            'name': 'Gemini',
            'provider_type': 'gemini',
            'base_url': None,
            'model': GEMINI_MODEL,
            'api_key': key('GEMINI_API_KEY'),
            'is_active': True,
            'priority': 300,
        },
    }
    return [specs[o] for o in order if o in specs]


def _cached_client(key, builder):
    """Cliente por provider con caché módulo-local."""
    if key in _clients:
        return _clients[key]
    try:
        client = builder()
    except Exception as e:
        logger.error(f'Failed to build client {key}: {e}')
        return None
    if client is not None:
        _clients[key] = client
    return client


def _to_anthropic_messages(messages):
    """Convierte [{role, content}] al formato de Anthropic (system aparte)."""
    system = '\n'.join(m['content'] for m in messages if m.get('role') == 'system')
    body = []
    for m in messages:
        if m.get('role') == 'system':
            continue
        role = 'assistant' if m.get('role') == 'assistant' else 'user'
        body.append({'role': role, 'content': m.get('content') or ''})
    merged = []
    for m in body:
        if merged and merged[-1]['role'] == m['role']:
            merged[-1]['content'] += '\n\n' + m['content']
        else:
            merged.append(dict(m))
    if merged and merged[0]['role'] == 'assistant':
        merged.insert(0, {'role': 'user', 'content': 'Continúa.'})
    return (system or None), merged


def _anthropic_text(response):
    parts = []
    for block in getattr(response, 'content', None) or []:
        if getattr(block, 'type', '') == 'text':
            parts.append(getattr(block, 'text', '') or '')
    return '\n'.join(parts)


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


def get_glm_client_for(cfg):
    """Cliente NVIDIA NIM (OpenAI-compatible) construido desde un provider cfg."""
    return _cached_client(
        f'glm:{cfg["slug"]}',
        lambda: _build_openai_provider(cfg, fallback_base=GLM_BASE_URL, fallback_model=GLM_MODEL),
    )


def get_groq_client_for(cfg):
    """Cliente Groq construido desde un provider cfg."""
    return _cached_client(
        f'groq:{cfg["slug"]}',
        lambda: _build_groq_provider(cfg),
    )


def get_gemini_model_for(cfg):
    """Modelo Gemini construido desde un provider cfg."""
    return _cached_client(
        f'gemini:{cfg["slug"]}',
        lambda: _build_gemini_provider(cfg),
    )


def get_openai_provider_client(cfg):
    """Cliente OpenAI-compatible genérico (OpenAI, DeepSeek, custom base_url)."""
    return _cached_client(
        f'openai:{cfg["slug"]}',
        lambda: _build_openai_provider(cfg, fallback_base=None, fallback_model=None),
    )


def get_anthropic_provider_client(cfg):
    """Cliente Claude (SDK anthropic). None si la librería no está instalada."""

    def _build():
        try:
            from anthropic import Anthropic
        except ImportError:
            logger.error('anthropic library not installed — pip install anthropic')
            return None
        api_key = cfg.get('api_key')
        if not api_key:
            return None
        return Anthropic(api_key=api_key)

    return _cached_client(f'anthropic:{cfg["slug"]}', _build)


def _build_openai_provider(cfg, fallback_base=None, fallback_model=None):
    try:
        from openai import OpenAI
    except ImportError:
        logger.error('openai library not installed — pip install openai')
        return None
    api_key = cfg.get('api_key')
    if not api_key:
        return None
    base_url = cfg.get('base_url') or fallback_base
    return OpenAI(base_url=base_url, api_key=api_key)


def _build_groq_provider(cfg):
    try:
        from groq import Groq
    except ImportError:
        return None
    api_key = cfg.get('api_key')
    if not api_key:
        return None
    return Groq(api_key=api_key)


def _build_gemini_provider(cfg):
    try:
        import google.generativeai as genai
    except ImportError:
        return None
    api_key = cfg.get('api_key')
    if not api_key:
        return None
    genai.configure(api_key=api_key)
    model_name = cfg.get('model') or GEMINI_MODEL
    return genai.GenerativeModel(model_name)


def reset_clients():
    """Reset cached clients, circuit breaker y config de providers de BD."""
    _clients.clear()
    _provider_cooldowns.clear()
    _reset_provider_config_cache()


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

        tg_users = TelegramUser.query.filter_by(is_linked=True, is_active=True, notifications_enabled=True).all()

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

        tg_users = TelegramUser.query.filter_by(is_linked=True, is_active=True, notifications_enabled=True).all()

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


def llm_chat(messages, model=None, temperature=0.3, max_tokens=4096, tools=None, phase='route'):
    """
    Send chat completion through provider chain: Groq → GLM-5.2 → Gemini → Ollama
    (order configurable via LLM_PROVIDER). Providers with invalid keys are
    temporarily blocked to avoid wasting time on every call.

    Extra params (Ollama only):
      - tools: lista de schemas nativos ({'type':'function','function': {...}}).
               Cuando la resp. trae tool_calls de Ollama, se serializan de vuelta
               al formato de texto <function=name{...}</function> que ya parsea
               mcp_service, para reutilizar todo el flujo de ejecución existente.
      - phase: 'route' (router Qwen, decide la tool), 'resume' (respuesta final),
               'tactical' (MiniCPM, charla corta sin tools).
    Returns (content: str, provider: str) or raises RuntimeError.
    """
    errors = []
    logger.info(f'llm_chat called: {len(messages)} messages, providers in order: {_provider_order()}')

    for cfg in _configured_providers():
        name = cfg['slug']
        if _provider_blocked(name):
            errors.append(f'{name}: blocked (cooldown)')
            continue
        try:
            content = _invoke_provider(cfg, messages, model, temperature, max_tokens, tools=tools, phase=phase)
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


def _invoke_provider(cfg, messages, model=None, temperature=0.3, max_tokens=4096, tools=None, phase='route'):
    """Despacha una llamada de chat al tipo de provider configurado."""
    p_type = cfg.get('provider_type')
    if p_type == 'ollama':
        return _try_ollama(messages, temperature, model=model, tools=tools, phase=phase, max_tokens=max_tokens)
    if p_type == 'groq':
        return _try_groq(cfg, messages, model, temperature, max_tokens)
    if p_type == 'glm':
        return _try_glm(cfg, messages, model, temperature, max_tokens)
    if p_type == 'gemini':
        return _try_gemini(cfg, messages, temperature, max_tokens)
    if p_type == 'openai':
        return _try_openai(cfg, messages, model, temperature, max_tokens)
    if p_type == 'anthropic':
        return _try_anthropic(cfg, messages, model, temperature, max_tokens)
    logger.warning(f'Unknown provider_type={p_type} for {cfg.get("slug")}')
    return None


def _try_openai(cfg, messages, model, temperature, max_tokens):
    client = get_openai_provider_client(cfg)
    if not client:
        return None
    use_model = model or cfg.get('model')
    if not use_model:
        return None
    response = _chat_with_retry(
        lambda: client.chat.completions.create(
            model=use_model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
    )
    return response.choices[0].message.content or None


def _try_anthropic(cfg, messages, model, temperature, max_tokens):
    client = get_anthropic_provider_client(cfg)
    if not client:
        return None
    use_model = model or cfg.get('model')
    if not use_model:
        return None
    system, body = _to_anthropic_messages(messages)
    response = _chat_with_retry(
        lambda: client.messages.create(
            model=use_model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=body,
        )
    )
    return _anthropic_text(response) or None


def _ollama_route_model(phase, tools):
    """Elige el modelo local según la fase."""
    if phase == 'tactical':
        return OLLAMA_MODEL_TACTICAL
    if phase == 'resume':
        return OLLAMA_MODEL_FALLBACK if os.environ.get('OLLAMA_RESUME_GEMMA') == '1' else OLLAMA_MODEL_ROUTER
    # 'route' con tools nativas -> Qwen (rápido y correcto); sin tools -> fallback
    if tools:
        return OLLAMA_MODEL_ROUTER
    return os.environ.get('OLLAMA_MODEL', OLLAMA_MODEL_DEFAULT)


def _try_glm(cfg, messages, model, temperature, max_tokens):
    glm = get_glm_client_for(cfg)
    if not glm:
        return None
    use_model = model or cfg.get('model') or GLM_MODEL
    response = _chat_with_retry(
        lambda: glm.chat.completions.create(
            model=use_model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
    )
    return response.choices[0].message.content or None


def _try_groq(cfg, messages, model, temperature, max_tokens):
    groq = get_groq_client_for(cfg)
    if not groq:
        return None
    last_exc = None
    groq_models = [cfg['model']] if cfg.get('model') else GROQ_MODELS
    for gm in groq_models:
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


def _try_gemini(cfg, messages, temperature, max_tokens):
    gemini = get_gemini_model_for(cfg) or get_gemini_model()
    if not gemini:
        return None
    flat = '\n'.join(f'[{m["role"]}] {m["content"]}' for m in messages)
    resp = gemini.generate_content(flat)
    return resp.text or None


def _try_ollama(messages, temperature, model=None, tools=None, phase='route', max_tokens=None):
    ollama = get_ollama_client()
    if not ollama:
        return None

    if model:
        ollama_model = model
    else:
        ollama_model = _ollama_route_model(phase, tools)

    tactical = phase == 'tactical'
    ctx = OLLAMA_CTX_TACTICAL if tactical else OLLAMA_CTX_ROUTE
    # El táctico (charla corta) no debe ver el system de tools del router: lo
    # reemplazamos por una persona simple para evitar que MiniCPM "hable" de tools.
    if tactical:
        messages = [
            {'role': 'system', 'content': _TACTICAL_SYSTEM},
            *[m for m in messages if m.get('role') != 'system'],
        ]
    options = {
        'temperature': temperature,
        'num_ctx': ctx,
        'num_thread': 4,  # Usar todos los cores del i5-4590T
        'num_gpu': 0,  # Forzar CPU (no hay GPU)
        'top_p': 0.8 if tactical else 0.9,
        'repeat_penalty': 1.1,
    }
    if max_tokens:
        options['num_predict'] = int(max_tokens)
    # MiniCPM aún en "thinking" a pesar de phase tactical: se apaga explícito.
    if ollama_model.startswith('openbmb/minicpm'):
        options['enable_thinking'] = False

    req = {'model': ollama_model, 'messages': messages, 'options': options}
    if tools:
        req['tools'] = tools
    req['keep_alive'] = OLLAMA_KEEP_ALIVE
    try:
        resp = ollama.chat(**req)
    except TypeError:
        # Versiones antiguas del cliente sin param tools -> sin tools
        if tools:
            req.pop('tools', None)
            resp = ollama.chat(**req)
        else:
            raise

    msg = resp.get('message', {}) or {}
    content = msg.get('content') or ''
    tool_calls = msg.get('tool_calls') or []

    if tool_calls:
        # Serializar el tool_call nativo de Ollama al formato de texto que ya
        # entiende mcp_service: <function=name{...}</function>
        serialized = []
        for tc in tool_calls:
            fn = tc.get('function', {})
            tname = fn.get('name', '')
            targs = fn.get('arguments') or {}
            if isinstance(targs, str):
                try:
                    targs = json.loads(targs)
                except (json.JSONDecodeError, TypeError):
                    targs = {}
            serialized.append(f'<function={tname}{json.dumps(targs, ensure_ascii=False)}</function>')
        combined = '\n'.join(serialized)
        if combined.strip():
            return combined

    return content or None


def llm_chat_stream(messages, model=None, temperature=0.3, max_tokens=4096, tools=None, phase='route'):
    """
    Stream chat completion. Yields text chunks.
    Tries Groq first, then GLM-5.2, then Gemini, then Ollama.
    """
    logger.info(f'llm_chat_stream called: {len(messages)} messages, order: {_provider_order()}')

    for cfg in _configured_providers():
        name = cfg['slug']
        if _provider_blocked(name):
            continue
        try:
            done = yield from _stream_provider(cfg, messages, model, temperature, max_tokens, tools=tools, phase=phase)
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


def _stream_provider(cfg, messages, model=None, temperature=0.3, max_tokens=4096, tools=None, phase='route'):
    """Despacha un stream de chat al tipo de provider configurado."""
    p_type = cfg.get('provider_type')
    if p_type == 'ollama':
        yield from _stream_ollama(messages, temperature, model=model, tools=tools, phase=phase, max_tokens=max_tokens)
        return True
    if p_type == 'groq':
        yield from _stream_groq(cfg, messages, model, temperature, max_tokens)
        return True
    if p_type == 'glm':
        yield from _stream_glm(cfg, messages, model, temperature, max_tokens)
        return True
    if p_type == 'gemini':
        yield from _stream_gemini(cfg, messages, temperature, max_tokens)
        return True
    if p_type == 'openai':
        yield from _stream_openai(cfg, messages, model, temperature, max_tokens)
        return True
    if p_type == 'anthropic':
        yield from _stream_anthropic(cfg, messages, model, temperature, max_tokens)
        return True
    return False


def _stream_openai(cfg, messages, model, temperature, max_tokens):
    client = get_openai_provider_client(cfg)
    if not client:
        return False
    use_model = model or cfg.get('model')
    if not use_model:
        return False
    stream = _chat_with_retry(
        lambda: client.chat.completions.create(
            model=use_model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True,
        )
    )
    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content
    return True


def _stream_anthropic(cfg, messages, model, temperature, max_tokens):
    client = get_anthropic_provider_client(cfg)
    if not client:
        return False
    use_model = model or cfg.get('model')
    if not use_model:
        return False
    system, body = _to_anthropic_messages(messages)
    with client.messages.stream(
        model=use_model,
        max_tokens=max_tokens,
        temperature=temperature,
        system=system,
        messages=body,
    ) as stream:
        for text in stream.text_stream:
            if text:
                yield text
    return True


def _stream_glm(cfg, messages, model, temperature, max_tokens):
    glm = get_glm_client_for(cfg)
    if not glm:
        return False
    use_model = model or cfg.get('model') or GLM_MODEL
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


def _stream_groq(cfg, messages, model, temperature, max_tokens):
    groq = get_groq_client_for(cfg)
    if not groq:
        return False
    last_exc = None
    for gm in [cfg['model']] if cfg.get('model') else GROQ_MODELS:
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


def _stream_gemini(cfg, messages, temperature, max_tokens):
    gemini = get_gemini_model_for(cfg) or get_gemini_model()
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


def _stream_ollama(messages, temperature, model=None, tools=None, phase='route', max_tokens=None):
    ollama = get_ollama_client()
    if not ollama:
        return False
    ollama_model = model or _ollama_route_model(phase, tools)
    tactical = phase == 'tactical'
    ctx = OLLAMA_CTX_TACTICAL if tactical else OLLAMA_CTX_ROUTE
    if tactical:
        messages = [
            {'role': 'system', 'content': _TACTICAL_SYSTEM},
            *[m for m in messages if m.get('role') != 'system'],
        ]
    options = {
        'temperature': temperature,
        'num_ctx': ctx,
        'num_thread': 4,  # Usar todos los cores del i5-4590T
        'num_gpu': 0,  # Forzar CPU (no hay GPU)
        'top_p': 0.8 if tactical else 0.9,
        'repeat_penalty': 1.1,
    }
    if max_tokens:
        options['num_predict'] = int(max_tokens)
    if ollama_model.startswith('openbmb/minicpm'):
        options['enable_thinking'] = False
    stream = ollama.chat(
        model=ollama_model,
        messages=messages,
        options=options,
        tools=tools or None,
        stream=True,
        keep_alive=OLLAMA_KEEP_ALIVE,
    )
    for chunk in stream:
        msg = chunk.get('message', {}) or {}
        content_piece = msg.get('content') or ''
        if content_piece:
            yield content_piece
        for tc in msg.get('tool_calls') or []:
            fn = tc.get('function', {})
            tname = fn.get('name', '')
            targs = fn.get('arguments') or {}
            if isinstance(targs, str):
                try:
                    targs = json.loads(targs)
                except (json.JSONDecodeError, TypeError):
                    targs = {}
            yield f'<function={tname}{json.dumps(targs, ensure_ascii=False)}</function>'
        if chunk.get('done'):
            break
    return True


# ─── Legacy helpers (used by enhanced_llm_service_v5, _shared, etc.) ───────


def test_provider(cfg, max_tokens=24):
    """Prueba un provider individual con un mini chat. Devuelve dict de resultado."""
    start = time.monotonic()
    try:
        content = _invoke_provider(
            cfg,
            [{'role': 'user', 'content': 'Responde solo con: ok'}],
            None,
            0.2,
            max_tokens,
        )
        latency_ms = int((time.monotonic() - start) * 1000)
        if content and content.strip():
            return {'ok': True, 'latency_ms': latency_ms, 'response': content.strip()[:120]}
        return {'ok': False, 'latency_ms': latency_ms, 'error': 'Respuesta vacía'}
    except Exception as e:
        latency_ms = int((time.monotonic() - start) * 1000)
        return {'ok': False, 'latency_ms': latency_ms, 'error': str(e)[:200]}


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
