"""Automated Reports Service — Weekly, Monthly, Annual with AI.

Generates and sends comprehensive reports via Telegram and email with
BSC metrics, trend analysis, predictions, and data for analysis.
"""

import csv
import io
import json
import logging
from datetime import datetime, timedelta

from flask import current_app

from app.extensions import db
from app.models import User

logger = logging.getLogger(__name__)


# ─── Weekly Report ────────────────────────────────────────────────────────


def generate_weekly_reports():
    """Generate and send weekly reports every Saturday at 8 PM."""
    logger.info('Starting weekly report generation...')
    now = datetime.utcnow()
    week_start = now - timedelta(days=7)

    active_users = User.query.filter_by(is_active=True).all()
    sent = 0

    for user in active_users:
        try:
            _send_weekly_report(user, week_start, now)
            sent += 1
        except Exception as e:
            logger.error(f'Weekly report failed for user {user.id}: {e}')

    logger.info(f'Weekly reports complete: {sent}/{len(active_users)} sent')
    return {'sent': sent, 'total': len(active_users)}


def _send_weekly_report(user, since, until):
    """Generate and send weekly report for a user."""
    from app.models.notification import UserNotificationPreference

    prefs = UserNotificationPreference.query.filter_by(user_id=user.id).first()
    if not prefs or not getattr(prefs, 'digest_enabled', True):
        return

    data = _gather_period_data(since, until, 'semanal')
    ai_summary = _generate_ai_report(data, 'semanal', user.role)

    text = _build_report_text(user, ai_summary, data, 'semanal')
    html = _build_report_html(user, ai_summary, data, 'semanal')

    digest_channel = getattr(prefs, 'digest_channel', 'both')

    if digest_channel in ('telegram', 'both'):
        _send_report_telegram(user, text)
    if digest_channel in ('email', 'both'):
        _send_report_email(user, html, 'Semanal')


# ─── Monthly Report ───────────────────────────────────────────────────────


def generate_monthly_reports():
    """Generate and send monthly reports on the 1st at 9 PM."""
    logger.info('Starting monthly report generation...')
    now = datetime.utcnow()
    month_start = (now - timedelta(days=now.day)).replace(day=1)
    month_end = now.replace(day=1) - timedelta(seconds=1)

    active_users = User.query.filter_by(is_active=True).all()
    sent = 0

    for user in active_users:
        try:
            _send_monthly_report(user, month_start, month_end)
            sent += 1
        except Exception as e:
            logger.error(f'Monthly report failed for user {user.id}: {e}')

    logger.info(f'Monthly reports complete: {sent}/{len(active_users)} sent')
    return {'sent': sent, 'total': len(active_users)}


def _send_monthly_report(user, since, until):
    """Generate and send monthly report."""
    from app.models.notification import UserNotificationPreference

    prefs = UserNotificationPreference.query.filter_by(user_id=user.id).first()
    if not prefs or not getattr(prefs, 'digest_enabled', True):
        return

    data = _gather_period_data(since, until, 'mensual')
    prev_month_start = (since - timedelta(days=1)).replace(day=1)
    prev_data = _gather_period_data(prev_month_start, since - timedelta(seconds=1), 'mensual')
    data['prev'] = prev_data

    ai_summary = _generate_ai_report(data, 'mensual', user.role)

    text = _build_report_text(user, ai_summary, data, 'mensual')
    html = _build_report_html(user, ai_summary, data, 'mensual')

    digest_channel = getattr(prefs, 'digest_channel', 'both')

    if digest_channel in ('telegram', 'both'):
        _send_report_telegram(user, text)
    if digest_channel in ('email', 'both'):
        _send_report_email(user, html, 'Mensual')


# ─── Annual Report ────────────────────────────────────────────────────────


def generate_annual_reports():
    """Generate and send annual reports on Jan 1 at 10 PM."""
    logger.info('Starting annual report generation...')
    now = datetime.utcnow()
    year_start = now.replace(month=1, day=1)
    year_end = now.replace(month=1, day=1) - timedelta(seconds=1)
    year_end = now - timedelta(seconds=1)

    active_users = User.query.filter_by(is_active=True).all()
    sent = 0

    for user in active_users:
        try:
            _send_annual_report(user, year_start, year_end)
            sent += 1
        except Exception as e:
            logger.error(f'Annual report failed for user {user.id}: {e}')

    logger.info(f'Annual reports complete: {sent}/{len(active_users)} sent')
    return {'sent': sent, 'total': len(active_users)}


def _send_annual_report(user, since, until):
    """Generate and send annual report."""
    from app.models.notification import UserNotificationPreference

    prefs = UserNotificationPreference.query.filter_by(user_id=user.id).first()
    if not prefs or not getattr(prefs, 'digest_enabled', True):
        return

    # Gather monthly breakdown
    monthly_data = []
    current = since
    while current <= until:
        m_start = current.replace(day=1)
        if current.month == 12:
            m_end = current.replace(year=current.year + 1, month=1, day=1) - timedelta(seconds=1)
        else:
            m_end = current.replace(month=current.month + 1, day=1) - timedelta(seconds=1)
        m_data = _gather_period_data(m_start, m_end, 'mensual')
        monthly_data.append({'month': current.strftime('%B %Y'), **m_data})
        current = m_end + timedelta(days=1)

    data = _gather_period_data(since, until, 'anual')
    data['monthly_breakdown'] = monthly_data

    ai_summary = _generate_ai_report(data, 'anual', user.role)

    text = _build_report_text(user, ai_summary, data, 'anual')
    html = _build_report_html(user, ai_summary, data, 'anual')

    digest_channel = getattr(prefs, 'digest_channel', 'both')

    if digest_channel in ('telegram', 'both'):
        _send_report_telegram(user, text)
    if digest_channel in ('email', 'both'):
        _send_report_email(user, html, 'Anual')


# ─── Data Gathering ──────────────────────────────────────────────────────


def _gather_period_data(since, until, period_type):
    """Gather comprehensive data for a period."""
    data = {'since': since.isoformat(), 'until': until.isoformat(), 'period': period_type}

    try:
        from app.models.payment import Payment, Expense
        from app.models.appointment import Appointment, SessionMetrics
        from app.models.user import User as UserModel
        from app.models.report import SessionAudit
        from app.models.incidente import Incidente

        # Financial
        income = db.session.query(
            db.func.coalesce(db.func.sum(Payment.amount), 0)
        ).filter(
            Payment.date >= since, Payment.date <= until,
            Payment.status.in_(['paid', 'completed']),
        ).scalar()

        expenses = db.session.query(
            db.func.coalesce(db.func.sum(Expense.amount), 0)
        ).filter(Expense.date >= since, Expense.date <= until).scalar()

        overdue = db.session.query(
            db.func.coalesce(db.func.sum(Payment.amount), 0)
        ).filter(
            Payment.date < since,
            Payment.status.in_(['pending', 'overdue']),
        ).scalar()

        data['financial'] = {
            'income': float(income),
            'expenses': float(expenses),
            'net': float(income) - float(expenses),
            'overdue': float(overdue),
        }

        # Patients
        total_patients = UserModel.query.filter_by(role='jugador', is_active=True).count()
        sessions = Appointment.query.filter(
            Appointment.start_time >= since, Appointment.start_time <= until,
        ).count()
        completed = Appointment.query.filter(
            Appointment.start_time >= since, Appointment.start_time <= until,
            Appointment.status == 'completed',
        ).count()
        attended = Appointment.query.filter(
            Appointment.start_time >= since, Appointment.start_time <= until,
            Appointment.attendance == 'present',
        ).count()

        avg_accuracy = db.session.query(
            db.func.coalesce(db.func.avg(SessionMetrics.accurracy), 0)
        ).filter(SessionMetrics.date >= since, SessionMetrics.date <= until).scalar()

        data['patients'] = {
            'total': total_patients,
            'sessions': sessions,
            'completed': completed,
            'attended': attended,
            'attendance_rate': round(attended / sessions * 100, 1) if sessions > 0 else 0,
            'avg_accuracy': round(float(avg_accuracy), 1),
        }

        # Therapists
        therapists = UserModel.query.filter_by(role='terapista', is_active=True).all()
        ther_stats = []
        for t in therapists:
            t_sessions = Appointment.query.filter(
                Appointment.therapist_id == t.id,
                Appointment.start_time >= since, Appointment.start_time <= until,
            ).count()
            t_completed = Appointment.query.filter(
                Appointment.therapist_id == t.id,
                Appointment.start_time >= since, Appointment.start_time <= until,
                Appointment.status == 'completed',
            ).count()
            ther_stats.append({
                'name': t.username,
                'sessions': t_sessions,
                'completed': t_completed,
                'efficiency': round(t_completed / t_sessions * 100, 1) if t_sessions > 0 else 0,
            })
        ther_stats.sort(key=lambda x: x['efficiency'], reverse=True)
        data['therapists'] = ther_stats

        # Incidents
        data['incidents'] = {
            'total': Incidente.query.filter(Incidente.created_at >= since).count(),
            'open': Incidente.query.filter(Incidente.status.in_(['open', 'in_progress'])).count(),
        }

        # Audit
        avg_audit = db.session.query(
            db.func.coalesce(db.func.avg(SessionAudit.audit_score), 0)
        ).filter(SessionAudit.audited_at >= since).scalar()
        data['audit'] = {'avg_score': round(float(avg_audit), 1)}

    except Exception as e:
        logger.warning(f'Data gathering failed: {e}')

    return data


# ─── AI Report Generation ────────────────────────────────────────────────


def _generate_ai_report(data, period_type, user_role):
    """Generate AI-powered report summary."""
    try:
        from app.services.llm_client import llm_chat

        context_parts = []

        if data.get('financial'):
            fin = data['financial']
            context_parts.append(f"FINANZAS: Ingresos S/{fin['income']:.0f}, Gastos S/{fin['expenses']:.0f}, Utilidad neta S/{fin['net']:.0f}, Mora S/{fin['overdue']:.0f}")

        if data.get('patients'):
            pat = data['patients']
            context_parts.append(f"PACIENTES: {pat['total']} activos, {pat['sessions']} sesiones, {pat['completed']} completadas, Asistencia {pat['attendance_rate']}%, Precisión {pat['avg_accuracy']}%")

        if data.get('therapists'):
            top3 = data['therapists'][:3]
            top_str = ', '.join([f"{t['name']}({t['efficiency']}%)" for t in top3])
            context_parts.append(f"TERAPEUTAS: Top 3: {top_str}")

        if data.get('incidents'):
            inc = data['incidents']
            context_parts.append(f"INCIDENTES: {inc['total']} totales, {inc['open']} abiertos")

        if data.get('prev'):
            prev_fin = data['prev'].get('financial', {})
            curr_fin = data.get('financial', {})
            if prev_fin.get('income', 0) > 0:
                change = (curr_fin['income'] - prev_fin['income']) / prev_fin['income'] * 100
                context_parts.append(f"TENDENCIA: Ingresos {change:+.1f}% vs período anterior")

        if data.get('monthly_breakdown'):
            context_parts.append(f"MESES: {len(data['monthly_breakdown'])} meses de datos")

        context_text = '\n'.join(context_parts)

        period_label = {'semanal': 'semanal', 'mensual': 'mensual', 'anual': 'anual'}.get(period_type, period_type)

        prompt = f"""Eres el asistente ejecutivo del Centro Juan Pablo II.
Genera un reporte {period_label} detallado en español para un usuario con rol '{user_role}'.

DATOS DEL PERÍODO:
{context_text}

El reporte debe incluir:
1. Titular ejecutivo con período
2. Resumen financiero con análisis de tendencias
3. Rendimiento de pacientes (asistencia, precisión, progreso)
4. Ranking de terapeutas con eficiencia
5. Análisis de incidentes y seguridad
6. Predicciones y recomendaciones para el próximo período
7. Score BSC por perspectiva (1-10)
8. Datos descargables (JSON) para análisis externo

Responde SOLO con JSON:
{{"title": "📊 Reporte {period_label.title()} — Centro Juan Pablo II", "body": "resumen ejecutivo aquí (máx 20 líneas)", "highlights": ["punto 1", "punto 2", "punto 3", "punto 4"], "bsc_scores": {{"finance": 7, "patients": 8, "therapists": 6, "growth": 7}}, "recommendations": ["rec 1", "rec 2"], "data_export": {{"json": "datos para análisis"}}}}"""

        messages = [{'role': 'user', 'content': prompt}]
        content, provider = llm_chat(messages, temperature=0.3, max_tokens=800)

        result = json.loads(content.strip().strip('`').strip('json').strip())
        logger.info(f'{period_type.title()} report AI summary via {provider}')
        return result

    except Exception as e:
        logger.warning(f'AI report failed: {e}')
        return _fallback_report(data, period_type)


def _fallback_report(data, period_type):
    """Fallback report without AI."""
    parts = []
    if data.get('financial'):
        fin = data['financial']
        parts.append(f"Ingresos: S/{fin['income']:.0f}, Gastos: S/{fin['expenses']:.0f}")
    if data.get('patients'):
        pat = data['patients']
        parts.append(f"Pacientes: {pat['total']}, Asistencia: {pat['attendance_rate']}%")

    return {
        'title': f"📊 Reporte {period_type.title()} — {datetime.now().strftime('%d/%m/%Y')}",
        'body': '\n'.join(parts) if parts else 'Sin datos disponibles.',
        'highlights': [],
        'bsc_scores': {'finance': 5, 'patients': 5, 'therapists': 5, 'growth': 5},
        'recommendations': [],
    }


# ─── Report Builders ─────────────────────────────────────────────────────


def _build_report_text(user, ai_summary, data, period_type):
    """Build plain-text report for Telegram."""
    role_label = {'admin': 'Administrador', 'supervisor': 'Supervisor', 'terapista': 'Terapeuta', 'jugador': 'Paciente'}.get(user.role, user.role)

    lines = [
        ai_summary.get('title', f"📊 Reporte {period_type.title()}"),
        f"👤 {user.username} ({role_label})",
        f"📅 {datetime.now().strftime('%d/%m/%Y')}",
        '',
    ]

    # BSC
    bsc = ai_summary.get('bsc_scores', {})
    if bsc:
        lines.append('📊 *Balanced Scorecard:*')
        for key, label in [('finance', 'Finanzas'), ('patients', 'Pacientes'), ('therapists', 'Terapeutas'), ('growth', 'Crecimiento')]:
            s = bsc.get(key, 5)
            emoji = '🟢' if s >= 7 else '🟡' if s >= 5 else '🔴'
            lines.append(f'  {emoji} {label}: {s}/10')
        lines.append('')

    # Financial
    if data.get('financial'):
        fin = data['financial']
        lines.append('💰 *Finanzas:*')
        lines.append(f'  Ingresos: S/{fin["income"]:.0f}')
        lines.append(f'  Gastos: S/{fin["expenses"]:.0f}')
        lines.append(f'  Utilidad neta: S/{fin["net"]:.0f}')
        if fin.get('overdue', 0) > 0:
            lines.append(f'  Mora: S/{fin["overdue"]:.0f}')
        lines.append('')

    # Patients
    if data.get('patients'):
        pat = data['patients']
        lines.append('🏥 *Pacientes:*')
        lines.append(f'  Activos: {pat["total"]}')
        lines.append(f'  Sesiones: {pat["sessions"]} ({pat["completed"]} completadas)')
        lines.append(f'  Asistencia: {pat["attendance_rate"]}%')
        lines.append(f'  Precisión: {pat["avg_accuracy"]}%')
        lines.append('')

    # Therapists
    if data.get('therapists'):
        lines.append('👨‍⚕️ *Top Terapeutas:*')
        for t in data['therapists'][:5]:
            lines.append(f'  • {t["name"]}: {t["efficiency"]}% eficiencia')
        lines.append('')

    # Highlights
    highlights = ai_summary.get('highlights', [])
    if highlights:
        lines.append('🌟 *Destacado:*')
        for h in highlights:
            lines.append(f'• {h}')
        lines.append('')

    # Recommendations
    recs = ai_summary.get('recommendations', [])
    if recs:
        lines.append('💡 *Recomendaciones:*')
        for r in recs:
            lines.append(f'• {r}')
        lines.append('')

    lines.append('_Reporte generado por Chasqui 🦜_')

    return '\n'.join(lines)


def _build_report_html(user, ai_summary, data, period_type):
    """Build HTML report for email."""
    role_label = {'admin': 'Administrador', 'supervisor': 'Supervisor', 'terapista': 'Terapeuta', 'jugador': 'Paciente'}.get(user.role, user.role)
    bsc = ai_summary.get('bsc_scores', {})

    score_color = lambda s: '#10b981' if s >= 7 else '#f59e0b' if s >= 5 else '#ef4444'
    score_bg = lambda s: '#d1fae5' if s >= 7 else '#fef3c7' if s >= 5 else '#fee2e2'

    # BSC cards
    bsc_html = ''
    if bsc:
        cards = ''
        for key, label in [('finance', '💰 Finanzas'), ('patients', '🏥 Pacientes'), ('therapists', '👨‍⚕️ Terapeutas'), ('growth', '📈 Crecimiento')]:
            s = bsc.get(key, 5)
            cards += f'<div style="flex:1;min-width:100px;text-align:center;padding:12px;background:{score_bg(s)};border-radius:8px;"><div style="font-size:11px;color:#6b7280;">{label}</div><div style="font-size:24px;font-weight:700;color:{score_color(s)};">{s}/10</div></div>'
        bsc_html = f'<div style="background:white;border-radius:8px;padding:16px;margin-bottom:16px;border:1px solid #e5e7eb;"><h3 style="margin:0 0 12px;font-size:14px;">📊 Balanced Scorecard</h3><div style="display:flex;gap:12px;flex-wrap:wrap;">{cards}</div></div>'

    # Financial
    fin_html = ''
    if data.get('financial'):
        fin = data['financial']
        fin_html = f'<div style="background:white;border-radius:8px;padding:16px;margin-bottom:16px;border:1px solid #e5e7eb;"><h3 style="margin:0 0 12px;font-size:14px;">💰 Finanzas</h3><div style="display:flex;gap:12px;flex-wrap:wrap;"><div style="flex:1;min-width:100px;text-align:center;padding:10px;background:#f8f9fa;border-radius:6px;"><div style="font-size:20px;font-weight:700;color:#059669;">S/{fin["income"]:.0f}</div><div style="font-size:11px;color:#6b7280;">Ingresos</div></div><div style="flex:1;min-width:100px;text-align:center;padding:10px;background:#f8f9fa;border-radius:6px;"><div style="font-size:20px;font-weight:700;color:#ef4444;">S/{fin["expenses"]:.0f}</div><div style="font-size:11px;color:#6b7280;">Gastos</div></div><div style="flex:1;min-width:100px;text-align:center;padding:10px;background:#f8f9fa;border-radius:6px;"><div style="font-size:20px;font-weight:700;color:#2563eb;">S/{fin["net"]:.0f}</div><div style="font-size:11px;color:#6b7280;">Utilidad Neta</div></div></div></div>'

    # Therapists table
    ther_html = ''
    if data.get('therapists'):
        rows = ''
        for t in data['therapists'][:5]:
            eff_color = '#10b981' if t['efficiency'] >= 70 else '#f59e0b' if t['efficiency'] >= 50 else '#ef4444'
            rows += f'<tr><td style="padding:8px 12px;border-bottom:1px solid #eee;font-weight:600;">{t["name"]}</td><td style="padding:8px 12px;border-bottom:1px solid #eee;text-align:center;">{t["sessions"]}</td><td style="padding:8px 12px;border-bottom:1px solid #eee;text-align:center;">{t["completed"]}</td><td style="padding:8px 12px;border-bottom:1px solid #eee;text-align:center;color:{eff_color};font-weight:700;">{t["efficiency"]}%</td></tr>'
        ther_html = f'<div style="background:white;border-radius:8px;padding:16px;margin-bottom:16px;border:1px solid #e5e7eb;"><h3 style="margin:0 0 12px;font-size:14px;">👨‍⚕️ Terapeutas</h3><table style="width:100%;border-collapse:collapse;font-size:13px;"><thead><tr style="background:#f8f9fa;"><th style="padding:8px;text-align:left;">Nombre</th><th style="padding:8px;text-align:center;">Sesiones</th><th style="padding:8px;text-align:center;">Completadas</th><th style="padding:8px;text-align:center;">Eficiencia</th></tr></thead><tbody>{rows}</tbody></table></div>'

    # Highlights & Recommendations
    highlights = ai_summary.get('highlights', [])
    recs = ai_summary.get('recommendations', [])

    hl_html = ''
    if highlights:
        items = ''.join([f'<li style="margin:4px 0;">{h}</li>' for h in highlights])
        hl_html = f'<div style="background:white;border-radius:8px;padding:16px;margin-bottom:16px;border-left:4px solid #2563eb;"><h3 style="margin:0 0 8px;font-size:14px;color:#1e40af;">🌟 Destacado</h3><ul style="margin:0;padding-left:20px;font-size:13px;">{items}</ul></div>'

    rec_html = ''
    if recs:
        items = ''.join([f'<li style="margin:4px 0;">{r}</li>' for r in recs])
        rec_html = f'<div style="background:white;border-radius:8px;padding:16px;margin-bottom:16px;border-left:4px solid #059669;"><h3 style="margin:0 0 8px;font-size:14px;color:#047857;">💡 Recomendaciones</h3><ul style="margin:0;padding-left:20px;font-size:13px;">{items}</ul></div>'

    # Monthly breakdown (annual only)
    monthly_html = ''
    if data.get('monthly_breakdown'):
        rows = ''
        for m in data['monthly_breakdown']:
            rows += f'<tr><td style="padding:6px 12px;border-bottom:1px solid #eee;">{m["month"]}</td><td style="padding:6px 12px;border-bottom:1px solid #eee;text-align:right;">S/{m.get("financial", {}).get("income", 0):.0f}</td><td style="padding:6px 12px;border-bottom:1px solid #eee;text-align:right;">S/{m.get("financial", {}).get("expenses", 0):.0f}</td><td style="padding:6px 12px;border-bottom:1px solid #eee;text-align:right;">S/{m.get("financial", {}).get("net", 0):.0f}</td><td style="padding:6px 12px;border-bottom:1px solid #eee;text-align:center;">{m.get("patients", {}).get("sessions", 0)}</td></tr>'
        monthly_html = f'<div style="background:white;border-radius:8px;padding:16px;margin-bottom:16px;border:1px solid #e5e7eb;"><h3 style="margin:0 0 12px;font-size:14px;">📅 Desglose Mensual</h3><table style="width:100%;border-collapse:collapse;font-size:12px;"><thead><tr style="background:#f8f9fa;"><th style="padding:6px;text-align:left;">Mes</th><th style="padding:6px;text-align:right;">Ingresos</th><th style="padding:6px;text-align:right;">Gastos</th><th style="padding:6px;text-align:right;">Utilidad</th><th style="padding:6px;text-align:center;">Sesiones</th></tr></thead><tbody>{rows}</tbody></table></div>'

    return f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;max-width:700px;margin:0 auto;padding:20px;color:#1f2937;background:#f3f4f6;">
        <div style="background:linear-gradient(135deg,#1e3a5f,#2563eb);color:white;padding:24px;border-radius:12px 12px 0 0;">
            <h1 style="margin:0;font-size:20px;">{ai_summary.get('title', f'Reporte {period_type.title()}')}</h1>
            <p style="margin:8px 0 0;opacity:0.9;">{user.username} ({role_label}) · {datetime.now().strftime('%d/%m/%Y')}</p>
        </div>
        <div style="padding:20px;background:#f3f4f6;">
            {bsc_html}
            {fin_html}
            {ther_html}
            {hl_html}
            {rec_html}
            {monthly_html}
            <div style="text-align:center;padding:16px;font-size:12px;color:#9ca3af;">
                Reporte generado automáticamente por Chasqui 🦜 — Centro Juan Pablo II
            </div>
        </div>
    </body>
    </html>"""


# ─── Send Helpers ────────────────────────────────────────────────────────


def _send_report_telegram(user, text):
    """Send report via Telegram."""
    try:
        from app.services.telegram_bot_service import send_telegram_message
        bot_token = current_app.config.get('TELEGRAM_BOT_TOKEN')
        if not bot_token:
            return
        from app.models.telegram_user import TelegramUser
        tg_users = TelegramUser.query.filter_by(admin_user_id=user.id, is_linked=True, is_active=True).all()
        for tg in tg_users:
            send_telegram_message(tg.telegram_chat_id, text, bot_token)
            logger.info(f'Report sent via Telegram to user {user.id}')
    except Exception as e:
        logger.error(f'Telegram report failed for user {user.id}: {e}')


def _send_report_email(user, html, period_type):
    """Send report via email."""
    try:
        if not user.email:
            return
        from app.services.email_service import EmailService
        subject = f'📊 Reporte {period_type} — Centro Juan Pablo II ({datetime.now().strftime("%d/%m/%Y")})'
        EmailService.send_notification_email(subject=subject, recipients=[user.email], body=html)
        logger.info(f'Report sent via email to {user.email}')
    except Exception as e:
        logger.error(f'Email report failed for user {user.id}: {e}')


# ─── Data Export ─────────────────────────────────────────────────────────


def export_period_data(since, until, format='json'):
    """Export data for external analysis."""
    data = _gather_period_data(since, until, 'export')
    if format == 'csv':
        return _data_to_csv(data)
    return json.dumps(data, indent=2, default=str)


def _data_to_csv(data):
    """Convert data to CSV format."""
    output = io.StringIO()

    if data.get('financial'):
        writer = csv.writer(output)
        writer.writerow(['Metric', 'Value'])
        writer.writerow(['Income', data['financial']['income']])
        writer.writerow(['Expenses', data['financial']['expenses']])
        writer.writerow(['Net Profit', data['financial']['net']])
        writer.writerow(['Overdue', data['financial']['overdue']])

    return output.getvalue()
