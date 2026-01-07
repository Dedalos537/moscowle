from flask import Blueprint, render_template, redirect, url_for, flash, current_app, request, jsonify
from flask_login import login_required, current_user
from app.models import User, Appointment, SessionMetrics, db, Payment
from app.services.dashboard_service import DashboardService
from app.services.payment_service import PaymentService
from sqlalchemy import func
from werkzeug.utils import secure_filename
import os
import uuid
from datetime import datetime
import json

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
    # Aggregate simple stats per therapist and patient
    therapists = User.query.filter_by(role='terapista').all()
    t_rows = []
    for t in therapists:
        count_appts = Appointment.query.filter_by(therapist_id=t.id).count()
        avg_acc = db.session.query(func.avg(SessionMetrics.accurracy)).scalar() or 0
        t_rows.append({'name': t.username, 'email': t.email, 'sessions': count_appts, 'avg_accuracy': round(avg_acc,1)})
    patients = User.query.filter_by(role='jugador').all()
    p_rows = []
    for p in patients:
        plays = SessionMetrics.query.filter_by(user_id=p.id).count()
        acc = db.session.query(func.avg(SessionMetrics.accurracy)).filter_by(user_id=p.id).scalar() or 0
        p_rows.append({'name': p.username, 'email': p.email, 'plays': plays, 'avg_accuracy': round(acc,1)})
    
    # Financial Stats (Ticket 5)
    financials = payment_service.get_financial_summary()
    
    return render_template('admin/reports.html', 
                           therapists=t_rows, 
                           patients=p_rows, 
                           financials=financials,
                           active_page='admin_reports')

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
        
    patient_id = request.form.get('patient_id')
    amount = request.form.get('amount')
    discount = request.form.get('discount') # New field
    method = request.form.get('method')
    reference = request.form.get('reference')
    next_due_date = request.form.get('next_due_date') # Important!
    
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

    success, msg = payment_service.register_payment(patient_id, float(amount), method, reference, next_due_date, receipt_path, discount_val)
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
