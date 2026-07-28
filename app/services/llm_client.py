import logging
import os

logger = logging.getLogger('app.llm')

# ─── Provider configuration ────────────────────────────────────────────────

GLM_BASE_URL = 'https://integrate.api.nvidia.com/v1'
GLM_MODEL = 'z-ai/glm-5.2'

GROQ_MODELS = ['llama-3.3-70b-versatile', 'llama-3.1-8b-instant']
GEMINI_MODEL = 'gemini-1.5-flash'
OLLAMA_MODEL_DEFAULT = 'llama3.1:8b'


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
            return None
        client = OpenAI(base_url=GLM_BASE_URL, api_key=api_key)
        _clients['glm'] = client
        return client
    except ImportError:
        logger.warning('openai library not installed — GLM-5.2 unavailable')
        return None
    except Exception as e:
        logger.error(f'Failed to create GLM client: {e}')
        return None


def get_groq_client():
    if 'groq' in _clients:
        return _clients['groq']
    try:
        from groq import Groq

        api_key = os.environ.get('GROQ_API_KEY')
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
    """Reset cached clients (useful after key rotation)."""
    _clients.clear()


# ─── Unified chat completion ───────────────────────────────────────────────


def llm_chat(messages, model=None, temperature=0.3, max_tokens=4096):
    """
    Send chat completion through provider chain: GLM-5.2 → Groq → Gemini → Ollama.
    Returns (content: str, provider: str) or raises RuntimeError.
    """
    errors = []

    # 1) GLM-5.2 (primary)
    glm = get_glm_client()
    if glm:
        try:
            use_model = model or GLM_MODEL
            response = glm.chat.completions.create(
                model=use_model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            content = response.choices[0].message.content or ''
            if content.strip():
                return content, 'glm'
        except Exception as e:
            errors.append(f'GLM: {e}')
            logger.warning(f'GLM-5.2 failed: {e}')

    # 2) Groq (secondary)
    groq = get_groq_client()
    if groq:
        for gm in GROQ_MODELS:
            try:
                response = groq.chat.completions.create(
                    model=gm,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                content = response.choices[0].message.content or ''
                if content.strip():
                    return content, 'groq'
            except Exception as e:
                errors.append(f'Groq({gm}): {e}')
                logger.warning(f'Groq {gm} failed: {e}')

    # 3) Gemini (tertiary)
    gemini = get_gemini_model()
    if gemini:
        try:
            flat = '\n'.join(f'[{m["role"]}] {m["content"]}' for m in messages)
            resp = gemini.generate_content(flat)
            if resp.text and resp.text.strip():
                return resp.text, 'gemini'
        except Exception as e:
            errors.append(f'Gemini: {e}')
            logger.warning(f'Gemini failed: {e}')

    # 4) Ollama (last resort)
    ollama = get_ollama_client()
    if ollama:
        try:
            ollama_model = os.environ.get('OLLAMA_MODEL', OLLAMA_MODEL_DEFAULT)
            resp = ollama.chat(model=ollama_model, messages=messages, options={'temperature': temperature})
            content = resp.get('message', {}).get('content', '')
            if content and content.strip():
                return content, 'ollama'
        except Exception as e:
            errors.append(f'Ollama: {e}')
            logger.error(f'Ollama failed: {e}')

    raise RuntimeError(f'All LLM providers failed: {"; ".join(errors)}')


def llm_chat_stream(messages, model=None, temperature=0.3, max_tokens=4096):
    """
    Stream chat completion. Yields text chunks.
    Tries GLM-5.2 first, then Groq, then Ollama.
    """
    # GLM-5.2 streaming
    glm = get_glm_client()
    if glm:
        try:
            use_model = model or GLM_MODEL
            stream = glm.chat.completions.create(
                model=use_model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True,
            )
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
            return
        except Exception as e:
            logger.warning(f'GLM-5.2 stream failed, falling back: {e}')

    # Groq streaming
    groq = get_groq_client()
    if groq:
        for gm in GROQ_MODELS:
            try:
                stream = groq.chat.completions.create(
                    model=gm,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    stream=True,
                )
                for chunk in stream:
                    if chunk.choices and chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
                return
            except Exception as e:
                logger.warning(f'Groq stream {gm} failed: {e}')

    # Gemini streaming
    gemini = get_gemini_model()
    if gemini:
        try:
            response = gemini.generate_content(
                messages[-1]['content'] if messages else '',
                generation_config={'temperature': temperature, 'max_output_tokens': max_tokens},
                stream=True,
            )
            for chunk in response:
                if chunk.text:
                    yield chunk.text
            return
        except Exception as e:
            logger.warning(f'Gemini stream failed: {e}')

    # Ollama streaming (non-stream fallback — just get full response)
    ollama = get_ollama_client()
    if ollama:
        try:
            ollama_model = os.environ.get('OLLAMA_MODEL', OLLAMA_MODEL_DEFAULT)
            resp = ollama.chat(model=ollama_model, messages=messages, options={'temperature': temperature})
            content = resp.get('message', {}).get('content', '')
            if content:
                yield content
            return
        except Exception as e:
            logger.error(f'Ollama stream failed: {e}')

    yield 'Error: ningun proveedor LLM disponible.'


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
        return 'Lo siento, no pude conectar con ningun proveedor de IA. Verifica las API keys o la conexion a Internet.'
