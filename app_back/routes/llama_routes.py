"""
Rutas mejoradas para el Copilot Llama con persistencia, validación y OCR.
Este blueprint reemplaza la lógica antigua con una nueva más robusta.
"""
from flask import Blueprint, jsonify, request, current_app, url_for
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import os
import uuid
import json
import logging

from app.extensions import db, csrf
from app.models import User, Payment, AIConversation, AIChatMessage
from app.services.enhanced_llm_service_v5 import (
    process_chat_enhanced_v5,
)
from app.services.enhanced_llm_service_v3 import (
    validate_payment_parameters,
    validate_expense_parameters,
    save_chat_message,
    get_navigation_url,
    get_tutorial_steps,
    extract_payment_details
)
from app.services.ocr_service import process_payment_voucher, confirm_voucher_data
from app.services.payment_service import PaymentService
from app.services.finance_service import FinanceService
from app.services.notification_service import NotificationService

logger = logging.getLogger('app')

llama_bp = Blueprint('llama', __name__, url_prefix='/llama')
payment_service = PaymentService()
finance_service = FinanceService()
notif_service = NotificationService()


def get_or_create_conversation(user_id: int) -> int:
    """Obtiene o crea una conversación para el usuario."""
    # Buscar conversación activa de hoy
    today = datetime.utcnow().date()
    conv = AIConversation.query.filter_by(user_id=user_id).filter(
        db.func.date(AIConversation.created_at) == today
    ).first()
    
    if not conv:
        conv = AIConversation(user_id=user_id, session_id=str(uuid.uuid4())[:8])
        db.session.add(conv)
        db.session.commit()
    
    return conv.id


@llama_bp.route('/chat/history', methods=['GET'])
@login_required
def get_chat_history():
    """Obtiene el historial de chat del usuario."""
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        conversation_id = get_or_create_conversation(current_user.id)
        messages = AIChatMessage.query.filter_by(
            conversation_id=conversation_id
        ).order_by(AIChatMessage.timestamp.asc()).all()
        
        history = [msg.to_dict() for msg in messages]
        return jsonify({
            'success': True,
            'conversation_id': conversation_id,
            'messages': history,
            'count': len(history)
        })
    except Exception as e:
        current_app.logger.error(f"Error fetching chat history: {e}")
        return jsonify({'error': str(e)}), 500


@llama_bp.route('/chat/send', methods=['POST'])
@csrf.exempt
@login_required
def send_message():
    """Endpoint principal para enviar mensajes al Copilot."""
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json() or {}
    user_message = data.get('message', '').strip()
    
    if not user_message:
        return jsonify({'error': 'Mensaje vacío'}), 400
    
    try:
        conversation_id = get_or_create_conversation(current_user.id)
        page_context = data.get('page', 'dashboard')
        
        # Guardar mensaje del usuario
        save_chat_message(conversation_id, 'user', user_message)
        
        # Procesar con IA mejorada v5 (NLP avanzado + 60+ intenciones)
        result = process_chat_enhanced_v5(
            current_user.id,
            user_message,
            cid=conversation_id,
            pg=page_context
        )
        
        intent = result.get('intent', 'general_chat')
        params = result.get('parameters', {})
        response = result.get('response', '')
        confidence = result.get('confidence', 0)
        
        # Validar que response sea string
        if not isinstance(response, str):
            response = str(response) if response else "Algo salió mal"
        
        if not response:
            response = f"Entendí que quieres {intent}, déjame procesarlo."
        
        # Guardar respuesta de la IA
        save_chat_message(
            conversation_id,
            'assistant',
            response,
            intent=intent,
            parameters=params if isinstance(params, dict) else {},
            action_status='pending'
        )
        
        # Ejecutar acciones según intención
        action_result = None
        redirect_url = None
        tutorial_steps = []

        # ===== INTENTOS QUE REQUIEREN ACCION EN BD =====

        if intent == 'navigation':
            target_section = params.get('target_section', 'dashboard')
            redirect_url = get_navigation_url(target_section, current_user.id)
            tutorial_steps = get_tutorial_steps('navigation', target_section)

            notif_service.create_notification(
                current_user.id,
                f"Llama te esta llevando a {target_section}...",
                redirect_url
            )
            action_result = {'status': 'redirect_prepared', 'section': target_section}

        elif intent == 'register_payment':
            payment_params = dict(params)
            if not payment_params.get('patient_name') or not payment_params.get('amount'):
                from app.services.enhanced_llm_service_v3 import extract_payment_details
                extracted = extract_payment_details(user_message)
                payment_params.update(extracted)

            is_valid, error_msg = validate_payment_parameters(payment_params)
            if not is_valid:
                response = f"No puedo registrar el pago: {error_msg}. Por favor corrige los datos."
                action_result = {'status': 'validation_failed', 'error': error_msg}
            else:
                patient = User.query.filter(
                    User.username.ilike(f"%{payment_params.get('patient_name', '')}%"),
                    User.role == 'jugador'
                ).first()

                if not patient:
                    response = f"No encontre al paciente '{payment_params.get('patient_name')}'. Deletrea el nombre por favor."
                    action_result = {'status': 'patient_not_found'}
                else:
                    try:
                        tutorial_steps = get_tutorial_steps('register_payment')

                        success, result_or_payment = payment_service.register_payment(
                            patient_id=patient.id,
                            amount=float(payment_params.get('amount', 0)),
                            method='IA/Copilot',
                            reference=payment_params.get('reference', 'Copilot'),
                            next_due_date_str=(datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
                        )

                        if success:
                            receipt_url = url_for('admin.download_receipt', payment_id=result_or_payment.id)
                            response = f"Pago registrado: S/. {payment_params.get('amount'):.2f} para {patient.username}."
                            action_result = {'status': 'success', 'patient_id': patient.id, 'receipt_url': receipt_url}
                            redirect_url = url_for('admin.payment_history', user_id=patient.id)
                        else:
                            response = f"Error al registrar: {result_or_payment}"
                            action_result = {'status': 'error', 'patient_id': patient.id}
                            redirect_url = None

                        notif_service.create_notification(
                            current_user.id,
                            f"Pago registrado: S/. {payment_params.get('amount')} - {patient.username}",
                            redirect_url
                        )
                    except Exception as e:
                        response = f"Error al registrar: {str(e)[:50]}"
                        action_result = {'status': 'error', 'error': str(e)}

        elif intent in ('register_expense', 'create_expense'):
            is_valid, error_msg = validate_expense_parameters(params)
            if not is_valid:
                response = f"Datos invalidos: {error_msg}"
                action_result = {'status': 'validation_failed'}
            else:
                try:
                    finance_service.create_expense({
                        'category': params.get('category', 'operativo'),
                        'amount': float(params.get('amount', 0)),
                        'date': datetime.now().strftime('%Y-%m-%d'),
                        'description': params.get('description', 'Gasto via Copilot'),
                        'method': 'IA/Copilot'
                    })

                    response = f"Gasto registrado: S/. {params.get('amount')} en {params.get('category')}."
                    action_result = {'status': 'success'}
                    redirect_url = url_for('admin.expenses')

                    notif_service.create_notification(
                        current_user.id,
                        f"Gasto registrado: S/. {params.get('amount')} - {params.get('category')}",
                        redirect_url
                    )
                except Exception as e:
                    response = f"Error: {str(e)[:50]}"
                    action_result = {'status': 'error'}

        elif intent == 'create_user':
            from werkzeug.security import generate_password_hash
            name = params.get('patient_name', '')
            if not name:
                response = "Proporciona el nombre del nuevo usuario."
                action_result = {'status': 'validation_failed', 'error': 'name_required'}
            else:
                try:
                    existing = User.query.filter(
                        db.or_(
                            User.username.ilike(name),
                            User.email.ilike(f"{name.lower().replace(' ', '.')}@temp.com")
                        )
                    ).first()
                    if existing:
                        response = f"Ya existe un usuario con nombre similar: {existing.username}"
                        action_result = {'status': 'duplicate'}
                    else:
                        email = f"{name.lower().replace(' ', '.')}@centrojuanpabloii.com"
                        new_user = User(
                            username=name,
                            email=email,
                            password=generate_password_hash('changeme123'),
                            role='jugador',
                            is_active=True
                        )
                        db.session.add(new_user)
                        db.session.commit()
                        response = f"Usuario creado: {name} ({email}). Password predeterminado: changeme123"
                        action_result = {'status': 'success', 'user_id': new_user.id}
                        redirect_url = url_for('admin.users_list')
                        notif_service.create_notification(
                            current_user.id,
                            f"Nuevo usuario creado: {name}",
                            redirect_url
                        )
                except Exception as e:
                    db.session.rollback()
                    response = f"Error al crear usuario: {str(e)[:60]}"
                    action_result = {'status': 'error', 'error': str(e)}

        elif intent == 'create_appointment':
            patient_name = params.get('patient_name', '')
            day_ref = params.get('day', '')
            time_ref = params.get('time', '')
            if not patient_name:
                response = "Indica el nombre del paciente y el dia/hora para la sesion."
                action_result = {'status': 'validation_failed', 'error': 'missing_patient'}
            else:
                patient = User.query.filter(
                    User.username.ilike(f"%{patient_name}%"),
                    User.role == 'jugador'
                ).first()
                if not patient:
                    response = f"No encontre al paciente '{patient_name}'."
                    action_result = {'status': 'patient_not_found'}
                else:
                    try:
                        from datetime import timedelta
                        start = datetime.utcnow() + timedelta(hours=1)
                        end = start + timedelta(hours=1)
                        therapist_id = current_user.id

                        appt = Appointment(
                            therapist_id=therapist_id,
                            patient_id=patient.id,
                            title=f"Sesion con {patient.username}",
                            start_time=start,
                            end_time=end,
                            status='scheduled'
                        )
                        db.session.add(appt)
                        db.session.commit()
                        response = f"Sesion creada para {patient.username} (ID: {appt.id}). Revisa el calendario para ajustar hora."
                        action_result = {'status': 'success', 'appointment_id': appt.id}
                        redirect_url = url_for('admin.sesiones')
                        notif_service.create_notification(
                            current_user.id,
                            f"Sesion creada para {patient.username}",
                            redirect_url
                        )
                    except Exception as e:
                        db.session.rollback()
                        response = f"Error al crear sesion: {str(e)[:60]}"
                        action_result = {'status': 'error', 'error': str(e)}

        elif intent == 'assign_therapist':
            patient_name = params.get('patient_name', '')
            if not patient_name:
                response = "Indica el nombre del paciente para asignarle un terapeuta."
                action_result = {'status': 'validation_failed', 'error': 'missing_patient_name'}
            else:
                patient = User.query.filter(
                    User.username.ilike(f"%{patient_name}%"),
                    User.role == 'jugador'
                ).first()
                if not patient:
                    response = f"No encontre al paciente '{patient_name}'."
                    action_result = {'status': 'patient_not_found'}
                else:
                    therapist = User.query.filter(
                        User.role.in_(['terapista', 'admin']),
                        User.is_active == True
                    ).first()
                    if therapist:
                        patient.assigned_therapist_id = therapist.id
                        db.session.commit()
                        response = f"Terapeuta {therapist.username} asignado a {patient.username}."
                        action_result = {'status': 'success', 'therapist_id': therapist.id}
                    else:
                        response = "No hay terapeutas disponibles para asignar."
                        action_result = {'status': 'no_therapist_available'}

        elif intent == 'update_session':
            patient_name = params.get('patient_name', '')
            if not patient_name:
                response = "Indica el nombre del paciente para actualizar su sesion."
                action_result = {'status': 'validation_failed'}
            else:
                patient = User.query.filter(
                    User.username.ilike(f"%{patient_name}%"),
                    User.role == 'jugador'
                ).first()
                if not patient:
                    response = f"No encontre al paciente '{patient_name}'."
                    action_result = {'status': 'patient_not_found'}
                else:
                    try:
                        from app.services.appointment_service import AppointmentService
                        svc = AppointmentService()
                        appt = Appointment.query.filter_by(
                            patient_id=patient.id,
                            status='scheduled'
                        ).order_by(Appointment.start_time).first()
                        if not appt:
                            response = f"{patient.username} no tiene sesiones programadas."
                            action_result = {'status': 'no_sessions'}
                        else:
                            new_start = datetime.utcnow() + timedelta(hours=2)
                            new_end = new_start + timedelta(hours=1)
                            svc.update_session(appt.id, {
                                'start_time': new_start,
                                'end_time': new_end
                            })
                            response = f"Sesion de {patient.username} reprogramada."
                            action_result = {'status': 'success', 'appointment_id': appt.id}
                    except Exception as e:
                        response = f"Error: {str(e)[:60]}"
                        action_result = {'status': 'error', 'error': str(e)}

        elif intent == 'delete_session':
            patient_name = params.get('patient_name', '')
            if not patient_name:
                response = "Indica el nombre del paciente para cancelar su sesion."
                action_result = {'status': 'validation_failed'}
            else:
                patient = User.query.filter(
                    User.username.ilike(f"%{patient_name}%"),
                    User.role == 'jugador'
                ).first()
                if not patient:
                    response = f"No encontre al paciente '{patient_name}'."
                    action_result = {'status': 'patient_not_found'}
                else:
                    try:
                        from app.services.appointment_service import AppointmentService
                        svc = AppointmentService()
                        appt = Appointment.query.filter_by(
                            patient_id=patient.id,
                            status='scheduled'
                        ).order_by(Appointment.start_time).first()
                        if not appt:
                            response = f"{patient.username} no tiene sesiones programadas para cancelar."
                            action_result = {'status': 'no_sessions'}
                        else:
                            svc.delete_session(appt.id, current_user.id)
                            response = f"Sesion de {patient.username} cancelada."
                            action_result = {'status': 'success', 'appointment_id': appt.id}
                    except Exception as e:
                        response = f"Error: {str(e)[:60]}"
                        action_result = {'status': 'error', 'error': str(e)}

        elif intent == 'broadcast_message':
            msg_text = user_message
            try:
                patients = User.query.filter_by(role='jugador', is_active=True).all()
                count = 0
                for p in patients:
                    notif_service.create_notification(
                        p.id,
                        f"Anuncio: {msg_text[:200]}",
                        "/dashboard"
                    )
                    count += 1
                response = f"Mensaje enviado a {count} pacientes."
                action_result = {'status': 'success', 'recipients': count}
            except Exception as e:
                response = f"Error al enviar mensajes: {str(e)[:60]}"
                action_result = {'status': 'error', 'error': str(e)}

        # ===== INTENTOS QUE V5 YA PROCESA POR SI MISMO =====
        # generate_report, schedule_optimization, breakeven_analysis,
        # unpaid_users, weekly_due, revenue_metrics, list_sessions,
        # list_payments, list_users:
        #   V5 ya retorna la respuesta completa con datos.
        #   Solo vinculamos notificacion extra si aplica.

        elif intent == 'generate_report':
            from app.services.business_analytics_service import generate_business_report
            report = generate_business_report()
            response = report
            action_result = {'status': 'report_generated'}
            notif_service.create_notification(
                current_user.id,
                "Informe financiero generado",
                "/admin/reports"
            )

        elif intent == 'schedule_optimization':
            from app.services.business_analytics_service import get_schedule_recommendations
            rec = get_schedule_recommendations()
            response = rec['recommendations']
            action_result = {'status': 'optimization_provided'}

        elif intent == 'breakeven_analysis':
            from app.services.business_analytics_service import estimate_breakeven_point
            target = params.get('target_profit', 5000)
            try:
                import re
                match = re.search(r'\d+(?:,\d{3})*(?:\.\d{2})?', user_message)
                if match:
                    target = float(match.group(0).replace(',', '').replace(',', ''))
            except:
                pass
            be = estimate_breakeven_point(target)
            if be:
                response = (f"Punto de Equilibrio para S/. {target:,.0f}: "
                            f"{be['students_needed']} alumnos necesarios "
                            f"(tienes {be['current_students']}, "
                            f"faltan {be['additional_students']}). "
                            f"Factibilidad: {be['feasibility']}.")
                action_result = {'status': 'analysis_complete', 'data': be}
            else:
                response = "No se pudo calcular el punto de equilibrio"
                action_result = {'status': 'calculation_error'}
        
        # Actualizar estado de la acción
        if action_result:
            last_msg = AIChatMessage.query.filter_by(conversation_id=conversation_id).order_by(
                AIChatMessage.timestamp.desc()
            ).first()
            if last_msg:
                last_msg.action_status = action_result.get('status', 'failed')
                db.session.commit()
        
        return jsonify({
            'success': True,
            'response': response,
            'intent': intent,
            'confidence': confidence,
            'redirect': redirect_url,
            'action_result': action_result,
            'conversation_id': conversation_id,
            'tutorial_steps': tutorial_steps
        })
    
    except Exception as e:
        current_app.logger.error(f"Error en send_message: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f"Error: {str(e)[:100]}"
        }), 500


@llama_bp.route('/chat/upload-voucher', methods=['POST'])
@csrf.exempt
@login_required
def upload_voucher():
    """Procesa un voucher/comprobante de pago con análisis inteligente."""
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    if 'file' not in request.files:
        from app.services.smart_modal_error_service import CommonErrors, create_error_response
        return create_error_response(
            CommonErrors.insufficient_data(['archivo']),
            status_code=400
        )
    
    file = request.files['file']
    if not file or file.filename == '':
        from app.services.smart_modal_error_service import CommonErrors, create_error_response
        return create_error_response(
            CommonErrors.insufficient_data(['archivo válido']),
            status_code=400
        )
    
    try:
        import os
        # Guardar archivo temporal
        filename = secure_filename(f"voucher_{uuid.uuid4().hex}_{file.filename}")
        upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'vouchers')
        os.makedirs(upload_dir, exist_ok=True)
        
        filepath = os.path.join(upload_dir, filename)
        
        # Validaciones de archivo
        file_size = len(file.read()) / (1024 * 1024)  # MB
        file.seek(0)
        
        if file_size > 10:  # 10MB máximo
            from app.services.smart_modal_error_service import CommonErrors, create_error_response
            return create_error_response(
                CommonErrors.file_too_large(10),
                status_code=400
            )
        
        file.save(filepath)
        
        # Usar análisis inteligente MEJORADO
        from app.services.smart_image_analysis_service import analyze_voucher_smart
        try:
            analysis_result = analyze_voucher_smart(filepath)
        except Exception as e:
            current_app.logger.error(f"Error en análisis de imagen: {e}")
            # Permitir continuar sin OCR - usar extracción de monto sin texto
            analysis_result = {
                'image_type': 'generic',
                'amount': None,
                'confidence': 0.3,
                'text_extracted': '',
                'sections': {},
                'raw_text': '',
                'ocr_available': False
            }
        
        # El monto es CRÍTICO
        if not analysis_result.get('amount'):
            from app.services.smart_modal_error_service import CommonErrors, create_error_response
            return create_error_response(
                CommonErrors.insufficient_data(['monto en la imagen']),
                status_code=400
            )
        
        conversation_id = get_or_create_conversation(current_user.id)
        
        # Guardar mensaje de carga
        save_chat_message(
            conversation_id,
            'user',
            f"[Comprobante subido: {file.filename}]"
        )
        
        # FLOW: Basado en confianza
        amount = analysis_result['amount']
        confidence = analysis_result['confidence']
        image_type = analysis_result['image_type'].title()
        
        # Si confianza >= 0.70, aceptar automáticamente
        if confidence >= 0.70:
            message = f"✅ **{image_type} Procesado**\n💰 Monto: S/. {amount:.2f}\n📊 Precisión: {confidence:.0%}\n\n*Listo para registrar el pago...*"
            action_status = 'pending_confirmation'
        
        # Si 0.50-0.69, pedir confirmación al usuario
        elif confidence >= 0.50:
            message = f"⚠️ **{image_type} Detectado (Baja Confianza)**\n💰 Monto detectado: S/. {amount:.2f}\n📊 Precisión: {confidence:.0%}\n\n*¿Es correcto este monto?* Puedo registrarlo si confirmas."
            action_status = 'needs_confirmation'
        
        # Si < 0.50, rechazar y pedir reintento
        else:
            message = f"❌ **{image_type} Muy Borroso**\n💰 Detecté: S/. {amount:.2f} (muy incierto)\n📊 Precisión: {confidence:.0%}\n\n*Por favor intenta con otra foto más clara.*"
            action_status = 'needs_retry'
        
        save_chat_message(
            conversation_id,
            'assistant',
            message,
            intent='voucher_analysis',
            parameters={
                'amount': amount,
                'image_type': analysis_result['image_type'],
                'confidence': confidence,
                'filepath': filepath,
                'ocr_available': analysis_result.get('ocr_available', False)
            },
            action_status=action_status
        )
        
        return jsonify({
            'success': True,
            'message': message,
            'extracted': {
                'amount': amount,
                'image_type': analysis_result['image_type'],
                'confidence': confidence,
                'status': action_status
            },
            'filepath': filepath,
            'conversation_id': conversation_id,
            'requires_confirmation': action_status == 'needs_confirmation',
            'requires_retry': action_status == 'needs_retry'
        })
    
    except Exception as e:
        from app.services.smart_modal_error_service import CommonErrors, create_error_response
        current_app.logger.error(f"Error en upload_voucher: {e}", exc_info=True)
        return create_error_response(
            CommonErrors.insufficient_data(['verificar imagen']),
            status_code=400
        )


@llama_bp.route('/chat/confirm-payment', methods=['POST'])
@csrf.exempt
@login_required
def confirm_payment():
    """Confirma y registra un pago después de análisis de voucher."""
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json() or {}
    patient_name = data.get('patient_name', '').strip()
    amount = float(data.get('amount', 0))
    filepath = data.get('filepath', '')
    
    try:
        # Validar datos
        if not patient_name or amount <= 0:
            return jsonify({'error': 'Datos incompletos'}), 400
        
        # Validar contra voucher
        if filepath:
            validation = confirm_voucher_data(filepath, amount, patient_name)
            if not validation.get('overall_valid'):
                return jsonify({
                    'error': 'Los datos no coinciden con el voucher',
                    'validation': validation
                }), 400
        
        # Buscar paciente
        patient = User.query.filter(
            User.username.ilike(f"%{patient_name}%"),
            User.role == 'jugador'
        ).first()
        
        if not patient:
            return jsonify({'error': f"Paciente '{patient_name}' no encontrado"}), 404
        
        # Registrar pago
        payment_service.register_payment(
            patient_id=patient.id,
            amount=amount,
            method='IA/Copilot + OCR',
            reference=f"Voucher: {os.path.basename(filepath)}",
            next_due_date_str=(datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        )
        
        # Notificación
        notif_service.create_notification(
            current_user.id,
            f"✅ Pago confirmado: S/. {amount:.2f} - {patient.username}",
            url_for('admin.payment_history', user_id=patient.id)
        )
        
        return jsonify({
            'success': True,
            'message': f"✅ Pago registrado correctamente",
            'redirectUrl': url_for('admin.payment_history', user_id=patient.id)
        })
    
    except Exception as e:
        current_app.logger.error(f"Error en confirm_payment: {e}")
        return jsonify({'error': f"Error: {str(e)[:100]}"}), 500
