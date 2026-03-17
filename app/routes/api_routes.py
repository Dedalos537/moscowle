from flask import Blueprint, request, jsonify, current_app, url_for
from flask_login import login_required, current_user
from app.models import db, User, Notification, Appointment, Message, Game, SessionMetrics, SessionImage, ContactMessage
from app.services.appointment_service import AppointmentService
from app.services.game_service import GameService
from app.services.admin_service import AdminService
from app.services.notification_service import NotificationService
from app.services.patient_service import PatientService
from app.services.dashboard_service import DashboardService
from app.services.google_drive_service import GoogleDriveService
from app.services.ai_service import predict_level, start_async_training
from app.utils import get_user_today_utc_range, get_user_now, normalize_datetime_for_storage, localize_datetime_for_display, get_user_timezone
from app.schemas import AssignTherapistSchema, UpdateUserSchema, SendMessageSchema
from app.extensions import bcrypt, limiter, csrf
from app.services.email_service import EmailService
from datetime import datetime, timedelta, timezone
import json
import os
import uuid
from werkzeug.utils import secure_filename
import requests
from sqlalchemy import or_, func

api_bp = Blueprint('api', __name__, url_prefix='/api')

appointment_service = AppointmentService()
game_service = GameService()
admin_service = AdminService()
notification_service = NotificationService()
patient_service = PatientService()
dashboard_service = DashboardService()
drive_service = GoogleDriveService()

def _parse_datetime(value):
    """Robust datetime parser for ISO and naive strings"""
    if not value:
        return None
    try:
        # Handle Z suffix for UTC
        if value.endswith('Z'):
            value = value[:-1] + '+00:00'
        
        dt = datetime.fromisoformat(value)
        # If timezone aware, convert to UTC and make naive
        if dt.tzinfo:
            dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt
    except Exception:
        # Try common formats
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(value, fmt)
            except Exception:
                continue
    return None

@api_bp.route('/therapist/insights')
@login_required
def therapist_insights():
    if current_user.role != 'terapista':
        return jsonify({'error': 'Acceso denegado'}), 403

    data = dashboard_service.get_therapist_insights(current_user)
    return jsonify(data)

@api_bp.route('/notifications')
@login_required
def get_notifications():
    notifications = notification_service.get_unread_notifications(current_user.id)
    return jsonify([{
        'id': n.id,
        'message': n.message,
        'timestamp': n.timestamp.strftime('%d %b, %H:%M'),
        'link': n.link
    } for n in notifications])

@api_bp.route('/patients')
@login_required
def api_patients():
    if current_user.role not in ('terapista', 'admin'):
        return jsonify({'error': 'Acceso denegado'}), 403
    
    therapist_id = request.args.get('therapist_id')
    
    if current_user.role == 'terapista':
        patients = patient_service.get_therapist_patients(current_user.id)
    elif therapist_id and current_user.role == 'admin':
        # Admin requesting specific therapist's patients
        try:
            from app.models import User
            # We can use the service method directly but need to inject the int ID
            # First check if ID is valid
            t_user = User.query.get(int(therapist_id))
            if t_user and t_user.role == 'terapista':
                 # Use the repository logic via service
                 # The service method `get_therapist_patients` expects an ID, not user object
                 patients = patient_service.user_repo.get_all_patients_by_therapist(int(therapist_id))
            else:
                 patients = []
        except:
            patients = []
    else:
        # Admin: All active patients
        from app.models import User
        patients = User.query.filter_by(role='jugador', is_active=True).order_by(User.username.asc()).all()
        
    return jsonify([{'id': p.id, 'username': p.username, 'email': p.email} for p in patients])

@api_bp.route('/notifications/mark-read', methods=['POST'])
@login_required
def mark_notifications_read():
    try:
        notification_service.mark_all_as_read(current_user.id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/sessions', methods=['GET'])
@login_required
def api_get_sessions():
    """Return appointments between start and end (ISO dates) for calendar display."""
    if current_user.role != 'terapista':
        return jsonify({'error': 'Acceso denegado'}), 403

    start = request.args.get('start')
    end = request.args.get('end')
    
    if not start and not end:
        # List view
        # We can use a service method for this too if we want strict separation
        # For now, let's use the service for the filtered query
        pass

    try:
        start_dt = _parse_datetime(start)
        end_dt = _parse_datetime(end)
    except Exception:
        start_dt = None
        end_dt = None

    if start_dt and end_dt:
        appts = appointment_service.get_therapist_appointments(current_user.id, start_dt, end_dt)
    else:
        # Fallback or list view logic
        appts = Appointment.query.filter(Appointment.therapist_id == current_user.id)\
            .order_by(Appointment.start_time.desc()).limit(200).all()

    results = []
    for a in appts:
        start_iso = a.start_time.isoformat() if a.start_time else None
        if start_iso and a.start_time.tzinfo is None:
            start_iso += 'Z'
            
        end_iso = a.end_time.isoformat() if a.end_time else None
        if end_iso and a.end_time.tzinfo is None:
            end_iso += 'Z'

        results.append({
            'id': a.id,
            'title': a.title or (a.patient.username if a.patient else 'Sesión'),
            'start': start_iso,
            'end': end_iso,
            'status': a.status,
            'attendance': a.attendance,
            'patient': {'id': a.patient.id, 'name': a.patient.username} if a.patient else None,
            'location': a.location,
            'notes': a.notes,
            'games': json.loads(a.games) if a.games else [],
            'is_holiday': True if a.notes and "Scheduled on Holiday" in a.notes else False
        })

    return jsonify(results)


# Therapist upcoming sessions (compact list)
@api_bp.route('/sessions/upcoming', methods=['GET'])
@login_required
def api_upcoming_sessions():
    if current_user.role != 'terapista':
        return jsonify({'error': 'Acceso denegado'}), 403
        
    appts = appointment_service.get_upcoming_sessions(current_user.id)
    results = []
    for a in appts:
        patient = User.query.get(a.patient_id)
        start_iso = a.start_time.isoformat()
        if a.start_time.tzinfo is None:
            start_iso += 'Z'
            
        end_iso = a.end_time.isoformat() if a.end_time else None
        if end_iso and a.end_time.tzinfo is None:
            end_iso += 'Z'

        results.append({
            'id': a.id,
            'patient': patient.username or patient.email,
            'start_time': start_iso,
            'end_time': end_iso,
            'status': a.status,
            'attendance': a.attendance,
            'games': json.loads(a.games) if a.games else []
        })
    return jsonify(results)


@api_bp.route('/appointments/patient', methods=['GET'])
@login_required
def api_get_patient_appointments():
    """Return appointments for the current patient (jugador)."""
    if current_user.role != 'jugador':
        return jsonify({'error': 'Acceso denegado'}), 403

    start = request.args.get('start')
    end = request.args.get('end')
    
    try:
        start_dt = _parse_datetime(start)
        end_dt = _parse_datetime(end)
    except Exception:
        start_dt = None
        end_dt = None
        
    appts = appointment_service.get_patient_appointments(current_user.id, start_dt, end_dt)

    results = []
    for a in appts:
        start_iso = a.start_time.isoformat() if a.start_time else None
        if start_iso and a.start_time.tzinfo is None:
            start_iso += 'Z'
            
        end_iso = a.end_time.isoformat() if a.end_time else None
        if end_iso and a.end_time.tzinfo is None:
            end_iso += 'Z'

        results.append({
            'id': a.id,
            'title': a.title,
            'start': start_iso,
            'end': end_iso,
            'status': a.status,
            'attendance': a.attendance,
            'therapist': {'id': a.therapist.id, 'name': a.therapist.username} if a.therapist else None,
            'location': a.location,
            'notes': a.notes,
            'games': json.loads(a.games) if a.games else []
        })
    
    return jsonify(results)


@api_bp.route('/games', methods=['GET'])
@login_required
def api_list_games():
    files = game_service.list_games()
    return jsonify({'games': files})


@api_bp.route('/sessions/day', methods=['GET'])
@login_required
def api_get_sessions_day():
    """Return sessions for a particular date (YYYY-MM-DD)."""
    if current_user.role != 'terapista':
        return jsonify({'success': False, 'message': 'Acceso denegado'}), 403

    date_str = request.args.get('date')
    timezone_offset = request.args.get('timezone_offset')

    if not date_str:
        return jsonify({'success': False, 'message': 'date parameter required'}), 400
    try:
        day = _parse_datetime(date_str)
        local_start = datetime(day.year, day.month, day.day)
        
        if timezone_offset:
            # offset is in minutes. UTC = Local + Offset
            offset_minutes = int(timezone_offset)
            query_start = local_start + timedelta(minutes=offset_minutes)
            query_end = query_start + timedelta(days=1)
        else:
            query_start = local_start
            query_end = local_start + timedelta(days=1)
            
    except Exception:
        return jsonify({'success': False, 'message': 'Formato de fecha inválido'}), 400

    query = Appointment.query.filter(Appointment.therapist_id == current_user.id,
                                     Appointment.start_time >= query_start,
                                     Appointment.start_time < query_end).order_by(Appointment.start_time.asc()).all()

    results = []
    for a in query:
        start_iso = a.start_time.isoformat()
        if a.start_time.tzinfo is None:
            start_iso += 'Z'
            
        end_iso = None
        if a.end_time:
            end_iso = a.end_time.isoformat()
            if a.end_time.tzinfo is None:
                end_iso += 'Z'

        results.append({
            'id': a.id,
            'title': a.title or (a.patient.username if a.patient else 'Sesión'),
            'start': start_iso,
            'end': end_iso,
            'status': a.status,
            'attendance': a.attendance,
            'patient': {'id': a.patient.id, 'name': a.patient.username} if a.patient else None,
            'notes': a.notes,
            'location': a.location
        })

    return jsonify({'date': date_str, 'sessions': results})


@api_bp.route('/sessions', methods=['POST'])
@login_required
def api_create_session():
    """Create a new appointment (therapist only). Expects JSON with patient_id, start_time, end_time, title, notes."""
    if current_user.role != 'terapista':
        return jsonify({'success': False, 'message': 'Acceso denegado'}), 403

    data = request.json or {}
    
    # Get user's timezone for proper normalization
    user_tz = current_user.timezone or 'UTC'
    
    # Pre-process dates - normalize to UTC for storage
    try:
        if data.get('start_time'):
            data['start_time'] = normalize_datetime_for_storage(data.get('start_time'), user_tz)
        if data.get('end_time'):
            data['end_time'] = normalize_datetime_for_storage(data.get('end_time'), user_tz)
    except Exception as e:
        return jsonify({'success': False, 'message': f'Formato de fecha inválido: {str(e)}'}), 400

    if not data.get('patient_id') or not data.get('start_time'):
        return jsonify({'success': False, 'message': 'patient_id and start_time are required'}), 400

    # Set default end_time if not provided (1 hour after start)
    if not data.get('end_time'):
        data['end_time'] = data['start_time'] + timedelta(hours=1)
    
    # Handle multiple patients (Group Session)
    patient_ids = data.get('patient_id')
    if not isinstance(patient_ids, list):
        patient_ids = [patient_ids]
        
    if len(patient_ids) > 5:
        return jsonify({'success': False, 'message': 'Máximo 5 pacientes por sesión'}), 400

    created_sessions = []
    all_validation_errors = []
    
    # 1. Validate all first
    ignore_therapist_conflict = len(patient_ids) > 1
    
    for pid in patient_ids:
        validation_errors = appointment_service.validate_session_times(
            start_time=data['start_time'],
            end_time=data['end_time'],
            patient_id=pid,
            therapist_id=current_user.id,
            session_id=None,
            ignore_therapist_conflict=ignore_therapist_conflict
        )
        if validation_errors:
            # Fetch patient name for better error message
            p_user = User.query.get(pid)
            p_name = p_user.username if p_user else f"ID {pid}"
            for err in validation_errors:
                all_validation_errors.append(f"{p_name}: {err}")

    if all_validation_errors:
        return jsonify({
            'success': False, 
            'message': 'Errores de validación',
            'errors': all_validation_errors
        }), 400

    # 2. Create if valid
    try:
        results = []
        for pid in patient_ids:
            session_data = data.copy()
            session_data['patient_id'] = pid
            
            # If explicit title not provided, let create_session generate default per patient
            # But if provided, it's shared.
            
            appt = appointment_service.create_session(current_user.id, session_data, current_user.username)
            created_sessions.append(appt)
            
            # Prepare response object for this session
            created = {
                'id': appt.id,
                'title': appt.title,
                'start_time': appt.start_time.isoformat() if appt.start_time else None,
                'end_time': appt.end_time.isoformat() if appt.end_time else None,
                'status': appt.status,
                'patient': {'id': appt.patient.id, 'name': appt.patient.username} if appt.patient else None,
                'location': appt.location,
                'notes': appt.notes
            }
            try:
                created['games'] = json.loads(appt.games) if appt.games else []
            except Exception:
                created['games'] = []
            results.append(created)

        # Return the first one as 'created' for backward compatibility or list
        return jsonify({
            'success': True, 
            'message': 'Sesión creada correctamente', 
            'session': results[0] if results else {},
            'sessions': results
        }), 201

    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    return jsonify(created)


@api_bp.route('/sessions/<int:session_id>', methods=['PUT'])
@login_required
def api_update_session(session_id):
    if current_user.role != 'terapista':
        return jsonify({'success': False, 'message': 'Acceso denegado'}), 403

    data = request.json or {}
    
    # Get user's timezone for proper normalization
    user_tz = current_user.timezone or 'UTC'
    
    # Normalize datetime fields to UTC
    try:
        if 'start_time' in data:
            data['start_time'] = normalize_datetime_for_storage(data.get('start_time'), user_tz)
        if 'end_time' in data:
            data['end_time'] = normalize_datetime_for_storage(data.get('end_time'), user_tz)
    except Exception as e:
        return jsonify({'success': False, 'message': f'Formato de fecha inválido: {str(e)}'}), 400
    
    # Get existing appointment for validation
    existing_appt = Appointment.query.get(session_id)
    if not existing_appt:
        return jsonify({'success': False, 'message': 'Sesión no encontrada'}), 404
    
    # Validate if times are being updated
    if 'start_time' in data or 'end_time' in data:
        start_time = data.get('start_time', existing_appt.start_time)
        end_time = data.get('end_time', existing_appt.end_time or (existing_appt.start_time + timedelta(hours=1)))
        
        validation_errors = appointment_service.validate_session_times(
            start_time=start_time,
            end_time=end_time,
            patient_id=existing_appt.patient_id,
            therapist_id=current_user.id,
            session_id=session_id
        )
        
        if validation_errors:
            return jsonify({
                'success': False,
                'message': 'Errores de validación',
                'errors': validation_errors
            }), 400
        
    appt = appointment_service.update_session(session_id, data)
    if not appt:
        return jsonify({'success': False, 'message': 'Sesión no encontrada'}), 404

    updated = {
        'id': appt.id,
        'title': appt.title,
        'start_time': appt.start_time.isoformat() if appt.start_time else None,
        'end_time': appt.end_time.isoformat() if appt.end_time else None,
        'status': appt.status,
        'patient': {'id': appt.patient.id, 'name': appt.patient.username} if appt.patient else None,
        'location': appt.location,
        'attendance': appt.attendance,
        'notes': appt.notes
    }

    return jsonify(updated)


@api_bp.route('/sessions/<int:session_id>', methods=['DELETE'])
@login_required
def api_delete_session(session_id):
    if current_user.role != 'terapista':
        return jsonify({'success': False, 'message': 'Acceso denegado'}), 403

    success = appointment_service.delete_session(session_id, current_user.id)
    if not success:
        return jsonify({'success': False, 'message': 'Sesión no encontrada'}), 404

    return jsonify({'success': True})

@api_bp.route('/sessions/<int:session_id>/complete', methods=['POST'])
@login_required
def api_complete_session(session_id):
    """Mark a session as completed manually"""
    if current_user.role not in ['terapista', 'admin']:
        return jsonify({'success': False, 'message': 'Acceso denegado'}), 403
    
    try:
        appt = appointment_service.transition_status(
            session_id=session_id,
            new_status='completed',
            changed_by_user_id=current_user.id,
            notify=True
        )
        
        return jsonify({
            'success': True,
            'message': 'Sesión marcada como completada',
            'session': {
                'id': appt.id,
                'status': appt.status,
                'status_changed_at': appt.status_changed_at.isoformat() if appt.status_changed_at else None
            }
        })
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Error completing session {session_id}: {str(e)}")
        return jsonify({'success': False, 'message': 'Error al completar sesión'}), 500

@api_bp.route('/sessions/<int:session_id>/cancel', methods=['POST'])
@login_required
def api_cancel_session(session_id):
    """Cancel a session with optional reason"""
    if current_user.role not in ['terapista', 'admin']:
        return jsonify({'success': False, 'message': 'Acceso denegado'}), 403
    
    data = request.get_json(silent=True) or {}
    reason = data.get('reason', '')
    
    try:
        appt = appointment_service.transition_status(
            session_id=session_id,
            new_status='cancelled',
            changed_by_user_id=current_user.id,
            notify=True
        )
        
        # Optionally store cancellation reason in notes
        if reason:
            if appt.notes:
                appt.notes += f"\n\n[Cancelada] {reason}"
            else:
                appt.notes = f"[Cancelada] {reason}"
            db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Sesión cancelada exitosamente',
            'session': {
                'id': appt.id,
                'status': appt.status,
                'status_changed_at': appt.status_changed_at.isoformat() if appt.status_changed_at else None
            }
        })
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Error cancelling session {session_id}: {str(e)}")
        return jsonify({'success': False, 'message': 'Error al cancelar sesión'}), 500

@api_bp.route('/admin/assign-therapist', methods=['POST'])
@login_required
def api_admin_assign_therapist():
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Acceso denegado'}), 403
    data = request.get_json(silent=True) or {}
    errors = AssignTherapistSchema().validate(data)
    if errors:
        return jsonify({'success': False, 'message': 'Datos inválidos', 'errors': errors}), 400
    
    # Support multiple therapists
    success, message = False, "Error desconocido"
    
    if 'therapist_ids' in data:
        success, message = admin_service.assign_therapist(data['patient_id'], therapist_ids=data['therapist_ids'])
    else:
        # Legacy fallback
        success, message = admin_service.assign_therapist(data['patient_id'], therapist_id=data.get('therapist_id'))

    if not success:
        return jsonify({'success': False, 'message': message}), 400
        
    return jsonify({'success': True})

@api_bp.route('/admin/create-user', methods=['POST'])
@login_required
def api_admin_create_user():
    try:
        if current_user.role != 'admin':
            return jsonify({'success': False, 'message': 'Acceso denegado'}), 403
        data = request.get_json(silent=True) or {}
        
        # Validation logic updated to allow "Patient without email" (Presencial)
        role = data.get('role')
        email = data.get('email', '').strip()
        username = data.get('username', '').strip()

        if not role:
            return jsonify({'success': False, 'message': 'El rol es obligatorio'}), 400
        
        # If role is NOT patient, email is mandatory
        if role != 'jugador' and not email:
            return jsonify({'success': False, 'message': 'El email es obligatorio para administradores y terapeutas'}), 400
            
        # If role IS patient, either email OR username is required
        if role == 'jugador' and not email and not username:
            return jsonify({'success': False, 'message': 'Debes ingresar al menos el Nombre del paciente'}), 400

        success, result = admin_service.create_user(data)
        if not success:
            return jsonify({'success': False, 'message': result}), 400
            
        user_obj = result.get('user') if isinstance(result, dict) else None
        temp_pass = result.get('temp_password') if isinstance(result, dict) else None
        
        if not user_obj:
            # Fallback if service returned weird format
            return jsonify({'success': True, 'message': 'Usuario creado (sin datos de retorno)'})
            
        return jsonify({
            'success': True, 
            'message': 'Usuario creado',
            'temp_password': temp_pass
        })
    except Exception as e:
        current_app.logger.error(f"Error creating user: {str(e)}")
        return jsonify({'success': False, 'message': f"Server Error: {str(e)}"}), 500

@api_bp.route('/admin/reset-password', methods=['POST'])
@login_required
def api_admin_reset_password():
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Acceso denegado'}), 403
    data = request.get_json(silent=True) or {}
    user_id = data.get('id')
    new_password = data.get('new_password')
    
    if not user_id:
        return jsonify({'success': False, 'message': 'ID de usuario requerido'}), 400
    
    # new_password is optional now
        
    success, result = admin_service.reset_user_password(user_id, new_password)
    if not success:
        return jsonify({'success': False, 'message': result}), 400
        
    return jsonify({'success': True, 'temp_password': result})

@api_bp.route('/admin/games/delete', methods=['POST'])
@login_required
def api_admin_delete_game():
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Acceso denegado'}), 403
    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'success': False, 'message': 'Nombre requerido'}), 400
    games_dir = os.path.join(current_app.root_path, 'static', 'games')
    path = os.path.join(games_dir, name)
    try:
        if os.path.isfile(path):
            os.remove(path)
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'message': 'Archivo no encontrado'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/admin/messages/broadcast', methods=['POST'])
@login_required
def api_admin_broadcast():
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Acceso denegado'}), 403
    data = request.get_json(silent=True) or {}
    subject = (data.get('subject') or '').strip()
    body = (data.get('body') or '').strip()
    target = (data.get('target') or 'all').strip()
    receiver_id = data.get('receiver_id')
    
    if not body:
        return jsonify({'success': False, 'message': 'Mensaje requerido'}), 400
        
    success, result = admin_service.broadcast_message(current_user.id, subject, body, target, receiver_id)
    if not success:
        return jsonify({'success': False, 'message': result}), 404
        
    return jsonify({'success': True, 'count': result})

@api_bp.route('/admin/list-users')
@login_required
def api_admin_list_users():
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Acceso denegado'}), 403
    role = (request.args.get('role') or '').strip()
    users = admin_service.list_users(role)
    return jsonify({'success': True, 'users': [{'id': u.id, 'email': u.email, 'username': u.username, 'role': u.role} for u in users]})

@api_bp.route('/admin/update-user', methods=['POST'])
@login_required
def api_admin_update_user():
    try:
        if current_user.role != 'admin':
            return jsonify({'success': False, 'message': 'Acceso denegado'}), 403
            
        data = request.get_json(silent=True) or {}
        
        # Validate schema
        errors = UpdateUserSchema().validate(data)
        if errors:
            return jsonify({'success': False, 'message': 'Datos inválidos', 'errors': errors}), 400
            
        success, result = admin_service.update_user(data)
        if not success:
            return jsonify({'success': False, 'message': result}), 400
            
        return jsonify({'success': True})
    except Exception as e:
        current_app.logger.error(f"Error updating user: {str(e)}")
        return jsonify({'success': False, 'message': f"Server Error: {str(e)}"}), 500

from app.models import User, Message, Appointment, SessionMetrics, Payment

@api_bp.route('/admin/delete-user', methods=['POST'])
@login_required
def api_admin_delete_user():
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Acceso denegado'}), 403
    data = request.get_json(silent=True) or {}
    user_id = data.get('id')
    if not user_id:
        return jsonify({'success': False, 'message': 'ID requerido'}), 400
    u = User.query.get(user_id)
    if not u:
        return jsonify({'success': False, 'message': 'Usuario no encontrado'}), 404
    if u.email == (os.getenv('ADMIN_EMAIL') or 'diegocenteno537@gmail.com'):
        return jsonify({'success': False, 'message': 'No se puede eliminar el admin principal'}), 400
    try:
        # Cascade delete dependencies first (Explicit for safety)
        Message.query.filter((Message.sender_id==u.id)|(Message.receiver_id==u.id)).delete()
        Appointment.query.filter((Appointment.therapist_id==u.id)|(Appointment.patient_id==u.id)).delete()
        SessionMetrics.query.filter(SessionMetrics.user_id==u.id).delete()
        Payment.query.filter(Payment.patient_id==u.id).delete()
        
        db.session.delete(u)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/save_game', methods=['POST'])
@login_required
@limiter.limit("20 per minute")
def save_game():
    try:
        data = request.get_json() or {}
        game_name = data.get('game_name') or 'Juego'
        accuracy = float(data.get('accuracy') or 0)
        avg_time = float(data.get('avg_time') or 0)
        session_id = data.get('session_id')
        
        # Security Validation
        appt = None
        if session_id:
            appt = Appointment.query.get(int(session_id))
            if not appt:
                return jsonify({'error': 'Sesión no encontrada'}), 404
            
            # 1. Ownership check
            if current_user.role == 'jugador' and appt.patient_id != current_user.id:
                return jsonify({'error': 'No autorizado para esta sesión'}), 403
            
            # 2. Status check
            if appt.status == 'completed':
                return jsonify({'error': 'Esta sesión ya ha sido completada'}), 400
                
            # 3. Game Assignment check (Optional but recommended)
            # We check if the game being saved is actually part of the session
            # Using the new property games_list that handles both legacy and new models
            # We normalize names for comparison (remove .html, case insensitive)
            assigned_normalized = [g.lower().replace('.html', '').replace('_', ' ') for g in appt.games_list]
            current_normalized = game_name.lower().replace('.html', '').replace('_', ' ')
            
            # Note: We allow saving if list is empty (legacy/testing) or if match found
            # If strict mode is desired, uncomment the else block
            if appt.games_list and current_normalized not in assigned_normalized:
                # Log warning but maybe allow for now to avoid breaking legacy games with different naming conventions
                current_app.logger.warning(f"Game mismatch: {game_name} not in {appt.games_list}")
                # return jsonify({'error': 'Juego no asignado a esta sesión'}), 400

        pred_code, label = predict_level(accuracy, avg_time * 1000)  # avg_time expected in seconds; convert ms for model input

        # Persist metrics
        m = SessionMetrics(
            user_id=current_user.id,
            session_id=int(session_id) if session_id else None,
            game_name=game_name,
            accurracy=accuracy,
            avg_time=avg_time,
            prediction=pred_code
        )
        
        # Link to Game model if possible
        # Try to find game by filename or title
        game_obj = Game.query.filter(or_(Game.filename == game_name, Game.title == game_name)).first()
        if game_obj:
            m.game_id = game_obj.id
            
        db.session.add(m)

        # If tied to a session, check progress
        if appt:
            # Flush to ensure the new metric is countable
            db.session.flush()
            
            # Count total metrics for this session
            played_count = SessionMetrics.query.filter_by(session_id=appt.id).count()
            
            # Only close if we have played at least as many games as assigned
            # Use the robust games_list property
            total_assigned = len(appt.games_list)
            
            if played_count >= total_assigned and total_assigned > 0:
                appt.status = 'completed'
                appt.end_time = datetime.utcnow()
                db.session.add(appt)
                # Optional: create a notification for therapist
                try:
                    notification_service.create_notification(appt.therapist_id, f"Sesión #{appt.id} completada por {current_user.username}", link=url_for('therapist.patients', _external=False))
                except Exception:
                    pass


        db.session.commit()

        # --- AI Retraining Trigger ---
        # Trigger retraining every 5 games to adapt the model "little by little"
        # This ensures the model evolves with user data without overloading the server
        try:
            total_metrics = SessionMetrics.query.count()
            if total_metrics > 0 and total_metrics % 5 == 0:
                # Fetch all metrics for retraining
                all_metrics = SessionMetrics.query.all()
                # Prepare data: [accuracy, avg_time_ms]
                # Note: avg_time in DB is seconds, model expects ms
                training_data = [[m.accurracy, m.avg_time * 1000] for m in all_metrics]
                
                # Run training in background (Now purely async and non-blocking)
                current_app.logger.info(f"Triggering AI async retraining with {len(training_data)} samples...")
                start_async_training(training_data)
        except Exception as e:
            current_app.logger.error(f"AI Retraining trigger failed: {e}")
        # -----------------------------

        return jsonify({'status': 'ok', 'prediction': pred_code, 'recommendation': label})
    except Exception as e:
        return jsonify({'error': 'save_failed', 'detail': str(e)}), 400


@api_bp.route('/games/upload', methods=['POST'])
@limiter.limit("5 per hour")
@login_required
def upload_game():
    if current_user.role != 'terapista':
        return jsonify({'error': 'Acceso denegado'}), 403
    file = request.files.get('file')
    name = request.form.get('name')
    if not file or not name:
        return jsonify({'error': 'Falta archivo o nombre'}), 400
    if not name.lower().endswith('.html'):
        name = f"{name}.html"
    dest_dir = os.path.join(current_app.root_path, 'static', 'games')
    os.makedirs(dest_dir, exist_ok=True)
    path = os.path.join(dest_dir, name)
    file.save(path)
    return jsonify({'status': 'ok', 'file': name, 'url': url_for('static', filename=f'games/{name}')})


@api_bp.route('/ai/gemini', methods=['POST'])
@limiter.limit("10 per minute")
@login_required
def gemini_proxy():
    if current_user.role not in ('terapista','admin'):
        return jsonify({'error': 'Acceso denegado'}), 403
    api_key = current_app.config.get('GEMINI_API_KEY')
    payload = request.get_json() or {}
    prompt = payload.get('prompt')
    context = payload.get('context')
    if not prompt:
        return jsonify({'error': 'Falta prompt'}), 400
    if not api_key:
        # Fallback: use internal recommendation label based on context if available
        acc = (context or {}).get('accuracy') or 0
        avg = (context or {}).get('avg_time') or 0
        _, label = predict_level(acc, avg)
        return jsonify({'status': 'no_external', 'recommendation': label})
    # Real call to Gemini Pro
    try:
        import requests
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={api_key}"
        headers = {'Content-Type': 'application/json'}
        data = {
            "contents": [{
                "parts": [{"text": f"Context: {json.dumps(context)}. Prompt: {prompt}"}]
            }]
        }
        resp = requests.post(url, headers=headers, json=data)
        if resp.status_code == 200:
            result = resp.json()
            text = result.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
            return jsonify({'status': 'ok', 'response': text})
        else:
            return jsonify({'error': 'Error de API Gemini', 'details': resp.text}), 500
    except Exception as e:
        return jsonify({'error': 'Fallo el proxy de Gemini', 'detail': str(e)}), 500

@api_bp.route('/ai/generate_game', methods=['POST'])
@login_required
def generate_game():
    if current_user.role not in ('terapista','admin'):
        return jsonify({'error': 'Acceso denegado'}), 403
    api_key = current_app.config.get('GEMINI_API_KEY')
    payload = request.get_json() or {}
    prompt = payload.get('prompt') or 'Genera un juego terapéutico en HTML.'
    target_user_id = payload.get('user_id')
    game_name = (payload.get('name') or 'ai_game').strip().replace(' ', '_')
    if not target_user_id:
        return jsonify({'error': 'Falta user_id'}), 400
    user = User.query.get(target_user_id)
    if not user:
        return jsonify({'error': 'Usuario no encontrado'}), 404

    # Collect KPIs from DB for user
    kpi = {}
    kpi['total_sessions'] = SessionMetrics.query.filter_by(user_id=user.id).count()
    kpi['avg_accuracy'] = float(db.session.query(func.avg(SessionMetrics.accurracy)).filter_by(user_id=user.id).scalar() or 0)
    kpi['avg_time_ms'] = float((db.session.query(func.avg(SessionMetrics.avg_time)).filter_by(user_id=user.id).scalar() or 0) * 1000)
    kpi['last_games'] = [
        {
            'game_name': m.game_name,
            'accuracy': float(m.accurracy),
            'avg_time_ms': float(m.avg_time * 1000),
            'prediction': int(m.prediction),
            'date': m.date.isoformat()
        } for m in SessionMetrics.query.filter_by(user_id=user.id).order_by(SessionMetrics.date.desc()).limit(10)
    ]

    # Build prompt including KPIs to instruct Gemini to output HTML and JSON
    full_prompt = (
        f"{prompt}\n\n"
        "Genera dos bloques: 1) HTML completo para un juego sencillo de reflejos/cognitivo con UI moderna, tailwindcdn y FontAwesome (no frameworks).\n"
        "2) JSON de configuración KPI con claves: kpis(avg_accuracy, avg_time_ms, total_sessions), goals, difficulty, and tracking schema for events.\n"
        f"KPIs del paciente: {json.dumps(kpi, ensure_ascii=False)}\n"
        "Devuelve primero el JSON (entre marcadores ---JSON---) y luego el HTML (entre ---HTML---)."
    )

    if not api_key:
        # Fallback: simple generated HTML and JSON locally
        config = {
            'kpis': {'avg_accuracy': kpi['avg_accuracy'], 'avg_time_ms': kpi['avg_time_ms'], 'total_sessions': kpi['total_sessions']},
            'goals': ['Mejorar reflejos', 'Reducir tiempo de reacción'],
            'difficulty': 'medium',
            'tracking': {'events': ['click', 'hit', 'miss'], 'schema_version': 1}
        }
        html = '<!DOCTYPE html><html><head><meta charset="utf-8"><script src="https://cdn.tailwindcss.com"></script></head><body class="p-6">\n' \
               '<h2 class="text-2xl font-bold">Juego IA (fallback)</h2>\n' \
               '<p class="text-gray-600">Config basado en KPIs.</p>\n' \
               '</body></html>'
    else:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={api_key}"
            body = {"contents": [{"parts": [{"text": full_prompt}]}]}
            resp = requests.post(url, json=body, timeout=15)
            resp.raise_for_status()
            j = resp.json()
            text = (
                j.get('candidates', [{}])[0]
                .get('content', {})
                .get('parts', [{}])[0]
                .get('text') or ''
            )
            # Extract JSON and HTML by markers
            json_start = text.find('---JSON---')
            html_start = text.find('---HTML---')
            if json_start != -1 and html_start != -1:
                json_block = text[json_start + len('---JSON---'): html_start].strip()
                html_block = text[html_start + len('---HTML---'):].strip()
                try:
                    config = json.loads(json_block)
                except Exception:
                    config = {'raw': json_block}
                html = html_block
            else:
                # If markers missing, store raw
                config = {'raw': text}
                html = '<!DOCTYPE html><html><body><pre>Salida IA sin marcadores</pre></body></html>'
        except Exception as e:
            config = {'error': str(e), 'kpis': kpi}
            html = '<!DOCTYPE html><html><body><pre>Error generando juego IA</pre></body></html>'

    # Save HTML file
    dest_dir = os.path.join(current_app.root_path, 'static', 'games')
    os.makedirs(dest_dir, exist_ok=True)
    filename = f"{game_name}.html"
    path = os.path.join(dest_dir, filename)
    try:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(html)
    except Exception as e:
        return jsonify({'error': 'write_failed', 'detail': str(e)}), 500

    # Persist JSON config in user.game_profile
    try:
        user.game_profile = json.dumps(config, ensure_ascii=False)
        db.session.commit()
    except Exception as e:
        return jsonify({'error': 'persist_failed', 'detail': str(e)}), 500

    return jsonify({
        'status': 'ok',
        'file': filename,
        'url': url_for('static', filename=f'games/{filename}'),
        'config': config
    })

@api_bp.route('/sessions/assign-games', methods=['POST'])
@login_required
def assign_games_to_session():
    """Assign games to a session using the unified AppointmentGame table"""
    if current_user.role not in ('terapista','admin'):
        return jsonify({'error': 'Acceso denegado'}), 403
    
    data = request.get_json() or {}
    session_id = data.get('session_id')
    games = data.get('games') or []
    
    if not session_id:
        return jsonify({'error': 'session_id requerido'}), 400
    
    # Extract filenames from games list
    # Support both ['game.html'] and [{'name': 'game.html', 'url': '...'}]
    game_filenames = []
    for game in games:
        if isinstance(game, dict):
            game_filenames.append(game.get('name', ''))
        else:
            game_filenames.append(game)
    
    # Filter out empty strings
    game_filenames = [g for g in game_filenames if g]
    
    try:
        validated_games = appointment_service.set_session_games(session_id, game_filenames)
        return jsonify({
            'status': 'ok',
            'assigned': [{'name': g.filename, 'title': g.title} for g in validated_games]
        })
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        return jsonify({'error': f'Error asignando juegos: {str(e)}'}), 500


# Check available games for a session (only during time window)
@api_bp.route('/sessions/<int:session_id>/games', methods=['GET'])
@login_required
def session_games(session_id):
    appt = Appointment.query.get(session_id)
    if not appt:
        return jsonify({'error': 'Sesión no encontrada'}), 404
    now = datetime.utcnow()
    # Allow access if now is between start and end (or within scheduled with end None -> 2h)
    end_time = appt.end_time or (appt.start_time + timedelta(hours=2))
    enabled = appt.status == 'scheduled' and appt.start_time <= now <= end_time
    games = []
    try:
        games = json.loads(appt.games) if appt.games else []
    except Exception:
        games = []
    return jsonify({'enabled': enabled, 'games': games})


# Aggregate session results and update user profile (game_profile)
@api_bp.route('/sessions/<int:session_id>/complete', methods=['POST'])
@login_required
def complete_session(session_id):
    appt = Appointment.query.get(session_id)
    if not appt:
        return jsonify({'error': 'Sesión no encontrada'}), 404
    # Authorization: therapist owns session
    if current_user.id != appt.therapist_id:
        return jsonify({'error': 'Acceso denegado'}), 403

    # Mark completed if not already
    if appt.status != 'completed':
        appt.status = 'completed'
        appt.end_time = datetime.utcnow()
        db.session.add(appt)

    # Aggregate metrics for patient within this session
    metrics = SessionMetrics.query.filter_by(user_id=appt.patient_id, session_id=session_id).all()
    if not metrics:
        db.session.commit()
        return jsonify({'status': 'ok', 'message': 'Sin métricas para agregar'})

    avg_acc = float(sum(m.accurracy for m in metrics) / len(metrics))
    avg_time_ms = float(sum(m.avg_time for m in metrics) / len(metrics) * 1000)
    plays = len(metrics)
    last_games = [{
        'game_name': m.game_name,
        'accuracy': float(m.accurracy),
        'avg_time_ms': float(m.avg_time * 1000),
        'prediction': int(m.prediction),
        'date': m.date.isoformat()
    } for m in metrics]

    # Merge into user.game_profile JSON
    patient = User.query.get(appt.patient_id)
    try:
        existing = json.loads(patient.game_profile) if patient.game_profile else {}
    except Exception:
        existing = {}
    existing.setdefault('history', []).extend(last_games)
    existing['kpis'] = {
        'avg_accuracy': avg_acc,
        'avg_time_ms': avg_time_ms,
        'plays': plays
    }

    patient.game_profile = json.dumps(existing, ensure_ascii=False)
    db.session.commit()

    # Notify both therapist and patient about completion
    try:
        notification_service.create_notification(appt.therapist_id, f"Sesión #{appt.id} completada. {plays} juegos registrados.", link=url_for('therapist.reports'))
        notification_service.create_notification(appt.patient_id, f"Sesión completada. ¡Buen trabajo!", link=url_for('patient.progress'))
    except Exception:
        pass

    return jsonify({'status': 'ok', 'updated_profile': existing})

@api_bp.route('/resources/<int:resource_id>')
@login_required
def get_resource(resource_id):
    try:
        if resource_id == 1:
            # Guía de Ejercicios: summarize recent performance
            metrics = SessionMetrics.query.filter_by(user_id=current_user.id).order_by(SessionMetrics.date.desc()).limit(20).all()
            if metrics:
                avg_acc = sum((m.accurracy or 0) for m in metrics) / len(metrics)
                avg_time = sum((m.avg_time or 0) for m in metrics) / len(metrics)
                perf_summary = f"Tu precisión promedio en las últimas sesiones es {avg_acc:.0f}%. Tiempo medio por ejercicio {avg_time:.1f}s."
            else:
                perf_summary = "No hay datos de sesiones suficientes para personalizar esta guía."

            content = f"<h3>Guía de Ejercicios Personalizada</h3><p>{perf_summary}</p>"
            content += "<ol><li>Ejercicio respiratorio: 5 minutos.</li><li>Ejercicios de atención: 3 bloques de 4 minutos.</li><li>Revisión de estrategias aprendidas en la sesión.</li></ol>"
            return jsonify({'id': resource_id, 'title': 'Guía de Ejercicios', 'content': content})

        if resource_id == 2:
            content = "<h3>Video Tutorial: Técnicas básicas</h3><p>Este video explica las técnicas recomendadas y cuándo aplicarlas. Duración: 15:30.</p>"
            content += "<p>Puntos clave: respiración, pausas activas, seguimiento de progreso.</p>"
            return jsonify({'id': resource_id, 'title': 'Video Tutorial', 'content': content})

        if resource_id == 3:
            content = "<h3>Hoja de Práctica</h3><p>Plantilla descargable para llevar un registro de ejercicios diarios.</p>"
            content += "<ul><li>Día 1: Ejercicio A - 10 repeticiones</li><li>Día 2: Ejercicio B - 8 repeticiones</li></ul>"
            return jsonify({'id': resource_id, 'title': 'Hoja de Práctica', 'content': content})

        return jsonify({'error': 'Recurso no encontrado'}), 404
    except Exception as e:
        return jsonify({'error': 'Error generando recurso', 'detail': str(e)}), 500

@api_bp.route('/messages/send', methods=['POST'])
@login_required
def send_message():
    # Handle both JSON and Form Data
    if request.is_json:
        data = request.get_json()
    else:
        data = request.form.to_dict()

    receiver_id = data.get('receiver_id')
    body = data.get('body', '')
    subject = data.get('subject')
    
    if not receiver_id:
        return jsonify({'success': False, 'message': 'Datos incompletos'}), 400
    
    receiver = User.query.get(receiver_id)
    if not receiver:
        return jsonify({'success': False, 'message': 'Destinatario no encontrado'}), 404
    
    # File handling
    attachment_path = None
    attachment_type = None
    
    if 'file' in request.files:
        file = request.files['file']
        if file and file.filename:
            filename = secure_filename(file.filename)
            unique_filename = f"{uuid.uuid4().hex}_{filename}"
            
            # Determine type
            ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
            if ext in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
                attachment_type = 'image'
            elif ext in ['mp4', 'mov', 'webm']:
                attachment_type = 'video'
            elif ext in ['mp3', 'wav', 'ogg', 'm4a']:
                attachment_type = 'audio'
            else:
                attachment_type = 'file'

            # Ensure directory
            upload_folder = os.path.join(current_app.instance_path, 'uploads', 'messages')
            os.makedirs(upload_folder, exist_ok=True)
            
            # Save
            file.save(os.path.join(upload_folder, unique_filename))
            
            # Storing filename only, path is managed by frontend/template
            attachment_path = unique_filename

    if not body and not attachment_path:
         return jsonify({'success': False, 'message': 'El mensaje no puede estar vacío'}), 400
    
    # Create message
    message = Message(
        sender_id=current_user.id,
        receiver_id=receiver_id,
        subject=subject,
        body=body,
        attachment_path=attachment_path,
        attachment_type=attachment_type
    )
    db.session.add(message)
    db.session.commit()
    
    # Create notification for receiver
    notification_service.create_notification(
        user_id=receiver_id,
        message=f'Nuevo mensaje de {current_user.username}',
        link=url_for('main.messages_list')
    )
    
    # Send Email Notification
    try:
        email_service = EmailService()
        email_service.send_new_message_email(
            receiver.email,
            receiver.username,
            current_user.username,
            (body or "Has recibido un archivo adjunto")[:100] + ('...' if body and len(body) > 100 else '')
        )
    except Exception:
        pass # Non-critical
    
    return jsonify({
        'success': True,
        'message_id': message.id,
        'created_at': message.created_at.isoformat(),
        'attachment_path': attachment_path,
        'attachment_type': attachment_type
    })


@api_bp.route('/messages/unread-count')
@login_required
def unread_messages_count():
    count = Message.query.filter_by(receiver_id=current_user.id, is_read=False).count()
    return jsonify({'count': count})

@api_bp.route('/admin/profile', methods=['POST'])
@login_required
def api_admin_update_profile():
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Acceso denegado'}), 403
    data = request.get_json(silent=True) or {}
    name = (data.get('username') or '').strip()
    new_password = (data.get('new_password') or '').strip()
    changed = False
    if name:
        current_user.username = name
        changed = True
    if new_password:
        current_user.password = bcrypt.generate_password_hash(new_password).decode('utf-8')
        changed = True
        try:
            EmailService.send_password_change_email(current_user.email, new_password, current_user.username or 'Administrador')
        except Exception:
            pass
    if changed:
        db.session.commit()
    return jsonify({'success': True})

@api_bp.route('/appointments/<int:appointment_id>/upload_image', methods=['POST'])
@login_required
def upload_session_image(appointment_id):
    """Upload an image for a specific session"""
    if current_user.role not in ('terapista', 'admin'):
        return jsonify({'error': 'Acceso denegado'}), 403
        
    appointment = Appointment.query.get_or_404(appointment_id)
    
    # Verify ownership (therapist assigned to appointment)
    if current_user.role == 'terapista' and appointment.therapist_id != current_user.id:
        return jsonify({'error': 'No tienes permiso para editar esta sesión'}), 403
        
    if 'image' not in request.files:
        return jsonify({'error': 'No se encontró el archivo de imagen'}), 400
        
    file = request.files['image']
    image_type = request.form.get('image_type', 'session_photo')
    notes = request.form.get('notes', '')
    
    if file.filename == '':
        return jsonify({'error': 'Nombre de archivo vacío'}), 400
        
    if file:
        # Validate file extension
        allowed_extensions = {'png', 'jpg', 'jpeg', 'pdf'}
        if '.' not in file.filename or \
           file.filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
            return jsonify({'error': 'Tipo de archivo no permitido (solo png, jpg, jpeg, pdf)'}), 400
            
        # Create secure filename with UUID to prevent collisions
        original_filename = secure_filename(file.filename)
        extension = original_filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{uuid.uuid4().hex}.{extension}"
        
        # Create directory structure: static/uploads/session_images/YYYY/MM
        now = datetime.utcnow()
        relative_path = os.path.join('uploads', 'session_images', str(now.year), f"{now.month:02d}")
        upload_folder = os.path.join(current_app.root_path, 'static', relative_path)
        
        os.makedirs(upload_folder, exist_ok=True)
        
        # Save file
        file_path = os.path.join(upload_folder, unique_filename)
        file.save(file_path)

        # Upload to Google Drive (Background/Sync)
        try:
            # Pass the file PATH instead of opening it, to avoid stream issues
            patient_name = appointment.patient.username if appointment.patient else 'Paciente_Desconocido'
            session_date = appointment.start_time.strftime('%Y-%m-%d')
            
            print(f"Subiendo a Drive: {patient_name} / {session_date} / {unique_filename}")
            drive_service.upload_file(
                file_path,  # Path string 
                unique_filename,
                file.mimetype,
                patient_name,
                session_date
            )
        except Exception as e:
            print(f"Error subiendo a Google Drive: {str(e)}")
        
        # Store relative path in DB for serving
        db_relative_path = os.path.join(relative_path, unique_filename)
        
        # Create DB record
        session_image = SessionImage(
            appointment_id=appointment.id,
            image_path=db_relative_path,
            image_type=image_type,
            uploaded_by_id=current_user.id,
            notes=notes
        )
        
        db.session.add(session_image)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'image': {
                'id': session_image.id,
                'url': url_for('static', filename=db_relative_path),
                'type': session_image.image_type,
                'notes': session_image.notes
            }
        })
        
    return jsonify({'error': 'Error al subir archivo'}), 500

@api_bp.route('/appointments/<int:appointment_id>/images/<int:image_id>', methods=['DELETE'])
@login_required
def delete_session_image(appointment_id, image_id):
    """Delete a session image"""
    if current_user.role not in ('terapista', 'admin'):
        return jsonify({'error': 'Acceso denegado'}), 403

    image = SessionImage.query.get_or_404(image_id)
    
    # Verify it belongs to the appointment
    if image.appointment_id != appointment_id:
        return jsonify({'error': 'Imagen no corresponde a la sesión'}), 400
        
    # Verify ownership (therapist assigned to appointment)
    if current_user.role == 'terapista':
        appointment = Appointment.query.get(appointment_id)
        if appointment.therapist_id != current_user.id:
            return jsonify({'error': 'No tienes permiso para editar esta sesión'}), 403

    try:
        # Delete file from filesystem
        full_path = os.path.join(current_app.root_path, 'static', image.image_path)
        if os.path.exists(full_path):
            os.remove(full_path)
            
        # Delete from DB
        db.session.delete(image)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': f'Error al eliminar imagen: {str(e)}'}), 500

# --- SEDES MANAGEMENT ---
from app.models import Sede

@api_bp.route('/admin/sedes', methods=['GET', 'POST'])
@login_required
def admin_sedes():
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Forbidden'}), 403

    if request.method == 'GET':
        sedes = Sede.query.order_by(Sede.created_at.desc()).all()
        result = []
        for s in sedes:
            created_at_iso = None
            if s.created_at:
                try:
                    created_at_iso = s.created_at.isoformat()
                except AttributeError:
                    created_at_iso = str(s.created_at)
            
            result.append({
                'id': s.id,
                'name': s.name,
                'address': s.address,
                'active': s.active,
                'created_at': created_at_iso
            })
        return jsonify(result)

    if request.method == 'POST':
        data = request.get_json() or {}
        name = data.get('name')
        if not name:
            return jsonify({'success': False, 'message': 'Nombre es obligatorio'}), 400
        
        existing = Sede.query.filter_by(name=name).first()
        if existing:
            return jsonify({'success': False, 'message': 'Sede ya existe'}), 400

        address = data.get('address')
        s = Sede(name=name, address=address)
        db.session.add(s)
        db.session.commit()
        return jsonify({'success': True, 'id': s.id})

@api_bp.route('/admin/sedes/<int:sede_id>', methods=['PUT'])
@login_required
def admin_sedes_detail(sede_id):
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Forbidden'}), 403
        
    s = Sede.query.get(sede_id)
    if not s:
        return jsonify({'success': False, 'message': 'No encontrado'}), 404

    if request.method == 'PUT':
        data = request.get_json() or {}
        if 'active' in data:
            s.active = bool(data['active'])
        if 'name' in data and data['name']:
            s.name = data['name']
        if 'address' in data:
            s.address = data['address']
        
        db.session.commit()
        return jsonify({'success': True})

@api_bp.route('/public/contact', methods=['POST'])
@csrf.exempt
def contact_message():
    data = request.get_json() or {}
    # Validation
    required_fields = ['first_name', 'last_name', 'email', 'message']
    for field in required_fields:
        if field not in data or not data[field]:
            return jsonify({'error': f'Field {field} is required'}), 400

    new_msg = ContactMessage(
        first_name=data.get('first_name'),
        last_name=data.get('last_name'),
        email=data.get('email'),
        phone=data.get('phone'),
        subject=data.get('subject', 'Consulta Web'),
        message=data.get('message'),
        service_interest=data.get('service_interest'),
        urgency=data.get('urgency', 'medium'),
        status='unread'
    )
    
    try:
        db.session.add(new_msg)
        db.session.commit()
        return jsonify({'message': '¡Mensaje recibido! Nos pondremos en contacto pronto.'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

