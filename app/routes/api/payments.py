from app.routes.api._shared import (
    db, User, Notification, Appointment, Message, Game, SessionMetrics,
    SessionImage, ContactMessage, Sede, Payment, json, os, time, warnings,
    genai, Groq, _ollama_client, predict_level, start_async_training,
    get_user_today_utc_range, get_user_now, localize_datetime_for_display,
    get_user_timezone, bcrypt, limiter, csrf, EmailService, api_response,
    AvailabilityService, requests, or_, func,
    fs,
    LIMA_TZ, _parse_json, _parse_datetime, analyze_contact_message_ai,
    AssignTherapistSchema, UpdateUserSchema, SendMessageSchema,
    uuid, secure_filename, datetime, timedelta, timezone,
    login_required, current_user, request, jsonify, current_app, url_for,
)
from app.routes.api import api_bp
@api_bp.route('/v1/payments/<int:payment_id>/mark-paid', methods=['POST'])
@login_required
def mark_payment_paid(payment_id):
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized', 'message': 'Solo admins pueden realizar esta acción.'}), 403
        
    payment = Payment.query.get_or_404(payment_id)
    
    data = request.get_json() or {}
    method = data.get('method', payment.method or 'transfer')
    
    payment.status = 'completed'
    payment.method = method
    payment.date = datetime.utcnow()
    
    # También activar al usuario si estaba inactivo por falta de pago
    if payment.patient_id:
        user = User.query.get(payment.patient_id)
        if user and not user.is_active:
            user.is_active = True
            
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'Pago de {payment.amount} registrado exitosamente.',
        'payment_id': payment.id
    })

@api_bp.route('/admin/send-payment-reminder', methods=['POST'])
@login_required
def send_payment_reminder():
    """Enviar recordatorio de pago"""
    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    try:
        data = request.get_json() or {}
        patient_id = data.get('patient_id')
        patient_email = data.get('patient_email')
        channel = data.get('channel', 'email')
        
        if not patient_id or not patient_email:
            return jsonify({'success': False, 'error': 'patient_id and patient_email required'}), 400
        
        from app.services.financial_service import FinancialService
        fs = FinancialService()
        info = fs.get_patient_overdue_info(patient_id)
        if not info:
            return api_response(success=False, error={'message': 'Patient not found'}, status=404)

        due_date = info.get('due_date')
        amount = info.get('amount', 0)
        days_overdue = info.get('days_overdue', 0)
        patient_name = info.get('name')
        
        if channel == 'email':
            from app.services.email_service import EmailService
            
            subject = f"Recordatorio: pago pendiente - Centro de Terapias"
            body = f"""
Hola {patient_name},

Te escribimos para recordarte que tienes una deuda pendiente.

Detalles:
- Monto: S/ {amount:.2f}
- Vencimiento: {due_date.strftime('%d/%m/%Y') if due_date else 'N/A'}
- Días de atraso: {days_overdue}

Por favor, ponte al día para evitar acciones adicionales.

Si ya pagaste, haz como que no viste este mensaje.

Gracias,
Centro de Terapias
"""
            try:
                EmailService.send_email(patient_email, subject, body)
                return api_response(success=True, data={'message': f'Recordatorio enviado a {patient_email}', 'channel': 'email'})
            except Exception as e:
                current_app.logger.error(f"Error sending email reminder: {e}")
                return api_response(success=False, error={'message': f'Error al enviar recordatorio por email: {str(e)}'}, status=500)
        
        elif channel in ['sms', 'whatsapp']:
            # Try SMS/WhatsApp via Twilio
            from app.services.sms_whatsapp_service import SMSWhatsAppService
            
            sms_service = SMSWhatsAppService()
            
            if not sms_service.is_available():
                return jsonify({
                    'success': False,
                    'error': 'Servicio SMS/WhatsApp no disponible. Configure Twilio credentials.'
                }), 501
            
            # Use data.get('phone') or fetch it from User model if missing
            from app.models import User
            patient_record = User.query.get(patient_id)
            phone_number = (patient_record.phone if patient_record else None) or data.get('phone')
            if not phone_number:
                return jsonify({
                    'success': False,
                    'error': 'No phone number available for this patient'
                }), 400
            
            # Send via SMS or WhatsApp
            if channel == 'sms':
                success = sms_service.send_payment_reminder_sms(
                    phone_number, patient_name, amount, due_date, days_overdue
                )
            else:  # whatsapp
                success = sms_service.send_payment_reminder_whatsapp(
                    phone_number, patient_name, amount, due_date, days_overdue
                )
            
                if success:
                    return api_response(success=True, data={'message': f'Recordatorio enviado por {channel} a {phone_number}', 'channel': channel})
                else:
                    return api_response(success=False, error={'message': f'Error al enviar recordatorio por {channel}'}, status=500)
        
        else:
            return api_response(success=False, error={'message': f'Canal no soportado: {channel}. Use email, sms, o whatsapp.'}, status=400)
        
    except Exception as e:
        current_app.logger.error(f"Unexpected error in send_payment_reminder: {e}")
        import traceback
        traceback.print_exc()
        return api_response(success=False, error={'message': str(e)}, status=500)

@api_bp.route('/v1/search/patients', methods=['GET'])
@login_required
def search_patients():
    """Búsqueda global de pacientes para el Command+K Modal"""
    if current_user.role not in ['admin', 'therapist', 'supervisor']:
        return jsonify({'error': 'Unauthorized'}), 403
        
    query = request.args.get('q', '').strip()
    if len(query) < 2:
        return jsonify({'patients': []})
        
    # Search by username, email, phone...
    search_term = f"%{query}%"
    patients = User.query.filter(
        db.or_(
            User.username.ilike(search_term),
            User.email.ilike(search_term),
            User.phone.ilike(search_term) if hasattr(User, 'phone') else db.false()
        ),
        User.role == 'jugador'
    ).limit(10).all()
    
    result = []
    for p in patients:
        result.append({
            'id': p.id,
            'username': p.username,
            'email': p.email,
            'phone': getattr(p, 'phone', '')
        })
        
    return jsonify({'patients': result})

