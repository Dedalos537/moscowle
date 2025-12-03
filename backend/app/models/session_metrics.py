from ..extensions import db
from datetime import datetime


class SessionMetrics(db.Model):
    """
    Model to track performance metrics for therapeutic game sessions.
    Records student performance data for Machine Learning analysis and level progression.
    """
    __tablename__ = 'session_metrics'

    # Primary Key
    id = db.Column(db.Integer, primary_key=True)

    # Foreign Keys
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False, index=True)

    # Game Information
    game_name = db.Column(db.String(255), nullable=False)

    # Performance Metrics
    accuracy_rate = db.Column(db.Float, nullable=False, default=0.0)  # Percentage (0-100)
    average_time = db.Column(db.Float, nullable=False, default=0.0)   # Seconds
    failed_attempts = db.Column(db.Integer, nullable=False, default=0)

    # Level Information
    previous_level = db.Column(db.Integer, nullable=False, default=1)  # Current level (1-3)
    predicted_next_level = db.Column(db.Integer, nullable=True)        # Next level (0, 1, 2, or NULL)

    # Machine Learning
    cluster_id = db.Column(db.Integer, nullable=True)  # K-Means cluster assignment

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    patient = db.relationship('Patient', backref=db.backref('session_metrics', lazy='dynamic', cascade='all, delete-orphan'))

    def to_dict(self):
        """Serialize to dictionary for API responses."""
        return {
            'id': self.id,
            'patient_id': self.patient_id,
            'game_name': self.game_name,
            'accuracy_rate': self.accuracy_rate,
            'average_time': self.average_time,
            'failed_attempts': self.failed_attempts,
            'previous_level': self.previous_level,
            'predicted_next_level': self.predicted_next_level,
            'cluster_id': self.cluster_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<SessionMetrics(id={self.id}, patient_id={self.patient_id}, game_name={self.game_name})>'
