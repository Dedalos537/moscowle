from app.extensions import db
from app.models.base import AuditMixin


class BotConfig(db.Model, AuditMixin):
    __tablename__ = 'bot_config'

    id = db.Column(db.Integer, primary_key=True)
    # The public identity of the bot (what the dashboard shows / can be edited)
    bot_name = db.Column(db.String(120), default='Diego', nullable=False)
    bot_emoji = db.Column(db.String(16), default='\U0001f99c', nullable=False)
    persona_message = db.Column(db.Text, nullable=True)
    system_prompt = db.Column(db.Text, nullable=True)

    # Chasqui extras: allow the FAQ to grow with usage and MCP prompt auto-fill
    auto_faq_enabled = db.Column(db.Boolean, default=True, nullable=False)
    auto_faq_threshold = db.Column(db.Integer, default=3, nullable=False)
    mcp_prompt_enabled = db.Column(db.Boolean, default=True, nullable=False)
    notify_supervision_enabled = db.Column(db.Boolean, default=True, nullable=False)
    intervention_enabled = db.Column(db.Boolean, default=True, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'bot_name': self.bot_name,
            'bot_emoji': self.bot_emoji,
            'persona_message': self.persona_message or '',
            'system_prompt': self.system_prompt or '',
            'auto_faq_enabled': self.auto_faq_enabled,
            'auto_faq_threshold': self.auto_faq_threshold,
            'mcp_prompt_enabled': self.mcp_prompt_enabled,
            'notify_supervision_enabled': self.notify_supervision_enabled,
            'intervention_enabled': self.intervention_enabled,
        }

    @staticmethod
    def get_or_create():
        cfg = BotConfig.query.order_by(BotConfig.id.asc()).first()
        if cfg is None:
            cfg = BotConfig()
            db.session.add(cfg)
            db.session.commit()
        return cfg

    def __repr__(self):
        return f'<BotConfig {self.id}: {self.bot_name}>'
