from app.extensions import db
from app.models.base import AuditMixin


class AIProvider(db.Model, AuditMixin):
    """Provider de IA configurable desde Centro de Operaciones.

    Cada fila representa un provider de la cadena de fallback. El orden lo
    define `priority` (menor = primero). `provider_type` decide qué cliente
    SDK usa llm_client:
      - ollama    -> cliente local de Ollama
      - groq      -> SDK oficial de Groq
      - glm       -> OpenAI-compatible apuntando a NVIDIA NIM (GLM)
      - openai    -> cualquier API OpenAI-compatible (OpenAI, DeepSeek, custom)
      - anthropic -> Claude (SDK oficial de Anthropic)
      - gemini    -> google-generativeai
    """

    __tablename__ = 'ai_provider'

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(64), unique=True, nullable=True)
    name = db.Column(db.String(120), nullable=False)
    provider_type = db.Column(db.String(32), nullable=False, default='openai')
    base_url = db.Column(db.String(255), nullable=True)
    api_key = db.Column(db.String(512), nullable=True)
    model = db.Column(db.String(120), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    priority = db.Column(db.Integer, default=100, nullable=False)
    extra = db.Column(db.JSON, nullable=True)
    is_seed = db.Column(db.Boolean, default=False, nullable=False)

    def to_dict(self, mask_keys=True):
        key = self.api_key or ''
        return {
            'id': self.id,
            'slug': self.slug or '',
            'name': self.name,
            'provider_type': self.provider_type,
            'base_url': self.base_url or '',
            'model': self.model or '',
            'api_key': self._mask(key) if mask_keys else '',
            'has_key': bool(key),
            'is_active': self.is_active,
            'priority': self.priority,
            'is_seed': self.is_seed,
        }

    def to_config_dict(self):
        """Dict sin máscaras, listo para que llm_client construya el cliente."""
        return {
            'id': self.id,
            'slug': self.slug or '',
            'name': self.name,
            'provider_type': self.provider_type,
            'base_url': self.base_url,
            'model': self.model,
            'api_key': self.api_key,
            'is_active': self.is_active,
            'priority': self.priority,
        }

    @staticmethod
    def _mask(k):
        if not k:
            return ''
        if len(k) <= 8:
            return '****'
        return k[:4] + '****' + k[-4:]

    def __repr__(self):
        return f'<AIProvider {self.slug}: {self.name} ({self.provider_type}) prio={self.priority}>'


class AISettings(db.Model, AuditMixin):
    """Config global de IA. El toggle de fallback vive en la única fila."""

    __tablename__ = 'ai_settings'

    id = db.Column(db.Integer, primary_key=True)
    # ON  = cadena completa en orden de priority.
    # OFF = solo el primer provider activo (sin fallback).
    fallback_enabled = db.Column(db.Boolean, default=True, nullable=False)

    @staticmethod
    def get_or_create():
        s = AISettings.query.order_by(AISettings.id.asc()).first()
        if s is None:
            s = AISettings()
            db.session.add(s)
            db.session.commit()
        return s

    def to_dict(self):
        return {'id': self.id, 'fallback_enabled': self.fallback_enabled}

    def __repr__(self):
        return f'<AISettings fallback_enabled={self.fallback_enabled}>'
