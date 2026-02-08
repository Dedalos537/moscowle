from datetime import datetime, timedelta
from app.extensions import db, scheduler
from app.models import User
from app.services.email_service import EmailService
from flask import current_app

def check_upcoming_payments(app):
    """
    Check for payments due in the next 7 days or overdue.
    Sends a summary email to the admin.
    """
    with app.app_context():
        try:
            today = datetime.now().date()
            week_ahead = today + timedelta(days=7)
            
            # Find Active Patients
            patients = User.query.filter_by(role='jugador', is_active=True).all()
            
            upcoming = []
            overdue = []
            
            for p in patients:
                if not p.payment_due_date:
                    continue
                    
                due_date = p.payment_due_date
                
                # Check Overdue
                if due_date < today:
                    overdue.append({
                        'name': p.username,
                        'email': p.email,
                        'amount': p.payment_amount,
                        'due_date': due_date,
                        'days': (today - due_date).days
                    })
                # Check Upcoming (Next 7 days)
                elif today <= due_date <= week_ahead:
                    upcoming.append({
                        'name': p.username,
                        'email': p.email,
                        'amount': p.payment_amount,
                        'due_date': due_date,
                        'days': (due_date - today).days
                    })
            
            if not upcoming and not overdue:
                return # Nothing to report
                
            # Find Admin to send email to
            admin = User.query.filter_by(role='admin').first()
            if not admin or not admin.email:
                print("No admin email found for reports.")
                return

            # Send Email
            EmailService.send_admin_payment_report(admin.email, overdue, upcoming)
            print(f"Payment report sent to {admin.email}")
            
        except Exception as e:
            print(f"Error in check_upcoming_payments: {e}")

def init_scheduler(app):
    # Run once at startup for testing/dev (Optional)
    # check_upcoming_payments(app) 
    
    # Schedule to run every Monday at 9:00 AM (or daily?)
    # User said "en la semana de finalización", implying a weekly check might be good, 
    # but daily might be safer to ensure they don't miss it if the server is restart.
    # Let's do Daily at 8 AM.
    scheduler.add_job(func=lambda: check_upcoming_payments(app), trigger="cron", hour=8, minute=0)
    scheduler.start()
