"""Notification Repository — Data access layer for grouped notifications.

Provides CRUD operations for NotificationGroup and NotificationItem.
"""

from datetime import datetime, timedelta

from app.models import db
from app.models.notification_group import NotificationGroup, NotificationItem, UserNotificationPreference


class NotificationRepository:
    # ─── Group CRUD ──────────────────────────────────────────────────────────

    @staticmethod
    def create_group(user_id, group_key, category, priority='normal', title=None):
        """Create a new notification group."""
        group = NotificationGroup(
            user_id=user_id,
            group_key=group_key,
            category=category,
            priority=priority,
            title=title,
            count=0,
            last_item_at=datetime.utcnow(),
            is_read=False,
            is_collapsed=True,
        )
        db.session.add(group)
        db.session.flush()
        return group

    @staticmethod
    def find_active_group(user_id, group_key, ttl_seconds=1800):
        """Find an existing active group within TTL window."""
        cutoff = datetime.utcnow() - timedelta(seconds=ttl_seconds)
        return (
            NotificationGroup.query.filter_by(user_id=user_id, group_key=group_key, is_active=True)
            .filter(NotificationGroup.last_item_at >= cutoff)
            .first()
        )

    @staticmethod
    def add_item_to_group(
        group_id, user_id, message, notif_type='info', priority='normal', icon=None, link=None, metadata_json=None
    ):
        """Add an item to a group and update group counters."""
        item = NotificationItem(
            group_id=group_id,
            user_id=user_id,
            message=message,
            type=notif_type,
            priority=priority,
            icon=icon,
            link=link,
            metadata_json=metadata_json,
            timestamp=datetime.utcnow(),
        )
        db.session.add(item)

        group = NotificationGroup.query.get(group_id)
        if group:
            group.count += 1
            group.last_item_at = datetime.utcnow()
            if priority and _priority_rank(priority) > _priority_rank(group.priority):
                group.priority = priority

        db.session.commit()
        return item

    # ─── Group Reads ─────────────────────────────────────────────────────────

    @staticmethod
    def get_unread_groups(user_id):
        """Get all unread groups for a user."""
        return (
            NotificationGroup.query.filter_by(user_id=user_id, is_active=True, is_read=False)
            .order_by(NotificationGroup.last_item_at.desc())
            .all()
        )

    @staticmethod
    def get_groups(user_id, category=None, include_read=True, limit=50):
        """Get groups with optional category filter."""
        query = NotificationGroup.query.filter_by(user_id=user_id, is_active=True)
        if not include_read:
            query = query.filter_by(is_read=False)
        if category:
            query = query.filter_by(category=category)
        return query.order_by(NotificationGroup.last_item_at.desc()).limit(limit).all()

    @staticmethod
    def get_count_by_user(user_id):
        """Get unread group count."""
        return NotificationGroup.query.filter_by(user_id=user_id, is_read=False, is_active=True).count()

    @staticmethod
    def get_by_category(user_id, category, limit=20):
        """Get groups by category."""
        return (
            NotificationGroup.query.filter_by(user_id=user_id, category=category, is_active=True)
            .order_by(NotificationGroup.last_item_at.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_group_items(group_id, user_id, limit=20):
        """Get items within a group."""
        return (
            NotificationItem.query.filter_by(group_id=group_id, user_id=user_id)
            .order_by(NotificationItem.timestamp.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_groups_for_digest(user_id, since=None):
        """Get groups for digest report."""
        query = NotificationGroup.query.filter_by(user_id=user_id, is_active=True)
        if since:
            query = query.filter(NotificationGroup.created_at >= since)
        return query.order_by(NotificationGroup.last_item_at.desc()).all()

    # ─── Group Updates ───────────────────────────────────────────────────────

    @staticmethod
    def mark_all_read(user_id):
        """Mark all groups and items as read."""
        NotificationGroup.query.filter_by(user_id=user_id, is_active=True).update({'is_read': True})
        NotificationItem.query.filter_by(user_id=user_id).update({'is_read': True})
        db.session.commit()

    @staticmethod
    def mark_one_read(user_id, group_id):
        """Mark a single group as read."""
        NotificationGroup.query.filter_by(id=group_id, user_id=user_id).update({'is_read': True})
        NotificationItem.query.filter_by(group_id=group_id).update({'is_read': True})
        db.session.commit()

    @staticmethod
    def toggle_collapse(group_id, user_id):
        """Toggle collapsed state."""
        group = NotificationGroup.query.filter_by(id=group_id, user_id=user_id).first()
        if group:
            group.is_collapsed = not group.is_collapsed
            db.session.commit()
        return group

    @staticmethod
    def delete_old_read(days=30):
        """Delete read groups and their items older than N days."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        old_groups = (
            NotificationGroup.query.filter_by(is_read=True, is_active=True)
            .filter(NotificationGroup.created_at < cutoff)
            .all()
        )
        for g in old_groups:
            db.session.delete(g)
        db.session.commit()

    # ─── Preferences ─────────────────────────────────────────────────────────

    @staticmethod
    def get_preferences(user_id):
        """Get or create default preferences."""

        prefs = UserNotificationPreference.query.filter_by(user_id=user_id).first()
        if not prefs:
            prefs = UserNotificationPreference(user_id=user_id)
            db.session.add(prefs)
            db.session.commit()
        return prefs

    @staticmethod
    def update_preferences(user_id, data):
        """Update preferences fields."""
        prefs = NotificationRepository.get_preferences(user_id)
        for field in [
            'debt_enabled',
            'activity_enabled',
            'system_enabled',
            'alert_enabled',
            'payment_enabled',
            'sound_enabled',
            'browser_notifications',
            'digest_enabled',
            'digest_channel',
        ]:
            if field in data:
                setattr(prefs, field, data[field])
        db.session.commit()
        return prefs


def _priority_rank(p):
    return {'low': 0, 'normal': 1, 'high': 2, 'urgent': 3}.get(p, 1)
