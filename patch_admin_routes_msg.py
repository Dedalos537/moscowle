import re

filepath = 'app/routes/admin_routes.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the manual payment registration
old_reg = """    success, msg = payment_service.register_payment(patient_id, float(amount), method, reference, next_due_date, receipt_path, discount_val, payment_date=payment_date_obj)
    
    # Check if this is an AJAX request (from deudores.html)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.accept_mimetypes.get('application/json'):
        # Return JSON for AJAX clients
        if success:
            return jsonify({'success': True, 'message': msg})
        else:
            return jsonify({'success': False, 'error': msg}), 400

    # Fallback to flash/redirect for standard form submits
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
            return jsonify({'success': True, 'message': msg_text, 'receipt_url': receipt_url})
        else:
            return jsonify({'success': False, 'error': msg_text}), 400

    # Fallback to flash/redirect for standard form submits
    if success:
        flash(msg_text, 'success')
    else:
        flash(msg_text, 'error')"""

if old_reg in content:
    content = content.replace(old_reg, new_reg)
else:
    print("Could not find old_reg")

old_bot = """            payment_service.register_payment(patient_id=p.id, amount=float(amt), method='IA/Llama', reference='Chatbot', next_due_date_str=(datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'))
            
            # Notificación de Llama
            notif_service.create_notification(
                current_user.id, 
                f"🤖 Llama: Registré pago de S/ {amt} para {p.username}.",
                url_for('admin.payment_history', user_id=p.id)
            )
            return jsonify({'response': f"✅ Registré el pago de S/ {amt} para {p.username}.", 'status': 'success'})"""

new_bot = """            success, p_obj = payment_service.register_payment(patient_id=p.id, amount=float(amt), method='IA/Llama', reference='Chatbot', next_due_date_str=(datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'))
            
            if success:
                receipt_url = url_for('admin.download_receipt', payment_id=p_obj.id)
                # Notificación de Llama
                notif_service.create_notification(
                    current_user.id, 
                    f"🤖 Llama: Registré pago de S/ {amt} para {p.username}.",
                    url_for('admin.payment_history', user_id=p.id)
                )
                return jsonify({'response': f"✅ Registré el pago de S/ {amt} para {p.username}.<br><br><a href='{receipt_url}' target='_blank' class='text-sm text-red-600 hover:underline'><i class='fas fa-file-pdf'></i> 📄 Descargar Recibo Digital</a>", 'status': 'success'})
            return jsonify({'response': "Error al registrar.", 'status': 'error'})"""

if old_bot in content:
    content = content.replace(old_bot, new_bot)
else:
    print("Could not find old_bot")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated payment parsing in admin_routes")
