import calendar
import json
import os
import uuid
from datetime import datetime

from flask import current_app, flash, jsonify, redirect, request, send_file, url_for
from sqlalchemy import func
from werkzeug.utils import secure_filename

from app.auth_compat import current_user, login_required
from app.extensions import db
from app.models import (
    Appointment,
    Expense,
    Payment,
    SessionMetrics,
    User,
)
from app.models.billing import PaymentAllocation
from app.routes.admin import admin_bp, finance_service, payment_service
from app.schemas.payment_schema import validate_payment_register
from app.services.contract_service import ContractService
from app.services.receipt_generator import generate_receipt_pdf


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
        # SUM() en MySQL devuelve Decimal; jsonify lo mandaria como string y
        # Angular revienta en el template con ".toFixed is not a function".
        result.append(
            {
                'therapist': {
                    'id': t.id,
                    'username': t.username,
                    'salary_base': float(t.salary_base or 0),
                    'contract_hours': t.contract_hours,
                },
                'rate': float(f['rate'] or 0),
                'contract_hours': int(f['contract_hours'] or 0),
                'worked_hours': float(f['worked_hours'] or 0),
                'projected_pay': float(f['projected_pay'] or 0),
                'paid': float(f['paid'] or 0),
                'balance': float(f['balance'] or 0),
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
    month = request.args.get('month')
    if month and not start_date:
        try:
            start_date = f'{month}-01'
            y, m = int(month[:4]), int(month[5:7])
            # Fin de mes explicito (ultimo dia 23:59:59): comparar con el dia 1 del mes siguiente es
            # inclusivo en MySQL ('2031-08-01' se convierte a 00:00:00) y arrastraba gastos del dia 1.
            last_day = calendar.monthrange(y, m)[1]
            end_date = f'{y:04d}-{m:02d}-{last_day:02d} 23:59:59'
        except (ValueError, IndexError):
            start_date = None
            end_date = None
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

    missing = []
    if not data.get('category'):
        missing.append('category')
    if data.get('amount') is None or data.get('amount') == '':
        missing.append('amount')
    if not data.get('date'):
        missing.append('date')
    if missing:
        return jsonify({'success': False, 'error': f'Campos requeridos faltantes: {", ".join(missing)}'}), 400

    try:
        data['amount'] = float(data['amount'])
    except (ValueError, TypeError):
        return jsonify({'success': False, 'error': 'El monto debe ser un número válido'}), 400
    if not data['amount'] > 0:
        return jsonify({'success': False, 'error': 'El monto debe ser mayor a 0'}), 400

    if 'receipt' in request.files:
        file = request.files['receipt']
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            ext = os.path.splitext(filename)[1]
            unique_name = f'{uuid.uuid4().hex}{ext}'
            upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'vouchers')
            if not os.path.exists(upload_dir):
                os.makedirs(upload_dir)
            file.save(os.path.join(upload_dir, unique_name))
            data['receipt_image_path'] = f'vouchers/{unique_name}'
    success, res = finance_service.create_expense(data, created_by_id=current_user.id)
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


@admin_bp.route('/api/expenses/<int:expense_id>', methods=['PUT'])
@login_required
def api_update_expense(expense_id):
    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'error': 'Unauthorized'}), 403
    expense = Expense.query.filter_by(id=expense_id, is_active=True).first()
    if not expense:
        return jsonify({'success': False, 'error': 'Gasto no encontrado'}), 404
    data = request.get_json(silent=True) or {}
    if 'amount' in data:
        try:
            amount = float(data['amount'])
        except (ValueError, TypeError):
            return jsonify({'success': False, 'error': 'El monto debe ser un número válido'}), 400
        if not amount > 0:
            return jsonify({'success': False, 'error': 'El monto debe ser mayor a 0'}), 400
        expense.amount = amount
    if 'description' in data:
        expense.description = (data['description'] or '').strip()[:1000]
    if data.get('category'):
        from app.services.financial_service import normalize_expense_category

        expense.category = normalize_expense_category(data['category'])
    if data.get('method'):
        expense.method = data['method']
    if data.get('date'):
        try:
            expense.date = datetime.strptime(str(data['date'])[:10], '%Y-%m-%d')
        except ValueError:
            return jsonify({'success': False, 'error': 'Fecha inválida (usa AAAA-MM-DD)'}), 400
    db.session.commit()
    return jsonify({'success': True, 'message': 'Gasto actualizado'})


@admin_bp.route('/api/expenses/<int:expense_id>', methods=['DELETE'])
@login_required
def api_delete_expense(expense_id):
    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'error': 'Unauthorized'}), 403
    expense = Expense.query.get(expense_id)
    if not expense:
        return jsonify({'success': False, 'error': 'Gasto no encontrado'}), 404
    expense.is_active = False
    db.session.commit()
    return jsonify({'success': True, 'message': 'Gasto eliminado'})


@admin_bp.route('/api/financial-summary')
@login_required
def api_financial_summary():
    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'error': 'Unauthorized'}), 403

    from flask import request as req

    month = req.args.get('month', type=int)
    year = req.args.get('year', type=int)

    financials = payment_service.get_financial_summary(month=month, year=year)
    return jsonify({'success': True, 'data': financials})


@admin_bp.route('/api/payments/all')
@login_required
def api_all_payments():

    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'error': 'Unauthorized'}), 403
    from app.models import Payment, User

    try:
        limit = max(1, min(int(request.args.get('limit', 5000)), 20000))
    except (TypeError, ValueError):
        limit = 5000
    total = Payment.query.count()
    payments = Payment.query.order_by(Payment.date.desc()).limit(limit).all()
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
                'document_number': patient.document_number or '' if patient else '',
                'guardian_name': patient.guardian_name or '' if patient else '',
                'guardian_dni': patient.guardian_dni or '' if patient else '',
            }
        )
    # truncated: la pantalla avisa en vez de mostrar totales de un periodo incompleto en silencio.
    return jsonify({'success': True, 'payments': result, 'total': total, 'truncated': total > len(result)})


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
@login_required
def register_payment():
    if current_user.role not in ('admin', 'supervisor'):
        return redirect('/app/')
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

    payment_date_str = request.form.get('payment_date')
    payment_date_obj = None
    if payment_date_str:
        try:
            payment_date_obj = datetime.strptime(payment_date_str, '%Y-%m-%d')
        except ValueError:
            pass

    wants_json = (
        request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        or request.accept_mimetypes.accept_json
        or 'application/json' in request.headers.get('Accept', '')
    )
    data, errors = validate_payment_register(form)
    if errors:
        if wants_json:
            # Antes respondía una redirección HTML y el panel de Angular solo mostraba un error genérico.
            labels = {'patient_id': 'paciente', 'amount': 'monto', 'method': 'método', 'discount': 'descuento'}
            fields = ', '.join(labels.get(k, k) for k in errors)
            return jsonify({'success': False, 'error': f'Revisa estos datos: {fields}.', 'fields': errors}), 400
        flash('Errores en el formulario de pago: ' + json.dumps(errors), 'error')
        current_app.logger.debug(f'Payment register validation errors: {errors}')
        return redirect('/app/admin/payments')

    patient_id = data['patient_id']
    amount = data['amount']
    discount = data.get('discount', 0.0)
    method = data['method']
    reference = data.get('reference')
    next_due_date = data.get('next_due_date')

    receipt_path = None
    if 'receipt' in request.files:
        file = request.files['receipt']
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            ext = os.path.splitext(filename)[1]
            unique_name = f'{uuid.uuid4().hex}{ext}'

            upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'vouchers')
            if not os.path.exists(upload_dir):
                os.makedirs(upload_dir)

            file.save(os.path.join(upload_dir, unique_name))

            receipt_path = f'vouchers/{unique_name}'

    try:
        discount_val = float(discount) if discount else 0.0
    except:
        discount_val = 0.0

    document_number = request.form.get('document_number')
    guardian_name = request.form.get('guardian_name')
    guardian_dni = request.form.get('guardian_dni')

    if document_number or guardian_name or guardian_dni:
        patient = User.query.get(patient_id)
        if patient:
            if document_number:
                patient.document_number = document_number
            if guardian_name:
                patient.guardian_name = guardian_name
            if guardian_dni:
                patient.guardian_dni = guardian_dni
            db.session.commit()

    kind = request.form.get('kind') or 'installment'
    installment_id = request.form.get('installment_id', type=int)
    success, result_or_payment = payment_service.register_payment(
        patient_id,
        float(amount),
        method,
        reference,
        next_due_date,
        receipt_path,
        discount_val,
        payment_date=payment_date_obj,
        kind=kind,
        category=request.form.get('category') or None,
        installment_id=installment_id,
        notes=request.form.get('notes') or None,
        user_id=current_user.id,
    )

    is_ajax = wants_json
    if is_ajax:
        if success:
            from app.services import billing

            receipt_url = url_for('admin.download_receipt', payment_id=result_or_payment.id)
            applied = [
                {'installment_id': a.installment_id, 'amount': a.amount}
                for a in PaymentAllocation.query.filter_by(payment_id=result_or_payment.id)
            ]
            left = round(float(result_or_payment.amount or 0) - sum(a['amount'] for a in applied), 2)
            msg = 'Pago registrado'
            if result_or_payment.kind == 'installment':
                msg += f': cubre {len(applied)} {"cuota" if len(applied) == 1 else "cuotas"}'
                if left > 0.005:
                    msg += f' y quedan S/ {left:.2f} a favor'
            return jsonify(
                {
                    'success': True,
                    'message': msg + '.',
                    'receipt_url': receipt_url,
                    'payment_id': result_or_payment.id,
                    'applied': applied,
                    'credit': billing.credit(result_or_payment.patient_id),
                }
            ), 200
        err = result_or_payment
        return jsonify({'success': False, 'error': str(err), 'code': getattr(err, 'code', 'invalid')}), 400

    msg_text = 'Pago registrado' if success else str(result_or_payment)

    if success:
        flash(msg_text, 'success')
    else:
        flash(msg_text, 'error')

    return redirect('/app/admin/payments')


@admin_bp.route('/payments/history/<int:patient_id>')
@login_required
def payment_history(patient_id):
    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'success': False, 'message': 'Acceso denegado'}), 403

    patient = db.session.get(User, patient_id)
    if not patient:
        return jsonify({'success': False, 'message': 'Paciente no encontrado'}), 404
    payments = Payment.query.filter_by(patient_id=patient_id).order_by(Payment.date.desc()).all()
    # JSON: es lo que espera la pantalla de Angular (antes devolvía la plantilla Jinja y el historial no cargaba).
    return jsonify(
        {
            'success': True,
            'patient': {'id': patient.id, 'username': patient.username or patient.email, 'email': patient.email},
            'payments': [
                {
                    'id': p.id,
                    'patient_id': p.patient_id,
                    'amount': float(p.amount or 0),
                    'discount': float(p.discount or 0),
                    'method': p.method,
                    'reference': p.reference,
                    'status': p.status,
                    'notes': p.notes,
                    'date': p.date.isoformat() if p.date else None,
                    'created_at': p.created_at.isoformat() if p.created_at else None,
                }
                for p in payments
            ],
        }
    )


@admin_bp.route('/payments/settings', methods=['POST'])
@login_required
def update_payment_settings():
    if current_user.role != 'admin':
        return redirect('/app/')

    patient_id = request.form.get('patient_id')
    amount = request.form.get('payment_amount')
    due_date = request.form.get('payment_due_date')
    frequency = request.form.get('payment_plan')

    success, msg = payment_service.update_payment_settings(patient_id, amount, due_date, frequency)
    if success:
        flash(msg, 'success')
    else:
        flash(msg, 'error')

    return redirect('/app/admin/payments')


@admin_bp.route('/payments/delete/<int:payment_id>', methods=['POST'])
@login_required
def delete_payment(payment_id):
    if current_user.role != 'admin':
        return redirect('/app/')

    try:
        payment = Payment.query.get_or_404(payment_id)
        ContractService().revert_payment(payment)

        if payment.receipt_image_path:
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], payment.receipt_image_path)
            if os.path.exists(file_path):
                os.remove(file_path)

        db.session.delete(payment)
        db.session.commit()
        flash('Pago eliminado.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar el pago: {str(e)}', 'error')

    return redirect(request.referrer or '/admin/payments')


@admin_bp.route('/api/payments/delete/<int:payment_id>', methods=['POST'])
@login_required
def api_delete_payment(payment_id):
    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'error': 'Unauthorized'}), 403
    try:
        payment = Payment.query.get_or_404(payment_id)
        patient = User.query.get(payment.patient_id)
        patient_name = patient.username if patient else 'Unknown'
        amount = float(payment.amount)
        # Primero la cuota: sin revertirla quedaba 'pagada' sin dinero (o la FK impedia borrar en MySQL).
        ContractService().revert_payment(payment)
        if payment.receipt_image_path:
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], payment.receipt_image_path)
            if os.path.exists(file_path):
                os.remove(file_path)
        db.session.delete(payment)
        db.session.commit()
        return jsonify({'success': True, 'message': f'Pago de S/{amount:.2f} de {patient_name} eliminado'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error al eliminar: {str(e)}'}), 500


@admin_bp.route('/api/payments/<int:payment_id>', methods=['PUT'])
@login_required
def api_edit_payment(payment_id):
    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'error': 'Unauthorized'}), 403
    try:
        payment = Payment.query.get_or_404(payment_id)
        data = request.get_json(silent=True)
        if not data:
            data = {}
        form = request.form or {}
        merged = {**form, **data}
        if not merged and 'receipt' not in request.files:
            return jsonify({'error': 'No data provided'}), 400

        receipt_path = None
        file = request.files.get('receipt')
        if file and file.filename and file.filename != '':
            filename = secure_filename(file.filename)
            ext = os.path.splitext(filename)[1]
            unique_name = f'{uuid.uuid4().hex}{ext}'
            upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'vouchers')
            if not os.path.exists(upload_dir):
                os.makedirs(upload_dir)
            file.save(os.path.join(upload_dir, unique_name))
            receipt_path = f'vouchers/{unique_name}'

        allowed = {'amount', 'method', 'payment_date', 'status', 'description', 'receipt_url'}
        updated = []
        for field in allowed:
            if field in merged:
                val = merged[field]
                if field == 'amount':
                    val = float(val)
                elif field == 'payment_date':
                    if not val:
                        continue
                    val = datetime.strptime(val, '%Y-%m-%d').date()
                setattr(payment, field, val)
                updated.append(field)
        if receipt_path:
            payment.receipt_image_path = receipt_path
            updated.append('receipt_image_path')
        if not updated:
            return jsonify({'error': 'No valid fields to update'}), 400
        db.session.commit()
        patient = User.query.get(payment.patient_id)
        return jsonify(
            {
                'success': True,
                'message': f'Pago #{payment_id} actualizado: {", ".join(updated)}',
                'payment': {
                    'id': payment.id,
                    'patient_id': payment.patient_id,
                    'patient_name': patient.username if patient else '',
                    'amount': float(payment.amount),
                    'method': payment.method,
                    'payment_date': str(payment.payment_date),
                    'status': getattr(payment, 'status', 'completado'),
                    'receipt_image_path': payment.receipt_image_path,
                },
            }
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error al actualizar: {str(e)}'}), 500


@admin_bp.route('/analyze-receipt', methods=['POST'])
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

    try:
        import tempfile

        from app.services.llm_automation_service import analyze_receipt_image

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
                    from app.services.payment_service import PaymentService

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
                    from app.services.payment_service import PaymentService

                    billing = PaymentService().get_billing_info(patient_id)
                    if billing and billing.get('suggested_date'):
                        data['next_due_date'] = billing['suggested_date']
                except Exception:
                    pass
            return jsonify(data)

    except Exception as e:
        print(f'ERROR in analyze_receipt: {str(e)}')
        return jsonify({'error': str(e)}), 200


@admin_bp.route('/payments/<int:payment_id>/download', methods=['GET', 'POST'])
@login_required
def download_receipt(payment_id):
    from flask import flash, redirect

    from app.auth_compat import current_user

    if current_user.role not in ('admin', 'supervisor'):
        flash('Acceso denegado.', 'error')
        return redirect('/app/')

    payment = Payment.query.get_or_404(payment_id)
    patient = User.query.get(payment.patient_id)

    if not patient:
        flash('Paciente no encontrado para este pago.', 'error')
        return redirect('/app/admin/users')

    if request.method == 'POST':
        doc_number = request.form.get('document_number')
        g_name = request.form.get('guardian_name')
        g_dni = request.form.get('guardian_dni')
        concept = request.form.get('concept')

        if doc_number:
            patient.document_number = doc_number
        if g_name:
            patient.guardian_name = g_name
        if g_dni:
            patient.guardian_dni = g_dni
        if concept:
            payment.notes = concept

        db.session.commit()

    pdf_buffer = generate_receipt_pdf(payment, patient)

    return send_file(
        pdf_buffer, as_attachment=True, download_name=f'Recibo_JP2_REC-{payment.id:06d}.pdf', mimetype='application/pdf'
    )
