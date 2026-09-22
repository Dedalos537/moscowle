from app.extensions import db
from app.models.base import AuditMixin


class Holiday(db.Model, AuditMixin):
    __table_args__ = (
        db.Index('idx_holiday_date', 'date'),
        db.Index('idx_holiday_date_region', 'date', 'region'),
    )

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    name = db.Column(db.String(150), nullable=False)
    holiday_type = db.Column(db.String(20), nullable=False, default='nacional')
    region = db.Column(db.String(50), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
