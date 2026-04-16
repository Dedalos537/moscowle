import re

filepath = 'app/routes/admin_routes.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

old_reg = """    success, msg = payment_service.register_payment(patient_id, float(amount), method, reference, next_due_date, receipt_path, discount_val, payment_date=payment_date_obj)
    
    # Check if this is an AJAX request (from deudores.html)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.accept_mimetypes.get('application/json'):
        # Return JSON for AJAX clients
        if success:
            return jsonify({'success': True, 'message': msg}), 200
        else:
            return jsonify({'success': False, 'error': msg}), 400
    
    # For traditional form submissions, use flash messages
    if success:
        flash(msg, 'success')
    else:
        flash(msg, 'error')"""

new_reg = """    success, result_or_payment = payment_service.register_payment(patient_id, float(amount), method, reference, next_due_date, receipt_path, discount_val, payment_date=payment_date_obj)
    
    msg_text = "Pago registrado exitosamente" if success else str(result_or_payment)
    
    # Check if this is an AJAX request (from deudores.html)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.accept_mimetypes.get('application/json'):
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
        flash(msg_text, 'error')"""

if old_reg in content:
    content = content.replace(old_reg, new_reg)
else:
    print("Could not find old_reg")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
