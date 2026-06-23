from app.extensions import db
from app.models.base import AuditMixin


class Game(db.Model, AuditMixin):
    __tablename__ = 'game'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    filename = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)
    thumbnail = db.Column(db.String(200), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
