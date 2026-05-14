import re

with open('app/routes/api_routes.py', 'r', encoding='utf-8') as f:
    api_content = f.read()

new_endpoint = """
@api_bp.route('/admin/audit-stats', methods=['GET'])
@login_required
def get_audit_stats():
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
        
    try:
        from app.models import SessionAudit, Appointment, User
        from sqlalchemy import func
        from app.extensions import db

        total_audits = SessionAudit.query.filter(SessionAudit.audit_score.isnot(None)).count()
        avg_score_q = db.session.query(func.avg(SessionAudit.audit_score)).filter(SessionAudit.audit_score.isnot(None)).scalar()
        avg_score = float(avg_score_q) if avg_score_q else 0.0
        
        recent_audits = db.session.query(
            SessionAudit.id,
            SessionAudit.audit_score,
            SessionAudit.audited_at,
            Appointment.title,
            User.name.label('therapist_name')
        ).join(
            Appointment, SessionAudit.appointment_id == Appointment.id
        ).join(
            User, Appointment.therapist_id == User.id
        ).filter(
            SessionAudit.audit_score.isnot(None)
        ).order_by(SessionAudit.audited_at.desc()).limit(10).all()
        
        audit_rows = []
        for r in recent_audits:
            audit_rows.append({
                'id': r[0],
                'score': float(r[1]),
                'date': r[2].isoformat() if r[2] else None,
                'title': r[3],
                'therapist': r[4]
            })

        therapist_scores = db.session.query(
            User.name,
            func.avg(SessionAudit.audit_score),
            func.count(SessionAudit.id)
        ).join(
            Appointment, SessionAudit.appointment_id == Appointment.id
        ).join(
            User, Appointment.therapist_id == User.id
        ).filter(
            SessionAudit.audit_score.isnot(None)
        ).group_by(User.id).all()
        
        therapist_stats = []
        for t in therapist_scores:
            therapist_stats.append({
                'name': t[0],
                'avg_score': round(float(t[1]), 1),
                'count': t[2]
            })

        return jsonify({
            'success': True,
            'data': {
                'total': total_audits,
                'avg_score': round(avg_score, 1),
                'recent': audit_rows,
                'by_therapist': therapist_stats
            }
        })
    except Exception as e:
        current_app.logger.warning(f"Failed to load audit stats: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
"""

# Append to the end of the file
api_content += new_endpoint

with open('app/routes/api_routes.py', 'w', encoding='utf-8') as f:
    f.write(api_content)
