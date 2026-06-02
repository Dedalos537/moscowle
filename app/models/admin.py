from datetime import datetime
from app.extensions import db


class SmartAction(db.Model):
    __tablename__ = 'smart_action'
    id = db.Column(db.Integer, primary_key=True)
    module = db.Column(db.String(50), nullable=False, index=True)
    description = db.Column(db.String(255), nullable=False)

    suggested_payload = db.Column(db.Text, nullable=True)

    automation_level = db.Column(db.String(30), default='manual')

    status = db.Column(db.String(20), default='pending', index=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime, nullable=True)

    def get_payload(self):
        import json
        try:
            return json.loads(self.suggested_payload) if self.suggested_payload else {}
        except:
            return {}


class CSPReport(db.Model):
    __tablename__ = 'csp_report'
    id = db.Column(db.Integer, primary_key=True)
    received_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    document_uri = db.Column(db.String(1000), nullable=True)
    violated_directive = db.Column(db.String(255), nullable=True)
    blocked_uri = db.Column(db.String(1000), nullable=True)
    original_policy = db.Column(db.Text, nullable=True)
    raw_report = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(100), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    user = db.relationship('User', backref=db.backref('csp_reports', lazy=True, cascade='all, delete-orphan'))


class AdminAPIToken(db.Model):
    __tablename__ = 'admin_api_token'
    id = db.Column(db.Integer, primary_key=True)
    token_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    def deactivate(self):
        self.is_active = False
