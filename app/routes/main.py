from flask import Blueprint, render_template, request, redirect, url_for, jsonify, flash, session, make_response, current_app
from flask_login import login_required, current_user, logout_user
from app.models import SessionMetrics, db, User, Notification, Appointment, Message
from app.extensions import bcrypt
from app.schemas import CreateUserSchema, UpdateUserSchema, AssignTherapistSchema, SendMessageSchema
from app.services.ai_service import predict_level, get_cluster, train_model
from app.services.dashboard_service import DashboardService
from app.services.email_service import EmailService
from datetime import datetime, timedelta
from sqlalchemy import func, or_
import json
import io
import csv
from email_validator import validate_email, EmailNotValidError
import requests
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import random
import os
import secrets
import string

from app.services.appointment_service import AppointmentService
from app.services.game_service import GameService
from app.services.admin_service import AdminService
from app.services.notification_service import NotificationService
from app.services.patient_service import PatientService
from app.utils import get_user_today_utc_range
import pytz

main_bp = Blueprint('main', __name__)
dashboard_service = DashboardService()
appointment_service = AppointmentService()
game_service = GameService()
admin_service = AdminService()
notification_service = NotificationService()
patient_service = PatientService()

@main_bp.route('/')
def index():
    return redirect(url_for('auth.login'))

@main_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'admin':
        # Admin overview
        overview = dashboard_service.get_admin_overview()
        try:
            return render_template(
                'admin/dashboard.html',
                overview=overview,
                active_page='admin_dashboard',
            )
        except Exception as e:
            current_app.logger.error(f"Error rendering admin dashboard: {e}")
            flash(f'Error cargando el panel de administración: {str(e)}', 'error')
            return render_template('base.html')
    elif current_user.role == 'terapista':
        # Therapist stats
        stats = dashboard_service.get_therapist_stats(current_user.id)
        patients = dashboard_service.get_therapist_patients_data(current_user.id)

        # Alerts: simple heuristics (keep structure for now, move to service later if needed)
        alerts = []
        low_accuracy_users = db.session.query(User.username)\
            .join(SessionMetrics, SessionMetrics.user_id == User.id)\
            .filter(User.role == 'jugador', SessionMetrics.accurracy < 60)\
            .limit(2).all()
        for name_tuple in low_accuracy_users:
            alerts.append({"patient": name_tuple[0], "message": "Rendimiento bajo detectado", "type": "red"})

        return render_template('therapist/dashboard.html',
                               stats=stats,
                               patients=patients,
                               alerts=alerts,
                               active_page='dashboard')
    elif current_user.role == 'jugador':
        # Player stats
        player_stats = dashboard_service.get_player_stats(current_user.id)
        
        # Get today's sessions for the dashboard
        today_start, today_end = get_user_today_utc_range(current_user)
        today_sessions = appointment_service.get_patient_appointments(current_user.id, today_start, today_end)
        
        # Process sessions to include game info
        sessions_data = []
        for s in today_sessions:
            games = []
            try:
                games = json.loads(s.games) if s.games else []
            except:
                games = []
            
            # Check if session is active (within time window)
            is_active = False
            if s.status == 'scheduled':
                end_time = s.end_time or (s.start_time + timedelta(hours=1))
                if s.start_time <= now <= end_time:
                    is_active = True
            
            sessions_data.append({
                'id': s.id,
                'title': s.title,
                'start_time': s.start_time,
                'end_time': s.end_time,
                'games': games,
                'is_active': is_active,
                'therapist_name': s.therapist.username if s.therapist else 'Terapeuta'
            })

        return render_template('patient/dashboard.html', 
                               player_stats=player_stats,
                               today_sessions=sessions_data,
                               active_page='dashboard',
                               now=now)

@main_bp.route('/patient/sessions')
@login_required
def sessions_patient():
    if current_user.role != 'jugador':
        flash('Acceso denegado', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Get upcoming sessions
    sessions = appointment_service.get_patient_appointments(current_user.id, limit=20)
    
    # Process for display
    sessions_data = []
    now = datetime.utcnow()
    
    for s in sessions:
        games = []
        try:
            games = json.loads(s.games) if s.games else []
        except:
            games = []
            
        # Check if active
        is_active = False
        if s.status == 'scheduled':
            end_time = s.end_time or (s.start_time + timedelta(hours=1))
            # Allow access 15 mins before and until end time
            # Also allow if it's "today" in a broad sense for testing
            if (s.start_time - timedelta(minutes=15)) <= now <= end_time:
                is_active = True
            # Fallback for demo: if it's today, just make it active
            if s.start_time.date() == now.date():
                 is_active = True
        
        sessions_data.append({
            'id': s.id,
            'title': s.title,
            'start_time': s.start_time,
            'therapist_name': s.therapist.username if s.therapist else 'Terapeuta',
            'games': games,
            'is_active': is_active,
            'status': s.status
        })
        
    return render_template('patient/sessions.html', active_page='sessions', sessions=sessions_data)

# Therapist insights API: weekly progress and alerts
@main_bp.route('/api/therapist/insights')
@login_required
def therapist_insights():
    if current_user.role != 'terapista':
        return jsonify({'error': 'Acceso denegado'}), 403

    data = dashboard_service.get_therapist_insights(current_user)
    return jsonify(data)

@main_bp.route('/api/notifications')
@login_required
def get_notifications():
    notifications = notification_service.get_unread_notifications(current_user.id)
    return jsonify([{
        'id': n.id,
        'message': n.message,
        'timestamp': n.timestamp.strftime('%d %b, %H:%M'),
        'link': n.link
    } for n in notifications])

@main_bp.route('/api/patients')
@login_required
def api_patients():
    if current_user.role not in ('terapista', 'admin'):
        return jsonify({'error': 'Acceso denegado'}), 403
    
    if current_user.role == 'terapista':
        patients = patient_service.get_therapist_patients(current_user.id)
    else:
        patients = patient_service.get_all_active_patients()
        
    return jsonify([{'id': p.id, 'username': p.username, 'email': p.email} for p in patients])

@main_bp.route('/api/notifications/mark-read', methods=['POST'])
@login_required
def mark_notifications_read():
    try:
        notification_service.mark_all_as_read(current_user.id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@main_bp.route('/patients/manage')
@login_required
def manage_patients():
    if current_user.role != 'terapista':
        flash('Acceso denegado.', 'error')
        return redirect(url_for('main.dashboard'))
    
    patients = patient_service.get_therapist_patients(current_user.id)
    return render_template('therapist/patients.html', patients=patients, active_page='patients')


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


@main_bp.route('/api/sessions', methods=['GET'])
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
@main_bp.route('/api/sessions/upcoming', methods=['GET'])
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


@main_bp.route('/api/appointments/patient', methods=['GET'])
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


@main_bp.route('/api/games', methods=['GET'])
@login_required
def api_list_games():
    files = game_service.list_games()
    return jsonify({'games': files})


@main_bp.route('/api/sessions/day', methods=['GET'])
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


@main_bp.route('/api/sessions', methods=['POST'])
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


@main_bp.route('/api/sessions/<int:session_id>', methods=['PUT'])
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


@main_bp.route('/api/sessions/<int:session_id>', methods=['DELETE'])
@login_required
def api_delete_session(session_id):
    if current_user.role != 'terapista':
        return jsonify({'success': False, 'message': 'Acceso denegado'}), 403

    success = appointment_service.delete_session(session_id, current_user.id)
    if not success:
        return jsonify({'success': False, 'message': 'Sesión no encontrada'}), 404

    return jsonify({'success': True})


@main_bp.route('/sessions')
@login_required
def sessions():
    if current_user.role != 'terapista':
        flash('Acceso denegado.', 'error')
        return redirect(url_for('main.dashboard'))
    # Compute session statistics for the cards
    today_start, today_end = get_user_today_utc_range(current_user)
    now = datetime.utcnow()

    sessions_today = Appointment.query.filter(
        Appointment.therapist_id == current_user.id,
        Appointment.start_time >= today_start,
        Appointment.start_time < today_end,
        Appointment.status == 'scheduled'
    ).count()

    completed_sessions = Appointment.query.filter(
        Appointment.therapist_id == current_user.id,
        Appointment.status == 'completed'
    ).count()

    pending_sessions = Appointment.query.filter(
        Appointment.therapist_id == current_user.id,
        Appointment.status == 'scheduled',
        Appointment.start_time > now
    ).count()

    active_patients = User.query.filter_by(role='jugador', is_active=True).count()

    return render_template('therapist/sessions.html',
                           active_page='sessions',
                           sessions_today=sessions_today,
                           completed_sessions=completed_sessions,
                           pending_sessions=pending_sessions,
                           active_patients=active_patients)

@main_bp.route('/games')
@login_required
def games_list():
    if current_user.role not in ('terapista','admin'):
        return redirect(url_for('main.dashboard'))
    files = game_service.list_games()
    return render_template('therapist/games.html', custom_games=files, active_page='games')
    
    
@main_bp.route('/admin')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash('Acceso denegado.', 'error')
        return redirect(url_for('main.dashboard'))
    
    overview = dashboard_service.get_admin_overview()
    return render_template('admin/dashboard.html', overview=overview, active_page='admin_dashboard')

@main_bp.route('/admin/users')
@login_required
def admin_users():
    if current_user.role != 'admin':
        flash('Acceso denegado.', 'error')
        return redirect(url_for('main.dashboard'))
    users = User.query.order_by(User.created_at.desc()).all()
    therapists = User.query.filter_by(role='terapista').order_by(User.username.asc()).all()
    return render_template('admin/users.html', users=users, therapists=therapists, active_page='admin_users')

@main_bp.route('/api/admin/assign-therapist', methods=['POST'])
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

@main_bp.route('/api/admin/create-user', methods=['POST'])
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
    errors = CreateUserSchema().validate(data)
    if errors:
        return jsonify({'success': False, 'message': 'Datos inválidos', 'errors': errors}), 400
    email = (data.get('email') or '').strip().lower()
    username = (data.get('username') or '').strip() or email.split('@')[0]
    role = (data.get('role') or '').strip().lower()
    if role == 'terapeuta':
        role = 'terapista'
    try:
        valid = validate_email(email)
        email = valid.email
    except EmailNotValidError as e:
        current_app.logger.warning(f"Email inválido al crear usuario admin: {email} - {str(e)}")
        return jsonify({'success': False, 'message': 'Email inválido'}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({'success': False, 'message': 'Email ya registrado'}), 400
    temp_pw = EmailService.generate_password()
    hashed_pw = bcrypt.generate_password_hash(temp_pw).decode('utf-8')
    try:
        u = User(username=username, email=email, password=hashed_pw, role=role, is_active=True)
        db.session.add(u)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(f"Error al crear usuario: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Error al crear usuario'}), 500
    EmailService.send_welcome_email(email, temp_pw, username)
    try:
        notification_service.create_notification(u.id, "Tu cuenta ha sido creada", link=url_for('main.dashboard'))
    except Exception:
        pass
    return jsonify({'success': True, 'user': {'id': u.id, 'email': u.email, 'role': u.role}, 'temp_password': temp_pw})

@main_bp.route('/admin/games')
@login_required
def admin_games():
    if current_user.role != 'admin':
        flash('Acceso denegado.', 'error')
        return redirect(url_for('main.dashboard'))
    games_dir = os.path.join(current_app.root_path, 'static', 'games')
    try:
        files = [f for f in os.listdir(games_dir) if f.lower().endswith('.html')]
    except Exception:
        files = []
    return render_template('admin/games.html', games=files, active_page='admin_games')

@main_bp.route('/api/admin/games/delete', methods=['POST'])
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

@main_bp.route('/admin/reports')
@login_required
def admin_reports():
    if current_user.role != 'admin':
        flash('Acceso denegado.', 'error')
        return redirect(url_for('main.dashboard'))
    # Aggregate simple stats per therapist and patient
    therapists = User.query.filter_by(role='terapista').all()
    t_rows = []
    for t in therapists:
        count_appts = Appointment.query.filter_by(therapist_id=t.id).count()
        avg_acc = db.session.query(func.avg(SessionMetrics.accurracy)).scalar() or 0
        t_rows.append({'name': t.username, 'email': t.email, 'sessions': count_appts, 'avg_accuracy': round(avg_acc,1)})
    patients = User.query.filter_by(role='jugador').all()
    p_rows = []
    for p in patients:
        plays = SessionMetrics.query.filter_by(user_id=p.id).count()
        acc = db.session.query(func.avg(SessionMetrics.accurracy)).filter_by(user_id=p.id).scalar() or 0
        p_rows.append({'name': p.username, 'email': p.email, 'plays': plays, 'avg_accuracy': round(acc,1)})
    return render_template('admin/reports.html', therapists=t_rows, patients=p_rows, active_page='admin_reports')

@main_bp.route('/admin/messages')
@login_required
def admin_messages():
    if current_user.role != 'admin':
        flash('Acceso denegado.', 'error')
        return redirect(url_for('main.dashboard'))
    therapists = User.query.filter_by(role='terapista', is_active=True).order_by(User.username.asc()).all()
    patients = User.query.filter_by(role='jugador', is_active=True).order_by(User.username.asc()).all()
    return render_template('admin/messages.html', therapists=therapists, patients=patients, active_page='admin_messages')

@main_bp.route('/api/admin/messages/broadcast', methods=['POST'])
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

@main_bp.route('/api/admin/list-users')
@login_required
def api_admin_list_users():
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Acceso denegado'}), 403
    role = (request.args.get('role') or '').strip()
    users = admin_service.list_users(role)
    return jsonify({'success': True, 'users': [{'id': u.id, 'email': u.email, 'username': u.username, 'role': u.role} for u in users]})

@main_bp.route('/api/admin/update-user', methods=['POST'])
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
    if errors:
        return jsonify({'success': False, 'message': 'Datos inválidos', 'errors': errors}), 400
    user_id = data.get('id')
    u = User.query.get(user_id)
    if not u:
        return jsonify({'success': False, 'message': 'Usuario no encontrado'}), 404
    username = (data.get('username') or '').strip()
    role = (data.get('role') or '').strip().lower()
    active = data.get('is_active')
    if username:
        u.username = username
    if role:
        if role == 'terapeuta':
            role = 'terapista'
        if role not in ('terapista','jugador','admin'):
            return jsonify({'success': False, 'message': 'Rol inválido'}), 400
        u.role = role
    if active is not None:
        u.is_active = bool(active)
    db.session.commit()
    return jsonify({'success': True})

@main_bp.route('/api/admin/delete-user', methods=['POST'])
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

@main_bp.route('/analytics')
@login_required
def analytics():
    if current_user.role != 'terapista':
        flash('Acceso denegado.', 'error')
        return redirect(url_for('main.dashboard'))

    # --- Real Data Calculation ---
    
    # 1. AI Overview
    total_metrics = SessionMetrics.query.count()
    
    # Calculate averages
    avg_acc = db.session.query(func.avg(SessionMetrics.accurracy)).scalar() or 0
    
    # Success rate: Percentage of "Avanzar Nivel" (1) predictions
    total_predictions = SessionMetrics.query.filter(SessionMetrics.prediction.isnot(None)).count()
    advance_predictions = SessionMetrics.query.filter_by(prediction=1).count()
    success_rate = (advance_predictions / total_predictions * 100) if total_predictions > 0 else 0
    
    # Active models (Static for MVP, but could be dynamic if we had multiple model files)
    active_models_count = 1 

    ai_overview = {
        "total_adaptations": total_metrics,
        "adaptations_change": 0, # Placeholder for trend
        "avg_accuracy": round(avg_acc, 1),
        "accuracy_improvement": 0, # Placeholder
        "success_rate": round(success_rate, 1),
        "success_rate_increase": 0, # Placeholder
        "active_models": active_models_count,
        "insight": "El modelo SVM se está adaptando a los patrones de tiempo y precisión de los pacientes."
    }

    # 2. Model Performance (Mocked for MVP as we don't have ground truth labels in DB yet)
    # In a real system, we'd compare prediction vs therapist feedback
    model_performance = [
        {"name": "Clasificación de Nivel", "accuracy": 92},
        {"name": "Detección de Fatiga", "accuracy": 85}, # Future feature
    ]

    # 3. Recent Adaptations (Last 10 metrics)
    recent_metrics = db.session.query(SessionMetrics, User).join(User, SessionMetrics.user_id == User.id)\
        .order_by(SessionMetrics.date.desc()).limit(10).all()
    
    recent_adaptations = []
    labels = {0: "Mantener Nivel", 1: "Avanzar Nivel", 2: "Retroceder/Apoyo"}
    
    for m, u in recent_metrics:
        recent_adaptations.append({
            "patient_name": u.username or u.email,
            "patient_avatar": f"https://ui-avatars.com/api/?name={(u.username or 'User').replace(' ', '+')}&background=random",
            "game_type": m.game_name,
            "prev_level": "?", # We don't track prev level explicitly in metrics yet
            "new_level": labels.get(m.prediction, "Desconocido"),
            "reason": f"Precisión: {m.accurracy:.1f}%, Tiempo: {m.avg_time:.2f}s",
            "timestamp": m.date.strftime("%d/%m %H:%M"),
            "confidence": 90 # Mock confidence
        })

    # 4. Charts Data
    
    # Chart 1: Difficulty Adaptation Over Time (Last 30 days, top 5 active patients)
    # We'll plot 'prediction' as a proxy for difficulty level/decision
    last_30_days = datetime.utcnow() - timedelta(days=30)
    
    # Get top 5 patients by activity
    top_patients = db.session.query(SessionMetrics.user_id, func.count(SessionMetrics.id))\
        .group_by(SessionMetrics.user_id).order_by(func.count(SessionMetrics.id).desc()).limit(5).all()
    
    top_patient_ids = [p[0] for p in top_patients]
    
    metrics_data = SessionMetrics.query.filter(
        SessionMetrics.date >= last_30_days,
        SessionMetrics.user_id.in_(top_patient_ids)
    ).order_by(SessionMetrics.date).all()
    
    # Organize by patient
    patient_data = {}
    for m in metrics_data:
        p_name = User.query.get(m.user_id).username or "User"
        if p_name not in patient_data:
            patient_data[p_name] = {'x': [], 'y': []}
        patient_data[p_name]['x'].append(m.date.isoformat())
        patient_data[p_name]['y'].append(m.prediction) # 0, 1, 2

    fig_difficulty = go.Figure()
    for name, data in patient_data.items():
        fig_difficulty.add_trace(go.Scatter(x=data['x'], y=data['y'], name=name, mode='lines+markers'))
    
    fig_difficulty.update_layout(
        title='Adaptación de Nivel (Últimos 30 días)', 
        xaxis_title='Fecha', 
        yaxis_title='Decisión IA (0=Mantener, 1=Avanzar, 2=Apoyo)',
        template='plotly_white',
        legend_title_text='Pacientes'
    )
    difficulty_adaptation_data = json.loads(fig_difficulty.to_json())

    # Chart 2: Patient Progress Distribution (Latest prediction per patient)
    # Get latest metric for each patient
    subq = db.session.query(
        SessionMetrics.user_id, 
        func.max(SessionMetrics.date).label('max_date')
    ).group_by(SessionMetrics.user_id).subquery()
    
    latest_metrics = db.session.query(SessionMetrics).join(
        subq, 
        (SessionMetrics.user_id == subq.c.user_id) & (SessionMetrics.date == subq.c.max_date)
    ).all()
    
    # Count predictions
    pred_counts = {0: 0, 1: 0, 2: 0}
    for m in latest_metrics:
        if m.prediction in pred_counts:
            pred_counts[m.prediction] += 1
            
    df_progress = pd.DataFrame({
        'Decisión': ['Mantener', 'Avanzar', 'Apoyo'],
        'Pacientes': [pred_counts[0], pred_counts[1], pred_counts[2]]
    })
    
    fig_progress = px.bar(df_progress, x='Decisión', y='Pacientes', title='Estado Actual de Pacientes', template='plotly_white', color='Decisión')
    patient_progress_data = json.loads(fig_progress.to_json())

    # Chart 3: Adaptation Frequency by Game
    game_counts = db.session.query(SessionMetrics.game_name, func.count(SessionMetrics.id))\
        .group_by(SessionMetrics.game_name).all()
    
    if game_counts:
        df_adaptation = pd.DataFrame(game_counts, columns=['Juego', 'Frecuencia'])
        fig_adaptation = px.pie(df_adaptation, values='Frecuencia', names='Juego', title='Juegos Más Jugados', hole=.3, template='plotly_white')
        adaptation_frequency_data = json.loads(fig_adaptation.to_json())
    else:
        adaptation_frequency_data = {}

    return render_template('therapist/analytics.html',
                           ai_overview=ai_overview,
                           model_performance=model_performance,
                           recent_adaptations=recent_adaptations,
                           difficulty_adaptation_data=difficulty_adaptation_data,
                           patient_progress_data=patient_progress_data,
                           adaptation_frequency_data=adaptation_frequency_data,
                           active_page='analytics')

@main_bp.route('/reports')
@login_required
def reports():
    if current_user.role != 'terapista':
        flash('Acceso denegado.', 'error')
        return redirect(url_for('main.dashboard'))
    # Filters
    start = request.args.get('start')
    end = request.args.get('end')
    start_dt = _parse_datetime(start) if start else None
    end_dt = _parse_datetime(end) if end else None
    # Overview stats from DB
    # Improvement rate similar to dashboard
    now = datetime.utcnow()
    last_30 = now - timedelta(days=30)
    prev_60 = now - timedelta(days=60)
    avg_last_30 = db.session.query(func.avg(SessionMetrics.accurracy)).filter(SessionMetrics.date >= last_30).scalar() or 0
    avg_prev_30 = db.session.query(func.avg(SessionMetrics.accurracy)).filter(SessionMetrics.date >= prev_60, SessionMetrics.date < last_30).scalar() or 0
    improvement_rate = 0
    improvement_rate_change = 0
    if avg_prev_30:
        improvement_rate = round(avg_last_30, 1)
        improvement_rate_change = round(((avg_last_30 - avg_prev_30) / avg_prev_30) * 100, 1)

    # Average session time proxy: avg of SessionMetrics.avg_time
    avg_session_time = db.session.query(func.avg(SessionMetrics.avg_time)).scalar() or 0
    avg_session_time_change = 0

    completed_objectives = SessionMetrics.query.filter(SessionMetrics.accurracy >= 80).count()
    completed_objectives_change = 0

    active_patients = User.query.filter_by(role='jugador', is_active=True).count()
    active_patients_change = 0

    overview_stats = {
        'improvement_rate': improvement_rate,
        'improvement_rate_change': improvement_rate_change,
        'avg_session_time': round(avg_session_time, 1),
        'avg_session_time_change': avg_session_time_change,
        'completed_objectives': completed_objectives,
        'completed_objectives_change': completed_objectives_change,
        'active_patients': active_patients,
        'active_patients_change': active_patients_change
    }

    # Chart 1: Monthly Progress (avg accuracy per month)
    q_monthly = db.session.query(
        func.strftime('%Y-%m', SessionMetrics.date).label('Mes'),
        func.avg(SessionMetrics.accurracy).label('Progreso')
    )
    if start_dt:
        q_monthly = q_monthly.filter(SessionMetrics.date >= start_dt)
    if end_dt:
        q_monthly = q_monthly.filter(SessionMetrics.date <= end_dt)
    q_monthly = q_monthly.group_by(func.strftime('%Y-%m', SessionMetrics.date))
    df_monthly = pd.read_sql(q_monthly.statement, db.engine)
    if df_monthly.empty:
        df_monthly = pd.DataFrame({'Mes': [], 'Progreso': []})
    fig_monthly = go.Figure()
    fig_monthly.add_trace(go.Scatter(x=df_monthly['Mes'], y=df_monthly['Progreso'], mode='lines',
                                     line=dict(color='#75a83a', width=3), fill='tozeroy', fillcolor='rgba(117, 168, 58, 0.1)'))
    monthly_progress_chart = json.loads(fig_monthly.to_json())

    # Chart 2: Sessions per Day (appointments per weekday)
    q_sessions = db.session.query(
        func.strftime('%w', Appointment.start_time).label('weekday'),
        func.count(Appointment.id).label('count')
    ).filter(Appointment.therapist_id == current_user.id).group_by(
        func.strftime('%w', Appointment.start_time)
    )
    if start_dt:
        q_sessions = q_sessions.filter(Appointment.start_time >= start_dt)
    if end_dt:
        q_sessions = q_sessions.filter(Appointment.start_time <= end_dt)
    df_sessions = pd.read_sql(q_sessions.statement, db.engine)
    # Map weekdays to labels
    weekday_map = {'1': 'Lun', '2': 'Mar', '3': 'Mié', '4': 'Jue', '5': 'Vie', '6': 'Sáb', '0': 'Dom'}
    df_sessions['Día'] = df_sessions['weekday'].map(weekday_map)
    df_sessions['Sesiones'] = df_sessions['count']
    fig_sessions = go.Figure()
    fig_sessions.add_trace(go.Bar(x=df_sessions['Día'], y=df_sessions['Sesiones'], marker_color='#75a83a', marker_line_width=0, width=0.6))
    fig_sessions.update_traces(marker_cornerradius=8)
    sessions_per_day_chart = json.loads(fig_sessions.to_json())

    # Chart 3: Game Performance (distribution of metrics by game)
    q_games = db.session.query(
        SessionMetrics.game_name.label('Juego'),
        func.count(SessionMetrics.id).label('Rendimiento')
    )
    if start_dt:
        q_games = q_games.filter(SessionMetrics.date >= start_dt)
    if end_dt:
        q_games = q_games.filter(SessionMetrics.date <= end_dt)
    q_games = q_games.group_by(SessionMetrics.game_name)
    df_games = pd.read_sql(q_games.statement, db.engine)
    colors = ['#75a83a', '#3b82f6', '#8b5cf6', '#f59e0b']
    fig_games = go.Figure(data=[go.Pie(labels=df_games['Juego'], values=df_games['Rendimiento'], hole=.4, marker_colors=colors)])
    game_performance_chart = json.loads(fig_games.to_json())

    # Difficulty analysis buckets based on prediction
    q_pred = db.session.query(
        SessionMetrics.prediction,
        func.count(SessionMetrics.id).label('cnt')
    )
    if start_dt:
        q_pred = q_pred.filter(SessionMetrics.date >= start_dt)
    if end_dt:
        q_pred = q_pred.filter(SessionMetrics.date <= end_dt)
    q_pred = q_pred.group_by(SessionMetrics.prediction)
    df_pred = pd.read_sql(q_pred.statement, db.engine)
    difficulty_analysis = [
        {'name': 'Fácil', 'percentage': int(df_pred['cnt'].sum()), 'color': 'bg-green-500'}
    ]
    # Keep layout by providing static labels; replace with refined bucketing later

    # Patient insights: top 3 by recent avg accuracy
    q_insights = db.session.query(
        SessionMetrics.user_id.label('uid'),
        func.avg(SessionMetrics.accurracy).label('acc')
    )
    if start_dt:
        q_insights = q_insights.filter(SessionMetrics.date >= start_dt)
    if end_dt:
        q_insights = q_insights.filter(SessionMetrics.date <= end_dt)
    q_insights = q_insights.group_by(SessionMetrics.user_id)
    df_insights = pd.read_sql(q_insights.statement, db.engine)
    patient_insights = []
    for _, row in df_insights.iterrows():
        user = User.query.get(row['uid'])
        patient_insights.append({'title': 'Mejor Rendimiento', 'description': f"{user.username if user else 'Paciente'} - Acc: {round(row['acc'],1)}%", 'icon': 'fas fa-star', 'icon_color': 'text-olive', 'bg_color': 'bg-green-50'})

    # Detailed reports: latest metrics per patient
    detailed_reports = []
    users = User.query.filter_by(role='jugador').all()
    for u in users:
        latest = SessionMetrics.query.filter_by(user_id=u.id).order_by(SessionMetrics.date.desc()).first()
        if latest:
            detailed_reports.append({'id': str(u.id), 'name': u.username, 'avatar': f'https://ui-avatars.com/api/?name={u.username.replace(" ", "+")}', 'last_session': latest.date.strftime('%d %b %Y %H:%M') if hasattr(latest, 'date') and latest.date else '', 'progress': int(round(latest.accurracy or 0)), 'total_time': f"{round(latest.avg_time or 0,1)}s", 'status': 'Activo' if u.is_active else 'Pausado'})

    return render_template('therapist/reports.html',
                           overview_stats=overview_stats,
                           monthly_progress_chart=monthly_progress_chart,
                           sessions_per_day_chart=sessions_per_day_chart,
                           game_performance_chart=game_performance_chart,
                           difficulty_analysis=difficulty_analysis,
                           patient_insights=patient_insights,
                           detailed_reports=detailed_reports,
                           start=start or '', end=end or '',
                           active_page='reports')

@main_bp.route('/therapist/reports')
@login_required
def therapist_reports():
    return redirect(url_for('main.reports'))


@main_bp.route('/reports/export', methods=['GET'])
@login_required
def export_reports():
    if current_user.role not in ('terapista', 'admin'):
        return jsonify({'error': 'Acceso denegado'}), 403

    start = request.args.get('start')
    end = request.args.get('end')
    try:
        if start:
            start_dt = _parse_datetime(start)
        else:
            start_dt = datetime.utcnow() - timedelta(days=90)
        if end:
            end_dt = _parse_datetime(end)
        else:
            end_dt = datetime.utcnow()
    except Exception:
        return jsonify({'error': 'Fechas inválidas'}), 400

    # Query appointments for this therapist in range
    appts = Appointment.query.filter(
        Appointment.therapist_id == current_user.id,
        Appointment.start_time >= start_dt,
        Appointment.start_time <= end_dt
    ).order_by(Appointment.start_time.asc()).all()

    # Prepare CSV in-memory
    output = io.StringIO()
    writer = csv.writer(output)
    # header
    writer.writerow(['appointment_id', 'patient_id', 'patient_name', 'start_time', 'end_time', 'status', 'location', 'notes', 'games', 'patient_total_sessions', 'patient_avg_accuracy', 'patient_avg_time', 'patient_last_session'])

    for a in appts:
        pid = a.patient_id
        patient = a.patient
        # aggregate metrics for patient in the same range
        total_sessions = SessionMetrics.query.filter(SessionMetrics.user_id == pid, SessionMetrics.date >= start_dt, SessionMetrics.date <= end_dt).count()
        avg_acc = db.session.query(func.avg(SessionMetrics.accurracy)).filter(SessionMetrics.user_id == pid, SessionMetrics.date >= start_dt, SessionMetrics.date <= end_dt).scalar() or 0
        avg_time = db.session.query(func.avg(SessionMetrics.avg_time)).filter(SessionMetrics.user_id == pid, SessionMetrics.date >= start_dt, SessionMetrics.date <= end_dt).scalar() or 0
        last_session = db.session.query(func.max(SessionMetrics.date)).filter(SessionMetrics.user_id == pid).scalar()
        last_session_str = last_session.isoformat() if last_session else ''
        try:
            games_list = json.loads(a.games) if a.games else []
        except Exception:
            games_list = []

        writer.writerow([
            a.id,
            pid,
            (patient.username if patient else ''),
            a.start_time.isoformat() if a.start_time else '',
            a.end_time.isoformat() if a.end_time else '',
            a.status,
            a.location or '',
            (a.notes or '').replace('\n', ' '),
            ';'.join(games_list),
            total_sessions,
            f"{float(avg_acc):.2f}",
            f"{float(avg_time):.2f}",
            last_session_str
        ])

    csv_data = output.getvalue()
    output.close()

    filename = f"reports_{current_user.id}_{datetime.utcnow().strftime('%Y%m%d')}.csv"
    response = make_response(csv_data)
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    response.mimetype = 'text/csv'
    return response


@main_bp.route('/patients/add', methods=['POST'])
@login_required
def add_patient():
    if current_user.role != 'terapista':
        return jsonify({'success': False, 'message': 'Acceso denegado'}), 403
    
    email = request.form.get('email', '').strip().lower()
    username = request.form.get('username', '').strip()
    
    # Validate email
    try:
        valid = validate_email(email)
        email = valid.email
    except EmailNotValidError:
        flash('Por favor, ingresa un correo electrónico válido.', 'error')
        return redirect(url_for('main.manage_patients'))
    
    # Check if user already exists
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        flash('Este correo electrónico ya está registrado.', 'error')
        return redirect(url_for('main.manage_patients'))
    
    # Generate random password
    password = EmailService.generate_password()
    hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
    
    # Create new patient
    new_patient = User(
        username=username or email.split('@')[0],
        email=email,
        password=hashed_pw,
        role='jugador',
        is_active=True
    )
    db.session.add(new_patient)
    db.session.commit()

    # Create a notification for the therapist with credentials
    notification_service.create_notification(
        user_id=current_user.id,
        message=f'Paciente {new_patient.username} agregado. Email: {email} | Contraseña: {password}',
        link=url_for('main.manage_patients')
    )

    # Send email (include username so message greets them by name)
    email_sent = EmailService.send_welcome_email(email, password, new_patient.username)
    
    # Always show credentials in flash message for easy access
    if email_sent:
        flash(f'✅ Paciente {new_patient.username} agregado exitosamente.<br>'
              f'📧 Email enviado a: <strong>{email}</strong><br>'
              f'🔑 Contraseña temporal: <strong>{password}</strong><br>'
              f'<small>El paciente recibirá estas credenciales por correo.</small>', 'success')
    else:
        flash(f'✅ Paciente {new_patient.username} agregado exitosamente.<br>'
              f'⚠️ No se pudo enviar el correo electrónico.<br>'
              f'📧 Email: <strong>{email}</strong><br>'
              f'🔑 Contraseña temporal: <strong>{password}</strong><br>'
              f'<small>Por favor, comparte estas credenciales manualmente con el paciente.</small>', 'warning')
    
    return redirect(url_for('main.manage_patients'))

@main_bp.route('/patients/toggle/<int:patient_id>', methods=['POST'])
@login_required
def toggle_patient_status(patient_id):
    if current_user.role != 'terapista':
        return jsonify({'success': False, 'message': 'Acceso denegado'}), 403
    
    patient = User.query.get_or_404(patient_id)
    patient.is_active = not patient.is_active
    db.session.commit()

    status_message = "activado" if patient.is_active else "desactivado"
    notification_service.create_notification(
        user_id=current_user.id,
        message=f'El paciente {patient.username} ha sido {status_message}.',
        link=url_for('main.manage_patients')
    )
    
    return jsonify({'success': True, 'is_active': patient.is_active})

@main_bp.route('/patients/delete/<int:patient_id>', methods=['POST'])
@login_required
def delete_patient(patient_id):
    if current_user.role != 'terapista':
        return jsonify({'success': False, 'message': 'Acceso denegado'}), 403
    
    patient = User.query.get_or_404(patient_id)
    
    # Don't allow deleting therapists
    if patient.role == 'terapista':
        return jsonify({'success': False, 'message': 'No se puede eliminar un terapeuta'}), 403
    
    patient_username = patient.username # Store for notification message
    
    try:
        # Delete patient's related records first to satisfy FK constraints
        SessionMetrics.query.filter_by(user_id=patient_id).delete()
        Appointment.query.filter_by(patient_id=patient_id).delete()
        db.session.delete(patient)

        notification_service.create_notification(
            user_id=current_user.id,
            message=f'El paciente {patient_username} ha sido eliminado permanentemente.'
        )

        db.session.commit()
        flash('Paciente eliminado exitosamente.', 'success')
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@main_bp.route('/game')
@login_required
def game():
    return render_template('game.html')

@main_bp.route('/api/save_game', methods=['POST'])
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
            print(f"DEBUG: Role={current_user.role}, UserID={current_user.id}, ApptPatientID={appt.patient_id}")
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
        from app.models import Game
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
                    notification_service.create_notification(appt.therapist_id, f"Sesión #{appt.id} completada por {current_user.username}", link=url_for('main.patients', _external=False))
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


# Upload custom game HTML to static/games
@main_bp.route('/api/games/upload', methods=['POST'])
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


# Gemini proxy for recommendations (requires GEMINI_API_KEY)
@main_bp.route('/api/ai/gemini', methods=['POST'])
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
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={api_key}"
        # Construct content: include prompt and structured context
        text_parts = [prompt]
        if context:
            text_parts.append(f"Contexto: precision={context.get('accuracy')}, tiempo_promedio={context.get('avg_time')} ms")
        body = {
            "contents": [
                {
                    "parts": [{"text": "\n\n".join([str(p) for p in text_parts])}]
                }
            ]
        }
        resp = requests.post(url, json=body, timeout=10)
        resp.raise_for_status()
        j = resp.json()
        # Parse response text
        candidate = (
            j.get('candidates', [{}])[0]
            .get('content', {})
            .get('parts', [{}])[0]
            .get('text')
        )
        # Blend internal recommendation for consistency
        acc = (context or {}).get('accuracy') or 0
        avg = (context or {}).get('avg_time') or 0
        _, label = predict_level(acc, avg)
        return jsonify({
            'status': 'ok',
            'model': 'gemini-pro',
            'recommendation': label,
            'summary': candidate or f"Basado en IA: {label}"
        })
    except Exception as e:
        # Fallback on error
        acc = (context or {}).get('accuracy') or 0
        avg = (context or {}).get('avg_time') or 0
        _, label = predict_level(acc, avg)
        return jsonify({'status': 'error', 'recommendation': label, 'detail': str(e)}), 502


# Generate an AI-driven game (HTML + JSON KPIs) and persist JSON to user
@main_bp.route('/api/ai/generate_game', methods=['POST'])
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


# Assign games to a session (Appointment.games JSON list) and enable during session
@main_bp.route('/api/sessions/assign-games', methods=['POST'])
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
@main_bp.route('/api/sessions/<int:session_id>/games', methods=['GET'])
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
@main_bp.route('/api/sessions/<int:session_id>/complete', methods=['POST'])
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
        notification_service.create_notification(appt.therapist_id, f"Sesión #{appt.id} completada. {plays} juegos registrados.", link=url_for('main.reports'))
        notification_service.create_notification(appt.patient_id, f"Sesión completada. ¡Buen trabajo!", link=url_for('main.progress'))
    except Exception:
        pass

    return jsonify({'status': 'ok', 'updated_profile': existing})

@main_bp.route('/calendar/patient')
@login_required
def calendar_patient():
    if current_user.role != 'jugador':
        flash('Acceso no autorizado', 'error')
        return redirect(url_for('main.dashboard'))
    return render_template('patient/calendar.html', active_page='calendar')

@main_bp.route('/calendar/therapist')
@login_required
def calendar_therapist():
    if current_user.role != 'terapeuta':
        flash('Acceso no autorizado', 'error')
        return redirect(url_for('main.dashboard'))
    return render_template('therapist/calendar.html', active_page='calendar')

@main_bp.route('/progress')
@login_required
def progress():
    # Show personal progress charts for the logged-in patient
    # Allow only players to view their own progress
    if current_user.role != 'jugador':
        flash('Acceso denegado: esta sección es para pacientes.', 'error')
        return redirect(url_for('main.dashboard'))

    # Build last 7 days series
    today = datetime.utcnow().date()
    days = [today - timedelta(days=i) for i in range(6, -1, -1)]
    labels = [d.strftime('%a') for d in days]
    accuracy_series = []
    time_series = []
    sessions_count = 0

    for d in days:
        start_dt = datetime(d.year, d.month, d.day)
        end_dt = start_dt + timedelta(days=1)
        q = SessionMetrics.query.filter(
            SessionMetrics.user_id == current_user.id,
            SessionMetrics.date >= start_dt,
            SessionMetrics.date < end_dt
        )
        rows = q.all()
        if rows:
            acc_vals = [r.accurracy for r in rows if r.accurracy is not None]
            time_vals = [r.avg_time for r in rows if r.avg_time is not None]
            avg_acc = round(sum(acc_vals) / len(acc_vals), 1) if acc_vals else 0
            avg_time = round(sum(time_vals) / len(time_vals), 2) if time_vals else 0
            sessions_count += len(rows)
        else:
            avg_acc = 0
            avg_time = 0
        accuracy_series.append(avg_acc)
        time_series.append(avg_time)

    # Weekly summary
    total_sessions = SessionMetrics.query.filter(SessionMetrics.user_id == current_user.id).count()
    overall_avg_acc = db.session.query(func.avg(SessionMetrics.accurracy)).filter(SessionMetrics.user_id == current_user.id).scalar() or 0
    overall_avg_time = db.session.query(func.avg(SessionMetrics.avg_time)).filter(SessionMetrics.user_id == current_user.id).scalar() or 0

    # Improvement: compare last 7 days average vs previous 7 days
    last_7_start = today - timedelta(days=6)
    prev_7_start = last_7_start - timedelta(days=7)
    last_7_acc = db.session.query(func.avg(SessionMetrics.accurracy)).filter(
        SessionMetrics.user_id == current_user.id,
        SessionMetrics.date >= datetime(last_7_start.year, last_7_start.month, last_7_start.day)
    ).scalar() or 0
    prev_7_acc = db.session.query(func.avg(SessionMetrics.accurracy)).filter(
        SessionMetrics.user_id == current_user.id,
        SessionMetrics.date >= datetime(prev_7_start.year, prev_7_start.month, prev_7_start.day),
        SessionMetrics.date < datetime(last_7_start.year, last_7_start.month, last_7_start.day)
    ).scalar() or 0
    improvement = 0
    if prev_7_acc and prev_7_acc != 0:
        improvement = int(round(((last_7_acc - prev_7_acc) / prev_7_acc) * 100))

    # Achievements (simple heuristics)
    achievements = {
        'first_session': total_sessions >= 1,
        'five_day_streak': False,
        'ten_sessions': total_sessions >= 10,
        'expert': total_sessions >= 50,
    }

    # Compute a simple streak: check last 5 days have at least one session each
    streak_ok = True
    for i in range(0, 5):
        d = today - timedelta(days=i)
        s = SessionMetrics.query.filter(
            SessionMetrics.user_id == current_user.id,
            SessionMetrics.date >= datetime(d.year, d.month, d.day),
            SessionMetrics.date < datetime(d.year, d.month, d.day) + timedelta(days=1)
        ).count()
        if s == 0:
            streak_ok = False
            break
    achievements['five_day_streak'] = streak_ok

    return render_template('patient/progress.html',
                           labels=labels,
                           accuracy_data=accuracy_series,
                           time_data=time_series,
                           weekly_summary={'sessions': sessions_count, 'avg_accuracy': int(round(overall_avg_acc)), 'avg_time': round(overall_avg_time, 2), 'improvement': f"{improvement}%"},
                           achievements=achievements,
                           active_page='progress'
                           )

@main_bp.route('/my-therapist')
@login_required
def my_therapist():
    if current_user.role != 'jugador':
        flash('Acceso no autorizado', 'error')
        return redirect(url_for('main.dashboard'))

    # Get player stats for sidebar
    total_sessions = SessionMetrics.query.filter_by(user_id=current_user.id).count()
    last_played_date = db.session.query(func.max(SessionMetrics.date)).filter_by(user_id=current_user.id).scalar()
    last_played = last_played_date.strftime('%d de %B, %Y') if last_played_date else 'Nunca'
    player_stats = {
        'total_sessions': total_sessions,
        'last_played': last_played
    }

    # Resolve assigned therapist for this patient
    therapist = None
    if current_user.assigned_therapist_id:
        therapist = User.query.get(current_user.assigned_therapist_id)
    if not therapist:
        therapist = User.query.filter_by(role='terapista', is_active=True).order_by(User.username.asc()).first()

    # Recent messages from admin or assigned therapist
    recent_messages = []
    try:
        recent_q = Message.query.join(User, Message.sender).filter(
            Message.receiver_id == current_user.id,
            or_(User.role == 'admin', User.id == current_user.assigned_therapist_id)
        ).order_by(Message.created_at.desc()).limit(6)

        for m in recent_q:
            recent_messages.append({
                'id': m.id,
                'sender_name': (m.sender.username or m.sender.email) if m.sender else 'Sistema',
                'sender_role': m.sender.role if m.sender else 'system',
                'subject': m.subject or '',
                'body': m.body or '',
                'created_at': m.created_at.strftime('%d %B, %Y') if m.created_at else ''
            })
    except Exception:
        recent_messages = []

    # Recommended resources for quick access (lightweight placeholders)
    resources = [
        {'id': 1, 'title': 'Guía de Ejercicios', 'type': 'pdf', 'meta': 'PDF - 2.5 MB'},
        {'id': 2, 'title': 'Video Tutorial', 'type': 'video', 'meta': 'MP4 - 15:30'},
        {'id': 3, 'title': 'Hoja de Práctica', 'type': 'doc', 'meta': 'DOCX - 0.4 MB'}
    ]

    return render_template('patient/my_therapist.html', active_page='therapist', player_stats=player_stats, therapist=therapist, recent_messages=recent_messages, resources=resources)


@main_bp.route('/api/resources/<int:resource_id>')
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

@main_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))


# ==================== PATIENT DETAIL VIEW ====================
@main_bp.route('/patients/<int:patient_id>')
@login_required
def patient_detail(patient_id):
    if current_user.role != 'terapista':
        flash('Acceso denegado.', 'error')
        return redirect(url_for('main.dashboard'))
    
    patient = User.query.get_or_404(patient_id)
    if patient.role != 'jugador':
        flash('Usuario no es un paciente.', 'error')
        return redirect(url_for('main.manage_patients'))
    
    # Get patient statistics
    total_sessions = SessionMetrics.query.filter_by(user_id=patient_id).count()
    avg_accuracy = db.session.query(func.avg(SessionMetrics.accurracy)).filter_by(user_id=patient_id).scalar() or 0
    avg_time = db.session.query(func.avg(SessionMetrics.avg_time)).filter_by(user_id=patient_id).scalar() or 0
    
    # Get recent sessions (last 10)
    recent_sessions = SessionMetrics.query.filter_by(user_id=patient_id).order_by(SessionMetrics.date.desc()).limit(10).all()
    
    # Get all sessions for chart data
    all_sessions = SessionMetrics.query.filter_by(user_id=patient_id).order_by(SessionMetrics.date.asc()).all()
    
    # Get upcoming appointments
    upcoming_appointments = Appointment.query.filter(
        Appointment.patient_id == patient_id,
        Appointment.start_time >= datetime.utcnow(),
        Appointment.status == 'scheduled'
    ).order_by(Appointment.start_time).limit(5).all()
    
    # Get completed appointments
    completed_appointments = Appointment.query.filter(
        Appointment.patient_id == patient_id,
        Appointment.status == 'completed'
    ).count()
    
    return render_template('therapist/patient_detail.html',
                         patient=patient,
                         total_sessions=total_sessions,
                         avg_accuracy=round(avg_accuracy, 1),
                         avg_time=round(avg_time, 2),
                         recent_sessions=recent_sessions,
                         all_sessions=all_sessions,
                         upcoming_appointments=upcoming_appointments,
                         completed_appointments=completed_appointments,
                         active_page='patients')


@main_bp.route('/patients/<int:patient_id>/update', methods=['POST'])
@login_required
def update_patient(patient_id):
    if current_user.role != 'terapista':
        return jsonify({'success': False, 'message': 'Acceso denegado'}), 403
    
    patient = User.query.get_or_404(patient_id)
    if patient.role != 'jugador':
        return jsonify({'success': False, 'message': 'Usuario no es un paciente'}), 403
    
    data = request.json
    
    # Update allowed fields
    if 'phone' in data:
        patient.phone = data['phone']
    if 'date_of_birth' in data and data['date_of_birth']:
        try:
            patient.date_of_birth = datetime.strptime(data['date_of_birth'], '%Y-%m-%d').date()
        except:
            pass
    if 'guardian_name' in data:
        patient.guardian_name = data['guardian_name']
    if 'guardian_contact' in data:
        patient.guardian_contact = data['guardian_contact']
    if 'therapy_goals' in data:
        patient.therapy_goals = data['therapy_goals']
    if 'notes' in data:
        patient.notes = data['notes']
    
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Paciente actualizado correctamente'})


# ==================== MESSAGING SYSTEM ====================
@main_bp.route('/messages')
@login_required
def messages_list():
    if current_user.role == 'admin':
        # Admin uses the dedicated admin messaging page
        return redirect(url_for('main.admin_messages'))
    # Get conversations grouped by other user
    if current_user.role == 'terapista':
        # Therapist sees all patients they've messaged
        conversations_query = db.session.query(
            User.id, User.username, User.email,
            func.max(Message.created_at).label('last_message'),
            func.count(Message.id).filter(Message.is_read == False, Message.receiver_id == current_user.id).label('unread_count')
        ).join(
            Message, 
            or_(
                (Message.sender_id == User.id) & (Message.receiver_id == current_user.id),
                (Message.receiver_id == User.id) & (Message.sender_id == current_user.id)
            )
        ).filter(User.role == 'jugador').group_by(User.id).order_by(func.max(Message.created_at).desc()).all()
        
        conversations = [{
            'user_id': c[0],
            'username': c[1],
            'email': c[2],
            'last_message': c[3],
            'unread_count': c[4]
        } for c in conversations_query]
        
        return render_template('therapist/messages.html', 
                             conversations=conversations, 
                             active_page='messages')
    else:
        # Patient sees assigned therapist; fallback to any active therapist
        therapist = None
        if current_user.assigned_therapist_id:
            therapist = User.query.get(current_user.assigned_therapist_id)
        if not therapist:
            therapist = User.query.filter_by(role='terapista', is_active=True).order_by(User.username.asc()).first()
        if not therapist:
            flash('No hay terapeutas disponibles', 'error')
            return redirect(url_for('main.dashboard'))
        
        # Get messages with this therapist
        messages = Message.query.filter(
            or_(
                (Message.sender_id == current_user.id) & (Message.receiver_id == therapist.id),
                (Message.sender_id == therapist.id) & (Message.receiver_id == current_user.id)
            )
        ).order_by(Message.created_at.desc()).all()
        
        # Mark received messages as read
        Message.query.filter(
            Message.receiver_id == current_user.id,
            Message.sender_id == therapist.id,
            Message.is_read == False
        ).update({'is_read': True})
        db.session.commit()
        
        # Get player stats for sidebar
        total_sessions = SessionMetrics.query.filter_by(user_id=current_user.id).count()
        last_played_date = db.session.query(func.max(SessionMetrics.date)).filter_by(user_id=current_user.id).scalar()
        last_played = last_played_date.strftime('%d de %B, %Y') if last_played_date else 'Nunca'
        player_stats = {
            'total_sessions': total_sessions,
            'last_played': last_played
        }
        
        return render_template('patient/messages.html',
                             therapist=therapist,
                             messages=messages,
                             player_stats=player_stats,
                             active_page='messages')


@main_bp.route('/messages/<int:user_id>')
@login_required
def messages_conversation(user_id):
    if current_user.role != 'terapista':
        flash('Acceso denegado', 'error')
        return redirect(url_for('main.dashboard'))
    
    other_user = User.query.get_or_404(user_id)
    
    # Get all messages between these two users
    messages = Message.query.filter(
        or_(
            (Message.sender_id == current_user.id) & (Message.receiver_id == user_id),
            (Message.sender_id == user_id) & (Message.receiver_id == current_user.id)
        )
    ).order_by(Message.created_at.asc()).all()
    
    # Mark received messages as read
    Message.query.filter(
        Message.receiver_id == current_user.id,
        Message.sender_id == user_id,
        Message.is_read == False
    ).update({'is_read': True})
    db.session.commit()
    
    return render_template('therapist/conversation.html',
                         other_user=other_user,
                         messages=messages,
                         active_page='messages')


@main_bp.route('/api/messages/send', methods=['POST'])
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


@main_bp.route('/api/messages/unread-count')
@login_required
def unread_messages_count():
    count = Message.query.filter_by(receiver_id=current_user.id, is_read=False).count()
    return jsonify({'count': count})


# ==================== PROFILE MANAGEMENT ====================
@main_bp.route('/profile')
@login_required
def profile():
    if current_user.role == 'admin':
        return redirect(url_for('main.admin_profile'))
    if current_user.role == 'terapista':
        # Get therapist stats
        patients_count = User.query.filter_by(assigned_therapist_id=current_user.id, role='jugador', is_active=True).count()
        # Number of appointments (sessions) handled by this therapist
        sessions_count = Appointment.query.filter_by(therapist_id=current_user.id).count()
        # Upcoming scheduled appointments starting from now
        upcoming_appointments = Appointment.query.filter(
            Appointment.therapist_id == current_user.id,
            Appointment.status == 'scheduled',
            Appointment.start_time >= datetime.utcnow()
        ).count()

        return render_template('therapist/profile.html',
                             active_page='profile',
                             patients_count=patients_count,
                             sessions_count=sessions_count,
                             upcoming_appointments=upcoming_appointments)
    else:
        # Get player stats for sidebar
        total_sessions = SessionMetrics.query.filter_by(user_id=current_user.id).count()
        last_played_date = db.session.query(func.max(SessionMetrics.date)).filter_by(user_id=current_user.id).scalar()
        last_played = last_played_date.strftime('%d de %B, %Y') if last_played_date else 'Nunca'
        player_stats = {
            'total_sessions': total_sessions,
            'last_played': last_played
        }
        return render_template('patient/profile.html', player_stats=player_stats, active_page='profile')

# ==================== ADMIN PROFILE ====================
@main_bp.route('/admin/profile')
@login_required
def admin_profile():
    if current_user.role != 'admin':
        flash('Acceso denegado.', 'error')
        return redirect(url_for('main.dashboard'))
    return render_template('admin/profile.html', active_page='admin_dashboard')

@main_bp.route('/api/admin/profile', methods=['POST'])
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


@main_bp.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    # Accept JSON body only; return JSON
    data = request.get_json(silent=True) or {}
    username = (data.get('username') or '').strip()
    phone = (data.get('phone') or '').strip()
    date_of_birth = (data.get('date_of_birth') or '').strip()
    timezone = (data.get('timezone') or '').strip()

    # Validate timezone (basic allowlist matching the UI options)
    allowed_tz = {
        'America/Lima',
        'America/New_York',
        'America/Mexico_City',
        'America/Bogota',
        'America/Argentina/Buenos_Aires',
        'Europe/Madrid'
    }
    if timezone and timezone not in allowed_tz:
        return jsonify({'success': False, 'message': 'Zona horaria inválida'}), 400

    # Parse date_of_birth (accept YYYY-MM-DD and DD/MM/YYYY)
    dob_dt = None
    if date_of_birth:
        parsed = None
        for fmt in ('%Y-%m-%d', '%d/%m/%Y'):
            try:
                parsed = datetime.strptime(date_of_birth, fmt).date()
                break
            except Exception:
                continue
        if not parsed:
            return jsonify({'success': False, 'message': 'Fecha de nacimiento inválida'}), 400
        dob_dt = parsed

    # Apply changes
    try:
        current_user.username = username or current_user.username
        current_user.phone = phone
        current_user.timezone = timezone or current_user.timezone
        current_user.date_of_birth = dob_dt if dob_dt else current_user.date_of_birth
        db.session.commit()
        return jsonify({'success': True, 'message': 'Perfil actualizado correctamente'})
    except Exception as e:
        current_app.logger.error(f"Profile update failed for user {current_user.id}: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Error al actualizar el perfil'}), 500


@main_bp.route('/profile/change-password', methods=['POST'])
@login_required
def change_password():
    data = request.get_json(silent=True) or {}
    current_password = data.get('current_password') or ''
    new_password = data.get('new_password') or ''

    # Basic validations aligned with UI
    if not current_password or not new_password:
        return jsonify({'success': False, 'message': 'Completa todos los campos'}), 400

    # Verify current password
    try:
        if not bcrypt.check_password_hash(current_user.password, current_password):
            return jsonify({'success': False, 'message': 'La contraseña actual es incorrecta'}), 400
    except Exception:
        # In case legacy hashes cause issues, fail securely
        return jsonify({'success': False, 'message': 'No se pudo verificar la contraseña actual'}), 400

    # Enforce minimum strength (sync with front-end suggestions)
    if len(new_password) < 8:
        return jsonify({'success': False, 'message': 'La contraseña debe tener al menos 8 caracteres'}), 400
    if not any(c.islower() for c in new_password):
        return jsonify({'success': False, 'message': 'La contraseña debe incluir una letra minúscula'}), 400
    if not any(c.isupper() for c in new_password):
        return jsonify({'success': False, 'message': 'La contraseña debe incluir una letra mayúscula'}), 400
    if not any(c.isdigit() for c in new_password):
        return jsonify({'success': False, 'message': 'La contraseña debe incluir un número'}), 400

    # Update password
    try:
        hashed_pw = bcrypt.generate_password_hash(new_password).decode('utf-8')
        current_user.password = hashed_pw
        db.session.commit()
        # Fire-and-forget email (do not block success)
        try:
            EmailService.send_password_change_email(current_user.email, new_password, current_user.username)
        except Exception as e:
            current_app.logger.warning(f"Non-blocking: error sending password change email: {e}")
        return jsonify({'success': True, 'message': 'Contraseña actualizada correctamente'})
    except Exception as e:
        current_app.logger.error(f"Password change failed: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Error al cambiar la contraseña'}), 500
    


