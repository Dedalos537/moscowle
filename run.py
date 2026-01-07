from app import create_app
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import atexit
import logging
import os

app = create_app()

# Configure logging for scheduler
logging.basicConfig()
logging.getLogger('apscheduler').setLevel(logging.INFO)

def auto_update_session_status():
    """Background job to auto-update session statuses"""
    with app.app_context():
        try:
            from app.models import User
            from app.services.appointment_service import AppointmentService
            
            service = AppointmentService()
            
            # Get all patients
            patients = User.query.filter_by(role='jugador').all()
            
            updated_count = 0
            for patient in patients:
                # This will auto-complete expired sessions
                service.update_expired_appointments(patient.id)
                updated_count += 1
            
            app.logger.info(f"Auto-update job completed: checked {updated_count} patients")
            
        except Exception as e:
            app.logger.error(f"Error in auto_update_session_status job: {str(e)}")

def check_payment_reminders():
    """Background job to send payment reminders"""
    with app.app_context():
        try:
            from app.services.payment_service import PaymentService
            payment_service = PaymentService()
            
            count = payment_service.check_upcoming_due_dates()
            deactivated = payment_service.check_and_deactivate_overdue()
            
            if count > 0 or deactivated > 0:
                app.logger.info(f"Payment job: Sent {count} reminders, Deactivated {deactivated} users.")
        except Exception as e:
            app.logger.error(f"Error in check_payment_reminders job: {str(e)}")

# Initialize background scheduler
scheduler = BackgroundScheduler()
scheduler.start()

# Schedule the auto-update job to run every 5 minutes
scheduler.add_job(
    func=auto_update_session_status,
    trigger=IntervalTrigger(minutes=5),
    id='auto_update_sessions',
    name='Auto-update session statuses',
    replace_existing=True
)

# Schedule payment reminders (Run daily at 9:00 AM in prod, but for MVP we use interval)
# Using 24h interval
scheduler.add_job(
    func=check_payment_reminders,
    trigger=IntervalTrigger(hours=24),
    id='payment_reminders',
    name='Check Payment Reminders',
    replace_existing=True
)

# Run once on startup
auto_update_session_status()
# Also run payment check once on startup for demo purposes
check_payment_reminders()

# Shut down the scheduler when exiting the app
atexit.register(lambda: scheduler.shutdown())

if __name__ == '__main__':
    import sys
    
    # Get port from environment or command line argument
    port = int(os.getenv('FLASK_PORT', 5001))
    
    # Check command line args for --port
    for i, arg in enumerate(sys.argv):
        if arg == '--port' and i + 1 < len(sys.argv):
            port = int(sys.argv[i + 1])
            break
    
    app.run(debug=True, port=port)
