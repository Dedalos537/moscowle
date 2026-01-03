from flask import Blueprint, render_template, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from app.models import SessionMetrics, db, User, Message, Appointment
from app.services.dashboard_service import DashboardService
from app.services.appointment_service import AppointmentService
from app.utils import get_user_today_utc_range, get_user_now
from sqlalchemy import func, or_
import json
import pytz
from datetime import datetime, timedelta

patient_bp = Blueprint('patient', __name__, url_prefix='/patient')
dashboard_service = DashboardService()
appointment_service = AppointmentService()

@patient_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role != 'jugador':
        return redirect(url_for('main.dashboard'))
        
    # Player stats
    player_stats = dashboard_service.get_player_stats(current_user.id)
    
    # Get today's sessions for the dashboard
    today_start, today_end = get_user_today_utc_range(current_user)
    today_sessions = appointment_service.get_patient_appointments(current_user.id, today_start, today_end)
    
    # Define now for session active check
    now = get_user_now(current_user)

    # Process sessions to include game info
    sessions_data = []
    for s in today_sessions:
        games = []
        try:
            games = json.loads(s.games) if s.games else []
        except:
            games = []
        
        # Localize DB times to UTC for comparison with aware 'now'
        # DB stores naive UTC
        s_start_aware = s.start_time.replace(tzinfo=pytz.UTC)
        s_end_val = s.end_time or (s.start_time + timedelta(hours=1))
        s_end_aware = s_end_val.replace(tzinfo=pytz.UTC)

        # Check if session is active (within time window)
        is_active = False
        if s.status == 'scheduled':
            if s_start_aware <= now <= s_end_aware:
                is_active = True
        
        sessions_data.append({
            'id': s.id,
            'title': s.title,
            'start_time': s_start_aware,
            'end_time': s_end_aware,
            'games': games,
            'is_active': is_active,
            'therapist_name': s.therapist.username if s.therapist else 'Terapeuta'
        })

    return render_template('patient/dashboard.html', 
                           player_stats=player_stats,
                           today_sessions=sessions_data,
                           active_page='dashboard',
                           now=now)

@patient_bp.route('/sessions')
@login_required
def sessions():
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

@patient_bp.route('/calendar')
@login_required
def calendar():
    if current_user.role != 'jugador':
        flash('Acceso no autorizado', 'error')
        return redirect(url_for('main.dashboard'))
    return render_template('patient/calendar.html', active_page='calendar')

@patient_bp.route('/progress')
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

@patient_bp.route('/my-therapist')
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

@patient_bp.route('/messages')
@login_required
def messages():
    if current_user.role != 'jugador':
        return redirect(url_for('main.messages_list'))

    # Patient sees assigned therapist; fallback to any active therapist
    therapist = None
    if current_user.assigned_therapist_id:
        therapist = User.query.get(current_user.assigned_therapist_id)
    if not therapist:
        therapist = User.query.filter_by(role='terapista', is_active=True).order_by(User.username.asc()).first()
    if not therapist:
        flash('No hay terapeutas disponibles', 'error')
        return redirect(url_for('patient.dashboard'))
    
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

@patient_bp.route('/profile')
@login_required
def profile():
    if current_user.role != 'jugador':
        return redirect(url_for('main.profile'))
        
    # Get player stats for sidebar
    total_sessions = SessionMetrics.query.filter_by(user_id=current_user.id).count()
    last_played_date = db.session.query(func.max(SessionMetrics.date)).filter_by(user_id=current_user.id).scalar()
    last_played = last_played_date.strftime('%d de %B, %Y') if last_played_date else 'Nunca'
    player_stats = {
        'total_sessions': total_sessions,
        'last_played': last_played
    }
    return render_template('patient/profile.html', player_stats=player_stats, active_page='profile')
