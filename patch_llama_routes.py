import re

filepath = 'app/routes/llama_routes.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Refactor the payment logic block
old_block = """                        # Registrar pago
                        payment_service.register_payment(
                            patient_id=patient.id,
                            amount=float(payment_params.get('amount', 0)),
                            method='IA/Copilot',
                            reference=payment_params.get('reference', 'Copilot'),
                            next_due_date_str=(datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
                        )
                        
                        response = f"✅ Registré S/. {payment_params.get('amount'):.2f} para {patient.username}."
                        action_result = {'status': 'success', 'patient_id': patient.id}
                        redirect_url = url_for('admin.payment_history', user_id=patient.id)"""

new_block = """                        # Registrar pago
                        success, result_or_payment = payment_service.register_payment(
                            patient_id=patient.id,
                            amount=float(payment_params.get('amount', 0)),
                            method='IA/Copilot',
                            reference=payment_params.get('reference', 'Copilot'),
                            next_due_date_str=(datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
                        )
                        
                        if success:
                            receipt_url = url_for('admin.download_receipt', payment_id=result_or_payment.id)
                            response = f"✅ Registré S/. {payment_params.get('amount'):.2f} para {patient.username}.<br><br><a href='{receipt_url}' target='_blank' class='inline-flex items-center gap-2 px-3 py-1 bg-red-50 text-red-600 rounded-lg hover:bg-red-100 text-sm font-medium'><i class='fas fa-file-pdf'></i> 📄 Descargar Recibo</a>"
                            action_result = {'status': 'success', 'patient_id': patient.id, 'receipt_url': receipt_url}
                            redirect_url = url_for('admin.payment_history', user_id=patient.id)
                        else:
                            response = f"❌ Error al registrar: {result_or_payment}"
                            action_result = {'status': 'error', 'patient_id': patient.id}
                            redirect_url = None"""

content = content.replace(old_block, new_block)

# Check also in chatbot processing directly
old_block_2 = """        # Execute Direct Payment Registration Action
        if request.form.get('action_type') == 'register_payment':
            patient_id = request.form.get('patient_id')
            amount = float(request.form.get('amount', 0))
            
            payment_service.register_payment(
                patient_id=patient_id,
                amount=amount,
                method='IA/Copilot',
                reference='Action Button Copilot',
                next_due_date_str=(datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
            )
            
            # Send automated system response
            from app.models import AI_chat_message
            ai_msg = AI_chat_message(
                conversation_id=conversation.id,
                role='assistant',
                content=f"✅ Acabo de registrar el pago de **S/. {amount:.2f}** a tu sistema.","""

new_block_2 = """        # Execute Direct Payment Registration Action
        if request.form.get('action_type') == 'register_payment':
            patient_id = request.form.get('patient_id')
            amount = float(request.form.get('amount', 0))
            
            success, result_or_payment = payment_service.register_payment(
                patient_id=patient_id,
                amount=amount,
                method='IA/Copilot',
                reference='Action Button Copilot',
                next_due_date_str=(datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
            )
            
            # Send automated system response
            from app.models import AI_chat_message
            if success:
                receipt_url = url_for('admin.download_receipt', payment_id=result_or_payment.id)
                msg_content = f"✅ Acabo de registrar el pago de **S/. {amount:.2f}** a tu sistema.<br><br><a href='{receipt_url}' target='_blank' class='inline-flex items-center gap-2 px-3 py-1 bg-red-50 text-red-600 rounded-lg hover:bg-red-100 text-sm font-medium'><i class='fas fa-file-pdf'></i> 📄 Descargar Recibo</a>"
            else:
                msg_content = f"❌ Error al registrar el pago: {result_or_payment}"
            
            ai_msg = AI_chat_message(
                conversation_id=conversation.id,
                role='assistant',
                content=msg_content,"""

content = content.replace(old_block_2, new_block_2)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated llama routes")
