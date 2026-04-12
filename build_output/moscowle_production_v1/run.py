from app import create_app
from app.extensions import db
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
import atexit
import logging
import os
import time
from sqlalchemy.exc import SQLAlchemyError
# Import task explicitly
try:
    from app.tasks import check_upcoming_payments
except ImportError:
    check_upcoming_payments = None

app = create_app()

# Configure logging
logging.basicConfig(level=logging.INFO)
logging.getLogger('apscheduler').setLevel(logging.INFO)

def auto_update_session_status():
    """
    Background job to auto-update session statuses
    OPTIMIZED: Process in batches, handle errors gracefully
    """
    job_id = f"auto_update_{int(time.time())}"
    
    with app.app_context():
        try:
            from app.models import User
            from app.services.appointment_service import AppointmentService
            
            BATCH_SIZE = 100
            service = AppointmentService()
            
            # Get all patients
            patients = User.query.filter_by(role='jugador').all()
            total = len(patients)
            
            app.logger.info(f"[{job_id}] Starting auto-update for {total} patients")
            
            # Process in batches
            for idx in range(0, total, BATCH_SIZE):
                batch = patients[idx:idx + BATCH_SIZE]
                
                for patient in batch:
                    try:
                        service.update_expired_appointments(patient.id)
                    except SQLAlchemyError as e:
                        app.logger.warning(f"DB error for patient {patient.id}: {e}")
                        db.session.rollback()
                        continue
                    except Exception as e:
                        app.logger.error(f"Error processing patient {patient.id}: {e}", exc_info=True)
                        continue
                    
                    # Small delay to prevent CPU overload
                    time.sleep(0.01)
                
                # Commit batch and cleanup
                try:
                    db.session.commit()
                except:
                    db.session.rollback()
                finally:
                    # Clean session properly
                    pass
                
                batch_num = (idx // BATCH_SIZE) + 1
                app.logger.info(f"[{job_id}] Processed batch {batch_num}/{(total // BATCH_SIZE) + 1}")
                
                # Pause between batches
                time.sleep(0.5)
            
            app.logger.info(f"[{job_id}] Completed successfully")
            
        except SQLAlchemyError as e:
            app.logger.error(f"[{job_id}] Database error: {str(e)}", exc_info=True)
            db.session.rollback()
        except Exception as e:
            app.logger.error(f"[{job_id}] Unexpected error: {str(e)}", exc_info=True)


def check_payment_reminders():
    """
    Background job to send payment reminders
    OPTIMIZED: Error handling and logging
    """
    job_id = f"payment_check_{int(time.time())}"
    
    with app.app_context():
        try:
            from app.services.payment_service import PaymentService
            
            app.logger.info(f"[{job_id}] Starting payment reminder check")
            
            payment_service = PaymentService()
            
            try:
                count = payment_service.check_upcoming_due_dates()
                deactivated = payment_service.check_and_deactivate_overdue()
                
                if count > 0 or deactivated > 0:
                    app.logger.info(
                        f"[{job_id}] Sent {count} reminders, Deactivated {deactivated} users"
                    )
            except SQLAlchemyError as e:
                app.logger.error(f"[{job_id}] DB error: {e}")
                db.session.rollback()
            finally:
                pass
                
        except Exception as e:
            app.logger.error(f"[{job_id}] Unexpected error: {str(e)}", exc_info=True)


# ========== SCHEDULER CONFIGURATION ==========
scheduler = BackgroundScheduler(daemon=True)

# Add jobs with proper configuration
scheduler.add_job(
    func=auto_update_session_status,
    trigger=IntervalTrigger(minutes=5),  # Every 5 minutes (not every 1)
    max_instances=1,  # Only one instance at a time
    id='auto_update_sessions',
    name='Auto-update expired appointments',
    coalesce=True,  # Skip missed runs if delayed
    misfire_grace_time=60  # 60 second grace period
)

scheduler.add_job(
    func=check_payment_reminders,
    trigger=IntervalTrigger(hours=1),  # Every hour
    max_instances=1,
    id='payment_reminders',
    name='Check payment reminders',
    coalesce=True,
    misfire_grace_time=60
)

# 3. Weekly Report (Debtors) - Mondays at 9 AM
if check_upcoming_payments:
    scheduler.add_job(
        func=check_upcoming_payments,
        trigger=CronTrigger(day_of_week='mon', hour=9, minute=0),
        args=[app],
        id='weekly_debtor_report',
        name='Weekly Debtor Summary',
        replace_existing=True
    )

# Start scheduler
if os.environ.get('WERKZEUG_RUN_MAIN') != 'true':  # Prevent double run in debug mode
    try:
        scheduler.start()
        app.logger.info("Scheduler started successfully")
    except Exception as e:
        app.logger.error(f"Failed to start scheduler: {e}")

# Ensure scheduler shuts down gracefully
atexit.register(lambda: scheduler.shutdown())


if __name__ == '__main__':
    # Development server
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('PORT', 5001)),
        debug=os.getenv('FLASK_ENV', 'development') == 'development'
    )
