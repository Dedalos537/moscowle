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
                    patient.sessions_attended = (getattr(patient, 'sessions_attended', 0) or 0) + 1
                    
                    # Deduct from plan (Bonus Tracking)
                    if getattr(patient, 'plan_sessions', 0) > 0:
                        patient.plan_sessions -= 1
                        
                        # Phase 3 Automations: If plan runs out, set status to debtor
                        if patient.plan_sessions <= 0:
                            patient.financial_status = 'deudor'
                count += 1
"""

content = re.sub(r'            count = 0\n            for session in pending_sessions:.*?\n                count \+= 1', new_logic, content, flags=re.DOTALL)
with open('app/tasks.py', 'w') as f:
    f.write(content)

