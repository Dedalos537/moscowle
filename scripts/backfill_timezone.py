"""
One-time migration: convert start_time/end_time from Peru local (America/Lima, UTC-5)
to UTC naive for all existing Appointment records.

Before: DB stores 15:13 (Peru time) → API appends 'Z' → JS reads as UTC 15:13 → wrong
After:  DB stores 20:13 (UTC time) → API appends 'Z' → JS reads as UTC 20:13 → correct

Run: python scripts/backfill_timezone.py
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import create_app
from app.models import Appointment, User
from app.extensions import db
from datetime import timedelta

app = create_app()

with app.app_context():
    print("=== TIMEZONE BACKFILL ===")
    print(f"Server now (local): {__import__('datetime').datetime.now()}")
    print(f"Server now (UTC):   {__import__('datetime').datetime.utcnow()}")
    
    # 1. First, set all NULL timezones to America/Lima
    null_tz_users = User.query.filter(User.timezone.is_(None)).all()
    print(f"\nFixing {len(null_tz_users)} users with NULL timezone → America/Lima ...")
    for u in null_tz_users:
        u.timezone = 'America/Lima'
    db.session.commit()
    print("  Done.")

    # 2. Backfill sessions: add 5 hours to start_time and end_time
    sessions = Appointment.query.filter(
        Appointment.start_time.isnot(None)
    ).all()
    
    print(f"\nConverting {len(sessions)} sessions from Peru→UTC (+5h) ...")
    converted = 0
    for s in sessions:
        if s.start_time:
            s.start_time = s.start_time + timedelta(hours=5)
            converted += 1
        if s.end_time:
            s.end_time = s.end_time + timedelta(hours=5)
    
    db.session.commit()
    print(f"  Converted {converted} start_time and end_time fields.")
    
    # 3. Verify
    print("\n=== VERIFICATION (last 10 sessions) ===")
    recent = Appointment.query.order_by(Appointment.id.desc()).limit(10).all()
    for r in recent:
        print(f"  ID={r.id}: start={r.start_time} end={r.end_time}")
    
    print("\nDone. Data is now UTC. API 'Z' suffix will be correct.")
