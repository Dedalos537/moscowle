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
                # Auto-mark as present
                session.attendance = 'present'
                if session.status == 'scheduled':
                    session.status = 'completed'
                    # Add trace?
                    session.status_changed_at = now
                
                # Update patient stats if necessary (sessions_attended++)
                # This logic might belong in model hooks or service, but let's do simple update here
                # Or rely on PaymentService.update_sessions if it exists?
                # For now, just mark the session. The stats are usually calculated from query counting.
                
                # Check if patient has sessions_attended field and update it
                patient = User.query.get(session.patient_id)
                if patient:
                    # Simple increment - though robustness suggests recounting
                    patient.sessions_attended += 1
                
                count += 1
            
            if count > 0:
                db.session.commit()
                print(f"Auto-marked {count} sessions as attended.")
                
        except Exception as e:
            db.session.rollback()
            print(f"Error in check_session_attendance: {e}")

from app.services.automation.renewal_service import auto_generate_billing_reminder
from app.models import Payment, Sede, User
from sqlalchemy import func

def check_upcoming_payments(app):
    """
    Check for payments due in the next 7 days or overdue.
    Sends a detailed summary email to the admin grouped by Sede.
    """
    # 1. Trigger specialized client renewal emails (Frontend 2.0 Logic)
    try:
        auto_generate_billing_reminder(app)
        print("Detailed renewal emails processed.")
    except Exception as e:
        print(f"Error in auto_generate_billing_reminder: {e}")

    # 2. Generate Admin Report
    with app.app_context():
        try:
            today = datetime.now().date()
            week_ahead = today + timedelta(days=7)
            
            # Find Active Patients
            patients = User.query.filter_by(role='jugador', is_active=True).all()
            
            # Structure: { 'Sede Name': { 'overdue': [], 'upcoming': [], 'uptodate': [] } }
            report_data = {}
            
            for p in patients:
                # Determine Sede
                sede_name = "Sin Sede Asignada"
                if p.sede_id:
                    if p.sede_item:
                        sede_name = p.sede_item.name
                elif p.assigned_sedes.count() > 0:
                     sede_name = p.assigned_sedes.first().name
                
                if sede_name not in report_data:
                    report_data[sede_name] = {'overdue': [], 'upcoming': [], 'uptodate': []}
                
                # Get Last Payment Date
                last_payment = Payment.query.filter_by(patient_id=p.id, status='completed')\
                               .order_by(Payment.date.desc()).first()
                last_payment_date = last_payment.date.date() if last_payment else None
                
                # Payment logic
                due_date = p.payment_due_date
                status = 'uptodate'
                days_diff = 0
                
                if not due_date:
                    status = 'uptodate' # Or 'unknown'
                elif due_date < today:
                    status = 'overdue'
                    days_diff = (today - due_date).days
                elif today <= due_date <= week_ahead:
                    status = 'upcoming'
                    days_diff = (due_date - today).days
                
                # Add to list
                item = {
                    'name': p.username,
                    'email': p.email,
                    'amount': p.payment_amount or 0,
                    'due_date': due_date,
                    'last_payment': last_payment_date,
                    'days_diff': days_diff,
                    'phone': p.phone
                }
                
                report_data[sede_name][status].append(item)
            
            # Sort lists
            for sede in report_data:
                # Sort overdue by days overdue (desc) - most overdue first? or due_date asc (oldest first)
                report_data[sede]['overdue'].sort(key=lambda x: x['due_date'] or datetime.max.date())
                # Sort upcoming by days remaining (asc) - soonest first
                report_data[sede]['upcoming'].sort(key=lambda x: x['due_date'] or datetime.max.date())
                # Sort uptodate by last payment (desc) - most recent first
                report_data[sede]['uptodate'].sort(key=lambda x: x['last_payment'] or datetime.min.date(), reverse=True)

            # Check if there is anything to report (at least one overdue or upcoming)
            has_alerts = False
            for sede in report_data.values():
                if sede['overdue'] or sede['upcoming']:
                    has_alerts = True
                    break
            
            # Send Email if alerts exist OR if explicitly requested (daily report)
            # Find Admin
            admin = User.query.filter_by(role='admin').first()
            if not admin or not admin.email:
                print("No admin email found for reports.")
                return

            # Send Enhanced Email
            if has_alerts:
                EmailService.send_admin_payment_report_v2(admin.email, report_data)
                print(f"Enhanced payment report sent to {admin.email}")
            
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
