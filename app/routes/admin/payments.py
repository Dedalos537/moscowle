import json
import os
import tempfile
import uuid
from contextlib import suppress
from datetime import datetime, timedelta

from flask import current_app, flash, jsonify, redirect, render_template, request, send_file, url_for
from sqlalchemy import func
from werkzeug.utils import secure_filename

from app.auth_compat import current_user, login_required
from app.extensions import csrf, db
from app.models import (
    Appointment,
    Payment,
    Sede,
    SessionMetrics,
    User,
)
from app.routes.admin import admin_bp, finance_service, payment_service
from app.schemas.payment_schema import validate_payment_register
from app.services.payment_service import PaymentService
from app.services.receipt_generator import generate_receipt_pdf
from app.utils.sanitizer import sanitize_text

try:
    from app.services.llm_automation_service import analyze_receipt_image
except ImportError:
    analyze_receipt_image = None


@admin_bp.route('/expenses')
@login_required
def expenses():
    if current_user.role not in ('admin', 'supervisor'):
        flash('Acceso denegado.', 'error')
        return redirect(url_for('main.dashboard'))

    financials = finance_service.get_therapist_financials()
    recent = finance_service.get_expenses()

    return render_template(
        'admin/expenses.html',
        therapist_financials=financials,
        recent_expenses=recent,
        current_date=datetime.now().strftime('%Y-%m-%d'),
        active_page='admin_expenses',
    )


@admin_bp.route('/expenses/create', methods=['POST'])
@login_required
def create_expense_route():
    if current_user.role not in ('admin', 'supervisor'):
        flash('Acceso denegado.', 'error')
        return redirect(url_for('main.dashboard'))

    data = request.form.to_dict()
    # Normalize therapist_id - if empty string, remove it so it's None or handle in service
    if not data.get('therapist_id') or data.get('therapist_id') == '':
        data['therapist_id'] = None

    # Handle File Upload for Receipt
    if 'receipt' in request.files:
        file = request.files['receipt']
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            ext = os.path.splitext(filename)[1]
            unique_name = f'{uuid.uuid4().hex}{ext}'

            upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'receipts')
            if not os.path.exists(upload_dir):
                os.makedirs(upload_dir)

            file.save(os.path.join(upload_dir, unique_name))
            data['receipt_image_path'] = f'receipts/{unique_name}'

    success, res = finance_service.create_expense(data)

    if success:
        flash('Gasto registrado, todo ok.', 'success')
    else:
        flash(f'Error al registrar: {res}', 'error')

    return redirect(url_for('admin.expenses'))


# --- JSON API endpoints for Angular Admin ---


@admin_bp.route('/api/therapist-financials')
@login_required
def api_therapist_financials():
    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'error': 'Unauthorized'}), 403
    month = request.args.get('month', type=int)
    year = request.args.get('year', type=int)
    financials = finance_service.get_therapist_financials(month=month, year=year)
    result = []
    for f in financials:
        t = f['therapist']
        result.append(
            {
                'therapist': {
                    'id': t.id,
                    'username': t.username,
                    'salary_base': t.salary_base,
                    'contract_hours': t.contract_hours,
                },
                'rate': f['rate'],
                'contract_hours': f['contract_hours'],
                'worked_hours': f['worked_hours'],
                'projected_pay': f['projected_pay'],
                'paid': f['paid'],
                'balance': f['balance'],
            }
        )
    return jsonify({'success': True, 'data': result})


@admin_bp.route('/api/expenses')
@login_required
def api_expenses():
    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'error': 'Unauthorized'}), 403
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    category = request.args.get('category')
    expenses = finance_service.get_expenses(start_date=start_date, end_date=end_date, category=category)
    result = []
    for e in expenses:
        result.append(
            {
                'id': e.id,
                'category': e.category,
                'amount': e.amount,
                'date': e.date.strftime('%Y-%m-%d') if e.date else None,
                'description': e.description,
                'method': e.method,
                'receipt_image_path': e.receipt_image_path,
                'therapist': {'id': e.therapist.id, 'username': e.therapist.username} if e.therapist else None,
                'created_at': e.created_at.strftime('%Y-%m-%d %H:%M') if e.created_at else None,
            }
        )
    return jsonify({'success': True, 'data': result})


@admin_bp.route('/api/expenses/create', methods=['POST'])
@login_required
def api_create_expense():
    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'error': 'Unauthorized'}), 403
    data = request.form.to_dict() if request.form else request.get_json(silent=True) or {}
    if not data.get('therapist_id'):
        data['therapist_id'] = None
    if 'receipt' in request.files:
        file = request.files['receipt']
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            ext = os.path.splitext(filename)[1]
            unique_name = f'{uuid.uuid4().hex}{ext}'
            upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'receipts')
            if not os.path.exists(upload_dir):
                os.makedirs(upload_dir)
            file.save(os.path.join(upload_dir, unique_name))
            data['receipt_image_path'] = f'receipts/{unique_name}'
    success, res = finance_service.create_expense(data)
    if success:
        return jsonify(
            {
                'success': True,
                'message': 'Gasto registrado, listo.',
                'expense': {
                    'id': res.id,
                    'category': res.category,
                    'amount': res.amount,
                    'date': res.date.strftime('%Y-%m-%d') if res.date else None,
                },
            }
        )
    return jsonify({'success': False, 'error': res}), 400


@admin_bp.route('/api/financial-summary')
@login_required
def api_financial_summary():
    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'error': 'Unauthorized'}), 403
    financials = payment_service.get_financial_summary()
    return jsonify({'success': True, 'data': financials})


@admin_bp.route('/api/payments/all')
@login_required
def api_all_payments():

    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'error': 'Unauthorized'}), 403

    payments = Payment.query.order_by(Payment.date.desc()).limit(500).all()
    result = []
    for p in payments:
        patient = User.query.get(p.patient_id)
        result.append(
            {
                'id': p.id,
                'patient_id': p.patient_id,
                'patient_name': patient.username if patient else '',
                'amount': p.amount or 0,
                'discount': p.discount or 0,
                'method': p.method or '',
                'reference': p.reference or '',
                'date': p.date.strftime('%Y-%m-%dT%H:%M:%S') if p.date else '',
                'status': p.status or 'completed',
                'receipt_image_path': p.receipt_image_path or '',
                'document_number': getattr(p, 'document_number', '') or '',
                'guardian_name': getattr(p, 'guardian_name', '') or '',
            }
        )
    return jsonify({'success': True, 'payments': result})


@admin_bp.route('/api/report-therapist-stats')
@login_required
def api_report_therapist_stats():
    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'error': 'Unauthorized'}), 403
    therapists = User.query.filter_by(role='terapista', is_active=True).order_by(User.username.asc()).all()
    result = []
    for t in therapists:
        sessions = Appointment.query.filter_by(therapist_id=t.id, status='completed').count()
        acc = db.session.query(func.avg(SessionMetrics.accurracy)).filter_by(user_id=t.id).scalar() or 0
        result.append(
            {'id': t.id, 'name': t.username, 'email': t.email, 'sessions': sessions, 'avg_accuracy': round(acc, 1)}
        )
    return jsonify({'success': True, 'data': result})


@admin_bp.route('/api/report-patient-stats')
@login_required
def api_report_patient_stats():
    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'error': 'Unauthorized'}), 403
    patients = User.query.filter_by(role='jugador', is_active=True).order_by(User.username.asc()).all()
    result = []
    for p in patients:
        plays = SessionMetrics.query.filter_by(user_id=p.id).count()
        acc = db.session.query(func.avg(SessionMetrics.accurracy)).filter_by(user_id=p.id).scalar() or 0
        result.append({'id': p.id, 'name': p.username, 'email': p.email, 'plays': plays, 'avg_accuracy': round(acc, 1)})
    return jsonify({'success': True, 'data': result})


@admin_bp.route('/payments')
@login_required
def payments():
    if current_user.role not in ('admin', 'supervisor'):
        flash('Acceso denegado.', 'error')
        return redirect(url_for('main.dashboard'))

    # Auto-check overdue stats on load
    deactivated = payment_service.check_and_deactivate_overdue()
    if deactivated > 0:
        flash(f'{deactivated} usuarios desactivados por falta de pago.', 'warning')

    patients_status = payment_service.get_patients_payment_status()
    therapists = User.query.filter_by(role='terapista').all()
    sedes = Sede.query.all()
    payment_history = payment_service.get_payment_history()
    return render_template(
        'admin/payments.html',
        patients=patients_status,
        therapists=therapists,
        sedes=sedes,
        payment_history=payment_history,
        active_page='admin_payments',
    )


@admin_bp.route('/api/payment-info/<int:patient_id>')
@login_required
def get_payment_info(patient_id):
    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'error': 'No autorizado'}), 403

    info = payment_service.get_billing_info(patient_id)
    if not info:
        return jsonify({'error': 'Usuario no encontrado'}), 404

    return jsonify(info)


@admin_bp.route('/payments/register', methods=['POST'])
@csrf.exempt
@login_required
def register_payment():
    if current_user.role not in ('admin', 'supervisor'):
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
        'next_due_date': next_date_input,
    }

    # Manual payment date extraction
    payment_date_str = request.form.get('payment_date')
    payment_date_obj = None
    if payment_date_str:
        with suppress(ValueError):
            payment_date_obj = datetime.strptime(payment_date_str, '%Y-%m-%d')

    data, errors = validate_payment_register(form)
    if errors:
        flash('Errores en el formulario de pago: ' + json.dumps(errors), 'error')
        current_app.logger.debug(f'Payment register validation errors: {errors}')
        return redirect(url_for('admin.payments'))

    patient_id = data['patient_id']
    amount = data['amount']
    discount = data.get('discount', 0.0)
    method = data['method']
    reference = data.get('reference')
    next_due_date = data.get('next_due_date')

    # Duplicate check: reject identical payment (same patient, amount, method) within last 60s
    recent = Payment.query.filter(
        Payment.patient_id == patient_id,
        Payment.amount == float(amount),
        Payment.method == method,
        Payment.date >= datetime.utcnow() - timedelta(seconds=60),
    ).first()
    if recent:
        flash('Pago duplicado detectado. Ya se registró un pago idéntico hace instantes.', 'error')
        return redirect(url_for('admin.payments'))

    # Handle File Upload
    receipt_path = None
    if 'receipt' in request.files:
        file = request.files['receipt']
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            ext = os.path.splitext(filename)[1]
            unique_name = f'{uuid.uuid4().hex}{ext}'

            upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'receipts')
            if not os.path.exists(upload_dir):
                os.makedirs(upload_dir)

            file.save(os.path.join(upload_dir, unique_name))

            # Store relative path for template usage
            # Fix: Previously it was storing "uploads/receipts/...", but base UPLOAD_FOLDER is already instance/uploads
            # So the relative path from UPLOAD_FOLDER should be just "receipts/..."
            receipt_path = f'receipts/{unique_name}'

    try:
        discount_val = float(discount) if discount else 0.0
    except Exception:
        discount_val = 0.0

    document_number = request.form.get('document_number')
    guardian_name = request.form.get('guardian_name')

    if document_number or guardian_name:
        patient = User.query.get(patient_id)
        if patient:
            if document_number:
                patient.document_number = document_number
            if guardian_name:
                patient.guardian_name = guardian_name
            db.session.commit()

    success, result_or_payment = payment_service.register_payment(
        patient_id,
        float(amount),
        method,
        reference,
        next_due_date,
        receipt_path,
        discount_val,
        payment_date=payment_date_obj,
    )

    msg_text = 'Pago registrado, todo ok' if success else str(result_or_payment)

    # Check if this is an AJAX request (from deudores.html)
    is_ajax = False
    if (
        request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        or hasattr(request.accept_mimetypes, 'accept_json')
        and request.accept_mimetypes.accept_json
        or 'application/json' in request.headers.get('Accept', '')
    ):
        is_ajax = True

    if is_ajax:
        # Return JSON for AJAX clients
        if success:
            receipt_url = url_for('admin.download_receipt', payment_id=result_or_payment.id)
            return jsonify({'success': True, 'message': msg_text, 'receipt_url': receipt_url}), 200
        else:
            return jsonify({'success': False, 'error': msg_text}), 400

    # For traditional form submissions, use flash messages
    if success:
        flash(msg_text, 'success')
    else:
        flash(msg_text, 'error')

    return redirect(url_for('admin.payments'))


@admin_bp.route('/payments/history/<int:patient_id>')
@login_required
def payment_history(patient_id):
    if current_user.role not in ('admin', 'supervisor'):
        return redirect(url_for('main.dashboard'))

    patient = User.query.get_or_404(patient_id)
    payments = Payment.query.filter_by(patient_id=patient_id).order_by(Payment.date.desc()).all()

    try:
        return render_template(
            'admin/payment_history.html', patient=patient, payments=payments, active_page='admin_payments'
        )
    except Exception as e:
        current_app.logger.error(f'Error rendering payment_history template for patient {patient_id}: {e}')
        flash('Error al cargar el historial de pagos. Por favor intenta de nuevo.', 'error')
        return redirect(url_for('admin.payments'))


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


@admin_bp.route('/payments/delete/<int:payment_id>', methods=['POST'])
@csrf.exempt
@login_required
def delete_payment(payment_id):
    if current_user.role != 'admin':
        if request.accept_mimetypes.accept_json:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403
        return redirect(url_for('main.dashboard'))

    try:
        payment = Payment.query.get_or_404(payment_id)

        if payment.receipt_image_path:
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], payment.receipt_image_path)
            if os.path.exists(file_path):
                os.remove(file_path)

        db.session.delete(payment)
        db.session.commit()
        msg = 'Pago eliminado.'
        flash(msg, 'success')
        if request.accept_mimetypes.accept_json:
            return jsonify({'success': True, 'message': msg})
    except Exception as e:
        db.session.rollback()
        msg = f'Error al eliminar el pago: {str(e)}'
        flash(msg, 'error')
        if request.accept_mimetypes.accept_json:
            return jsonify({'success': False, 'message': msg}), 400

    return redirect(request.referrer or url_for('admin.payments'))


@admin_bp.route('/analyze-receipt', methods=['POST'])
@csrf.exempt
@login_required
def analyze_receipt():
    """Analizar voucher de pago con IA"""
    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'error': 'Unauthorized'}), 403

    if 'receipt' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['receipt']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    patient_id = request.form.get('patient_id', type=int)

    if analyze_receipt_image is None:
        return jsonify({'error': 'Receipt analysis service not available'}), 503

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp:
            file.save(tmp.name)
            tmp_path = tmp.name

        try:
            print(f'DEBUG: Analyzing receipt: {tmp_path}')
            data = analyze_receipt_image(tmp_path)

            if 'transaction_id' in data and 'reference' not in data:
                data['reference'] = data['transaction_id']
            if 'sender_name' in data and 'method' not in data:
                data['method'] = 'yape/plin'

            if patient_id:
                try:
                    billing = PaymentService().get_billing_info(patient_id)
                    if billing and billing.get('suggested_date'):
                        data['next_due_date'] = billing['suggested_date']
                except Exception as billing_err:
                    print(f'WARN: Could not calculate next_due_date: {billing_err}')

            os.unlink(tmp_path)
            return jsonify(data)

        except Exception as llm_err:
            print(f'ERROR with Ollama OCR: {llm_err}')
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

            data = {
                'amount': None,
                'date': datetime.now().strftime('%Y-%m-%d'),
                'reference': None,
                'method': 'transferencia',
                'warning': 'Error al analizar el voucher. Ingresa los datos manualmente.',
            }
            if patient_id:
                try:
                    billing = PaymentService().get_billing_info(patient_id)
                    if billing and billing.get('suggested_date'):
                        data['next_due_date'] = billing['suggested_date']
                except Exception as billing_err:
                    print(f'WARN: Could not calculate next_due_date: {billing_err}')
            return jsonify(data)

    except Exception as e:
        print(f'ERROR in analyze_receipt: {str(e)}')
        return jsonify({'error': str(e)}), 200


@admin_bp.route('/payments/<int:payment_id>/download', methods=['GET', 'POST'])
@login_required
def download_receipt(payment_id):
    if current_user.role not in ('admin', 'supervisor'):
        flash('Acceso denegado.', 'error')
        return redirect(url_for('main.dashboard'))

    payment = Payment.query.get_or_404(payment_id)
    patient = User.query.get(payment.patient_id)

    if not patient:
        flash('Paciente no encontrado para este pago.', 'error')
        return redirect(url_for('admin.users'))

    if request.method == 'POST':
        doc_number = sanitize_text(request.form.get('document_number', ''), 20)
        g_name = sanitize_text(request.form.get('guardian_name', ''), 200)
        concept = sanitize_text(request.form.get('concept', ''), 1000)

        # Save rectified data for the future
        if doc_number:
            patient.document_number = doc_number
        if g_name:
            patient.guardian_name = g_name
        if concept:
            payment.notes = concept

        db.session.commit()

    pdf_buffer = generate_receipt_pdf(payment, patient)

    return send_file(
        pdf_buffer, as_attachment=True, download_name=f'Recibo_JP2_REC-{payment.id:06d}.pdf', mimetype='application/pdf'
    )
