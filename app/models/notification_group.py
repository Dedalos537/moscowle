from datetime import datetime

from app.extensions import db


class NotificationGroup(db.Model):
    """A grouped notification that consolidates multiple similar notifications.

    Each group has a canonical key (e.g. 'msg:41' for messages from user 41),
    and collects NotificationItem children within a TTL window.
    """

    __tablename__ = 'notif_group'

    id = db.Column(db.Integer, primary_key=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    group_key = db.Column(db.String(100), nullable=False, index=True)
    category = db.Column(db.String(50), nullable=False, default='system')
    priority = db.Column(db.String(20), nullable=False, default='normal')
    title = db.Column(db.String(200), nullable=True)
    summary = db.Column(db.Text, nullable=True)
    count = db.Column(db.Integer, default=0, nullable=False)
    last_item_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    is_collapsed = db.Column(db.Boolean, default=True, nullable=False)
    ai_summary_generated = db.Column(db.Boolean, default=False, nullable=False)
    digest_sent = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = db.relationship(
        'User',
        foreign_keys=[user_id],
        backref=db.backref('notification_groups', cascade='all, delete-orphan'),
    )

    items = db.relationship(
        'NotificationItem',
        backref='group',
        lazy='dynamic',
        cascade='all, delete-orphan',
        order_by='NotificationItem.timestamp.desc()',
    )

    __table_args__ = (db.UniqueConstraint('user_id', 'group_key', name='uq_notif_group_user_key'),)

    @property
    def latest_items(self):
        """Return up to 5 most recent items for preview."""
        return self.items.limit(5).all()

    def __repr__(self):
        return f'<NotificationGroup {self.group_key} count={self.count} user={self.user_id}>'


class NotificationItem(db.Model):
    """Individual notification item within a group.

    Replaces the old Notification table for write path.
    Kept for detail drill-down and audit trail.
    """

    __tablename__ = 'notif_item'

    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('notif_group.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    message = db.Column(db.String(255), nullable=False)
    type = db.Column(db.String(50), nullable=True, default='info')
    priority = db.Column(db.String(20), nullable=True, default='normal')
    icon = db.Column(db.String(50), nullable=True)
    link = db.Column(db.String(255), nullable=True)
    metadata_json = db.Column(db.JSON, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship(
        'User',
        foreign_keys=[user_id],
        backref=db.backref('notification_items', cascade='all, delete-orphan'),
    )

    def __repr__(self):
        return f'<NotificationItem group={self.group_id} type={self.type}>'
