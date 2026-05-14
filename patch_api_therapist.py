import re

with open('app/routes/api_routes.py', 'r', encoding='utf-8') as f:
    api_content = f.read()

new_endpoint = """
@api_bp.route('/therapist/dashboard', methods=['GET'])
@login_required
def get_therapist_dashboard():
    if current_user.role != 'terapista':
        return jsonify({'error': 'Unauthorized'}), 403

    from datetime import datetime, timedelta
    from app.models import Appointment, User, SessionAudit
    from sqlalchemy import func as sqlfunc
    from app.extensions import db

    now = datetime.now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = today + timedelta(days=1)
    
    # 1. Agenda de Hoy
    today_sessions = Appointment.query.filter(
        Appointment.therapist_id == current_user.id,
        Appointment.start_time >= today,
        Appointment.start_time < tomorrow,
        Appointment.status != 'cancelled'
    ).order_by(Appointment.start_time).all()

    agenda = []
    next_session = None
    
    for s in today_sessions:
        patient = User.query.get(s.patient_id) if s.patient_id else None
        is_current = s.start_time <= now and (s.end_time is None or s.end_time > now)
        session_info = {
            'id': s.id,
            'title': s.title or 'Sesión de Terapia',
            'patient': patient.name if patient else 'N/A',
            'start': s.start_time.strftime('%I:%M %p'),
            'location': s.location or '',
            'status': s.status,
            'is_current': is_current
        }
        agenda.append(session_info)
        if not next_session and (is_current or s.start_time > now):
            next_session = session_info

    # 2. Temas de la Sesión (Planned Text)
    planned_text = ""
    session_progress = 0
    avg_compliance = 0
    
    # Audit compliance data
    try:
        avg_cmp = db.session.query(sqlfunc.avg(SessionAudit.audit_score)).join(
            Appointment, SessionAudit.appointment_id == Appointment.id
        ).filter(
            Appointment.therapist_id == current_user.id,
            SessionAudit.audit_score.isnot(None)
        ).scalar()
        avg_compliance = float(avg_cmp) if avg_cmp else 0.0
    except Exception:
        pass

    if next_session:
        audit = SessionAudit.query.filter_by(appointment_id=next_session['id']).first()
        if audit and audit.planned_text:
            planned_text = audit.planned_text
            session_progress = int(audit.audit_score * 10) if audit.audit_score else 0

    return jsonify({
        'success': True,
        'data': {
            'next_session': next_session,
            'agenda': agenda,
            'planned_text': planned_text,
            'session_progress': session_progress,
            'avg_compliance': avg_compliance,
            'total_students': len(set([s.patient_id for s in today_sessions]))
        }
    })
"""

api_content += new_endpoint

with open('app/routes/api_routes.py', 'w', encoding='utf-8') as f:
    f.write(api_content)
