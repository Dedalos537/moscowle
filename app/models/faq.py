from app.extensions import db
from app.models.base import AuditMixin


class Faq(db.Model, AuditMixin):
    __tablename__ = 'faqs'

    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(80), default='general', nullable=False, index=True)
    keywords = db.Column(db.Text, nullable=True)

    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)

    # Auto-growth tracking
    usage_count = db.Column(db.Integer, default=0, nullable=False)
    last_used_at = db.Column(db.DateTime, nullable=True)
    source = db.Column(db.String(20), default='manual', nullable=False)  # manual | auto_proposed | auto
    status = db.Column(db.String(20), default='active', nullable=False)  # active | proposed | rejected

    def to_dict(self):
        return {
            'id': self.id,
            'question': self.question,
            'answer': self.answer,
            'category': self.category,
            'keywords': self.keywords or '',
            'is_active': self.is_active,
            'usage_count': self.usage_count,
            'last_used_at': self.last_used_at.isoformat() if self.last_used_at else None,
            'source': self.source,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<Faq {self.id}: {self.question[:40]}>'
