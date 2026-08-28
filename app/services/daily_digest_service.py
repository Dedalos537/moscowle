"""Daily Notification Digest Service.

Generates and sends a personalized daily summary at 6:00 AM to all active users
via Telegram and/or email, using AI to create role-specific summaries.
"""

import logging
from datetime import datetime, timedelta

from flask import current_app

from app.extensions import db
from app.models import User
from app.services.notification_intelligence import (
    generate_ai_digest_summary,
    get_groups_for_digest,
)

logger = logging.getLogger(__name__)


# ─── Digest Generation ────────────────────────────────────────────────────


def generate_daily_digests():
    """Main entry point: generate and send daily digests for all active users.

    Called by the APScheduler job at 6:00 AM daily.
    """
    logger.info('Starting daily notification digest generation...')
    yesterday = datetime.utcnow() - timedelta(hours=24)

    active_users = User.query.filter_by(is_active=True).all()
    sent_count = 0
    skipped_count = 0

    for user in active_users:
        try:
            _send_digest_for_user(user, yesterday)
            sent_count += 1
        except Exception as e:
            logger.error(f'Digest failed for user {user.id} ({user.username}): {e}')
            skipped_count += 1

    logger.info(f'Daily digest complete: {sent_count} sent, {skipped_count} failed out of {len(active_users)} users')
    return {'sent': sent_count, 'failed': skipped_count, 'total': len(active_users)}


def _send_digest_for_user(user, since):
    """Generate and send digest for a single user via their preferred channels."""
    from app.models.notification import UserNotificationPreference

    prefs = UserNotificationPreference.query.filter_by(user_id=user.id).first()
    if not prefs or not getattr(prefs, 'digest_enabled', True):
        return

    groups = get_groups_for_digest(user.id, since=since)
    if not groups:
        return  # Nothing to report

    # Generate AI summary
    ai_summary = generate_ai_digest_summary(groups, user.role)
    if not ai_summary:
        return

    # Build the digest message
    digest_text = _build_digest_text(user, ai_summary, groups)
    digest_html = _build_digest_html(user, ai_summary, groups)

    digest_channel = getattr(prefs, 'digest_channel', 'both')

    # Send via Telegram
    if digest_channel in ('telegram', 'both'):
        _send_telegram_digest(user, digest_text)

    # Send via email
    if digest_channel in ('email', 'both'):
        _send_email_digest(user, digest_html)

    # Mark groups as digest_sent
    for g in groups:
        g.digest_sent = True
    db.session.commit()


# ─── Telegram Digest ──────────────────────────────────────────────────────


def _send_telegram_digest(user, text):
    """Send digest via Telegram to all linked accounts of the user."""
    try:
        from app.services.telegram_bot_service import send_telegram_message

        bot_token = current_app.config.get('TELEGRAM_BOT_TOKEN')
        if not bot_token:
            return

        from app.models.telegram_user import TelegramUser

        tg_users = TelegramUser.query.filter_by(
            admin_user_id=user.id,
            is_linked=True,
            is_active=True,
        ).all()

        for tg in tg_users:
            send_telegram_message(
                tg.telegram_chat_id,
                text,
                bot_token,
            )
            logger.info(f'Digest sent via Telegram to user {user.id}, chat {tg.telegram_chat_id}')

    except Exception as e:
        logger.error(f'Telegram digest failed for user {user.id}: {e}')


def _send_email_digest(user, html_body):
    """Send digest via email."""
    try:
        if not user.email:
            return

        from app.services.email_service import EmailService

        subject = f'📊 Resumen Diario — Centro Juan Pablo II ({datetime.now().strftime("%d/%m/%Y")})'
        EmailService.send_notification_email(
            subject=subject,
            recipients=[user.email],
            body=html_body,
        )
        logger.info(f'Digest sent via email to {user.email}')

    except Exception as e:
        logger.error(f'Email digest failed for user {user.id}: {e}')


# ─── Message Builders ─────────────────────────────────────────────────────


def _build_digest_text(user, ai_summary, groups):
    """Build the plain-text digest for Telegram (Markdown)."""
    role_label = {
        'admin': 'Administrador',
        'supervisor': 'Supervisor',
        'terapista': 'Terapeuta',
        'jugador': 'Paciente',
    }.get(user.role, user.role)

    priority_emoji = {'urgent': '🔴', 'high': '🟠', 'normal': '🟢', 'low': '⚪'}

    lines = [
        ai_summary.get('title', '📊 Resumen Diario'),
        f'👤 {user.username} ({role_label})',
        f'📅 {datetime.now().strftime("%A %d/%m/%Y")}',
        '',
        f'📈 *{sum(g.count for g in groups)}* notificaciones en *{len(groups)}* agrupaciones',
        '',
    ]

    # Priority breakdown
    by_priority = {}
    for g in groups:
        by_priority[g.priority] = by_priority.get(g.priority, 0) + g.count

    for pri in ['urgent', 'high', 'normal', 'low']:
        if pri in by_priority:
            emoji = priority_emoji.get(pri, '⚪')
            label = {'urgent': 'Urgente', 'high': 'Alta', 'normal': 'Normal', 'low': 'Baja'}.get(pri, pri)
            lines.append(f'{emoji} {label}: *{by_priority[pri]}*')

    lines.append('')

    # Highlights
    highlights = ai_summary.get('highlights', [])
    if highlights:
        lines.append('🌟 *Destacado:*')
        for h in highlights[:5]:
            lines.append(f'• {h}')
        lines.append('')

    # Category breakdown
    by_category = {}
    for g in groups:
        cat_label = _category_label(g.category)
        by_category[cat_label] = by_category.get(cat_label, 0) + g.count

    lines.append('📂 *Por categoría:*')
    for cat, count in sorted(by_category.items(), key=lambda x: -x[1])[:8]:
        lines.append(f'  • {cat}: {count}')

    lines.append('')
    lines.append('_Revisa tu panel para más detalle._')

    return '\n'.join(lines)


def _build_digest_html(user, ai_summary, groups):
    """Build HTML digest for email."""
    role_label = {
        'admin': 'Administrador',
        'supervisor': 'Supervisor',
        'terapista': 'Terapeuta',
        'jugador': 'Paciente',
    }.get(user.role, user.role)

    priority_emoji = {'urgent': '🔴', 'high': '🟠', 'normal': '🟢', 'low': '⚪'}

    # Build groups table
    groups_html = ''
    for g in groups[:30]:
        emoji = priority_emoji.get(g.priority, '⚪')
        cat_label = _category_label(g.category)
        summary_line = g.summary or f'{g.count} notificaciones'
        groups_html += f"""
        <tr>
            <td style="padding:8px 12px;border-bottom:1px solid #eee;">{emoji}</td>
            <td style="padding:8px 12px;border-bottom:1px solid #eee;font-weight:600;">{cat_label}</td>
            <td style="padding:8px 12px;border-bottom:1px solid #eee;">{g.title or g.group_key}</td>
            <td style="padding:8px 12px;border-bottom:1px solid #eee;text-align:center;">{g.count}</td>
            <td style="padding:8px 12px;border-bottom:1px solid #eee;color:#666;font-size:13px;">{summary_line[:100]}</td>
        </tr>"""

    highlights_html = ''
    highlights = ai_summary.get('highlights', [])
    if highlights:
        highlights_html = '<div style="margin:20px 0;padding:16px;background:#f8f9fa;border-radius:8px;border-left:4px solid #2563eb;">'
        highlights_html += '<strong style="color:#1e40af;">🌟 Destacado del día</strong><ul style="margin:8px 0 0 0;padding-left:20px;">'
        for h in highlights[:5]:
            highlights_html += f'<li style="margin:4px 0;color:#374151;">{h}</li>'
        highlights_html += '</ul></div>'

    total = sum(g.count for g in groups)

    return f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;max-width:680px;margin:0 auto;padding:20px;color:#1f2937;">
        <div style="background:linear-gradient(135deg,#1e3a5f,#2563eb);color:white;padding:24px;border-radius:12px 12px 0 0;">
            <h1 style="margin:0;font-size:20px;">📊 Resumen Diario — Centro Juan Pablo II</h1>
            <p style="margin:8px 0 0;opacity:0.9;">{user.username} ({role_label}) · {datetime.now().strftime('%d/%m/%Y')}</p>
        </div>

        <div style="background:white;padding:24px;border:1px solid #e5e7eb;border-top:none;border-radius:0 0 12px 12px;">
            <div style="display:flex;gap:20px;margin-bottom:20px;">
                <div style="text-align:center;padding:12px 20px;background:#f8f9fa;border-radius:8px;flex:1;">
                    <div style="font-size:28px;font-weight:700;color:#2563eb;">{total}</div>
                    <div style="font-size:12px;color:#6b7280;">Notificaciones</div>
                </div>
                <div style="text-align:center;padding:12px 20px;background:#f8f9fa;border-radius:8px;flex:1;">
                    <div style="font-size:28px;font-weight:700;color:#059669;">{len(groups)}</div>
                    <div style="font-size:12px;color:#6b7280;">Grupos</div>
                </div>
            </div>

            {highlights_html}

            <h2 style="font-size:16px;color:#374151;margin:24px 0 12px;">Detalle por grupo</h2>
            <table style="width:100%;border-collapse:collapse;font-size:14px;">
                <thead>
                    <tr style="background:#f8f9fa;">
                        <th style="padding:8px 12px;text-align:left;border-bottom:2px solid #e5e7eb;"></th>
                        <th style="padding:8px 12px;text-align:left;border-bottom:2px solid #e5e7eb;">Categoría</th>
                        <th style="padding:8px 12px;text-align:left;border-bottom:2px solid #e5e7eb;">Grupo</th>
                        <th style="padding:8px 12px;text-align:center;border-bottom:2px solid #e5e7eb;">Nº</th>
                        <th style="padding:8px 12px;text-align:left;border-bottom:2px solid #e5e7eb;">Resumen</th>
                    </tr>
                </thead>
                <tbody>{groups_html}</tbody>
            </table>

            <p style="margin-top:24px;font-size:12px;color:#9ca3af;text-align:center;">
                Este resumen fue generado automáticamente por el sistema de notificaciones inteligente.
            </p>
        </div>
    </body>
    </html>"""


def _category_label(category):
    """Human-readable category label."""
    labels = {
        'message': 'Mensajes',
        'session': 'Sesiones',
        'game': 'Juegos',
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
    return labels.get(category, category.title())


# ─── Manual Trigger (for testing) ─────────────────────────────────────────


def send_test_digest(user_id):
    """Send a test digest to a specific user. Used from Centro de Operaciones."""
    user = User.query.get(user_id)
    if not user:
        return {'success': False, 'error': 'User not found'}

    since = datetime.utcnow() - timedelta(hours=24)
    groups = get_groups_for_digest(user.id, since=since)

    if not groups:
        # Create a sample for testing
        from app.models.notification_group import NotificationGroup, NotificationItem

        test_group = NotificationGroup(
            user_id=user.id,
            group_key='test:sample',
            category='system',
            priority='normal',
            title='Grupo de prueba',
            count=3,
            last_item_at=datetime.utcnow(),
            is_read=False,
        )
        db.session.add(test_group)
        db.session.flush()
        for i in range(3):
            db.session.add(
                NotificationItem(
                    group_id=test_group.id,
                    user_id=user.id,
                    message=f'Notificación de prueba #{i + 1}',
                    type='info',
                    priority='normal',
                    timestamp=datetime.utcnow(),
                )
            )
        db.session.commit()
        groups = [test_group]

    ai_summary = generate_ai_digest_summary(groups, user.role)
    if not ai_summary:
        return {'success': False, 'error': 'AI summary generation failed'}

    digest_text = _build_digest_text(user, ai_summary, groups)
    digest_html = _build_digest_html(user, ai_summary, groups)

    _send_telegram_digest(user, digest_text)
    _send_email_digest(user, digest_html)

    # Clean up test group
    from app.models.notification_group import NotificationGroup

    test = NotificationGroup.query.filter_by(user_id=user.id, group_key='test:sample').first()
    if test:
        db.session.delete(test)
        db.session.commit()

    return {'success': True, 'message': f'Digest sent to {user.username}'}
