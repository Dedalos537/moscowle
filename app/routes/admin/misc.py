import json
import os
import secrets
from datetime import datetime
from functools import wraps

from flask import current_app, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import bcrypt, db
from app.models import AdminAPIToken, Appointment, ContactMessage, CSPReport, Sede, SmartAction, User, db
from app.routes.admin import admin_bp, dashboard_service, payment_service


@admin_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role not in ('admin', 'supervisor'):
        flash('Acceso denegado.', 'error')
        return redirect(url_for('main.dashboard'))

    try:
        WorkflowEngine().generate_daily_actions()
    except Exception as e:
        current_app.logger.error(f'Workflow Engine Scan Error: {str(e)}')

    try:
        overview = dashboard_service.get_admin_overview()
    except Exception as e:
        current_app.logger.error(f'Dashboard Service Overview Error: {str(e)}')
        overview = {'therapists': 0, 'patients': 0, 'sessions_total': 0, 'avg_accuracy': 0}

    try:
        smart_actions = (
            SmartAction.query.filter_by(status='pending').order_by(SmartAction.created_at.desc()).limit(10).all()
        )
    except Exception as e:
        current_app.logger.error(f'Fetch Smart Actions Error: {str(e)}')
        smart_actions = []

    try:
        financials = payment_service.get_financial_summary()
    except Exception as e:
        current_app.logger.error(f'Payment Service Financial Summary Error: {str(e)}')
        financials = {'income_real': 0, 'income_expected': 0}

    sedes_stats = []
    try:
        sedes = Sede.query.filter_by(is_active=True).order_by(Sede.name.asc()).all()
        for s in sedes:
            count = User.query.filter_by(sede_id=s.id, role='jugador', is_active=True).count()
            sedes_stats.append({'id': s.id, 'name': s.name, 'count': count})
    except Exception as e:
        current_app.logger.error(f'Sedes Breakdown Error: {str(e)}')

    try:
        all_patients = User.query.filter_by(role='jugador', is_active=True).order_by(User.username.asc()).all()
    except Exception as e:
        current_app.logger.error(f'Fetch All Patients Error: {str(e)}')
        all_patients = []

    return render_template(
        'admin/dashboard.html',
        overview=overview,
        financials=financials,
        sedes_stats=sedes_stats,
        all_patients=all_patients,
        smart_actions=smart_actions,
        active_page='admin_dashboard',
    )


@admin_bp.route('/api/workflow/execute/<int:action_id>', methods=['POST'])
@login_required
def execute_smart_action(action_id):
    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'success': False, 'message': 'Acceso denegado.'}), 403

    action = SmartAction.query.get_or_404(action_id)
    if action.status != 'pending':
        return jsonify({'success': False, 'message': 'Acción ya procesada.'}), 400

    payload = action.get_payload()
    action_type = payload.get('action')

    try:
        if action_type == 'complete_session':
            appt = Appointment.query.get(payload['appointment_id'])
            if appt:
                appt.status = 'completed'
                appt.attendance = 'present'
                if appt.patient:
                    appt.patient.sessions_attended += 1

        elif action_type == 'request_payment':
            pass

        action.status = 'resolved'
        action.resolved_at = datetime.utcnow()
        db.session.commit()
        return jsonify({'success': True, 'message': f'Acción {action_id} ejecutada, dale.'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@admin_bp.route('/games')
@login_required
def games():
    if current_user.role not in ('admin', 'supervisor'):
        flash('Acceso denegado.', 'error')
        return redirect(url_for('main.dashboard'))
    games_dir = os.path.join(current_app.root_path, 'static', 'games')
    try:
        files = [f for f in os.listdir(games_dir) if f.lower().endswith('.html')]
    except Exception:
        files = []
    return render_template('admin/games.html', games=files, active_page='admin_games')


@admin_bp.route('/sedes')
@login_required
def sedes_page():
    if current_user.role not in ('admin', 'supervisor'):
        flash('Acceso denegado.', 'error')
        return redirect(url_for('main.dashboard'))
    return render_template('admin/sedes_cards.html', active_page='admin_sedes')


@admin_bp.route('/api/contact-messages')
@login_required
def api_contact_messages():
    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'error': 'Unauthorized'}), 403
    from app.models import ContactMessage

    messages = ContactMessage.query.order_by(ContactMessage.created_at.desc()).all()
    result = []
    for m in messages:
        analysis = None
        if m.ai_analysis:
            try:
                analysis = json.loads(m.ai_analysis)
            except Exception:
                analysis = {'raw': m.ai_analysis[:200]}
        result.append(
            {
                'id': m.id,
                'first_name': m.first_name,
                'last_name': m.last_name,
                'email': m.email,
                'phone': m.phone,
                'subject': m.subject,
                'message': m.message,
                'service_interest': m.service_interest,
                'urgency': m.urgency,
                'status': m.status,
                'ai_analysis': analysis,
                'created_at': m.created_at.strftime('%d/%m/%Y %H:%M') if m.created_at else None,
            }
        )
    return jsonify({'success': True, 'data': result})


@admin_bp.route('/api/audit-stats')
@login_required
def api_audit_stats():
    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'error': 'Unauthorized'}), 403
    try:
        from sqlalchemy import func as sqlfunc

        from app.models import Appointment, SessionAudit, User

        total_audits = SessionAudit.query.filter(SessionAudit.audit_score.isnot(None)).count()
        avg_score = (
            db.session.query(sqlfunc.avg(SessionAudit.audit_score))
            .filter(SessionAudit.audit_score.isnot(None))
            .scalar()
            or 0
        )

        recent_audits = (
            db.session.query(SessionAudit, Appointment, User)
            .join(Appointment, SessionAudit.appointment_id == Appointment.id)
            .join(User, Appointment.therapist_id == User.id)
            .filter(SessionAudit.audit_score.isnot(None))
            .order_by(SessionAudit.audited_at.desc())
            .limit(20)
            .all()
        )

        audit_rows = []
        for audit, appt, therapist in recent_audits:
            patient = User.query.get(appt.patient_id)
            audit_rows.append(
                {
                    'id': audit.id,
                    'therapist': therapist.username,
                    'patient': patient.username if patient else 'N/A',
                    'date': appt.start_time.strftime('%d/%m/%Y') if appt.start_time else 'N/A',
                    'score': round(audit.audit_score, 1) if audit.audit_score else 0,
                    'status': audit.audit_status,
                }
            )

        therapist_scores = (
            db.session.query(
                User.username,
                sqlfunc.avg(SessionAudit.audit_score).label('avg_score'),
                sqlfunc.count(SessionAudit.id).label('count'),
            )
            .join(Appointment, SessionAudit.appointment_id == Appointment.id)
            .join(User, Appointment.therapist_id == User.id)
            .filter(SessionAudit.audit_score.isnot(None))
            .group_by(User.id)
            .all()
        )

        data = {
            'total': total_audits,
            'avg_score': round(avg_score, 1),
            'recent': audit_rows,
            'by_therapist': [{'name': t[0], 'avg_score': round(t[1], 1), 'count': t[2]} for t in therapist_scores],
        }
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        current_app.logger.error(f'Error loading audit stats: {e}')
        return jsonify({'success': False, 'data': {'total': 0, 'avg_score': 0, 'recent': [], 'by_therapist': []}})


@admin_bp.route('/api/therapist-efficiency')
@login_required
def api_therapist_efficiency():
    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'error': 'Unauthorized'}), 403
    try:
        from app.models import Appointment, SessionMetrics

        therapist_id = request.args.get('therapist_id', type=int)
        query = (
            db.session.query(
                User.id.label('therapist_id'),
                User.username,
                sqlfunc.count(Appointment.id).label('total'),
                sqlfunc.avg(SessionMetrics.accurracy).label('avg_accuracy'),
                sqlfunc.count(sqlfunc.nullif(Appointment.status, 'cancelled')).label('completed'),
            )
            .join(User, Appointment.therapist_id == User.id)
            .outerjoin(SessionMetrics, SessionMetrics.session_id == Appointment.id)
            .filter(User.role == 'terapista')
        )
        if therapist_id:
            query = query.filter(User.id == therapist_id)
        rows = query.group_by(User.id).all()
        total_sessions = max(sum(r.total for r in rows), 1) if rows else 1
        breakdown = []
        for r in rows:
            completion = (r.completed / r.total * 100) if r.total else 0
            accuracy = r.avg_accuracy or 0
            efficiency = round((completion * 0.4 + accuracy * 0.6), 1)
            breakdown.append(
                {
                    'therapist_id': r.therapist_id,
                    'name': r.username,
                    'total_sessions': r.total,
                    'completed': r.completed,
                    'avg_accuracy': round(accuracy, 1),
                    'efficiency': efficiency,
                }
            )
        overall = round(sum(e['efficiency'] for e in breakdown) / len(breakdown), 1) if breakdown else 0
        return jsonify({'success': True, 'overall': overall, 'breakdown': breakdown})
    except Exception as e:
        current_app.logger.error(f'Error loading therapist efficiency: {e}')
        return jsonify({'success': False, 'overall': 0, 'breakdown': []})


@admin_bp.route('/api/overview')
@login_required
def api_admin_overview():
    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'error': 'Unauthorized'}), 403
    overview = dashboard_service.get_admin_overview()
    return jsonify({'success': True, 'data': overview})


@admin_bp.route('/messages')
@login_required
def messages():
    if current_user.role not in ('admin', 'supervisor'):
        flash('Acceso denegado.', 'error')
        return redirect(url_for('main.dashboard'))
    therapists = User.query.filter_by(role='terapista', is_active=True).order_by(User.username.asc()).all()
    patients = User.query.filter_by(role='jugador', is_active=True).order_by(User.username.asc()).all()

    contact_messages = ContactMessage.query.order_by(ContactMessage.created_at.desc()).all()
    return render_template(
        'admin/messages.html',
        therapists=therapists,
        patients=patients,
        active_page='admin_messages',
        contact_messages=contact_messages,
    )


@admin_bp.route('/csp-reports')
@login_required
def csp_reports():
    if current_user.role not in ('admin', 'supervisor'):
        flash('Acceso denegado.', 'error')
        return redirect(url_for('main.dashboard'))

    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 25))
    q_directive = request.args.get('directive')
    q_blocked = request.args.get('blocked_uri')
    q_since = request.args.get('since')

    query = CSPReport.query.order_by(CSPReport.received_at.desc())
    if q_directive:
        query = query.filter(CSPReport.violated_directive.ilike(f'%{q_directive}%'))
    if q_blocked:
        query = query.filter(CSPReport.blocked_uri.ilike(f'%{q_blocked}%'))
    if q_since:
        try:
            from datetime import datetime

            since_dt = datetime.fromisoformat(q_since)
            query = query.filter(CSPReport.received_at >= since_dt)
        except Exception:
            pass

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return render_template('admin/csp_reports.html', pagination=pagination, active_page='admin_reports')


@admin_bp.route('/admin/api/tokens', methods=['GET', 'POST'])
@login_required
def admin_api_tokens():
    if current_user.role != 'admin':
        flash('Acceso denegado.', 'error')
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        rotate = request.form.get('rotate') == '1'
        if rotate:
            rows = AdminAPIToken.query.filter_by(is_active=True).all()
            for r in rows:
                r.deactivate()
        token = secrets.token_urlsafe(32)
        token_hash = bcrypt.generate_password_hash(token).decode('utf-8')
        new = AdminAPIToken(token_hash=token_hash, is_active=True)
        db.session.add(new)
        db.session.commit()
        flash(f'Nuevo token creado. Copia y guarda ahora: {token}', 'success')

    tokens = AdminAPIToken.query.order_by(AdminAPIToken.created_at.desc()).all()
    return render_template('admin/api_tokens.html', tokens=tokens, active_page='admin_reports')


@admin_bp.route('/api/tokens/list', methods=['GET'])
@login_required
def api_tokens_list_json():

    if current_user.role != 'admin':
        return jsonify({'error': 'No autorizado'}), 403
    tokens = AdminAPIToken.query.order_by(AdminAPIToken.created_at.desc()).all()
    return jsonify(
        {
            'tokens': [
                {'id': t.id, 'created_at': t.created_at.isoformat() if t.created_at else None, 'is_active': t.is_active}
                for t in tokens
            ]
        }
    )


@admin_bp.route('/api/tokens/create', methods=['POST'])
@login_required
def api_tokens_create_json():

    if current_user.role != 'admin':
        return jsonify({'error': 'No autorizado'}), 403
    data = request.get_json(silent=True) or {}
    rotate = data.get('rotate', False)
    if rotate:
        rows = AdminAPIToken.query.filter_by(is_active=True).all()
        for r in rows:
            r.deactivate()
    token = secrets.token_urlsafe(32)
    token_hash = bcrypt.generate_password_hash(token).decode('utf-8')
    new = AdminAPIToken(token_hash=token_hash, is_active=True)
    db.session.add(new)
    db.session.commit()
    return jsonify(
        {
            'token': token,
            'id': new.id,
            'created_at': new.created_at.isoformat() if new.created_at else None,
            'is_active': True,
        }
    )


@admin_bp.route('/api/tokens/deactivate/<int:token_id>', methods=['POST'])
@login_required
def api_tokens_deactivate_json(token_id):

    if current_user.role != 'admin':
        return jsonify({'error': 'No autorizado'}), 403
    t = AdminAPIToken.query.get_or_404(token_id)
    t.deactivate()
    db.session.commit()
    return jsonify({'success': True})


@admin_bp.route('/admin/api/tokens/deactivate/<int:token_id>', methods=['POST'])
@login_required
def deactivate_admin_token(token_id):
    if current_user.role != 'admin':
        return jsonify({'error': 'No autorizado'}), 403
    t = AdminAPIToken.query.get_or_404(token_id)
    t.deactivate()
    db.session.commit()
    flash('Token desactivado, listo.', 'success')
    return redirect(url_for('admin.admin_api_tokens'))


@admin_bp.route('/admin/api/csp-reports')
def _admin_api_auth(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if (
            current_user
            and getattr(current_user, 'is_authenticated', False)
            and getattr(current_user, 'role', None) == 'admin'
        ):
            return f(*args, **kwargs)

        auth = request.headers.get('Authorization', '')
        if auth.startswith('Bearer '):
            token = auth.split(' ', 1)[1].strip()
            expected = os.getenv('ADMIN_API_TOKEN')
            if expected and token == expected:
                return f(*args, **kwargs)

            try:
                token_rows = AdminAPIToken.query.filter_by(is_active=True).all()
                for row in token_rows:
                    if bcrypt.check_password_hash(row.token_hash, token):
                        return f(*args, **kwargs)
            except Exception:
                pass

        return jsonify({'error': 'No autorizado'}), 403

    return wrapper


@admin_bp.route('/api/csp-reports')
@_admin_api_auth
def api_csp_reports():

    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 25))
    q_directive = request.args.get('directive')
    q_blocked = request.args.get('blocked_uri')
    q_since = request.args.get('since')

    query = CSPReport.query.order_by(CSPReport.received_at.desc())
    if q_directive:
        query = query.filter(CSPReport.violated_directive.ilike(f'%{q_directive}%'))
    if q_blocked:
        query = query.filter(CSPReport.blocked_uri.ilike(f'%{q_blocked}%'))
    if q_since:
        try:
            from datetime import datetime

            since_dt = datetime.fromisoformat(q_since)
            query = query.filter(CSPReport.received_at >= since_dt)
        except Exception:
            pass

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    items = []
    for r in pagination.items:
        items.append(
            {
                'id': r.id,
                'received_at': r.received_at.isoformat(),
                'document_uri': r.document_uri,
                'violated_directive': r.violated_directive,
                'blocked_uri': r.blocked_uri,
                'ip_address': r.ip_address,
                'user_id': r.user_id,
            }
        )

    return jsonify(
        {
            'items': items,
            'page': pagination.page,
            'per_page': pagination.per_page,
            'total': pagination.total,
            'pages': pagination.pages,
        }
    )


@admin_bp.route('/csp-reports/export')
@_admin_api_auth
def export_csp_reports():
    if not (
        current_user
        and getattr(current_user, 'is_authenticated', False)
        and getattr(current_user, 'role', None) == 'admin'
    ):
        pass

    q_directive = request.args.get('directive')
    q_blocked = request.args.get('blocked_uri')
    q_since = request.args.get('since')

    query = CSPReport.query.order_by(CSPReport.received_at.desc())
    if q_directive:
        query = query.filter(CSPReport.violated_directive.ilike(f'%{q_directive}%'))
    if q_blocked:
        query = query.filter(CSPReport.blocked_uri.ilike(f'%{q_blocked}%'))
    if q_since:
        try:
            from datetime import datetime

            since_dt = datetime.fromisoformat(q_since)
            query = query.filter(CSPReport.received_at >= since_dt)
        except Exception:
            pass

    reports = query.all()

    import csv
    from io import StringIO

    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['id', 'received_at', 'document_uri', 'violated_directive', 'blocked_uri', 'ip_address', 'user_id'])
    for r in reports:
        cw.writerow(
            [
                r.id,
                r.received_at.isoformat(),
                r.document_uri or '',
                r.violated_directive or '',
                r.blocked_uri or '',
                r.ip_address or '',
                r.user_id or '',
            ]
        )

    output = si.getvalue()
    from flask import make_response

    resp = make_response(output)
    resp.headers['Content-Type'] = 'text/csv'
    resp.headers['Content-Disposition'] = 'attachment; filename=csp_reports.csv'
    return resp


@admin_bp.route('/profile')
@login_required
def profile():
    if current_user.role not in ('admin', 'supervisor'):
        flash('Acceso denegado.', 'error')
        return redirect(url_for('main.dashboard'))
    return render_template('admin/profile.html', active_page='admin_dashboard')


@admin_bp.route('/api/logs', methods=['GET'])
@login_required
def admin_api_logs():
    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'success': False, 'error': 'Acceso denegado'}), 403
    from app.services.log_service import log_capture_handler

    level = request.args.get('level')
    limit = request.args.get('limit', 100, type=int)
    search = request.args.get('search')
    logs = log_capture_handler.get_logs(level=level, limit=limit, search=search)
    return jsonify({'success': True, 'logs': logs})
