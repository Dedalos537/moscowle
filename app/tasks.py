from datetime import datetime, timedelta

from flask import current_app

from app.extensions import db, scheduler
from app.models import Appointment, User
from app.services.email_service import EmailService


def _wrap(f):
    """Wrap a task function so it runs inside an app context.
    The function receives no arguments; use current_app internally.
    """

    def wrapper():
        with current_app.app_context():
            try:
                f()
            except Exception as e:
                print(f'Scheduler task {f.__name__} failed: {e}')

    wrapper.__name__ = f.__name__
    return wrapper


def check_session_attendance(app):
    """
    Check for sessions that have finished but are still pending attendance.
    Mark them as attended/completed automatically.
    """
    with app.app_context():
        try:
            now = datetime.now()
            cutoff = now - timedelta(minutes=15)

            pending_sessions = Appointment.query.filter(
                Appointment.end_time < cutoff, Appointment.attendance == 'pending', Appointment.status != 'cancelled'
            ).all()

            count = 0
            for session in pending_sessions:
                session.attendance = 'present'
                if session.status == 'scheduled':
                    session.status = 'completed'
                    session.status_changed_at = now

                patient = User.query.get(session.patient_id)
                if patient:
                    patient.sessions_attended = (getattr(patient, 'sessions_attended', 0) or 0) + 1

                    if getattr(patient, 'plan_sessions', 0) > 0:
                        patient.plan_sessions -= 1

                        if patient.plan_sessions <= 0:
                            patient.financial_status = 'deudor'
                count += 1

            if count > 0:
                db.session.commit()
                print(f'Auto-marked {count} sessions as attended.')

        except Exception as e:
            db.session.rollback()
            print(f'Error in check_session_attendance: {e}')


from app.services.automation.renewal_service import auto_generate_billing_reminder
from app.services.financial_service import FinancialService


def check_upcoming_payments(app, force=False):
    """
    Check for payments due in the next 7 days or overdue.
    Sends a detailed summary email to the admin grouped by Sede.
    """
    if not force:
        try:
            auto_generate_billing_reminder(app)
            print('Detailed renewal emails processed.')
        except Exception as e:
            print(f'Error in auto_generate_billing_reminder: {e}')

    with app.app_context():
        try:
            from app.models import User

            fs = FinancialService()
            report = fs.build_debt_report(days_ahead=7)

            email_report = {}
            for sede_id, sede_data in report.get('por_sede', {}).items():
                sede_name = sede_data.get('sede_name', f'Sede {sede_id}')
                email_report[sede_name] = {'overdue': [], 'upcoming': [], 'uptodate': []}

                for d in sede_data.get('deudores', []):
                    p_info = fs.get_patient_overdue_info(d['id']) or {}

                    item = {
                        'name': d['paciente'],
                        'phone': p_info.get('phone', 'N/A'),
                        'amount': d['monto'],
                        'days_diff': d['dias_adeudo']
                        if d['estado'] == 'vencido'
                        else (
                            datetime.strptime(d['fecha_vencimiento'], '%Y-%m-%d').date() - datetime.utcnow().date()
                        ).days,
                        'due_date': d['fecha_vencimiento'],
                        'last_payment': 'N/A',
                    }

                    if d['estado'] == 'vencido':
                        email_report[sede_name]['overdue'].append(item)
                    else:
                        email_report[sede_name]['upcoming'].append(item)

            has_alerts = any(len(s['overdue']) > 0 or len(s['upcoming']) > 0 for s in email_report.values())

            admin = User.query.filter_by(role='admin').first()
            if not admin or not admin.email:
                print('No admin email found for reports.')
                return

            if has_alerts or force:
                EmailService.send_admin_payment_report_v2(admin.email, email_report)
                print(f'Enhanced payment report sent to {admin.email} (Force={force})')

        except Exception as e:
            print(f'Error in check_upcoming_payments: {e}')
            import traceback

            traceback.print_exc()


def run_daily_audits(app):
    """
    Run automated audits for all sessions completed today
    that have both a program and transcript but haven't been audited yet.
    """
    with app.app_context():
        try:
            from app.models import SessionAudit
            from app.services.audit_service import run_audit

            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = datetime.now().replace(hour=23, minute=59, second=59)

            pending_audits = (
                db.session.query(SessionAudit)
                .join(Appointment, SessionAudit.appointment_id == Appointment.id)
                .filter(
                    Appointment.start_time >= today_start,
                    Appointment.start_time <= today_end,
                    SessionAudit.planned_text.isnot(None),
                    SessionAudit.transcript_text.isnot(None),
                    SessionAudit.audit_status == 'pending',
                )
                .all()
            )

            count = 0
            for audit in pending_audits:
                try:
                    run_audit(audit.appointment_id)
                    count += 1
                except Exception as e:
                    audit.audit_status = 'error'
                    print(f'Audit failed for session {audit.appointment_id}: {e}')

            if count > 0:
                db.session.commit()
                print(f'Daily audit: {count} sessions audited automatically')

        except Exception as e:
            db.session.rollback()
            print(f'Error in run_daily_audits: {e}')


def generate_weekly_reports(app):
    """Auto-generate weekly reports for all therapists/patients on Saturday."""
    with app.app_context():
        try:
            from app.services.report_service import ReportService

            rs = ReportService()
            week_start, week_end = rs.get_this_week_range()
            generated = rs.generate_all_weekly_reports(week_start)

            from app.models import Notification

            admin_users = User.query.filter_by(role='admin').all()
            for admin in admin_users:
                notif = Notification(
                    user_id=admin.id,
                    title='Reportes Semanales Listos',
                    message=f'Se generaron {len(generated)} reportes semanales del {week_start.strftime("%d/%m")} al {week_end.strftime("%d/%m")}.',
                    type='reportes',
                )
                db.session.add(notif)

            therapists = User.query.filter_by(role='terapista', is_active=True).all()
            for therapist in therapists:
                patient_count = therapist.associated_patients.filter_by(role='jugador').count()
                if patient_count > 0:
                    notif = Notification(
                        user_id=therapist.id,
                        title='Reporte Semanal Disponible',
                        message=f'Tus reportes semanales del {week_start.strftime("%d/%m")} al {week_end.strftime("%d/%m")} ya estan listos. Revisalos en tu panel.',
                        type='reportes',
                    )
                    db.session.add(notif)

            db.session.commit()
            print(f'Weekly reports: {len(generated)} generated for week {week_start} - {week_end}')
        except Exception as e:
            db.session.rollback()
            print(f'Error in generate_weekly_reports: {e}')


def generate_monthly_reports(app):
    """Auto-generate monthly reports on the 1st of each month."""
    with app.app_context():
        try:
            from datetime import date

            from app.models import Notification
            from app.services.report_service import ReportService

            rs = ReportService()
            today = date.today()
            year = today.year
            month = today.month
            if month == 1:
                month = 12
                year -= 1
            else:
                month -= 1
            generated = rs.generate_all_monthly_reports(year, month)
            month_name = {
                1: 'Enero',
                2: 'Febrero',
                3: 'Marzo',
                4: 'Abril',
                5: 'Mayo',
                6: 'Junio',
                7: 'Julio',
                8: 'Agosto',
                9: 'Setiembre',
                10: 'Octubre',
                11: 'Noviembre',
                12: 'Diciembre',
            }.get(month, str(month))
            admin_users = User.query.filter_by(role='admin').all()
            for admin in admin_users:
                notif = Notification(
                    user_id=admin.id,
                    title='Reportes Mensuales Listos',
                    message=f'Se generaron {len(generated)} reportes mensuales de {month_name} {year}.',
                    type='reportes',
                )
                db.session.add(notif)
            db.session.commit()
            print(f'Monthly reports: {len(generated)} generated for {month_name} {year}')
        except Exception as e:
            db.session.rollback()
            print(f'Error in generate_monthly_reports: {e}')


def generate_quarterly_reports(app):
    """Auto-generate quarterly reports on Jan 1, Apr 1, Jul 1, Oct 1."""
    with app.app_context():
        try:
            from app.models import Notification
            from app.services.report_service import ReportService

            rs = ReportService()
            today = datetime.now()
            current_quarter = (today.month - 1) // 3 + 1
            year = today.year
            prev_quarter = current_quarter - 1
            if prev_quarter == 0:
                prev_quarter = 4
                year -= 1
            generated = rs.generate_all_quarterly_reports(year, prev_quarter)
            admin_users = User.query.filter_by(role='admin').all()
            for admin in admin_users:
                notif = Notification(
                    user_id=admin.id,
                    title='Reportes Trimestrales Listos',
                    message=f'Se generaron {len(generated)} reportes trimestrales del Q{prev_quarter} {year}.',
                    type='reportes',
                )
                db.session.add(notif)
            db.session.commit()
            print(f'Quarterly reports: {len(generated)} generated for Q{prev_quarter} {year}')
        except Exception as e:
            db.session.rollback()
            print(f'Error in generate_quarterly_reports: {e}')


def run_daily_backup(app):
    """Run database backup to JSON daily."""
    with app.app_context():
        try:
            from app.services.backup_service import run_backup

            filepath = run_backup()
            print(f'Daily backup completed: {filepath}')
        except Exception as e:
            print(f'Error in run_daily_backup: {e}')
            import traceback

            traceback.print_exc()


def run_notification_cleanup(app):
    """Delete read notifications older than 30 days."""
    with app.app_context():
        try:
            from app.repositories.notification_repository import NotificationRepository

            repo = NotificationRepository()
            repo.delete_old_read(days=30)
            print('Notification cleanup completed.')
        except Exception as e:
            print(f'Error in run_notification_cleanup: {e}')


def send_whatsapp_debt_reminders(app):
    """Send WhatsApp reminders for overdue installments (daily at 9am)."""
    with app.app_context():
        try:
            from app.services.contract_service import ContractService
            from app.services.whatsapp_service import whatsapp_service

            cs = ContractService()
            due = cs.get_due_installments()
            sent = 0
            for inst in due:
                if not inst['patient_phone']:
                    continue
                if inst['reminder_sent'] and inst['days_overdue'] % 7 != 0:
                    continue

                result = whatsapp_service.send_installment_reminder(
                    patient_name=inst['patient_name'],
                    patient_phone=inst['patient_phone'],
                    installment_number=inst['number'],
                    due_date=inst['due_date'],
                    amount=inst['remaining'],
                    days_overdue=inst['days_overdue'],
                )
                if result.get('sent'):
                    from app.models.contract import Installment

                    installment = Installment.query.get(inst['installment_id'])
                    if installment:
                        installment.reminder_sent = True
                        db.session.commit()
                    sent += 1

            print(f'WhatsApp reminders: {sent} sent, {len(due)} due')
        except Exception as e:
            print(f'Error in send_whatsapp_debt_reminders: {e}')
            import traceback

            traceback.print_exc()


def init_scheduler(app):
    scheduler.add_job(func=lambda: check_upcoming_payments(app), trigger='cron', hour=8, minute=0)

    scheduler.add_job(func=lambda: check_session_attendance(app), trigger='interval', minutes=30)

    scheduler.add_job(func=lambda: run_daily_audits(app), trigger='cron', hour=23, minute=0)

    scheduler.add_job(func=lambda: run_daily_backup(app), trigger='cron', hour=3, minute=0)

    scheduler.add_job(func=lambda: generate_weekly_reports(app), trigger='cron', day_of_week='sat', hour=20, minute=0)

    scheduler.add_job(func=lambda: generate_monthly_reports(app), trigger='cron', day=1, hour=21, minute=0)

    scheduler.add_job(
        func=lambda: generate_quarterly_reports(app), trigger='cron', month='1,4,7,10', day=1, hour=22, minute=0
    )

    scheduler.add_job(func=lambda: run_notification_cleanup(app), trigger='cron', day_of_week='sun', hour=4, minute=0)

    scheduler.add_job(
        func=lambda: send_whatsapp_debt_reminders(app), trigger='cron', hour=9, minute=0, id='whatsapp_cobranza'
    )

    scheduler.start()
