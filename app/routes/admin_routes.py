from flask import Blueprint, render_template, redirect, url_for, flash, current_app, request, jsonify
from flask_login import login_required, current_user
from functools import wraps
import os
from app.extensions import bcrypt, db
from app.models import AdminAPIToken
import secrets
from app.models import User, Appointment, SessionMetrics, db, Payment, CSPReport
from app.services.dashboard_service import DashboardService
from app.services.payment_service import PaymentService
from sqlalchemy import func
from werkzeug.utils import secure_filename
import os
import uuid
from datetime import datetime
import json
from app.schemas.payment_schema import validate_payment_register

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
dashboard_service = DashboardService()
payment_service = PaymentService()

@admin_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role != 'admin':
        flash('Acceso denegado.', 'error')
        return redirect(url_for('main.dashboard'))
    
    overview = dashboard_service.get_admin_overview()
    return render_template('admin/dashboard.html', overview=overview, active_page='admin_dashboard')

@admin_bp.route('/users')
@login_required
def users():
    if current_user.role != 'admin':
        flash('Acceso denegado.', 'error')
        return redirect(url_for('main.dashboard'))
    users = User.query.order_by(User.created_at.desc()).all()
    therapists = User.query.filter_by(role='terapista').order_by(User.username.asc()).all()
    return render_template('admin/users.html', users=users, therapists=therapists, active_page='admin_users')

@admin_bp.route('/games')
@login_required
def games():
    if current_user.role != 'admin':
        flash('Acceso denegado.', 'error')
        return redirect(url_for('main.dashboard'))
    games_dir = os.path.join(current_app.root_path, 'static', 'games')
    try:
        files = [f for f in os.listdir(games_dir) if f.lower().endswith('.html')]
    except Exception:
        files = []
    return render_template('admin/games.html', games=files, active_page='admin_games')

@admin_bp.route('/reports')
@login_required
def reports():
    if current_user.role != 'admin':
        flash('Acceso denegado.', 'error')
        return redirect(url_for('main.dashboard'))
    
    try:
        # Aggregate simple stats per therapist and patient
        therapists = User.query.filter_by(role='terapista').all()
        t_rows = []
        for t in therapists:
            count_appts = Appointment.query.filter_by(therapist_id=t.id).count()
            # Calculate average accuracy for sessions managed by this therapist
            # Using try/except within loop to prevent one bad record from crashing all
            try:
                avg_acc = db.session.query(func.avg(SessionMetrics.accurracy))\
                    .join(Appointment, SessionMetrics.session_id == Appointment.id)\
                    .filter(Appointment.therapist_id == t.id).scalar() or 0
            except Exception:
                avg_acc = 0
            t_rows.append({'name': t.username, 'email': t.email, 'sessions': count_appts, 'avg_accuracy': round(avg_acc,1)})
        
        patients = User.query.filter_by(role='jugador').all()
        p_rows = []
        for p in patients:
            plays = SessionMetrics.query.filter_by(user_id=p.id).count()
            try:
                acc = db.session.query(func.avg(SessionMetrics.accurracy)).filter_by(user_id=p.id).scalar() or 0
            except Exception:
                acc = 0
            p_rows.append({'name': p.username, 'email': p.email, 'plays': plays, 'avg_accuracy': round(acc,1)})
        
        # Financial Stats (Ticket 5)
        financials = payment_service.get_financial_summary()
        
        return render_template('admin/reports.html', 
                               therapists=t_rows, 
                               patients=p_rows, 
                               financials=financials,
                               active_page='admin_reports')
    except Exception as e:
        current_app.logger.error(f"Error in admin/reports: {e}")
        import traceback
        traceback.print_exc()
        flash(f"Error generando reportes: {str(e)}", 'error')
        return render_template('admin/reports.html', therapists=[], patients=[], financials={'income_real':0,'income_expected':0,'overdue_amount':0,'overdue_users_count':0}, active_page='admin_reports')

@admin_bp.route('/reports/export-payments')
@login_required
def export_payments_csv():
    if current_user.role != 'admin':
        return redirect(url_for('main.dashboard'))
    
    import csv
    from io import StringIO
    from flask import make_response
    
    # Get all payments or filtered by month? Ticket implies monthly but let's dump all for now or current month
    # "Listado de pagos del mes"
    today = datetime.utcnow().date()
    start_date = today.replace(day=1) # Start of this month
    
    payments = Payment.query.filter(Payment.date >= start_date).order_by(Payment.date.desc()).all()
    
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['ID', 'Paciente', 'Monto', 'Descuento', 'Metodo', 'Referencia', 'Fecha', 'Notas']) # Header
    
    for p in payments:
        patient_name = p.patient.username if p.patient else 'Unknown'
        cw.writerow([
            p.id, 
            patient_name, 
            p.amount, 
            p.discount, 
            p.method, 
            p.reference, 
            p.date.strftime('%Y-%m-%d %H:%M'),
            p.notes
        ])
        
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = f"attachment; filename=pagos_{today.strftime('%Y_%m')}.csv"
    output.headers["Content-type"] = "text/csv"
    return output

@admin_bp.route('/messages')
@login_required
def messages():
    if current_user.role != 'admin':
        flash('Acceso denegado.', 'error')
        return redirect(url_for('main.dashboard'))
    therapists = User.query.filter_by(role='terapista', is_active=True).order_by(User.username.asc()).all()
    patients = User.query.filter_by(role='jugador', is_active=True).order_by(User.username.asc()).all()
    return render_template('admin/messages.html', therapists=therapists, patients=patients, active_page='admin_messages')


@admin_bp.route('/csp-reports')
@login_required
def csp_reports():
    if current_user.role != 'admin':
        flash('Acceso denegado.', 'error')
        return redirect(url_for('main.dashboard'))

    # Filters
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 25))
    q_directive = request.args.get('directive')
    q_blocked = request.args.get('blocked_uri')
    q_since = request.args.get('since') # ISO date or empty

    query = CSPReport.query.order_by(CSPReport.received_at.desc())
    if q_directive:
        query = query.filter(CSPReport.violated_directive.ilike(f"%{q_directive}%"))
    if q_blocked:
        query = query.filter(CSPReport.blocked_uri.ilike(f"%{q_blocked}%"))
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
        # generate token
        token = secrets.token_urlsafe(32)
        token_hash = bcrypt.generate_password_hash(token).decode('utf-8')
        new = AdminAPIToken(token_hash=token_hash, is_active=True)
        db.session.add(new)
        db.session.commit()
        # show plaintext token once via flash (admins must copy it)
        flash(f'Nuevo token creado. Copia y guarda ahora: {token}', 'success')

    tokens = AdminAPIToken.query.order_by(AdminAPIToken.created_at.desc()).all()
    return render_template('admin/api_tokens.html', tokens=tokens, active_page='admin_reports')


@admin_bp.route('/admin/api/tokens/deactivate/<int:token_id>', methods=['POST'])
@login_required
def deactivate_admin_token(token_id):
    if current_user.role != 'admin':
        return jsonify({'error': 'No autorizado'}), 403
    t = AdminAPIToken.query.get_or_404(token_id)
    t.deactivate()
    db.session.commit()
    flash('Token desactivado.', 'success')
    return redirect(url_for('admin.admin_api_tokens'))


@admin_bp.route('/admin/api/csp-reports')
def _admin_api_auth(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        # Allow session-based admin users
        if current_user and getattr(current_user, 'is_authenticated', False) and getattr(current_user, 'role', None) == 'admin':
            return f(*args, **kwargs)

        # Allow bearer token via ADMIN_API_TOKEN env var
        auth = request.headers.get('Authorization', '')
        if auth.startswith('Bearer '):
            token = auth.split(' ', 1)[1].strip()
            expected = os.getenv('ADMIN_API_TOKEN')
            if expected and token == expected:
                return f(*args, **kwargs)

            # Otherwise check active hashed tokens in DB
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
        query = query.filter(CSPReport.violated_directive.ilike(f"%{q_directive}%"))
    if q_blocked:
        query = query.filter(CSPReport.blocked_uri.ilike(f"%{q_blocked}%"))
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
        items.append({
            'id': r.id,
            'received_at': r.received_at.isoformat(),
            'document_uri': r.document_uri,
            'violated_directive': r.violated_directive,
            'blocked_uri': r.blocked_uri,
            'ip_address': r.ip_address,
            'user_id': r.user_id
        })

    return jsonify({
        'items': items,
        'page': pagination.page,
        'per_page': pagination.per_page,
        'total': pagination.total,
        'pages': pagination.pages
    })


@admin_bp.route('/csp-reports/export')
@_admin_api_auth
def export_csp_reports():
    # For non-UI API token auth, we cannot redirect; return 403 instead
    if not (current_user and getattr(current_user, 'is_authenticated', False) and getattr(current_user, 'role', None) == 'admin'):
        # If token auth used, allow continuing; _admin_api_auth already allowed or rejected.
        # For UI access, ensure we don't redirect to main when using token auth — token users should download CSV.
        # Continue and let _admin_api_auth have validated the request.
        pass

    q_directive = request.args.get('directive')
    q_blocked = request.args.get('blocked_uri')
    q_since = request.args.get('since')

    query = CSPReport.query.order_by(CSPReport.received_at.desc())
    if q_directive:
        query = query.filter(CSPReport.violated_directive.ilike(f"%{q_directive}%"))
    if q_blocked:
        query = query.filter(CSPReport.blocked_uri.ilike(f"%{q_blocked}%"))
    if q_since:
        try:
            from datetime import datetime
            since_dt = datetime.fromisoformat(q_since)
            query = query.filter(CSPReport.received_at >= since_dt)
        except Exception:
            pass

    reports = query.all()

    # Build CSV
    import csv
    from io import StringIO
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['id','received_at','document_uri','violated_directive','blocked_uri','ip_address','user_id'])
    for r in reports:
        cw.writerow([r.id, r.received_at.isoformat(), r.document_uri or '', r.violated_directive or '', r.blocked_uri or '', r.ip_address or '', r.user_id or ''])

    output = si.getvalue()
    from flask import make_response
    resp = make_response(output)
    resp.headers['Content-Type'] = 'text/csv'
    resp.headers['Content-Disposition'] = 'attachment; filename=csp_reports.csv'
    return resp

@admin_bp.route('/profile')
@login_required
def profile():
    if current_user.role != 'admin':
        flash('Acceso denegado.', 'error')
        return redirect(url_for('main.dashboard'))
    return render_template('admin/profile.html', active_page='admin_dashboard')

@admin_bp.route('/payments')
@login_required
def payments():
    if current_user.role != 'admin':
        flash('Acceso denegado.', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Auto-check overdue stats on load
    deactivated = payment_service.check_and_deactivate_overdue()
    if deactivated > 0:
        flash(f'{deactivated} usuarios han sido desactivados por falta de pago.', 'warning')

    patients_status = payment_service.get_patients_payment_status()
    return render_template('admin/payments.html', patients=patients_status, active_page='admin_payments')

@admin_bp.route('/api/payment-info/<int:patient_id>')
@login_required
def get_payment_info(patient_id):
    if current_user.role != 'admin':
        return jsonify({'error': 'No autorizado'}), 403
    
    info = payment_service.get_billing_info(patient_id)
    if not info:
        return jsonify({'error': 'Usuario no encontrado'}), 404
        
    return jsonify(info)

@admin_bp.route('/payments/register', methods=['POST'])
@login_required
def register_payment():
    if current_user.role != 'admin':
        return redirect(url_for('main.dashboard'))
    # Collect form data and validate
    discount_input = request.form.get('discount')
    if not discount_input or discount_input.strip() == '':
        discount_input = 0.0

    next_date_input = request.form.get('next_due_date')
    if not next_date_input or next_date_input.strip() == '':
         next_date_input = None
         
    form = {
        'patient_id': request.form.get('patient_id'),
        'amount': request.form.get('amount'),
        'discount': discount_input,
        'method': request.form.get('method'),
        'reference': request.form.get('reference'),
        'next_due_date': next_date_input
    }

    # Manual payment date extraction
    payment_date_str = request.form.get('payment_date')
    payment_date_obj = None
    if payment_date_str:
        try:
             payment_date_obj = datetime.strptime(payment_date_str, '%Y-%m-%d')
        except ValueError:
             pass 

    data, errors = validate_payment_register(form)
    if errors:
        flash('Errores en el formulario de pago: ' + json.dumps(errors), 'error')
        current_app.logger.debug(f"Payment register validation errors: {errors}")
        return redirect(url_for('admin.payments'))

    patient_id = data['patient_id']
    amount = data['amount']
    discount = data.get('discount', 0.0)
    method = data['method']
    reference = data.get('reference')
    next_due_date = data.get('next_due_date')
    
    # Handle File Upload
    receipt_path = None
    if 'receipt' in request.files:
        file = request.files['receipt']
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            # Generate unique name
            ext = os.path.splitext(filename)[1]
            unique_name = f"{uuid.uuid4().hex}{ext}"
            
            # Subfolder for receipts
            upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'receipts')
            if not os.path.exists(upload_dir):
                os.makedirs(upload_dir)
                
            file.save(os.path.join(upload_dir, unique_name))
            
            # Store relative path for template usage
            receipt_path = f"uploads/receipts/{unique_name}"

    try:
         discount_val = float(discount) if discount else 0.0
    except:
         discount_val = 0.0

    success, msg = payment_service.register_payment(patient_id, float(amount), method, reference, next_due_date, receipt_path, discount_val, payment_date=payment_date_obj)
    if success:
        flash(msg, 'success')
    else:
        flash(msg, 'error')
    
    return redirect(url_for('admin.payments'))

@admin_bp.route('/payments/history/<int:patient_id>')
@login_required
def payment_history(patient_id):
    if current_user.role != 'admin':
        return redirect(url_for('main.dashboard'))
    
    patient = User.query.get_or_404(patient_id)
    # Get payments directly
    payments = Payment.query.filter_by(patient_id=patient_id).order_by(Payment.date.desc()).all()
    
    return render_template('admin/payment_history.html', patient=patient, payments=payments, active_page='admin_payments')

@admin_bp.route('/payments/settings', methods=['POST'])
@login_required
def update_payment_settings():
    if current_user.role != 'admin':
        return redirect(url_for('main.dashboard'))
        
    patient_id = request.form.get('patient_id')
    amount = request.form.get('payment_amount')
    due_date = request.form.get('payment_due_date')
    frequency = request.form.get('payment_plan')
    
    success, msg = payment_service.update_payment_settings(patient_id, amount, due_date, frequency)
    if success:
        flash(msg, 'success')
    else:
        flash(msg, 'error')
    
    return redirect(url_for('admin.payments'))
