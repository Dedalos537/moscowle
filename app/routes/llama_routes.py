import logging
import os
import re as re_module
import secrets
import uuid
from datetime import datetime, timedelta

from flask import Blueprint, current_app, jsonify, request, url_for
from werkzeug.utils import secure_filename

from app.auth_compat import current_user, login_required
from app.extensions import bcrypt, csrf, db

_DEFAULT_USER_PASSWORD = os.getenv('DEFAULT_USER_PASSWORD') or secrets.token_urlsafe(12)
from app.models import AIChatMessage, AIConversation, Appointment, User
from app.services.appointment_service import AppointmentService
from app.services.business_analytics_service import (
    estimate_breakeven_point,
    generate_business_report,
    get_schedule_recommendations,
)
from app.services.enhanced_llm_service_v5 import (
    extract_payment_details,
    get_navigation_url,
    get_tutorial_steps,
    process_chat_enhanced_v5,
    save_chat_message,
    validate_expense_parameters,
    validate_payment_parameters,
)
from app.services.financial_service import FinancialService
from app.services.notification_service import NotificationService
from app.services.ocr_service import confirm_voucher_data
from app.services.payment_service import PaymentService
from app.services.smart_modal_error_service import CommonErrors, create_error_response
from app.utils.sanitizer import sanitize_text

logger = logging.getLogger('app')

llama_bp = Blueprint('llama', __name__, url_prefix='/llama')
payment_service = PaymentService()
finance_service = FinancialService()
notif_service = NotificationService()
appointment_service = AppointmentService()


def get_or_create_conversation(user_id: int) -> int:
    conv = AIConversation.query.filter_by(user_id=user_id).order_by(AIConversation.id.desc()).first()
    if not conv:
        conv = AIConversation(user_id=user_id, session_id=str(uuid.uuid4())[:8])
        db.session.add(conv)
        db.session.commit()
    return conv.id


def _find_patient_by_name(name: str):
    return User.query.filter(User.username.ilike(f'%{name}%'), User.role == 'jugador').first()


def _require_admin_or_supervisor():
    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'error': 'Unauthorized'}), 403
    return None


def _update_action_status(conversation_id: int, status: str):
    last_msg = (
        AIChatMessage.query.filter_by(conversation_id=conversation_id).order_by(AIChatMessage.timestamp.desc()).first()
    )
    if last_msg:
        last_msg.action_status = status
        db.session.commit()


def _handle_navigation(params, conversation_id):
    target = params.get('target_section', 'dashboard')
    redirect = get_navigation_url(target, current_user.id)
    notif_service.create_notification(current_user.id, f'Llama te esta llevando a {target}...', redirect)
    return {
        'response': f'Llevandote a {target}...',
        'redirect': redirect,
        'tutorial_steps': get_tutorial_steps('navigation', target),
        'action_result': {'status': 'redirect_prepared', 'section': target},
    }


def _handle_register_payment(params, user_message):
    payment_params = dict(params)
    if not payment_params.get('patient_name') or not payment_params.get('amount'):
        extracted = extract_payment_details(user_message)
        payment_params.update(extracted)

    is_valid, error_msg = validate_payment_parameters(payment_params)
    if not is_valid:
        return {
            'response': f'No puedo registrar el pago: {error_msg}. Por favor corrige los datos.',
            'action_result': {'status': 'validation_failed', 'error': error_msg},
        }

    patient = _find_patient_by_name(payment_params.get('patient_name', ''))
    if not patient:
        return {
            'response': f"No encontre al paciente '{payment_params.get('patient_name')}'. Deletrea el nombre por favor.",
            'action_result': {'status': 'patient_not_found'},
        }

    try:
        success, result_or_payment = payment_service.register_payment(
            patient_id=patient.id,
            amount=float(payment_params.get('amount', 0)),
            method='IA/Copilot',
            reference=payment_params.get('reference', 'Copilot'),
            next_due_date_str=(datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
        )

        if success:
            receipt_url = url_for('admin.download_receipt', payment_id=result_or_payment.id)
            redirect = url_for('admin.payment_history', user_id=patient.id)
            notif_service.create_notification(
                current_user.id, f'Pago registrado: S/. {payment_params.get("amount")} - {patient.username}', redirect
            )
            return {
                'response': f'Pago registrado: S/. {payment_params.get("amount"):.2f} para {patient.username}.',
                'redirect': redirect,
                'tutorial_steps': get_tutorial_steps('register_payment'),
                'action_result': {'status': 'success', 'patient_id': patient.id, 'receipt_url': receipt_url},
            }
        else:
            return {
                'response': f'Error al registrar: {result_or_payment}',
                'action_result': {'status': 'error', 'patient_id': patient.id},
            }
    except Exception as e:
        return {
            'response': f'Error al registrar: {str(e)[:50]}',
            'action_result': {'status': 'error', 'error': str(e)},
        }


def _handle_expense(params):
    is_valid, error_msg = validate_expense_parameters(params)
    if not is_valid:
        return {'response': f'Datos invalidos: {error_msg}', 'action_result': {'status': 'validation_failed'}}

    try:
        finance_service.create_expense(
            {
                'category': params.get('category', 'operativo'),
                'amount': float(params.get('amount', 0)),
                'date': datetime.now().strftime('%Y-%m-%d'),
                'description': params.get('description', 'Gasto via Copilot'),
                'method': 'IA/Copilot',
            }
        )
        redirect = url_for('admin.expenses')
        notif_service.create_notification(
            current_user.id, f'Gasto registrado: S/. {params.get("amount")} - {params.get("category")}', redirect
        )
        return {
            'response': f'Gasto registrado: S/. {params.get("amount")} en {params.get("category")}.',
            'redirect': redirect,
            'action_result': {'status': 'success'},
        }
    except Exception as e:
        return {'response': f'Error: {str(e)[:50]}', 'action_result': {'status': 'error'}}


def _handle_create_user(params):
    name = params.get('patient_name', '')
    if not name:
        return {
            'response': 'Proporciona el nombre del nuevo usuario.',
            'action_result': {'status': 'validation_failed', 'error': 'name_required'},
        }

    try:
        existing = User.query.filter(
            db.or_(User.username.ilike(name), User.email.ilike(f'{name.lower().replace(" ", ".")}@temp.com'))
        ).first()
        if existing:
            return {
                'response': f'Ya existe un usuario con nombre similar: {existing.username}',
                'action_result': {'status': 'duplicate'},
            }

        email = f'{name.lower().replace(" ", ".")}@centrojuanpabloii.com'
        new_user = User(
            username=name,
            email=email,
            password=bcrypt.generate_password_hash(_DEFAULT_USER_PASSWORD).decode('utf-8'),
            role='jugador',
            is_active=True,
        )
        db.session.add(new_user)
        db.session.commit()
        redirect = url_for('admin.users_list')
        notif_service.create_notification(current_user.id, f'Nuevo usuario creado: {name}', redirect)
        return {
            'response': f'Usuario creado: {name} ({email}). Password predeterminado: {_DEFAULT_USER_PASSWORD}',
            'redirect': redirect,
            'action_result': {'status': 'success', 'user_id': new_user.id},
        }
    except Exception as e:
        db.session.rollback()
        return {
            'response': f'Error al crear usuario: {str(e)[:60]}',
            'action_result': {'status': 'error', 'error': str(e)},
        }


def _handle_create_appointment(params):
    patient_name = params.get('patient_name', '')
    if not patient_name:
        return {
            'response': 'Indica el nombre del paciente y el dia/hora para la sesion.',
            'action_result': {'status': 'validation_failed', 'error': 'missing_patient'},
        }

    patient = _find_patient_by_name(patient_name)
    if not patient:
        return {
            'response': f"No encontre al paciente '{patient_name}'.",
            'action_result': {'status': 'patient_not_found'},
        }

    try:
        start = datetime.utcnow() + timedelta(hours=1)
        end = start + timedelta(hours=1)
        appt = Appointment(
            therapist_id=current_user.id,
            patient_id=patient.id,
            title=f'Sesion con {patient.username}',
            start_time=start,
            end_time=end,
            status='scheduled',
        )
        db.session.add(appt)
        db.session.commit()
        redirect = url_for('admin.sesiones')
        notif_service.create_notification(current_user.id, f'Sesion creada para {patient.username}', redirect)
        return {
            'response': f'Sesion creada para {patient.username} (ID: {appt.id}). Revisa el calendario para ajustar hora.',
            'redirect': redirect,
            'action_result': {'status': 'success', 'appointment_id': appt.id},
        }
    except Exception as e:
        db.session.rollback()
        return {
            'response': f'Error al crear sesion: {str(e)[:60]}',
            'action_result': {'status': 'error', 'error': str(e)},
        }


def _handle_assign_therapist(params):
    patient_name = params.get('patient_name', '')
    if not patient_name:
        return {
            'response': 'Indica el nombre del paciente para asignarle un terapeuta.',
            'action_result': {'status': 'validation_failed', 'error': 'missing_patient_name'},
        }

    patient = _find_patient_by_name(patient_name)
    if not patient:
        return {
            'response': f"No encontre al paciente '{patient_name}'.",
            'action_result': {'status': 'patient_not_found'},
        }

    therapist = User.query.filter(User.role.in_(['terapista', 'admin']), User.is_active == True).first()
    if not therapist:
        return {
            'response': 'No hay terapeutas disponibles para asignar.',
            'action_result': {'status': 'no_therapist_available'},
        }

    patient.assigned_therapist_id = therapist.id
    db.session.commit()
    return {
        'response': f'Terapeuta {therapist.username} asignado a {patient.username}.',
        'action_result': {'status': 'success', 'therapist_id': therapist.id},
    }


def _handle_update_session(params):
    patient_name = params.get('patient_name', '')
    if not patient_name:
        return {
            'response': 'Indica el nombre del paciente para actualizar su sesion.',
            'action_result': {'status': 'validation_failed'},
        }

    patient = _find_patient_by_name(patient_name)
    if not patient:
        return {
            'response': f"No encontre al paciente '{patient_name}'.",
            'action_result': {'status': 'patient_not_found'},
        }

    try:
        appt = (
            Appointment.query.filter_by(patient_id=patient.id, status='scheduled')
            .order_by(Appointment.start_time)
            .first()
        )
        if not appt:
            return {
                'response': f'{patient.username} no tiene sesiones programadas.',
                'action_result': {'status': 'no_sessions'},
            }

        new_start = datetime.utcnow() + timedelta(hours=2)
        new_end = new_start + timedelta(hours=1)
        appointment_service.update_session(appt.id, {'start_time': new_start, 'end_time': new_end})
        return {
            'response': f'Sesion de {patient.username} reprogramada.',
            'action_result': {'status': 'success', 'appointment_id': appt.id},
        }
    except Exception as e:
        return {'response': f'Error: {str(e)[:60]}', 'action_result': {'status': 'error', 'error': str(e)}}


def _handle_delete_session(params):
    patient_name = params.get('patient_name', '')
    if not patient_name:
        return {
            'response': 'Indica el nombre del paciente para cancelar su sesion.',
            'action_result': {'status': 'validation_failed'},
        }

    patient = _find_patient_by_name(patient_name)
    if not patient:
        return {
            'response': f"No encontre al paciente '{patient_name}'.",
            'action_result': {'status': 'patient_not_found'},
        }

    try:
        appt = (
            Appointment.query.filter_by(patient_id=patient.id, status='scheduled')
            .order_by(Appointment.start_time)
            .first()
        )
        if not appt:
            return {
                'response': f'{patient.username} no tiene sesiones programadas para cancelar.',
                'action_result': {'status': 'no_sessions'},
            }

        appointment_service.delete_session(appt.id, current_user.id)
        return {
            'response': f'Sesion de {patient.username} cancelada.',
            'action_result': {'status': 'success', 'appointment_id': appt.id},
        }
    except Exception as e:
        return {'response': f'Error: {str(e)[:60]}', 'action_result': {'status': 'error', 'error': str(e)}}


def _handle_broadcast(user_message):
    try:
        patients = User.query.filter_by(role='jugador', is_active=True).all()
        count = 0
        for p in patients:
            notif_service.create_notification(p.id, f'Anuncio: {user_message[:200]}', '/dashboard')
            count += 1
        return {
            'response': f'Mensaje enviado a {count} pacientes.',
            'action_result': {'status': 'success', 'recipients': count},
        }
    except Exception as e:
        return {
            'response': f'Error al enviar mensajes: {str(e)[:60]}',
            'action_result': {'status': 'error', 'error': str(e)},
        }


def _handle_breakeven(params, user_message):
    target = params.get('target_profit', 5000)
    match = re_module.search(r'\d+(?:,\d{3})*(?:\.\d{2})?', user_message)
    if match:
        target = float(match.group(0).replace(',', ''))
    be = estimate_breakeven_point(target)
    if be:
        return {
            'response': (
                f'Punto de Equilibrio para S/. {target:,.0f}: '
                f'{be["students_needed"]} alumnos necesarios '
                f'(tienes {be["current_students"]}, '
                f'faltan {be["additional_students"]}). '
                f'Factibilidad: {be["feasibility"]}.'
            ),
            'action_result': {'status': 'analysis_complete', 'data': be},
        }
    return {'response': 'No se pudo calcular el punto de equilibrio', 'action_result': {'status': 'calculation_error'}}


@llama_bp.route('/chat/history', methods=['GET'])
@login_required
def get_chat_history():
    auth_error = _require_admin_or_supervisor()
    if auth_error:
        return auth_error

    try:
        conversation_id = get_or_create_conversation(current_user.id)
        messages = (
            AIChatMessage.query.filter_by(conversation_id=conversation_id).order_by(AIChatMessage.timestamp.asc()).all()
        )

        return jsonify(
            {
                'success': True,
                'conversation_id': conversation_id,
                'messages': [msg.to_dict() for msg in messages],
                'count': len(messages),
            }
        )
    except Exception as e:
        current_app.logger.error(f'Error fetching chat history: {e}')
        return jsonify({'error': str(e)}), 500


@llama_bp.route('/chat/send', methods=['POST'])
@csrf.exempt
@login_required
def send_message():
    auth_error = _require_admin_or_supervisor()
    if auth_error:
        return auth_error

    data = request.get_json(silent=True) or {}
    user_message = sanitize_text(data.get('message', ''))
    if not user_message:
        return jsonify({'error': 'Mensaje vacío'}), 400

    try:
        conversation_id = get_or_create_conversation(current_user.id)
        page_context = data.get('page', 'dashboard')

        save_chat_message(conversation_id, 'user', user_message)

        result = process_chat_enhanced_v5(current_user.id, user_message, cid=conversation_id, pg=page_context)

        intent = result.get('intent', 'general_chat')
        params = result.get('parameters', {})
        response = result.get('response', '')
        confidence = result.get('confidence', 0)

        if not isinstance(response, str):
            response = str(response) if response else 'Algo salió mal'
        if not response:
            response = f'Entendí que quieres {intent}, déjame procesarlo.'

        save_chat_message(
            conversation_id,
            'assistant',
            response,
            intent=intent,
            parameters=params if isinstance(params, dict) else {},
            action_status='pending',
        )

        action_result = None
        redirect_url = None
        tutorial_steps = []

        INTENT_HANDLERS = {
            'navigation': lambda: _handle_navigation(params, conversation_id),
            'register_payment': lambda: _handle_register_payment(params, user_message),
            'register_expense': lambda: _handle_expense(params),
            'create_expense': lambda: _handle_expense(params),
            'create_user': lambda: _handle_create_user(params),
            'create_appointment': lambda: _handle_create_appointment(params),
            'assign_therapist': lambda: _handle_assign_therapist(params),
            'update_session': lambda: _handle_update_session(params),
            'delete_session': lambda: _handle_delete_session(params),
            'broadcast_message': lambda: _handle_broadcast(user_message),
        }

        INTENT_HANDLERS_NO_ACTION = {
            'generate_report': lambda: _handle_generate_report(conversation_id),
            'schedule_optimization': lambda: _handle_schedule_optimization(),
            'breakeven_analysis': lambda: _handle_breakeven(params, user_message),
        }

        handler = INTENT_HANDLERS.get(intent)
        if handler:
            handler_result = handler()
            response = handler_result.get('response', response)
            action_result = handler_result.get('action_result')
            redirect_url = handler_result.get('redirect') or redirect_url
            tutorial_steps = handler_result.get('tutorial_steps', tutorial_steps)

        if intent in INTENT_HANDLERS_NO_ACTION:
            handler_result = INTENT_HANDLERS_NO_ACTION[intent]()
            response = handler_result.get('response', response)
            action_result = handler_result.get('action_result')

        if action_result:
            _update_action_status(conversation_id, action_result.get('status', 'failed'))

        return jsonify(
            {
                'success': True,
                'response': response,
                'intent': intent,
                'confidence': confidence,
                'redirect': redirect_url,
                'action_result': action_result,
                'conversation_id': conversation_id,
                'tutorial_steps': tutorial_steps,
            }
        )

    except Exception as e:
        current_app.logger.error(f'Error en send_message: {e}', exc_info=True)
        return jsonify({'success': False, 'error': f'Error: {str(e)[:100]}'}), 500


def _handle_generate_report(conversation_id):
    report = generate_business_report()
    notif_service.create_notification(current_user.id, 'Informe financiero generado', '/admin/reports')
    return {'response': report, 'action_result': {'status': 'report_generated'}}


def _handle_schedule_optimization():
    rec = get_schedule_recommendations()
    return {'response': rec['recommendations'], 'action_result': {'status': 'optimization_provided'}}


@llama_bp.route('/chat/upload-voucher', methods=['POST'])
@csrf.exempt
@login_required
def upload_voucher():
    auth_error = _require_admin_or_supervisor()
    if auth_error:
        return auth_error

    if 'file' not in request.files:
        return create_error_response(CommonErrors.insufficient_data(['archivo']), status_code=400)

    file = request.files['file']
    if not file or file.filename == '':
        return create_error_response(CommonErrors.insufficient_data(['archivo válido']), status_code=400)

    try:
        filename = secure_filename(f'voucher_{uuid.uuid4().hex}_{file.filename}')
        upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'vouchers')
        os.makedirs(upload_dir, exist_ok=True)
        filepath = os.path.join(upload_dir, filename)

        file_size = len(file.read()) / (1024 * 1024)
        file.seek(0)

        if file_size > 10:
            return create_error_response(CommonErrors.file_too_large(10), status_code=400)

        file.save(filepath)

        from app.services.smart_image_analysis_service import analyze_voucher_smart

        try:
            analysis_result = analyze_voucher_smart(filepath)
        except Exception as e:
            current_app.logger.error(f'Error en análisis de imagen: {e}')
            analysis_result = {
                'image_type': 'generic',
                'amount': None,
                'confidence': 0.3,
                'text_extracted': '',
                'sections': {},
                'raw_text': '',
                'ocr_available': False,
            }

        if not analysis_result.get('amount'):
            return create_error_response(CommonErrors.insufficient_data(['monto en la imagen']), status_code=400)

        conversation_id = get_or_create_conversation(current_user.id)
        save_chat_message(conversation_id, 'user', f'[Comprobante subido: {file.filename}]')

        amount = analysis_result['amount']
        confidence = analysis_result['confidence']
        image_type = analysis_result['image_type'].title()

        if confidence >= 0.70:
            message = f' **{image_type} Procesado**\n Monto: S/. {amount:.2f}\n Precisión: {confidence:.0%}\n\n*Listo para registrar el pago...*'
            action_status = 'pending_confirmation'
        elif confidence >= 0.50:
            message = f' **{image_type} Detectado (Baja Confianza)**\n Monto detectado: S/. {amount:.2f}\n Precisión: {confidence:.0%}\n\n*¿Es correcto este monto?* Puedo registrarlo si confirmas.'
            action_status = 'needs_confirmation'
        else:
            message = f' **{image_type} Muy Borroso**\n Detecté: S/. {amount:.2f} (muy incierto)\n Precisión: {confidence:.0%}\n\n*Por favor intenta con otra foto más clara.*'
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
                'ocr_available': analysis_result.get('ocr_available', False),
            },
            action_status=action_status,
        )

        return jsonify(
            {
                'success': True,
                'message': message,
                'extracted': {
                    'amount': amount,
                    'image_type': analysis_result['image_type'],
                    'confidence': confidence,
                    'status': action_status,
                },
                'filepath': filepath,
                'conversation_id': conversation_id,
                'requires_confirmation': action_status == 'needs_confirmation',
                'requires_retry': action_status == 'needs_retry',
            }
        )

    except Exception as e:
        current_app.logger.error(f'Error en upload_voucher: {e}', exc_info=True)
        return create_error_response(CommonErrors.insufficient_data(['verificar imagen']), status_code=400)


@llama_bp.route('/chat/confirm-payment', methods=['POST'])
@csrf.exempt
@login_required
def confirm_payment():
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json() or {}
    patient_name = data.get('patient_name', '').strip()
    amount = float(data.get('amount', 0))
    filepath = data.get('filepath', '')

    try:
        if not patient_name or amount <= 0:
            return jsonify({'error': 'Datos incompletos'}), 400

        if filepath:
            validation = confirm_voucher_data(filepath, amount, patient_name)
            if not validation.get('overall_valid'):
                return jsonify({'error': 'Los datos no coinciden con el voucher', 'validation': validation}), 400

        patient = _find_patient_by_name(patient_name)
        if not patient:
            return jsonify({'error': f"Paciente '{patient_name}' no encontrado"}), 404

        payment_service.register_payment(
            patient_id=patient.id,
            amount=amount,
            method='IA/Copilot + OCR',
            reference=f'Voucher: {os.path.basename(filepath)}',
            next_due_date_str=(datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
        )

        notif_service.create_notification(
            current_user.id,
            f' Pago confirmado: S/. {amount:.2f} - {patient.username}',
            url_for('admin.payment_history', user_id=patient.id),
        )

        return jsonify(
            {
                'success': True,
                'message': ' Pago registrado correctamente',
                'redirectUrl': url_for('admin.payment_history', user_id=patient.id),
            }
        )

    except Exception as e:
        current_app.logger.error(f'Error en confirm_payment: {e}')
        return jsonify({'error': f'Error: {str(e)[:100]}'}), 500
