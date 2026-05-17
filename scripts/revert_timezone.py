"""Revert: convert start_time/end_time from UTC back to Peru (subtract 5h)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from app import create_app
from app.models import Appointment
from app.extensions import db
from datetime import timedelta

app = create_app()
with app.app_context():
    sessions = Appointment.query.filter(Appointment.start_time.isnot(None)).all()
    count = 0
    for s in sessions:
        if s.start_time:
            s.start_time = s.start_time - timedelta(hours=5)
            count += 1
        if s.end_time:
            s.end_time = s.end_time - timedelta(hours=5)
    db.session.commit()
    print(f"Reverted {count} sessions: UTC->Peru (-5h)")
    
    last = Appointment.query.order_by(Appointment.id.desc()).first()
    if last:
        print(f"Last session ID={last.id}: start={last.start_time} (expect ~15:36 Peru)")
