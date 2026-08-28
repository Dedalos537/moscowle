"""Daily Notification Digest Service — Balanced Scorecard Edition.

Generates and sends a comprehensive daily summary at 6:00 AM to all active users
via Telegram and/or email, including BSC metrics, financials, sessions, patient
progress, trend analysis, and AI-powered predictions.
"""

import json
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

    # Gather BSC data
    bsc_data = _gather_bsc_data(user)

    # Gather notification groups
    groups = get_groups_for_digest(user.id, since=since)

    # Generate AI summary with BSC context
    ai_summary = _generate_ai_bsc_summary(bsc_data, groups, user.role)

    # Build messages
    digest_text = _build_digest_text(user, ai_summary, bsc_data, groups)
    digest_html = _build_digest_html(user, ai_summary, bsc_data, groups)

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


# ─── BSC Data Gathering ──────────────────────────────────────────────────


def _gather_bsc_data(user):
    """Gather Balanced Scorecard data from all sources."""
    now = datetime.utcnow()
    today = now.date()
    month_start = today.replace(day=1)
    last_month_start = (month_start - timedelta(days=1)).replace(day=1)
    last_month_end = month_start - timedelta(days=1)

    data = {}

    # ── Financial Perspective ──
    try:
        from app.models.payment import Payment, Expense

        # Current month income
        income_real = db.session.query(
            db.func.coalesce(db.func.sum(Payment.amount), 0)
        ).filter(
            Payment.date >= month_start,
            Payment.status.in_(['paid', 'completed']),
        ).scalar()

        # Expected income (all active patients * payment_amount)
        from app.models.user import User as UserModel
        active_patients = UserModel.query.filter_by(role='jugador', is_active=True).count()
        avg_payment = db.session.query(
            db.func.coalesce(db.func.avg(Payment.amount), 0)
        ).filter(Payment.date >= last_month_start).scalar()
        income_expected = active_patients * float(avg_payment) if avg_payment else 0

        # Overdue payments
        overdue_count = Payment.query.filter(
            Payment.status.in_(['pending', 'overdue']),
            Payment.date < today,
        ).count()

        overdue_amount = db.session.query(
            db.func.coalesce(db.func.sum(Payment.amount), 0)
        ).filter(
            Payment.status.in_(['pending', 'overdue']),
            Payment.date < today,
        ).scalar()

        # Expenses this month
        expenses = db.session.query(
            db.func.coalesce(db.func.sum(Expense.amount), 0)
        ).filter(Expense.date >= month_start).scalar()

        net_profit = float(income_real) - float(expenses)

        # Last month comparison
        last_month_income = db.session.query(
            db.func.coalesce(db.func.sum(Payment.amount), 0)
        ).filter(
            Payment.date >= last_month_start,
            Payment.date <= last_month_end,
            Payment.status.in_(['paid', 'completed']),
        ).scalar()

        income_trend = ((float(income_real) - float(last_month_income)) / float(last_month_income) * 100) if float(last_month_income) > 0 else 0

        data['financial'] = {
            'income_real': float(income_real),
            'income_expected': float(income_expected),
            'income_trend': round(income_trend, 1),
            'overdue_count': overdue_count,
            'overdue_amount': float(overdue_amount),
            'expenses': float(expenses),
            'net_profit': net_profit,
            'collection_rate': round(float(income_real) / float(income_expected) * 100, 1) if income_expected > 0 else 0,
        }
    except Exception as e:
        logger.warning(f'Financial data gathering failed: {e}')
        data['financial'] = None

    # ── Patient Perspective ──
    try:
        from app.models.appointment import Appointment

        total_patients = UserModel.query.filter_by(role='jugador', is_active=True).count()

        # Sessions today
        sessions_today = Appointment.query.filter(
            Appointment.start_time >= datetime.combine(today, datetime.min.time()),
            Appointment.start_time < datetime.combine(today + timedelta(days=1), datetime.min.time()),
        ).count()

        sessions_completed = Appointment.query.filter(
            Appointment.start_time >= datetime.combine(today, datetime.min.time()),
            Appointment.start_time < datetime.combine(today + timedelta(days=1), datetime.min.time()),
            Appointment.status == 'completed',
        ).count()

        # Attendance rate (last 7 days)
        week_ago = today - timedelta(days=7)
        total_sessions_week = Appointment.query.filter(
            Appointment.start_time >= datetime.combine(week_ago, datetime.min.time()),
        ).count()
        attended_week = Appointment.query.filter(
            Appointment.start_time >= datetime.combine(week_ago, datetime.min.time()),
            Appointment.attendance == 'present',
        ).count()
        attendance_rate = round(attended_week / total_sessions_week * 100, 1) if total_sessions_week > 0 else 0

        # Average accuracy (last 7 days)
        from app.models.appointment import Appointment, SessionMetrics

        avg_accuracy = db.session.query(
            db.func.coalesce(db.func.avg(SessionMetrics.accurracy), 0)
        ).filter(
            SessionMetrics.date >= week_ago,
        ).scalar()

        # Patients inactive > 2 weeks
        two_weeks_ago = today - timedelta(days=14)
        inactive_patients = db.session.query(UserModel.id).filter(
            UserModel.role == 'jugador',
            UserModel.is_active == True,
            UserModel.id.notin_(
                db.session.query(Appointment.patient_id).filter(
                    Appointment.start_time >= datetime.combine(two_weeks_ago, datetime.min.time())
                )
            ),
        ).count()

        data['patients'] = {
            'total': total_patients,
            'sessions_today': sessions_today,
            'sessions_completed': sessions_completed,
            'attendance_rate': attendance_rate,
            'avg_accuracy': round(float(avg_accuracy), 1),
            'inactive_2weeks': inactive_patients,
        }
    except Exception as e:
        logger.warning(f'Patient data gathering failed: {e}')
        data['patients'] = None

    # ── Therapist Perspective ──
    try:
        from sqlalchemy import func

        therapists = UserModel.query.filter_by(role='terapista', is_active=True).all()
        therapist_stats = []

        for t in therapists:
            t_sessions = Appointment.query.filter(
                Appointment.therapist_id == t.id,
                Appointment.start_time >= datetime.combine(week_ago, datetime.min.time()),
            ).count()
            t_completed = Appointment.query.filter(
                Appointment.therapist_id == t.id,
                Appointment.start_time >= datetime.combine(week_ago, datetime.min.time()),
                Appointment.status == 'completed',
            ).count()
            t_accuracy = db.session.query(
                db.func.coalesce(db.func.avg(SessionMetrics.accuracy), 0)
            ).join(Appointment, SessionMetrics.appointment_id == Appointment.id).filter(
                Appointment.therapist_id == t.id,
                SessionMetrics.date >= week_ago,
            ).scalar()

            efficiency = round(t_completed / t_sessions * 100, 1) if t_sessions > 0 else 0
            therapist_stats.append({
                'name': t.username,
                'sessions': t_sessions,
                'completed': t_completed,
                'accuracy': round(float(t_accuracy), 1),
                'efficiency': efficiency,
            })

        # Sort by efficiency
        therapist_stats.sort(key=lambda x: x['efficiency'], reverse=True)

        data['therapists'] = {
            'total': len(therapists),
            'stats': therapist_stats[:10],
            'avg_efficiency': round(sum(t['efficiency'] for t in therapist_stats) / len(therapist_stats), 1) if therapist_stats else 0,
        }
    except Exception as e:
        logger.warning(f'Therapist data gathering failed: {e}')
        data['therapists'] = None

    # ── Learning & Growth Perspective ──
    try:
        # Incidents this week
        from app.models.incidente import Incidente

        incidents_week = Incidente.query.filter(
            Incidente.created_at >= datetime.combine(week_ago, datetime.min.time()),
        ).count()

        incidents_open = Incidente.query.filter(
            Incidente.status.in_(['open', 'in_progress']),
        ).count()

        # Audit scores (last 7 days)
        from app.models.report import SessionAudit

        avg_audit = db.session.query(
            db.func.coalesce(db.func.avg(SessionAudit.audit_score), 0)
        ).filter(
            SessionAudit.audited_at >= datetime.combine(week_ago, datetime.min.time()),
        ).scalar()

        data['growth'] = {
            'incidents_week': incidents_week,
            'incidents_open': incidents_open,
            'avg_audit_score': round(float(avg_audit), 1),
        }
    except Exception as e:
        logger.warning(f'Growth data gathering failed: {e}')
        data['growth'] = None

    # ── AI Predictions ──
    data['predictions'] = _generate_predictions(data)

    return data


def _generate_predictions(bsc_data):
    """Generate simple AI predictions based on historical data."""
    predictions = {}

    try:
        now = datetime.utcnow()
        today = now.date()

        # Revenue prediction (next month)
        if bsc_data.get('financial'):
            fin = bsc_data['financial']
            # Simple projection based on current rate
            days_in_month = 30
            day_of_month = today.day
            if day_of_month > 0:
                projected = (fin['income_real'] / day_of_month) * days_in_month
                predictions['revenue_next_month'] = round(projected, 2)
                predictions['revenue_confidence'] = 'media' if day_of_month > 15 else 'baja'

        # Patient churn risk
        if bsc_data.get('patients'):
            pat = bsc_data['patients']
            if pat['inactive_2weeks'] > 0:
                predictions['churn_risk'] = pat['inactive_2weeks']
                predictions['churn_severity'] = 'alta' if pat['inactive_2weeks'] > 5 else 'media'
            else:
                predictions['churn_risk'] = 0
                predictions['churn_severity'] = 'baja'

        # Efficiency trend
        if bsc_data.get('therapists'):
            ther = bsc_data['therapists']
            predictions['therapist_efficiency_avg'] = ther['avg_efficiency']
            if ther['avg_efficiency'] < 50:
                predictions['efficiency_alert'] = 'La eficiencia promedio está por debajo del 50%'
            elif ther['avg_efficiency'] > 80:
                predictions['efficiency_alert'] = 'Excelente eficiencia del equipo'

    except Exception as e:
        logger.warning(f'Prediction generation failed: {e}')

    return predictions


# ─── AI Summary Generation ───────────────────────────────────────────────


def _generate_ai_bsc_summary(bsc_data, groups, user_role):
    """Generate AI-powered executive summary with BSC context."""
    try:
        from app.services.llm_client import llm_chat

        # Build context for AI
        context_parts = []

        if bsc_data.get('financial'):
            fin = bsc_data['financial']
            context_parts.append(
                f"FINANZAS: Ingresos S/{fin['income_real']:.0f} (meta S/{fin['income_expected']:.0f}, "
                f"{fin['collection_rate']:.0f}% cobranza). Mora: {fin['overdue_count']} usuarios S/{fin['overdue_amount']:.0f}. "
                f"Gastos S/{fin['expenses']:.0f}. Utilidad neta S/{fin['net_profit']:.0f}."
            )

        if bsc_data.get('patients'):
            pat = bsc_data['patients']
            context_parts.append(
                f"PACIENTES: {pat['total']} activos. Sesiones hoy: {pat['sessions_today']} "
                f"({pat['sessions_completed']} completadas). Asistencia 7d: {pat['attendance_rate']}%. "
                f"Precisión promedio: {pat['avg_accuracy']}%. Inactivos >2sem: {pat['inactive_2weeks']}."
            )

        if bsc_data.get('therapists'):
            ther = bsc_data['therapists']
            top3 = ther['stats'][:3]
            top_str = ', '.join([f"{t['name']}({t['efficiency']}%)" for t in top3])
            context_parts.append(
                f"TERAPEUTAS: {ther['total']} activos. Eficiencia promedio: {ther['avg_efficiency']}%. "
                f"Top 3: {top_str}."
            )

        if bsc_data.get('growth'):
            gro = bsc_data['growth']
            context_parts.append(
                f"CRECIMIENTO: Incidentes abiertos: {gro['incidents_open']}. "
                f"Score auditoría promedio: {gro['avg_audit_score']}/100."
            )

        if bsc_data.get('predictions'):
            pred = bsc_data['predictions']
            pred_parts = []
            if 'revenue_next_month' in pred:
                pred_parts.append(f"Ingreso proyectado mes: S/{pred['revenue_next_month']:.0f} (confianza {pred.get('revenue_confidence', 'baja')})")
            if pred.get('churn_risk', 0) > 0:
                pred_parts.append(f"Riesgo abandono: {pred['churn_risk']} pacientes (severidad {pred.get('churn_severity', 'media')})")
            if pred_parts:
                context_parts.append(f"PREDICCIONES: {'; '.join(pred_parts)}.")

        context_text = '\n'.join(context_parts)

        # Notification groups summary
        group_lines = []
        for g in (groups or [])[:10]:
            priority_emoji = {'urgent': '🔴', 'high': '🟠', 'normal': '🟢', 'low': '⚪'}.get(g.priority, '⚪')
            group_lines.append(f'- {priority_emoji} [{g.category}] {g.title or g.group_key} (x{g.count})')
        groups_text = '\n'.join(group_lines) if group_lines else 'Sin notificaciones pendientes'

        prompt = f"""Eres el asistente ejecutivo del Centro Juan Pablo II (terapia ocupacional).
Genera un resumen ejecutivo diario en español para un usuario con rol '{user_role}'.

DATOS DEL DÍA (Balanced Scorecard):
{context_text}

NOTIFICACIONES:
{groups_text}

Genera un resumen ejecutivo que incluya:
1. Titular con fecha y tono ejecutivo
2. Resumen de 4 perspectivas BSC (Finanzas, Pacientes, Terapeutas, Crecimiento)
3. 3-5 highlights accionables con recomendaciones
4. Predicciones y alertas
5. Tono profesional, usa emoji, máximo 15 líneas

Responde SOLO con JSON:
{{"title": "🦜 Buenos días — Resumen DD/MM/YYYY", "body": "resumen aquí", "highlights": ["punto 1", "punto 2", "punto 3"], "bsc_scores": {{"finance": 7, "patients": 8, "therapists": 6, "growth": 7}}}}"""

        messages = [{'role': 'user', 'content': prompt}]
        content, provider = llm_chat(messages, temperature=0.3, max_tokens=600)

        result = json.loads(content.strip().strip('`').strip('json').strip())
        logger.info(f'BSC digest AI summary via {provider}')
        return result

    except Exception as e:
        logger.warning(f'AI BSC summary failed: {e}')
        # Fallback
        return _fallback_summary(bsc_data, groups)


def _fallback_summary(bsc_data, groups):
    """Generate fallback summary without AI."""
    parts = []
    if bsc_data.get('financial'):
        fin = bsc_data['financial']
        parts.append(f"Ingresos: S/{fin['income_real']:.0f}/{fin['income_expected']:.0f}")
    if bsc_data.get('patients'):
        pat = bsc_data['patients']
        parts.append(f"Pacientes: {pat['total']}, Asistencia: {pat['attendance_rate']}%")
    if bsc_data.get('therapists'):
        parts.append(f"Terapeutas: {bsc_data['therapists']['total']}, Eficiencia: {bsc_data['therapists']['avg_efficiency']}%")

    body = '\n'.join(parts) if parts else 'Sin datos disponibles hoy.'
    total = sum(g.count for g in (groups or []))

    return {
        'title': f"🦜 Resumen Diario — {datetime.now().strftime('%d/%m/%Y')}",
        'body': body,
        'highlights': [f'{total} notificaciones pendientes'],
        'bsc_scores': {'finance': 5, 'patients': 5, 'therapists': 5, 'growth': 5},
    }


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

        subject = f'🦜 Resumen Diario — Centro Juan Pablo II ({datetime.now().strftime("%d/%m/%Y")})'
        EmailService.send_notification_email(
            subject=subject,
            recipients=[user.email],
            body=html_body,
        )
        logger.info(f'Digest sent via email to {user.email}')

    except Exception as e:
        logger.error(f'Email digest failed for user {user.id}: {e}')


# ─── Message Builders ─────────────────────────────────────────────────────


def _build_digest_text(user, ai_summary, bsc_data, groups):
    """Build the plain-text digest for Telegram (Markdown)."""
    role_label = {
        'admin': 'Administrador',
        'supervisor': 'Supervisor',
        'terapista': 'Terapeuta',
        'jugador': 'Paciente',
    }.get(user.role, user.role)

    lines = [
        ai_summary.get('title', f"🦜 Resumen Diario"),
        f"👤 {user.username} ({role_label})",
        f"📅 {datetime.now().strftime('%A %d/%m/%Y')}",
        '',
    ]

    # BSC Scores
    bsc_scores = ai_summary.get('bsc_scores', {})
    if bsc_scores:
        lines.append('📊 *Balanced Scorecard:*')
        score_emoji = lambda s: '🟢' if s >= 7 else '🟡' if s >= 5 else '🔴'
        labels = {'finance': 'Finanzas', 'patients': 'Pacientes', 'therapists': 'Terapeutas', 'growth': 'Crecimiento'}
        for key, label in labels.items():
            score = bsc_scores.get(key, 5)
            lines.append(f'  {score_emoji(score)} {label}: {score}/10')
        lines.append('')

    # Financial summary
    if bsc_data.get('financial'):
        fin = bsc_data['financial']
        lines.append('💰 *Finanzas:*')
        lines.append(f'  Ingresos: S/{fin["income_real"]:.0f} / S/{fin["income_expected"]:.0f} ({fin["collection_rate"]:.0f}%)')
        lines.append(f'  Tendencia: {"📈" if fin["income_trend"] > 0 else "📉"} {fin["income_trend"]:+.1f}% vs mes anterior')
        lines.append(f'  Mora: {fin["overdue_count"]} usuarios (S/{fin["overdue_amount"]:.0f})')
        lines.append(f'  Gastos: S/{fin["expenses"]:.0f} → Utilidad: S/{fin["net_profit"]:.0f}')
        lines.append('')

    # Patient summary
    if bsc_data.get('patients'):
        pat = bsc_data['patients']
        lines.append('🏥 *Pacientes:*')
        lines.append(f'  Activos: {pat["total"]} | Sesiones hoy: {pat["sessions_today"]}/{pat["sessions_completed"]} completadas')
        lines.append(f'  Asistencia 7d: {pat["attendance_rate"]}% | Precisión: {pat["avg_accuracy"]}%')
        if pat['inactive_2weeks'] > 0:
            lines.append(f'  ⚠️ {pat["inactive_2weeks"]} pacientes inactivos >2 semanas')
        lines.append('')

    # Therapist summary
    if bsc_data.get('therapists'):
        ther = bsc_data['therapists']
        lines.append('👨‍⚕️ *Terapeutas:*')
        lines.append(f'  Eficiencia promedio: {ther["avg_efficiency"]}%')
        for t in ther['stats'][:3]:
            lines.append(f'  • {t["name"]}: {t["efficiency"]}% eficiencia, {t["accuracy"]}% precisión')
        lines.append('')

    # Predictions
    if bsc_data.get('predictions'):
        pred = bsc_data['predictions']
        lines.append('🔮 *Predicciones (IA):*')
        if 'revenue_next_month' in pred:
            lines.append(f'  Ingreso proyectado: S/{pred["revenue_next_month"]:.0f} (confianza {pred.get("revenue_confidence", "baja")})')
        if pred.get('churn_risk', 0) > 0:
            lines.append(f'  ⚠️ Riesgo abandono: {pred["churn_risk"]} pacientes')
        if pred.get('efficiency_alert'):
            lines.append(f'  ℹ️ {pred["efficiency_alert"]}')
        lines.append('')

    # Highlights
    highlights = ai_summary.get('highlights', [])
    if highlights:
        lines.append('🌟 *Destacado:*')
        for h in highlights[:5]:
            lines.append(f'• {h}')
        lines.append('')

    # Notification summary
    if groups:
        total = sum(g.count for g in groups)
        lines.append(f'🔔 *Notificaciones:* {total} en {len(groups)} grupos')

    lines.append('')
    lines.append('_Generado por Chasqui 🦜 — Centro Juan Pablo II_')

    return '\n'.join(lines)


def _build_digest_html(user, ai_summary, bsc_data, groups):
    """Build HTML digest for email with BSC dashboard."""
    role_label = {
        'admin': 'Administrador',
        'supervisor': 'Supervisor',
        'terapista': 'Terapeuta',
        'jugador': 'Paciente',
    }.get(user.role, user.role)

    bsc_scores = ai_summary.get('bsc_scores', {})
    score_color = lambda s: '#10b981' if s >= 7 else '#f59e0b' if s >= 5 else '#ef4444'
    score_bg = lambda s: '#d1fae5' if s >= 7 else '#fef3c7' if s >= 5 else '#fee2e2'

    # Financial section
    fin_html = ''
    if bsc_data.get('financial'):
        fin = bsc_data['financial']
        fin_html = f"""
        <div style="background:white;border-radius:8px;padding:16px;margin-bottom:16px;border:1px solid #e5e7eb;">
            <h3 style="margin:0 0 12px;font-size:14px;color:#374151;">💰 Finanzas</h3>
            <div style="display:flex;gap:12px;flex-wrap:wrap;">
                <div style="flex:1;min-width:120px;text-align:center;padding:10px;background:#f8f9fa;border-radius:6px;">
                    <div style="font-size:20px;font-weight:700;color:#059669;">S/{fin['income_real']:.0f}</div>
                    <div style="font-size:11px;color:#6b7280;">Ingresos</div>
                </div>
                <div style="flex:1;min-width:120px;text-align:center;padding:10px;background:#f8f9fa;border-radius:6px;">
                    <div style="font-size:20px;font-weight:700;color:#6b7280;">S/{fin['income_expected']:.0f}</div>
                    <div style="font-size:11px;color:#6b7280;">Meta</div>
                </div>
                <div style="flex:1;min-width:120px;text-align:center;padding:10px;background:#f8f9fa;border-radius:6px;">
                    <div style="font-size:20px;font-weight:700;color:#ef4444;">S/{fin['overdue_amount']:.0f}</div>
                    <div style="font-size:11px;color:#6b7280;">Mora ({fin['overdue_count']})</div>
                </div>
                <div style="flex:1;min-width:120px;text-align:center;padding:10px;background:{score_bg(fin['collection_rate']/10)}border-radius:6px;">
                    <div style="font-size:20px;font-weight:700;color:{score_color(fin['collection_rate']/10)};">{fin['collection_rate']:.0f}%</div>
                    <div style="font-size:11px;color:#6b7280;">Cobranza</div>
                </div>
            </div>
        </div>"""

    # Patient section
    pat_html = ''
    if bsc_data.get('patients'):
        pat = bsc_data['patients']
        pat_html = f"""
        <div style="background:white;border-radius:8px;padding:16px;margin-bottom:16px;border:1px solid #e5e7eb;">
            <h3 style="margin:0 0 12px;font-size:14px;color:#374151;">🏥 Pacientes</h3>
            <div style="display:flex;gap:12px;flex-wrap:wrap;">
                <div style="flex:1;min-width:100px;text-align:center;padding:10px;background:#f8f9fa;border-radius:6px;">
                    <div style="font-size:20px;font-weight:700;color:#2563eb;">{pat['total']}</div>
                    <div style="font-size:11px;color:#6b7280;">Activos</div>
                </div>
                <div style="flex:1;min-width:100px;text-align:center;padding:10px;background:#f8f9fa;border-radius:6px;">
                    <div style="font-size:20px;font-weight:700;color:#059669;">{pat['sessions_completed']}/{pat['sessions_today']}</div>
                    <div style="font-size:11px;color:#6b7280;">Sesiones Hoy</div>
                </div>
                <div style="flex:1;min-width:100px;text-align:center;padding:10px;background:{score_bg(pat['attendance_rate']/10)}border-radius:6px;">
                    <div style="font-size:20px;font-weight:700;color:{score_color(pat['attendance_rate']/10)};">{pat['attendance_rate']}%</div>
                    <div style="font-size:11px;color:#6b7280;">Asistencia</div>
                </div>
                <div style="flex:1;min-width:100px;text-align:center;padding:10px;background:#f8f9fa;border-radius:6px;">
                    <div style="font-size:20px;font-weight:700;color:#8b5cf6;">{pat['avg_accuracy']}%</div>
                    <div style="font-size:11px;color:#6b7280;">Precisión</div>
                </div>
            </div>
            {f'<div style="margin-top:8px;padding:8px;background:#fef3c7;border-radius:6px;font-size:12px;color:#92400e;">⚠️ {pat["inactive_2weeks"]} pacientes inactivos &gt;2 semanas</div>' if pat['inactive_2weeks'] > 0 else ''}
        </div>"""

    # Therapist section
    ther_html = ''
    if bsc_data.get('therapists'):
        ther = bsc_data['therapists']
        rows = ''
        for t in ther['stats'][:5]:
            eff_color = '#10b981' if t['efficiency'] >= 70 else '#f59e0b' if t['efficiency'] >= 50 else '#ef4444'
            rows += f"""
            <tr>
                <td style="padding:8px 12px;border-bottom:1px solid #eee;font-weight:600;">{t['name']}</td>
                <td style="padding:8px 12px;border-bottom:1px solid #eee;text-align:center;">{t['sessions']}</td>
                <td style="padding:8px 12px;border-bottom:1px solid #eee;text-align:center;">{t['completed']}</td>
                <td style="padding:8px 12px;border-bottom:1px solid #eee;text-align:center;color:{eff_color};font-weight:700;">{t['efficiency']}%</td>
                <td style="padding:8px 12px;border-bottom:1px solid #eee;text-align:center;">{t['accuracy']}%</td>
            </tr>"""

        ther_html = f"""
        <div style="background:white;border-radius:8px;padding:16px;margin-bottom:16px;border:1px solid #e5e7eb;">
            <h3 style="margin:0 0 12px;font-size:14px;color:#374151;">👨‍⚕️ Terapeutas — Eficiencia promedio: {ther['avg_efficiency']}%</h3>
            <table style="width:100%;border-collapse:collapse;font-size:13px;">
                <thead>
                    <tr style="background:#f8f9fa;">
                        <th style="padding:8px;text-align:left;">Nombre</th>
                        <th style="padding:8px;text-align:center;">Sesiones</th>
                        <th style="padding:8px;text-align:center;">Completadas</th>
                        <th style="padding:8px;text-align:center;">Eficiencia</th>
                        <th style="padding:8px;text-align:center;">Precisión</th>
                    </tr>
                </thead>
                <tbody>{rows}</tbody>
            </table>
        </div>"""

    # Predictions section
    pred_html = ''
    if bsc_data.get('predictions'):
        pred = bsc_data['predictions']
        items = []
        if 'revenue_next_month' in pred:
            items.append(f"<div style='padding:6px 0;'>💰 Ingreso proyectado: <strong>S/{pred['revenue_next_month']:.0f}</strong> <span style='color:#6b7280;'>(confianza {pred.get('revenue_confidence', 'baja')})</span></div>")
        if pred.get('churn_risk', 0) > 0:
            items.append(f"<div style='padding:6px 0;'>⚠️ Riesgo abandono: <strong>{pred['churn_risk']} pacientes</strong></div>")
        if pred.get('efficiency_alert'):
            items.append(f"<div style='padding:6px 0;'>ℹ️ {pred['efficiency_alert']}</div>")

        if items:
            pred_html = f"""
            <div style="background:white;border-radius:8px;padding:16px;margin-bottom:16px;border:1px solid #e5e7eb;">
                <h3 style="margin:0 0 8px;font-size:14px;color:#374151;">🔮 Predicciones (IA)</h3>
                <div style="font-size:13px;color:#374151;">{''.join(items)}</div>
            </div>"""

    # Highlights
    highlights = ai_summary.get('highlights', [])
    highlights_html = ''
    if highlights:
        items = ''.join([f'<li style="margin:4px 0;color:#374151;">{h}</li>' for h in highlights[:5]])
        highlights_html = f"""
        <div style="background:white;border-radius:8px;padding:16px;margin-bottom:16px;border-left:4px solid #2563eb;">
            <h3 style="margin:0 0 8px;font-size:14px;color:#1e40af;">🌟 Destacado del día</h3>
            <ul style="margin:0;padding-left:20px;font-size:13px;">{items}</ul>
        </div>"""

    # Notification groups table
    groups_html = ''
    if groups:
        for g in groups[:20]:
            priority_emoji = {'urgent': '🔴', 'high': '🟠', 'normal': '🟢', 'low': '⚪'}.get(g.priority, '⚪')
            cat_label = _category_label(g.category)
            groups_html += f"""
            <tr>
                <td style="padding:6px 12px;border-bottom:1px solid #eee;">{priority_emoji}</td>
                <td style="padding:6px 12px;border-bottom:1px solid #eee;">{cat_label}</td>
                <td style="padding:6px 12px;border-bottom:1px solid #eee;font-weight:600;">{g.title or g.group_key}</td>
                <td style="padding:6px 12px;border-bottom:1px solid #eee;text-align:center;">{g.count}</td>
            </tr>"""

    # BSC Score cards
    bsc_html = ''
    if bsc_scores:
        cards = ''
        labels = {'finance': 'Finanzas', 'patients': 'Pacientes', 'therapists': 'Terapeutas', 'growth': 'Crecimiento'}
        icons = {'finance': '💰', 'patients': '🏥', 'therapists': '👨‍⚕️', 'growth': '📈'}
        for key, label in labels.items():
            score = bsc_scores.get(key, 5)
            cards += f"""
            <div style="flex:1;min-width:100px;text-align:center;padding:12px;background:{score_bg(score)};border-radius:8px;">
                <div style="font-size:11px;color:#6b7280;">{icons[key]} {label}</div>
                <div style="font-size:24px;font-weight:700;color:{score_color(score)};">{score}/10</div>
            </div>"""

        bsc_html = f"""
        <div style="background:white;border-radius:8px;padding:16px;margin-bottom:16px;border:1px solid #e5e7eb;">
            <h3 style="margin:0 0 12px;font-size:14px;color:#374151;">📊 Balanced Scorecard</h3>
            <div style="display:flex;gap:12px;flex-wrap:wrap;">{cards}</div>
        </div>"""

    return f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;max-width:700px;margin:0 auto;padding:20px;color:#1f2937;background:#f3f4f6;">
        <div style="background:linear-gradient(135deg,#1e3a5f,#2563eb);color:white;padding:24px;border-radius:12px 12px 0 0;">
            <h1 style="margin:0;font-size:20px;">🦜 {ai_summary.get('title', 'Resumen Diario')}</h1>
            <p style="margin:8px 0 0;opacity:0.9;">{user.username} ({role_label}) · {datetime.now().strftime('%d/%m/%Y')}</p>
        </div>

        <div style="padding:20px;background:#f3f4f6;">
            {bsc_html}
            {fin_html}
            {pat_html}
            {ther_html}
            {pred_html}
            {highlights_html}

            {'<div style="background:white;border-radius:8px;padding:16px;border:1px solid #e5e7eb;"><h3 style="margin:0 0 8px;font-size:14px;color:#374151;">🔔 Notificaciones</h3><table style="width:100%;border-collapse:collapse;font-size:13px;"><thead><tr style="background:#f8f9fa;"><th style="padding:6px;text-align:left;"></th><th style="padding:6px;text-align:left;">Cat.</th><th style="padding:6px;text-align:left;">Grupo</th><th style="padding:6px;text-align:center;">Nº</th></tr></thead><tbody>' + groups_html + '</tbody></table></div>' if groups_html else ''}

            <div style="text-align:center;padding:16px;font-size:12px;color:#9ca3af;">
                Generado automáticamente por Chasqui 🦜 — Centro Juan Pablo II<br>
                <a href="https://api-centrojuanpabloii.online" style="color:#2563eb;">Ver panel</a>
            </div>
        </div>
    </body>
    </html>"""


def _category_label(category):
    """Human-readable category label."""
    labels = {
        'message': 'Mensajes', 'session': 'Sesiones', 'game': 'Juegos',
        'payment': 'Pagos', 'alert': 'Alertas', 'incident': 'Incidentes',
        'security': 'Seguridad', 'report': 'Reportes', 'audit': 'Auditorías',
        'contact': 'Contacto', 'user_mgmt': 'Usuarios', 'system': 'Sistema',
        'debt': 'Deudas', 'activity': 'Actividad',
    }
    return labels.get(category, category.title())


# ─── Manual Trigger (for testing) ─────────────────────────────────────────


def send_test_digest(user_id):
    """Send a test digest to a specific user."""
    user = User.query.get(user_id)
    if not user:
        return {'success': False, 'error': 'User not found'}

    since = datetime.utcnow() - timedelta(hours=24)
    groups = get_groups_for_digest(user.id, since=since)
    bsc_data = _gather_bsc_data(user)
    ai_summary = _generate_ai_bsc_summary(bsc_data, groups, user.role)

    digest_text = _build_digest_text(user, ai_summary, bsc_data, groups)
    digest_html = _build_digest_html(user, ai_summary, bsc_data, groups)

    _send_telegram_digest(user, digest_text)
    _send_email_digest(user, digest_html)

    return {'success': True, 'message': f'BSC Digest sent to {user.username}'}
