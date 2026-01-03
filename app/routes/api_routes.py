from flask import Blueprint, request, jsonify, current_app, url_for
from flask_login import login_required, current_user
from app.models import db, User, Notification, Appointment, Message, Game, SessionMetrics
from app.services.appointment_service import AppointmentService
from app.services.game_service import GameService
from app.services.admin_service import AdminService
from app.services.notification_service import NotificationService
from app.services.patient_service import PatientService
from app.services.dashboard_service import DashboardService
from app.services.ai_service import predict_level, train_model
from app.utils import get_user_today_utc_range, get_user_now
from app.schemas import AssignTherapistSchema, UpdateUserSchema, SendMessageSchema
from app.extensions import bcrypt
from app.services.email_service import EmailService
from datetime import datetime, timedelta
import json
import os
import requests
from sqlalchemy import or_, func

api_bp = Blueprint('api', __name__)

appointment_service = AppointmentService()
game_service = GameService()
admin_service = AdminService()
notification_service = NotificationService()
patient_service = PatientService()
dashboard_service = DashboardService()

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
            import pytz
            dt = dt.astimezone(pytz.UTC).replace(tzinfo=None)
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
    
    if current_user.role == 'terapista':
        patients = patient_service.get_therapist_patients(current_user.id)
    else:
        patients = patient_service.get_all_active_patients()
        
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
            'patient': {'id': a.patient.id, 'name': a.patient.username} if a.patient else None,
            'location': a.location,
            'notes': a.notes,
            'games': json.loads(a.games) if a.games else []
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
            'end_time': end_iso
            ,'games': json.loads(a.games) if a.games else []
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
    
    # Pre-process dates for the service
    try:
        data['start_time'] = _parse_datetime(data.get('start_time'))
        data['end_time'] = _parse_datetime(data.get('end_time'))
    except Exception:
        return jsonify({'success': False, 'message': 'Formato de fecha inválido'}), 400

    if not data.get('patient_id') or not data.get('start_time'):
        return jsonify({'success': False, 'message': 'patient_id and start_time are required'}), 400

    try:
        appt = appointment_service.create_session(current_user.id, data, current_user.username)
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

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
    # include games if any
    try:
        created['games'] = json.loads(appt.games) if appt.games else []
    except Exception:
        created['games'] = []
    return jsonify(created)


@api_bp.route('/sessions/<int:session_id>', methods=['PUT'])
@login_required
def api_update_session(session_id):
    if current_user.role != 'terapista':
        return jsonify({'success': False, 'message': 'Acceso denegado'}), 403

    data = request.json or {}
    if 'start_time' in data:
        data['start_time'] = _parse_datetime(data.get('start_time'))
    if 'end_time' in data:
        data['end_time'] = _parse_datetime(data.get('end_time'))
        
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

@api_bp.route('/admin/assign-therapist', methods=['POST'])
@login_required
def api_admin_assign_therapist():
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Acceso denegado'}), 403
    data = request.get_json(silent=True) or {}
    errors = AssignTherapistSchema().validate(data)
    if errors:
        return jsonify({'success': False, 'message': 'Datos inválidos', 'errors': errors}), 400
    
    success, message = admin_service.assign_therapist(data['patient_id'], data['therapist_id'])
    if not success:
        return jsonify({'success': False, 'message': message}), 400
        
    return jsonify({'success': True})

@api_bp.route('/admin/create-user', methods=['POST'])
@login_required
def api_admin_create_user():
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Acceso denegado'}), 403
    data = request.get_json(silent=True) or {}
    
    # Basic validation (schema validation could be added here)
    if not data.get('email') or not data.get('role'):
        return jsonify({'success': False, 'message': 'Faltan datos requeridos'}), 400

    success, result = admin_service.create_user(data)
    if not success:
        return jsonify({'success': False, 'message': result}), 400
        
    return jsonify({'success': True, 'user': {'id': result.id, 'username': result.username, 'email': result.email}})

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
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Acceso denegado'}), 403
    data = request.get_json(silent=True) or {}
    errors = UpdateUserSchema().validate(data)
    if errors:
        return jsonify({'success': False, 'message': 'Datos inválidos', 'errors': errors}), 400
        
    success, result = admin_service.update_user(data)
    if not success:
        return jsonify({'success': False, 'message': result}), 400
        
    return jsonify({'success': True})

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
        # Cascade delete messages and appointments
        Message.query.filter((Message.sender_id==u.id)|(Message.receiver_id==u.id)).delete()
        Appointment.query.filter((Appointment.therapist_id==u.id)|(Appointment.patient_id==u.id)).delete()
        SessionMetrics.query.filter(SessionMetrics.user_id==u.id).delete()
        db.session.delete(u)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/save_game', methods=['POST'])
@login_required
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
                
                # Run training in background (conceptually, here synchronous for MVP simplicity)
                current_app.logger.info(f"Triggering AI retraining with {len(training_data)} samples...")
                train_model(training_data)
        except Exception as e:
            current_app.logger.error(f"AI Retraining failed: {e}")
        # -----------------------------

        return jsonify({'status': 'ok', 'prediction': pred_code, 'recommendation': label})
    except Exception as e:
        return jsonify({'error': 'save_failed', 'detail': str(e)}), 400


@api_bp.route('/games/upload', methods=['POST'])
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
            return jsonify({'error': 'Gemini API error', 'details': resp.text}), 500
    except Exception as e:
        return jsonify({'error': 'Gemini proxy failed', 'detail': str(e)}), 500

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
    if current_user.role not in ('terapista','admin'):
        return jsonify({'error': 'Acceso denegado'}), 403
    data = request.get_json() or {}
    session_id = data.get('session_id')
    games = data.get('games') or []  # list of {'name': 'file.html', 'url': '/static/games/file.html'}
    appt = Appointment.query.get(session_id)
    if not appt:
        return jsonify({'error': 'Sesión no encontrada'}), 404
    appt.games = json.dumps(games, ensure_ascii=False)
    db.session.commit()
    return jsonify({'status': 'ok', 'assigned': games})


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
    data = request.get_json(silent=True) or {}
    errors = SendMessageSchema().validate(data)
    if errors:
        return jsonify({'success': False, 'message': 'Datos inválidos', 'errors': errors}), 400
    receiver_id = data.get('receiver_id')
    subject = data.get('subject')
    body = data.get('body')
    
    receiver = User.query.get(receiver_id)
    if not receiver:
        return jsonify({'success': False, 'message': 'Destinatario no encontrado'}), 404
    
    # Create message
    message = Message(
        sender_id=current_user.id,
        receiver_id=receiver_id,
        subject=subject,
        body=body
    )
    db.session.add(message)
    db.session.commit()
    
    # Create notification for receiver
    notification_service.create_notification(
        user_id=receiver_id,
        message=f'Nuevo mensaje de {current_user.username}',
        link=url_for('main.messages_list')
    )
    
    return jsonify({
        'success': True,
        'message_id': message.id,
        'created_at': message.created_at.isoformat()
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
