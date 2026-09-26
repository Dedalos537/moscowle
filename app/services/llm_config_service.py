"""Configuración de providers de IA persistida en BD.

Contiene los presets que ofrece el panel de Centro de Operaciones y el seed
inicial que se ejecuta al primer arranque (toma las API keys del .env para no
perder la configuración actual).
"""

import logging

from app.extensions import db
from app.models.ai_provider import AIProvider, AISettings

logger = logging.getLogger('app.llm.config')

# ─── Presets disponibles en el panel ────────────────────────────────────────

LLM_PRESETS = {
    'groq': {
        'name': 'Groq',
        'provider_type': 'groq',
        'base_url': '',
        'model': '',
        'key_prefix': 'gsk_',
    },
    'glm': {
        'name': 'GLM/NVIDIA',
        'provider_type': 'glm',
        'base_url': 'https://integrate.api.nvidia.com/v1',
        'model': 'z-ai/glm-5.2',
        'key_prefix': 'nvapi-',
    },
    'gemini': {
        'name': 'Gemini',
        'provider_type': 'gemini',
        'base_url': '',
        'model': 'gemini-2.0-flash',
        'key_prefix': 'AI',
    },
    'openai': {
        'name': 'OpenAI (ChatGPT)',
        'provider_type': 'openai',
        'base_url': 'https://api.openai.com/v1',
        'model': 'gpt-4o-mini',
        'key_prefix': 'sk-',
    },
    'claude': {
        'name': 'Claude (Anthropic)',
        'provider_type': 'anthropic',
        'base_url': '',
        'model': 'claude-3-5-haiku-latest',
        'key_prefix': 'sk-ant-',
    },
    'deepseek': {
        'name': 'DeepSeek',
        'provider_type': 'openai',
        'base_url': 'https://api.deepseek.com/v1',
        'model': 'deepseek-chat',
        'key_prefix': 'sk-',
    },
    'custom': {
        'name': 'OpenAI-compatible',
        'provider_type': 'openai',
        'base_url': '',
        'model': '',
        'key_prefix': '',
    },
}

# Provider de seed y la env var de la que lee su key (None = sin key/siempre activo).
SEED_SPECS = [
    {
        'slug': 'ollama',
        'name': 'Ollama (Local)',
        'provider_type': 'ollama',
        'base_url': None,
        'model': None,
        'key_env': None,
        'priority': 0,
    },
    {
        'slug': 'groq',
        'name': 'Groq',
        'provider_type': 'groq',
        'base_url': None,
        'model': None,
        'key_env': 'GROQ_API_KEY',
        'priority': 100,
    },
    {
        'slug': 'glm',
        'name': 'GLM-5.2 (NVIDIA)',
        'provider_type': 'glm',
        'base_url': 'https://integrate.api.nvidia.com/v1',
        'model': 'z-ai/glm-5.2',
        'key_env': 'GLM_API_KEY',
        'priority': 200,
    },
    {
        'slug': 'gemini',
        'name': 'Gemini',
        'provider_type': 'gemini',
        'base_url': None,
        'model': 'gemini-2.0-flash',
        'key_env': 'GEMINI_API_KEY',
        'priority': 300,
    },
]

SEED_ENV_KEYS = [s['key_env'] for s in SEED_SPECS if s['key_env']]


def _resolve_key(env_name, default=''):
    """Lee la key de la env var y, si no existe, del config de Flask."""
    import os

    try:
        from flask import current_app

        return os.environ.get(env_name) or current_app.config.get(env_name) or default
    except Exception:
        return os.environ.get(env_name) or default


def seed_providers_from_env():
    """Crea la tabla ai_provider + ai_settings y los providers por defecto.

    Idempotente: solo actúa cuando la tabla está vacía (o si algún provider de
    seed no existe aún y su key está presente en el entorno).
    """
    try:
        AISettings.get_or_create()
        existing_slugs = {p.slug for p in AIProvider.query.all()}

        seeded = False
        for spec in SEED_SPECS:
            if spec['slug'] in existing_slugs:
                continue
            key = _resolve_key(spec['key_env']) if spec['key_env'] else None
            provider = AIProvider(
                slug=spec['slug'],
                name=spec['name'],
                provider_type=spec['provider_type'],
                base_url=spec['base_url'],
                model=spec['model'],
                api_key=key,
                is_active=spec['provider_type'] == 'ollama' or bool(key),
                priority=spec['priority'],
                is_seed=True,
            )
            db.session.add(provider)
            seeded = True

        if seeded:
            db.session.commit()
            logger.info('LLM providers seedeados desde el entorno')
    except Exception as e:
        db.session.rollback()
        logger.warning(f'seed_providers_from_env skipped: {e}')


def sync_env_key_to_provider(slug, env_name, key):
    """Actualiza la API key de un provider (y su env) desde el POST legacy."""
    if not key:
        return
    try:
        provider = AIProvider.query.filter_by(slug=slug).first()
        if provider:
            provider.api_key = key
            provider.is_active = True
            db.session.commit()
            logger.info(f'API key actualizada para provider {slug}')
    except Exception as e:
        db.session.rollback()
        logger.warning(f'sync_env_key_to_provider({slug}) failed: {e}')


def get_provider_by_slug(slug):
    return AIProvider.query.filter_by(slug=slug).first()


def get_active_providers():
    return AIProvider.query.filter_by(is_active=True).order_by(AIProvider.priority.asc(), AIProvider.id.asc()).all()


def list_config():
    """Snapshot completo para el panel (keys enmascaradas)."""
    settings = AISettings.get_or_create()
    providers = AIProvider.query.order_by(AIProvider.priority.asc(), AIProvider.id.asc()).all()
    return {
        'providers': [p.to_dict(mask_keys=True) for p in providers],
        'settings': settings.to_dict(),
        'presets': LLM_PRESETS,
    }
