"""Notification Intelligence Service — groups, deduplicates, and summarizes
notifications using rule-based aggregation and optional LLM summarization.

This is the core engine that reduces ~8600 notifications/day to ~50-150.
"""

import json
import logging
from datetime import datetime, timedelta

from app.extensions import db
from app.models.notification_group import NotificationGroup, NotificationItem

logger = logging.getLogger(__name__)

# ─── Group TTL windows per category (seconds) ──────────────────────────────

GROUP_TTL = {
    'message': 600,  # 10 minutes
    'session': 1800,  # 30 minutes
    'game': 1800,  # 30 minutes
    'payment': 86400,  # 24 hours
    'alert': 3600,  # 1 hour
    'incident': 3600,  # 1 hour
    'security': 3600,  # 1 hour
    'report': 86400,  # 24 hours
    'audit': 3600,  # 1 hour
    'contact': 3600,  # 1 hour
    'user_mgmt': 3600,  # 1 hour
    'system': 1800,  # 30 minutes
    'debt': 86400,  # 24 hours
    'activity': 1800,  # 30 minutes
}

# ─── AI summarization thresholds ───────────────────────────────────────────

AI_SUMMARY_THRESHOLD = 5  # Minimum items to trigger LLM summarization

# ─── Group key builders by event type ──────────────────────────────────────


def compute_group_key(event_type, **kwargs):
    """Compute a canonical group key for a notification event.

    Args:
        event_type: 'message', 'session', 'game', 'payment', 'alert', etc.
        **kwargs: context data to build the key

    Returns:
        (group_key: str, category: str, default_priority: str)
    """
    builders = {
        'message': lambda k: (f'msg:{k.get("sender_id", "unknown")}', 'activity', 'normal'),
        'session_created': lambda k: (f'sess:{k.get("patient_id", "unknown")}', 'activity', 'normal'),
        'session_updated': lambda k: (f'sess:{k.get("patient_id", "unknown")}', 'activity', 'normal'),
        'session_completed': lambda k: (f'sess:{k.get("patient_id", "unknown")}:done', 'activity', 'normal'),
        'session_deleted': lambda k: (f'sess:{k.get("patient_id", "unknown")}:del', 'activity', 'normal'),
        'game_completed': lambda k: (f'game:{k.get("player_id", "unknown")}', 'activity', 'normal'),
        'payment_due': lambda k: (f'pay:{k.get("patient_id", "unknown")}', 'payment', 'normal'),
        'payment_overdue': lambda k: (f'pay:{k.get("patient_id", "unknown")}', 'payment', 'high'),
        'incident': lambda k: (f'inc:{k.get("incident_id", "unknown")}', 'alert', 'high'),
        'incident_escalation': lambda k: (f'inc:{k.get("incident_id", "unknown")}:esc', 'alert', 'urgent'),
        'sla_breach': lambda k: (f'inc:{k.get("incident_id", "unknown")}:sla', 'alert', 'urgent'),
        'security': lambda k: (f'sec:{k.get("subject", "general")}', 'security', 'normal'),
        'report': lambda k: (f'rep:{k.get("kind", "general")}', 'report', 'normal'),
        'audit': lambda k: (f'aud:{k.get("session_id", "unknown")}', 'audit', 'normal'),
        'contact': lambda k: (f'contact:{k.get("subject", "general")}', 'alert', 'normal'),
        'user_assigned': lambda k: (f'user:{k.get("target_id", "unknown")}', 'system', 'normal'),
        'user_toggle': lambda k: (f'user:{k.get("target_id", "unknown")}', 'system', 'normal'),
        'user_deleted': lambda k: (f'user:{k.get("target_id", "unknown")}', 'system', 'normal'),
        'chatbot_action': lambda k: (f'chatbot:{k.get("action", "general")}', 'system', 'low'),
        'broadcast': lambda k: (f'broadcast:{k.get("sender_id", "admin")}', 'system', 'normal'),
        'whatsapp_reminder': lambda k: (f'wa:{k.get("patient_id", "unknown")}', 'payment', 'normal'),
    }

    builder = builders.get(event_type)
    if builder:
        return builder(kwargs)

    # Fallback: use event_type as category, generic key
    return (f'misc:{event_type}:{kwargs.get("id", "unk")}', 'system', 'normal')


# ─── Core Grouping Logic ───────────────────────────────────────────────────


def add_item_to_group(
    user_id,
    event_type,
    message,
    title=None,
    notif_type='info',
    link=None,
    priority='normal',
    icon=None,
    metadata_json=None,
    **event_kwargs,
):
    """Add a notification to the appropriate group. Creates group if needed.

    Returns (group: NotificationGroup, is_new_group: bool)
    """
    group_key, category, default_priority = compute_group_key(event_type, **event_kwargs)
    effective_priority = _max_priority(priority, default_priority)

    # Look for existing active group within TTL
    ttl_seconds = GROUP_TTL.get(category, 1800)
    cutoff = datetime.utcnow() - timedelta(seconds=ttl_seconds)

    group = (
        NotificationGroup.query.filter_by(user_id=user_id, group_key=group_key, is_active=True)
        .filter(NotificationGroup.last_item_at >= cutoff)
        .first()
    )

    is_new_group = group is None

    if is_new_group:
        try:
            group = NotificationGroup(
                user_id=user_id,
                group_key=group_key,
                category=category,
                priority=effective_priority,
                title=title,
                count=0,
                last_item_at=datetime.utcnow(),
                is_read=False,
                is_collapsed=True,
            )
            db.session.add(group)
            db.session.flush()
        except Exception:
            db.session.rollback()
            # Find ANY existing group with this key (not just recent ones)
            group = NotificationGroup.query.filter_by(user_id=user_id, group_key=group_key, is_active=True).first()
            if not group:
                # Last resort: create with merge to handle race conditions
                group = NotificationGroup(
                    user_id=user_id,
                    group_key=group_key,
                    category=category,
                    priority=effective_priority,
                    title=title,
                    count=0,
                    last_item_at=datetime.utcnow(),
                    is_read=False,
                    is_collapsed=True,
                )
                db.session.merge(group)
                db.session.flush()
            is_new_group = False

    # Create the item
    item = NotificationItem(
        group_id=group.id,
        user_id=user_id,
        message=message,
        type=notif_type,
        priority=effective_priority,
        icon=json.dumps(icon) if isinstance(icon, list) else icon,
        link=link,
        metadata_json=metadata_json,
        timestamp=datetime.utcnow(),
    )
    db.session.add(item)

    # Update group counters
    group.count += 1
    group.last_item_at = datetime.utcnow()
    group.priority = _max_priority(group.priority, effective_priority)
    if title and not group.title:
        group.title = title

    db.session.commit()

    # Generate AI summary if threshold reached
    if group.count >= AI_SUMMARY_THRESHOLD and not group.ai_summary_generated:
        _try_generate_ai_summary(group)

    return group, is_new_group


def get_user_groups(user_id, category=None, include_read=False, limit=50):
    """Get notification groups for a user, optionally filtered by category."""
    query = NotificationGroup.query.filter_by(user_id=user_id, is_active=True)
    if not include_read:
        query = query.filter_by(is_read=False)
    if category:
        query = query.filter_by(category=category)
    return query.order_by(NotificationGroup.last_item_at.desc()).limit(limit).all()


def get_group_items(group_id, user_id, limit=20):
    """Get items within a group."""
    return (
        NotificationItem.query.filter_by(group_id=group_id, user_id=user_id)
        .order_by(NotificationItem.timestamp.desc())
        .limit(limit)
        .all()
    )


def get_user_group_count(user_id):
    """Get count of unread groups for badge."""
    return NotificationGroup.query.filter_by(user_id=user_id, is_read=False, is_active=True).count()


def mark_group_read(group_id, user_id):
    """Mark a group (and all its items) as read."""
    group = NotificationGroup.query.filter_by(id=group_id, user_id=user_id).first()
    if group:
        group.is_read = True
        NotificationItem.query.filter_by(group_id=group_id).update({'is_read': True})
        db.session.commit()


def mark_all_groups_read(user_id):
    """Mark all groups for a user as read."""
    NotificationGroup.query.filter_by(user_id=user_id, is_active=True).update({'is_read': True})
    NotificationItem.query.filter_by(user_id=user_id).update({'is_read': True})
    db.session.commit()


def toggle_group_collapse(group_id, user_id):
    """Toggle collapsed state of a group."""
    group = NotificationGroup.query.filter_by(id=group_id, user_id=user_id).first()
    if group:
        group.is_collapsed = not group.is_collapsed
        db.session.commit()
    return group


def delete_group(group_id, user_id):
    """Delete a notification group and its items."""
    group = NotificationGroup.query.filter_by(id=group_id, user_id=user_id).first()
    if group:
        db.session.delete(group)
        db.session.commit()
        return True
    return False


def get_groups_for_digest(user_id, since=None):
    """Get groups for the daily digest report."""
    query = NotificationGroup.query.filter_by(user_id=user_id, is_active=True)
    if since:
        query = query.filter(NotificationGroup.created_at >= since)
    return query.order_by(NotificationGroup.priority.desc(), NotificationGroup.last_item_at.desc()).all()


# ─── Priority Helpers ──────────────────────────────────────────────────────

PRIORITY_RANK = {'low': 0, 'normal': 1, 'high': 2, 'urgent': 3}
PRIORITY_NAMES = {0: 'low', 1: 'normal', 2: 'high', 3: 'urgent'}


def _max_priority(a, b):
    """Return the higher of two priority levels."""
    ra = PRIORITY_RANK.get(a, 1)
    rb = PRIORITY_RANK.get(b, 1)
    return PRIORITY_NAMES.get(max(ra, rb), 'normal')


# ─── AI Summarization ─────────────────────────────────────────────────────


def _try_generate_ai_summary(group):
    """Try to generate an AI summary for a group using LLM. Non-blocking."""
    try:
        from app.services.llm_client import llm_chat

        items = group.items.limit(10).all()
        item_descriptions = []
        for item in items:
            item_descriptions.append(f'- [{item.priority}] {item.message[:120]}')

        items_text = '\n'.join(item_descriptions)

        # Determine user role for context
        from app.models import User

        user = User.query.get(group.user_id)
        user_role = user.role if user else 'admin'

        prompt = f"""Eres el asistente de notificaciones del Centro Juan Pablo II.
Genera UN título corto (máximo 60 caracteres) y UN resumen de 1-2 frases en español
para este grupo de {group.count} notificaciones al usuario con rol '{user_role}'.

Categoría: {group.category}
Prioridad actual: {group.priority}
Últimas notificaciones en el grupo:
{items_text}

Responde SOLO con JSON válido:
{{"title": "título aquí", "summary": "resumen aquí", "priority": "normal|high|urgent"}}"""

        messages = [{'role': 'user', 'content': prompt}]
        content, provider = llm_chat(messages, temperature=0.2, max_tokens=200)

        result = json.loads(content.strip().strip('`').strip('json').strip())
        group.title = result.get('title', group.title)
        group.summary = result.get('summary')
        group.priority = _max_priority(group.priority, result.get('priority', 'normal'))
        group.ai_summary_generated = True
        db.session.commit()
        logger.info(f'AI summary generated for group {group.id} via {provider}')

    except Exception as e:
        logger.warning(f'AI summary failed for group {group.id}: {e}')
        # Set a fallback summary without AI
        group.summary = f'{group.count} notificaciones de tipo {group.category}'
        group.ai_summary_generated = True
        db.session.commit()


def generate_ai_digest_summary(groups, user_role):
    """Generate an AI-powered digest summary for a list of groups.

    Returns: {'title': str, 'body': str, 'highlights': list[str]}
    """
    try:
        from app.services.llm_client import llm_chat

        if not groups:
            return None

        # Build group summaries
        lines = []
        for g in groups[:20]:  # Cap at 20 groups
            priority_emoji = {'urgent': '🔴', 'high': '🟠', 'normal': '🟢', 'low': '⚪'}.get(g.priority, '⚪')
            lines.append(f'- {priority_emoji} [{g.category}] {g.title or g.group_key} (x{g.count})')

        groups_text = '\n'.join(lines)

        prompt = f"""Eres el asistente de notificaciones del Centro Juan Pablo II.
Genera un resumen ejecutivo diario en español para un usuario con rol '{user_role}'.

Notificaciones de ayer ({len(groups)} grupos):
{groups_text}

Genera un resumen CONCISO en máximo 8 líneas que incluya:
1. Total de notificaciones por prioridad
2. Las 3-5 más importantes destacadas con acción sugerida
3. Tono ejecutivo y claro, usa emoji para prioridades

Responde SOLO con JSON:
{{"title": "📊 Resumen Diario — Centro Juan Pablo II", "body": "resumen aquí", "highlights": ["punto 1", "punto 2", "punto 3"]}}"""

        messages = [{'role': 'user', 'content': prompt}]
        content, provider = llm_chat(messages, temperature=0.3, max_tokens=400)

        result = json.loads(content.strip().strip('`').strip('json').strip())
        logger.info(f'Digest AI summary via {provider}')
        return result

    except Exception as e:
        logger.warning(f'AI digest summary failed: {e}')
        # Fallback: simple text summary
        total = sum(g.count for g in groups)
        by_priority = {}
        for g in groups:
            by_priority[g.priority] = by_priority.get(g.priority, 0) + g.count
        parts = [f'{count} {pri}' for pri, count in sorted(by_priority.items(), key=lambda x: -x[1])]
        return {
            'title': '📊 Resumen Diario',
            'body': f'Tuviste {total} notificaciones: {", ".join(parts)}.',
            'highlights': [f'{len(groups)} grupos de notificaciones acumuladas'],
        }


# ─── Backward Compatibility: Legacy Notification Support ──────────────────


def get_unread_notifications_legacy(user_id):
    """Get unread notifications in legacy format for backward compatibility.

    Returns items from new groups in the old format.
    """
    groups = (
        NotificationGroup.query.filter_by(user_id=user_id, is_read=False, is_active=True)
        .order_by(NotificationGroup.last_item_at.desc())
        .all()
    )
    result = []
    for g in groups:
        result.append(
            {
                'id': g.id,
                'title': g.title or _default_title(g.category),
                'type': 'info',
                'category': g.category,
                'priority': g.priority,
                'icon': None,
                'message': g.summary or f'{g.count} notificaciones de {g.category}',
                'timestamp': g.last_item_at.strftime('%d %b, %H:%M'),
                'link': None,
                'count': g.count,
            }
        )
    return result


def _default_title(category):
    """Default title by category."""
    titles = {
        'message': 'Mensajes',
        'session': 'Sesiones',
        'game': 'Actividad',
        'payment': 'Pagos',
        'alert': 'Alertas',
        'incident': 'Incidentes',
        'security': 'Seguridad',
        'report': 'Reportes',
        'audit': 'Auditorías',
        'contact': 'Contacto',
        'user_mgmt': 'Usuarios',
        'system': 'Sistema',
        'debt': 'Deudas',
        'activity': 'Actividad',
    }
    return titles.get(category, 'Notificaciones')
