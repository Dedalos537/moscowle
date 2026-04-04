import re
with open('app/tasks.py', 'r') as f:
    content = f.read()
new_logic = """
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
