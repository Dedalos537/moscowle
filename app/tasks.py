from datetime import datetime, timedelta
from app.extensions import db, scheduler
from app.models import User, Appointment
from app.services.email_service import EmailService
from flask import current_app

def check_session_attendance(app):
    """
    Check for sessions that have finished but are still pending attendance.
    Mark them as attended/completed automatically.
    """
    with app.app_context():
        try:
            now = datetime.now()
            # Threshold: Session ended 15 mins ago to be safe
            cutoff = now - timedelta(minutes=15)
            
            # Find appointments: 
            # - Ended before cutoff
            # - Attendance is 'pending'
            # - Status is not 'cancelled'
            pending_sessions = Appointment.query.filter(
                Appointment.end_time < cutoff,
                Appointment.attendance == 'pending',
                Appointment.status != 'cancelled'
            ).all()
            


            count = 0
            for session in pending_sessions:
                # Poka-Yoke Automation: Auto-mark as present
                session.attendance = 'present'
                if session.status == 'scheduled':
                    session.status = 'completed'
                    session.status_changed_at = now
                
                patient = User.query.get(session.patient_id)
                if patient:
                    # Increment attended sessions
                    patient.sessions_attended = (getattr(patient, 'sessions_attended', 0) or 0) + 1
                    
                    # Deduct from plan (Bonus Tracking)
                    if getattr(patient, 'plan_sessions', 0) > 0:
                        patient.plan_sessions -= 1
                        
                        # Phase 3 Automations: If plan runs out, set status to debtor
                        if patient.plan_sessions <= 0:
                            patient.financial_status = 'deudor'
                count += 1


            
            if count > 0:
                db.session.commit()
                print(f"Auto-marked {count} sessions as attended.")
                
        except Exception as e:
            db.session.rollback()
            print(f"Error in check_session_attendance: {e}")

from app.services.automation.renewal_service import auto_generate_billing_reminder
from app.models import Payment, Sede
from sqlalchemy import func
from app.services.financial_service import FinancialService

def check_upcoming_payments(app, force=False):
    """
    Check for payments due in the next 7 days or overdue.
    Sends a detailed summary email to the admin grouped by Sede.
    """
    # 1. Trigger specialized client renewal emails (Frontend 2.0 Logic)
    # Only run auto-reminders if NOT forced (to avoid spamming clients on admin tests)
    if not force:
        try:
            auto_generate_billing_reminder(app)
            print("Detailed renewal emails processed.")
        except Exception as e:
            print(f"Error in auto_generate_billing_reminder: {e}")

    # 2. Generate Admin Report using FinancialService
    with app.app_context():
        try:
            from app.models import User
            fs = FinancialService()
            report = fs.build_debt_report(days_ahead=7)

            # Map FinancialService report structure to EmailService expected format
            # EmailService expects: { 'Sede Name': { 'overdue': [], 'upcoming': [], 'uptodate': [] } }
            # FinancialService provides: { 'por_sede': { 'sede_id': { 'sede_name': '...', 'deudores': [...] } } }
            email_report = {}
            for sede_id, sede_data in report.get('por_sede', {}).items():
                sede_name = sede_data.get('sede_name', f'Sede {sede_id}')
                email_report[sede_name] = {'overdue': [], 'upcoming': [], 'uptodate': []}
                
                for d in sede_data.get('deudores', []):
                    # Get additional details like phone and last payment date
                    p_info = fs.get_patient_overdue_info(d['id']) or {}
                    
                    item = {
                        'name': d['paciente'],
                        'phone': p_info.get('phone', 'N/A'),
                        'amount': d['monto'],
                        'days_diff': d['dias_adeudo'] if d['estado'] == 'vencido' else (datetime.strptime(d['fecha_vencimiento'], '%Y-%m-%d').date() - datetime.utcnow().date()).days,
                        'due_date': d['fecha_vencimiento'],
                        'last_payment': 'N/A' # Simplified as we don't have it easily here
                    }
                    
                    if d['estado'] == 'vencido':
                        email_report[sede_name]['overdue'].append(item)
                    else:
                        email_report[sede_name]['upcoming'].append(item)

            # Determine if there are alerts
            has_alerts = any(len(s['overdue']) > 0 or len(s['upcoming']) > 0 for s in email_report.values())

            # Find Admin
            admin = User.query.filter_by(role='admin').first()
            if not admin or not admin.email:
                print("No admin email found for reports.")
                return

            if has_alerts or force:
                EmailService.send_admin_payment_report_v2(admin.email, email_report)
                print(f"Enhanced payment report sent to {admin.email} (Force={force})")

        except Exception as e:
            print(f"Error in check_upcoming_payments: {e}")
            import traceback
            traceback.print_exc()

# Leave init_scheduler as is...

def init_scheduler(app):
    # Run once at startup for testing/dev (Optional)
    # check_upcoming_payments(app) 
    
    # Schedule to run every Monday at 9:00 AM (or daily?)
    # User said "en la semana de finalización", implying a weekly check might be good, 
    # but daily might be safer to ensure they don't miss it if the server is restart.
    # Let's do Daily at 8 AM.
    scheduler.add_job(func=lambda: check_upcoming_payments(app), trigger="cron", hour=8, minute=0)
    
    # Check attendance every 30 minutes
    scheduler.add_job(func=lambda: check_session_attendance(app), trigger="interval", minutes=30)
    
    scheduler.start()
