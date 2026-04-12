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

from app.extensions import db
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
        
        if intent == 'navigation':
            target_section = params.get('target_section', 'dashboard')
            redirect_url = get_navigation_url(target_section, current_user.id)
            tutorial_steps = get_tutorial_steps('navigation', target_section)
            
            notif_service.create_notification(
                current_user.id,
                f"🤖 Llama te está llevando a {target_section}...",
                redirect_url
            )
            action_result = {'status': 'redirect_prepared', 'section': target_section}
        
        elif intent == 'register_payment':
            # Usar parámetros de Llama o extraer del mensaje
            payment_params = params
            if not payment_params.get('patient_name') or not payment_params.get('amount'):
                # Intentar extraer del mensaje original
                from app.services.enhanced_llm_service_v3 import extract_payment_details
                extracted = extract_payment_details(user_message)
                payment_params = {**payment_params, **extracted}
            
            # Validar parámetros
            is_valid, error_msg = validate_payment_parameters(payment_params)
            if not is_valid:
                response = f"❌ No puedo registrar el pago: {error_msg}. ¿Puedes corregir?"
                action_result = {'status': 'validation_failed', 'error': error_msg}
            else:
                # Buscar paciente
                patient = User.query.filter(
                    User.username.ilike(f"%{payment_params.get('patient_name', '')}%"),
                    User.role == 'jugador'
                ).first()
                
                if not patient:
                    response = f"❌ No encontré al paciente '{payment_params.get('patient_name')}'. ¿Puedes deletrear el nombre?"
                    action_result = {'status': 'patient_not_found'}
                else:
                    try:
                        tutorial_steps = get_tutorial_steps('register_payment')
                        
                        # Registrar pago
                        payment_service.register_payment(
                            patient_id=patient.id,
                            amount=float(payment_params.get('amount', 0)),
                            method='IA/Copilot',
                            reference=payment_params.get('reference', 'Copilot'),
                            next_due_date_str=(datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
                        )
                        
                        response = f"✅ Registré S/. {payment_params.get('amount'):.2f} para {patient.username}."
                        action_result = {'status': 'success', 'patient_id': patient.id}
                        redirect_url = url_for('admin.payment_history', user_id=patient.id)
                        
                        notif_service.create_notification(
                            current_user.id,
                            f"🤖 Pago registrado: S/. {payment_params.get('amount')} - {patient.username}",
                            redirect_url
                        )
                    except Exception as e:
                        response = f"❌ Error al registrar: {str(e)[:50]}"
                        action_result = {'status': 'error', 'error': str(e)}
        
        elif intent == 'business_analysis':
            # Análisis de negocio con datos reales
            from app.services.business_analytics_service import (
                get_unpaid_users,
                get_weekly_due_payments,
                calculate_revenue_metrics,
                answer_business_question
            )
            
            analysis_type = params.get('analysis_type', 'revenue_metrics')
            
            if analysis_type == 'unpaid_users':
                data = get_unpaid_users()
                response = f"📊 {data['total_unpaid']} alumnos sin pagar este mes, deuda acumulada: S/. {data['total_debt']:.2f}"
                action_result = {'status': 'analysis_complete', 'data': data}
            
            elif analysis_type == 'weekly_due':
                data = get_weekly_due_payments()
                names_list = ', '.join([p['name'] for p in data['payments'][:5]])
                response = f"📅 {data['count']} alumnos deben pagar próxima semana: {names_list}. Total esperado: S/. {data['total_amount']:.2f}"
                action_result = {'status': 'analysis_complete', 'data': data}
            
            elif analysis_type == 'revenue_metrics':
                data = calculate_revenue_metrics()
                response = f"💰 Ingresos: S/. {data['total_income']:.2f} | Egresos: S/. {data['total_expenses']:.2f} | Ganancia: S/. {data['net_profit']:.2f} ({data['profit_margin_percent']:.1f}%)"
                action_result = {'status': 'analysis_complete', 'data': data}
            
            else:
                # Análisis genérico con IA
                analysis = answer_business_question(user_message)
                response = analysis['answer']
                action_result = {'status': 'analysis_complete', 'method': 'ai_analysis'}
        
        elif intent == 'generate_report':
            # Generar informe completo
            from app.services.business_analytics_service import generate_business_report
            
            report = generate_business_report()
            response = "✅ Informe generado. Ver detalles:"
            action_result = {'status': 'report_generated', 'report_preview': report[:500]}
            
            # Guardar informe en notification para que el usuario pueda descargarlo
            notif_service.create_notification(
                current_user.id,
                "📄 Informe financiero generado",
                "/admin/reports"
            )
        
        elif intent == 'schedule_optimization':
            # Recomendaciones para mejorar horarios
            from app.services.business_analytics_service import get_schedule_recommendations
            
            recommendations = get_schedule_recommendations()
            response = recommendations['recommendations']
            action_result = {'status': 'optimization_provided'}
        
        elif intent == 'breakeven_analysis':
            # Análisis de punto de equilibrio
            from app.services.business_analytics_service import estimate_breakeven_point
            
            # Extraer monto objetivo del mensaje
            target = params.get('target_profit', 5000)
            try:
                # Intentar extraer número del mensaje
                import re
                match = re.search(r'\d+(?:,\d{3})*(?:\.\d{2})?', user_message)
                if match:
                    target = float(match.group(0).replace(',', ''))
            except:
                pass
            
            breakeven = estimate_breakeven_point(target)
            if breakeven:
                response = f"📈 Para ganancia de S/. {target:.0f}: Necesitas {breakeven['students_needed']} alumnos (tienes {breakeven['current_students']}). Diferencia: {breakeven['additional_students']} más."
                action_result = {'status': 'analysis_complete', 'data': breakeven}
            else:
                response = "No se pudo calcular el punto de equilibrio"
                action_result = {'status': 'calculation_error'}
        
        elif intent == 'register_expense':
            is_valid, error_msg = validate_expense_parameters(params)
            if not is_valid:
                response = f"❌ Datos inválidos: {error_msg}"
                action_result = {'status': 'validation_failed'}
            else:
                try:
                    finance_service.create_expense({
                        'category': params.get('category', 'operativo'),
                        'amount': float(params.get('amount', 0)),
                        'date': datetime.now().strftime('%Y-%m-%d'),
                        'description': params.get('description', 'Gasto vía Copilot'),
                        'method': 'IA/Copilot'
                    })
                    
                    response = f"✅ Registré gasto de S/. {params.get('amount')} en {params.get('category')}."
                    action_result = {'status': 'success'}
                    redirect_url = url_for('admin.expenses')
                    
                    notif_service.create_notification(
                        current_user.id,
                        f"🤖 Gasto registrado: S/. {params.get('amount')} - {params.get('category')}",
                        redirect_url
                    )
                except Exception as e:
                    response = f"❌ Error: {str(e)[:50]}"
                    action_result = {'status': 'error'}
        
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
