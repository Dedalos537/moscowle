import os
import uuid
from datetime import datetime, timedelta

from flask import current_app, flash, jsonify, redirect, render_template, request, url_for
from sqlalchemy import func
from werkzeug.utils import secure_filename

from app.auth_compat import current_user, login_required
from app.extensions import csrf, db
from app.models import (
    Appointment,
    MonthlyReport,
    Payment,
    QuarterlyReport,
    SessionMetrics,
    User,
    db,
)
from app.routes.admin import admin_bp, finance_service, payment_service


@admin_bp.route('/reports')
@login_required
def reports():
    if current_user.role not in ('admin', 'supervisor'):
        flash('Acceso denegado.', 'error')
        return redirect(url_for('main.dashboard'))

    try:
        therapists = User.query.filter_by(role='terapista').all()
        t_rows = []
        for t in therapists:
            count_appts = Appointment.query.filter_by(therapist_id=t.id).count()
            try:
                avg_acc = (
                    db.session.query(func.avg(SessionMetrics.accurracy))
                    .join(Appointment, SessionMetrics.session_id == Appointment.id)
                    .filter(Appointment.therapist_id == t.id)
                    .scalar()
                    or 0
                )
            except Exception:
                avg_acc = 0
            t_rows.append(
                {'name': t.username, 'email': t.email, 'sessions': count_appts, 'avg_accuracy': round(avg_acc, 1)}
            )

        patients = User.query.filter_by(role='jugador').all()
        p_rows = []
        for p in patients:
            plays = SessionMetrics.query.filter_by(user_id=p.id).count()
            try:
                acc = db.session.query(func.avg(SessionMetrics.accurracy)).filter_by(user_id=p.id).scalar() or 0
            except Exception:
                acc = 0
            p_rows.append({'name': p.username, 'email': p.email, 'plays': plays, 'avg_accuracy': round(acc, 1)})

        try:
            financials = payment_service.get_financial_summary()
        except Exception as e:
            current_app.logger.warning(f'Failed to load financials: {e}')
            financials = {
                'income_real': 0.0,
                'income_expected': 0.0,
                'overdue_amount': 0.0,
                'overdue_users_count': 0,
                'expenses': 0.0,
                'net_profit': 0.0,
            }

        try:
            from sqlalchemy import func as sqlfunc

            from app.models import SessionAudit

            total_audits = SessionAudit.query.filter(SessionAudit.audit_score.isnot(None)).count()
            avg_score = (
                db.session.query(sqlfunc.avg(SessionAudit.audit_score))
                .filter(SessionAudit.audit_score.isnot(None))
                .scalar()
                or 0
            )

            recent_audits = (
                db.session.query(SessionAudit, Appointment, User)
                .join(Appointment, SessionAudit.appointment_id == Appointment.id)
                .join(User, Appointment.therapist_id == User.id)
                .filter(SessionAudit.audit_score.isnot(None))
                .order_by(SessionAudit.audited_at.desc())
                .limit(20)
                .all()
            )

            audit_rows = []
            for audit, appt, therapist in recent_audits:
                patient = User.query.get(appt.patient_id)
                audit_rows.append(
                    {
                        'id': audit.id,
                        'therapist': therapist.username,
                        'patient': patient.username if patient else 'N/A',
                        'date': appt.start_time.strftime('%d/%m/%Y') if appt.start_time else 'N/A',
                        'score': round(audit.audit_score, 1) if audit.audit_score else 0,
                        'status': audit.audit_status,
                    }
                )

            therapist_scores = (
                db.session.query(
                    User.username,
                    sqlfunc.avg(SessionAudit.audit_score).label('avg_score'),
                    sqlfunc.count(SessionAudit.id).label('count'),
                )
                .join(Appointment, SessionAudit.appointment_id == Appointment.id)
                .join(User, Appointment.therapist_id == User.id)
                .filter(SessionAudit.audit_score.isnot(None))
                .group_by(User.id)
                .all()
            )

            audit_stats = {
                'total': total_audits,
                'avg_score': round(avg_score, 1),
                'recent': audit_rows,
                'by_therapist': [{'name': t[0], 'avg_score': round(t[1], 1), 'count': t[2]} for t in therapist_scores],
            }
        except Exception as e:
            current_app.logger.warning(f'Failed to load audit stats: {e}')
            audit_stats = {'total': 0, 'avg_score': 0, 'recent': [], 'by_therapist': []}

        return render_template(
            'admin/reports.html',
            therapists=t_rows,
            patients=p_rows,
            financials=financials,
            audit_stats=audit_stats,
            active_page='admin_reports',
        )
    except Exception as e:
        current_app.logger.error(f'Error in admin/reports: {e}')
        import traceback

        traceback.print_exc()
        flash(f'Error generando reportes: {str(e)}', 'error')
        return render_template(
            'admin/reports.html',
            therapists=[],
            patients=[],
            financials={'income_real': 0, 'income_expected': 0, 'overdue_amount': 0, 'overdue_users_count': 0},
            active_page='admin_reports',
        )


@admin_bp.route('/generate-ia-report', methods=['POST'])
@login_required
def generate_ia_report():
    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        from datetime import datetime, timedelta

        from sqlalchemy import func

        from app.services.financial_service import FinancialService
        from app.services.llm_automation_service import generate_weekly_report

        now = datetime.now()
        thirty_days_ago = now - timedelta(days=30)
        first_of_month = now.replace(day=1)

        total_therapists = User.query.filter_by(role='terapista', is_active=True).count()
        total_patients = User.query.filter_by(role='jugador', is_active=True).count()
        total_sessions = Appointment.query.filter(Appointment.status == 'completed').count()
        sessions_this_month = Appointment.query.filter(
            Appointment.status == 'completed', Appointment.updated_at >= first_of_month
        ).count()

        recent_payments = Payment.query.filter(Payment.date >= thirty_days_ago).all()
        total_income = sum((p.amount or 0) - (p.discount or 0) for p in recent_payments)

        total_expenses = 0
        try:
            from app.models import Expense

            recent_expenses = Expense.query.filter(Expense.date >= thirty_days_ago).all()
            total_expenses = sum((e.amount or 0) for e in recent_expenses)
        except ImportError:
            pass

        fs = FinancialService()
        debt_data = fs.build_debt_report(days_ahead=7, month='all')
        total_debt = debt_data.get('total_deuda', 0)
        total_debtors = debt_data.get('total_pacientes', 0)

        top_therapists = (
            db.session.query(User.username, func.count(Appointment.id).label('session_count'))
            .join(Appointment, Appointment.therapist_id == User.id)
            .filter(Appointment.status == 'completed')
            .group_by(User.id)
            .order_by(func.count(Appointment.id).desc())
            .limit(5)
            .all()
        )

        sessions = (
            Appointment.query.filter(Appointment.status == 'completed')
            .order_by(Appointment.updated_at.desc())
            .limit(10)
            .all()
        )
        session_data = [
            {
                'notes': s.notes,
                'patient': s.patient.username if s.patient else '—',
                'therapist': s.therapist.username if s.therapist else '—',
            }
            for s in sessions
            if s.notes
        ]

        data_for_ai = {
            'period': f'Reporte Estratégico {now.strftime("%d/%m/%Y")}',
            'general': {
                'therapists': total_therapists,
                'patients': total_patients,
                'total_sessions': total_sessions,
                'sessions_this_month': sessions_this_month,
            },
            'financial': {
                'total_debt': total_debt,
                'total_debtors': total_debtors,
                'income_last_30d': total_income,
                'total_expenses': total_expenses,
            },
            'top_therapists': [{'name': t.username, 'sessions': t.session_count} for t in top_therapists],
            'recent_session_notes': session_data,
        }

        try:
            report_md = generate_weekly_report(data_for_ai)
        except Exception as llm_err:
            current_app.logger.warning(f'LLM report generation failed, using fallback: {llm_err}')
            report_md = (
                f'# Reporte Estrategico - {now.strftime("%d/%m/%Y")}\n\n'
                f'## Resumen General\n'
                f'- Terapeutas activos: {total_therapists}\n'
                f'- Pacientes activos: {total_patients}\n'
                f'- Sesiones totales: {total_sessions}\n'
                f'- Sesiones este mes: {sessions_this_month}\n\n'
                f'## Financiero\n'
                f'- Ingresos (30 dias): S/ {total_income:.2f}\n'
                f'- Gastos (30 dias): S/ {total_expenses:.2f}\n'
                f'- Deuda total: S/ {total_debt:.2f}\n'
                f'- Deudores: {total_debtors}\n\n'
                f'## Top Terapeutas\n'
            )
            for t in top_therapists:
                report_md += f'- {t.username}: {t.session_count} sesiones\n'
            if session_data:
                report_md += '\n## Notas de Sesiones Recientes\n'
                for s in session_data:
                    report_md += f'- {s["patient"]} ({s["therapist"]}): {s["notes"][:100]}...\n'
        return jsonify({'success': True, 'report': report_md})
    except Exception as e:
        import traceback

        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/ai-chat-process', methods=['POST'])
@login_required
def ai_chat_process():
    """Chatbot Llama"""
    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'error': 'Unauthorized'}), 403

    if 'file' in request.files:
        file = request.files['file']
        if file:
            filename = secure_filename(f'chat_vc_{uuid.uuid4().hex}_{file.filename}')
            upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'receipts', filename)
            os.makedirs(os.path.dirname(upload_path), exist_ok=True)
            file.save(upload_path)

            try:
                from app.services.llm_automation_service import analyze_receipt_image

                ocr_out = analyze_receipt_image(upload_path)
                p = User.query.filter(
                    User.username.ilike(f'%{ocr_out.get("sender_name", "")}%'), User.role == 'jugador'
                ).first()

                msg = f'Leído: S/ {ocr_out.get("amount")} de {ocr_out.get("sender_name")}.\n'
                if p:
                    msg += f'Es {p.username}. ¿Confirmamos?'
                    return jsonify(
                        {
                            'response': msg,
                            'status': 'success',
                            'action': 'confirm_payment',
                            'params': {'patient_id': p.id, 'amount': ocr_out.get('amount'), 'path': upload_path},
                        }
                    )
                return jsonify({'response': msg + '¿De qué paciente es?', 'status': 'info'})
            except:
                return jsonify({'response': 'No entendí el voucher, ¿me dictas?', 'status': 'warning'})

    data = request.get_json() or {}
    msg_user = data.get('message', '')
    context = {'page': request.referrer or 'dashboard'}

    try:
        from app.services.llm_automation_service import process_chat_command
        from app.services.notification_service import NotificationService

        notif_service = NotificationService()

        result = process_chat_command(current_user.id, msg_user, context)

        intent = result.get('intent', 'general_chat')
        params = result.get('parameters', {})
        friendly = result.get('friendly_response', '¡Claro que sí! ')

        if intent == 'register_payment':
            p_name = params.get('patient_name')
            amt = params.get('amount')
            if not p_name or not amt:
                return jsonify({'response': friendly, 'status': 'info'})

            p = User.query.filter(User.username.ilike(f'%{p_name}%'), User.role == 'jugador').first()
            if not p:
                return jsonify({'response': f'No encontré a {p_name}.', 'status': 'warning'})

            payment_service.register_payment(
                patient_id=p.id,
                amount=float(amt),
                method='IA/Llama',
                reference='Chatbot',
                next_due_date_str=(datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
            )

            notif_service.create_notification(
                current_user.id,
                f' Llama: Registré pago de S/ {amt} para {p.username}.',
                url_for('admin.payment_history', user_id=p.id),
            )
            return jsonify(
                {'response': friendly, 'status': 'success', 'redirect': url_for('admin.payment_history', user_id=p.id)}
            )

        elif intent == 'register_expense':
            amt = params.get('amount')
            desc = params.get('description', 'Gasto vía Llama')
            cat = params.get('category', 'operativo')
            if not amt:
                return jsonify({'response': friendly, 'status': 'info'})

            finance_service.create_expense(
                {
                    'category': cat,
                    'amount': float(amt),
                    'date': datetime.now().strftime('%Y-%m-%d'),
                    'description': desc,
                    'method': 'IA/Chat',
                }
            )

            notif_service.create_notification(
                current_user.id, f' Llama: Registré un nuevo gasto de S/ {amt} ({cat}).', url_for('admin.expenses')
            )
            return jsonify({'response': friendly, 'status': 'success', 'redirect': url_for('admin.expenses')})

        elif intent == 'mark_attendance':
            p_name = params.get('patient_name')
            p = User.query.filter(User.username.ilike(f'%{p_name}%')).first()
            if p:
                apt = (
                    Appointment.query.filter_by(patient_id=p.id, status='scheduled')
                    .filter(func.date(Appointment.start_time) == datetime.now().date())
                    .first()
                )
                if apt:
                    apt.status = 'completed'
                    db.session.commit()
                    notif_service.create_notification(
                        current_user.id, f' Llama: Marqué asistencia para {p.username}.', url_for('admin.sessions_page')
                    )
                    return jsonify({'response': friendly, 'status': 'success'})
            return jsonify({'response': f'No hay citas hoy de {p_name}.', 'status': 'warning'})

        elif intent == 'navigate':
            dest = params.get('destination', '').lower()
            target_url = url_for('admin.dashboard')
            if 'pago' in dest or 'deuda' in dest:
                target_url = url_for('admin.deudores_page')
            elif 'gasto' in dest:
                target_url = url_for('admin.expenses')
            elif 'usuario' in dest:
                target_url = url_for('admin.users')

            notif_service.create_notification(current_user.id, f' Llama: Te estoy llevando a {dest}.', link=target_url)
            return jsonify({'response': friendly, 'status': 'info', 'redirect': target_url})

        return jsonify({'response': friendly, 'status': 'info'})

    except Exception as e:
        return jsonify({'response': f'Ups: {str(e)}', 'status': 'error'})


@admin_bp.route('/reports/send-weekly-summary', methods=['POST'])
@login_required
def send_weekly_summary_manual():
    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        from app.tasks import check_upcoming_payments

        app = current_app._get_current_object()

        check_upcoming_payments(app, force=True)

        return jsonify({'success': True, 'message': 'Reporte semanal enviado al admin.'})
    except Exception as e:
        current_app.logger.error(f'Manual report error: {e}')
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/reports/export-payments')
@login_required
def export_payments_csv():
    if current_user.role not in ('admin', 'supervisor'):
        return redirect(url_for('main.dashboard'))

    import csv
    from io import StringIO

    from flask import make_response

    today = datetime.utcnow().date()
    start_date = today.replace(day=1)

    payments = Payment.query.filter(Payment.date >= start_date).order_by(Payment.date.desc()).all()

    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['ID', 'Paciente', 'Monto', 'Descuento', 'Metodo', 'Referencia', 'Fecha', 'Notas'])

    for p in payments:
        patient_name = p.patient.username if p.patient else 'Unknown'
        cw.writerow(
            [
                p.id,
                patient_name,
                p.amount,
                p.discount,
                p.method,
                p.reference,
                p.date.strftime('%Y-%m-%d %H:%M'),
                p.notes,
            ]
        )

    output = make_response(si.getvalue())
    output.headers['Content-Disposition'] = f'attachment; filename=pagos_{today.strftime("%Y_%m")}.csv'
    output.headers['Content-type'] = 'text/csv'
    return output


@admin_bp.route('/deudores')
@login_required
def deudores_page():
    if current_user.role not in ('admin', 'supervisor'):
        flash('Acceso denegado.', 'error')
        return redirect(url_for('main.dashboard'))
    return render_template('admin/deudores.html', active_page='admin_deudores')


@admin_bp.route('/api/daily-reports', methods=['GET'])
@login_required
def api_daily_reports():

    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'error': 'Unauthorized'}), 403

    start = request.args.get('start')
    end = request.args.get('end')

    if not start or not end:
        today = datetime.utcnow().date()
        start = start or today.isoformat()
        end = end or today.isoformat()

    try:
        from app.services.report_service import ReportService

        rs = ReportService()
        reports = rs.get_daily_reports(start, end)
        return jsonify({'success': True, 'data': reports})
    except Exception as e:
        current_app.logger.error(f'Error fetching daily reports: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/api/weekly-summary', methods=['GET'])
@login_required
def api_weekly_summary():

    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'error': 'Unauthorized'}), 403

    week_start = request.args.get('week_start')
    if not week_start:
        today = datetime.utcnow().date()
        week_start = (today - timedelta(days=today.weekday())).isoformat()

    try:
        from app.services.report_service import ReportService

        rs = ReportService()
        summary = rs.get_weekly_summary(week_start)
        return jsonify({'success': True, 'data': summary})
    except Exception as e:
        current_app.logger.error(f'Error fetching weekly summary: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/api/reports/accumulate', methods=['POST'])
@csrf.exempt
@login_required
def api_accumulate_reports():
    """Acumular reportes diarios"""
    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'error': 'Unauthorized'}), 403

    report_date = request.args.get('date')

    from app.services.report_service import ReportService

    rs = ReportService()

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    if report_date:
        try:
            today_start = datetime.strptime(report_date, '%Y-%m-%d')
        except:
            pass

    tomorrow = today_start + timedelta(days=1)

    therapists = User.query.filter_by(role='terapista', is_active=True).all()
    accumulated = 0

    for therapist in therapists:
        patients = therapist.associated_patients.filter_by(role='jugador').all()
        for patient in patients:
            has_sessions = Appointment.query.filter(
                Appointment.patient_id == patient.id,
                Appointment.therapist_id == therapist.id,
                Appointment.start_time >= today_start,
                Appointment.start_time < tomorrow,
                Appointment.status == 'completed',
            ).count()

            if has_sessions > 0:
                rs.generate_daily_report(patient.id, therapist.id, today_start.strftime('%Y-%m-%d'))
                accumulated += 1

    return jsonify(
        {
            'success': True,
            'message': f'Reportes acumulados para {accumulated} pacientes',
            'date': today_start.strftime('%Y-%m-%d'),
        }
    )


@admin_bp.route('/api/reports/monthly', methods=['GET'])
@login_required
def api_monthly_reports():
    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'error': 'Unauthorized'}), 403

    year = request.args.get('year', type=int, default=datetime.utcnow().year)
    month = request.args.get('month', type=int, default=datetime.utcnow().month)

    from app.services.report_service import ReportService

    rs = ReportService()
    summary = rs.get_monthly_summary(year, month)
    return jsonify({'success': True, 'summary': summary})


@admin_bp.route('/api/reports/quarterly', methods=['GET'])
@login_required
def api_quarterly_reports():
    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'error': 'Unauthorized'}), 403

    year = request.args.get('year', type=int, default=datetime.utcnow().year)
    quarter = request.args.get('quarter', type=int, default=(datetime.utcnow().month - 1) // 3 + 1)

    from app.services.report_service import ReportService

    rs = ReportService()
    summary = rs.get_quarterly_summary(year, quarter)
    return jsonify({'success': True, 'summary': summary})


@admin_bp.route('/api/reports/generate-all-weekly', methods=['POST'])
@csrf.exempt
@login_required
def api_generate_all_weekly():
    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'error': 'Unauthorized'}), 403

    week_start = request.args.get('week_start')
    from app.services.report_service import ReportService

    rs = ReportService()
    generated = rs.generate_all_weekly_reports(week_start)

    from app.models import Notification

    admin_users = User.query.filter_by(role='admin').all()
    for admin in admin_users:
        notif = Notification(
            user_id=admin.id,
            title='Reportes Semanales Generados',
            message=f'Se generaron {len(generated)} reportes semanales automaticamente.',
            type='reportes',
        )
        db.session.add(notif)
    db.session.commit()

    return jsonify(
        {'success': True, 'message': f'{len(generated)} reportes semanales generados', 'count': len(generated)}
    )


@admin_bp.route('/api/reports/generate-monthly', methods=['POST'])
@login_required
def api_generate_monthly():
    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'error': 'Unauthorized'}), 403

    year = request.args.get('year', type=int, default=datetime.utcnow().year)
    month = request.args.get('month', type=int, default=datetime.utcnow().month)

    from app.services.report_service import ReportService

    rs = ReportService()
    generated = rs.generate_all_monthly_reports(year, month)

    return jsonify(
        {'success': True, 'message': f'{len(generated)} reportes mensuales generados', 'count': len(generated)}
    )


@admin_bp.route('/api/reports/generate-quarterly', methods=['POST'])
@login_required
def api_generate_quarterly():
    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'error': 'Unauthorized'}), 403

    year = request.args.get('year', type=int, default=datetime.utcnow().year)
    quarter = request.args.get('quarter', type=int, default=(datetime.utcnow().month - 1) // 3 + 1)

    from app.services.report_service import ReportService

    rs = ReportService()
    generated = rs.generate_all_quarterly_reports(year, quarter)

    return jsonify(
        {'success': True, 'message': f'{len(generated)} reportes trimestrales generados', 'count': len(generated)}
    )


@admin_bp.route('/api/reports/patient-monthly/<int:patient_id>', methods=['GET'])
@login_required
def api_patient_monthly_reports(patient_id):
    if current_user.role not in ('admin', 'terapista', 'supervisor'):
        return jsonify({'error': 'Unauthorized'}), 403

    if current_user.role == 'terapista':
        if patient_id not in [p.id for p in current_user.associated_patients]:
            return jsonify({'error': 'Paciente no asignado'}), 403

    reports = (
        MonthlyReport.query.filter_by(patient_id=patient_id)
        .order_by(MonthlyReport.year.desc(), MonthlyReport.month.desc())
        .all()
    )
    return jsonify(
        {
            'success': True,
            'reports': [
                {
                    'id': r.id,
                    'month': r.month,
                    'year': r.year,
                    'sessions_count': r.sessions_count,
                    'avg_score': r.avg_score,
                    'objectives_achieved': r.objectives_achieved,
                    'objectives_total': r.objectives_total,
                    'report_text': r.report_text,
                    'created_at': r.created_at.isoformat(),
                }
                for r in reports
            ],
        }
    )


@admin_bp.route('/api/reports/patient-quarterly/<int:patient_id>', methods=['GET'])
@login_required
def api_patient_quarterly_reports(patient_id):
    if current_user.role not in ('admin', 'terapista', 'supervisor'):
        return jsonify({'error': 'Unauthorized'}), 403

    if current_user.role == 'terapista':
        if patient_id not in [p.id for p in current_user.associated_patients]:
            return jsonify({'error': 'Paciente no asignado'}), 403

    reports = (
        QuarterlyReport.query.filter_by(patient_id=patient_id)
        .order_by(QuarterlyReport.year.desc(), QuarterlyReport.quarter.desc())
        .all()
    )
    return jsonify(
        {
            'success': True,
            'reports': [
                {
                    'id': r.id,
                    'quarter': r.quarter,
                    'year': r.year,
                    'sessions_count': r.sessions_count,
                    'avg_score': r.avg_score,
                    'objectives_achieved': r.objectives_achieved,
                    'objectives_total': r.objectives_total,
                    'report_text': r.report_text,
                    'created_at': r.created_at.isoformat(),
                }
                for r in reports
            ],
        }
    )
