from flask import Blueprint, render_template, request, redirect, url_for, jsonify, flash, make_response, current_app
from flask_login import login_required, current_user
from app.models import SessionMetrics, db, User, Appointment, Message
from app.extensions import bcrypt
from app.services.dashboard_service import DashboardService
from app.services.email_service import EmailService
from app.services.appointment_service import AppointmentService
from app.services.game_service import GameService
from app.services.notification_service import NotificationService
from app.services.patient_service import PatientService
from app.utils import get_user_today_utc_range
from sqlalchemy import func, or_
import json
import io
import csv
from email_validator import validate_email, EmailNotValidError
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import os
from datetime import datetime, timedelta
import pytz

therapist_bp = Blueprint('therapist', __name__, url_prefix='/therapist')
dashboard_service = DashboardService()
appointment_service = AppointmentService()
game_service = GameService()
notification_service = NotificationService()
patient_service = PatientService()

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

@therapist_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role != 'terapista':
        return redirect(url_for('main.dashboard'))

    # Therapist stats
    stats = dashboard_service.get_therapist_stats(current_user.id)
    patients = dashboard_service.get_therapist_patients_data(current_user.id)

    # Alerts: simple heuristics
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

@therapist_bp.route('/patients')
@login_required
def patients():
    if current_user.role != 'terapista':
        flash('Acceso denegado.', 'error')
        return redirect(url_for('main.dashboard'))
    
    patients = patient_service.get_therapist_patients(current_user.id)
    return render_template('therapist/patients.html', patients=patients, active_page='patients')

@therapist_bp.route('/sessions')
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

@therapist_bp.route('/games')
@login_required
def games():
    if current_user.role != 'terapista':
        return redirect(url_for('main.dashboard'))
    files = game_service.list_games()
    return render_template('therapist/games.html', custom_games=files, active_page='games')

@therapist_bp.route('/analytics')
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

@therapist_bp.route('/reports')
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

@therapist_bp.route('/reports/export', methods=['GET'])
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

@therapist_bp.route('/messages')
@login_required
def messages():
    if current_user.role != 'terapista':
        flash('Acceso denegado', 'error')
        return redirect(url_for('main.dashboard'))
        
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

@therapist_bp.route('/messages/<int:user_id>')
@login_required
def conversation(user_id):
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

@therapist_bp.route('/profile')
@login_required
def profile():
    if current_user.role != 'terapista':
        return redirect(url_for('main.dashboard'))
    
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

@therapist_bp.route('/patients/add', methods=['POST'])
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
        return redirect(url_for('therapist.patients'))
    
    # Check if user already exists
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        flash('Este correo electrónico ya está registrado.', 'error')
        return redirect(url_for('therapist.patients'))
    
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
        link=url_for('therapist.patients')
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
    
    return redirect(url_for('therapist.patients'))

@therapist_bp.route('/patients/toggle/<int:patient_id>', methods=['POST'])
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
        link=url_for('therapist.patients')
    )
    
    return jsonify({'success': True, 'is_active': patient.is_active})

@therapist_bp.route('/patients/delete/<int:patient_id>', methods=['POST'])
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

@therapist_bp.route('/calendar')
@login_required
def calendar():
    if current_user.role != 'terapista':
        flash('Acceso no autorizado', 'error')
        return redirect(url_for('main.dashboard'))
    return render_template('therapist/calendar.html', active_page='calendar')

@therapist_bp.route('/patients/<int:patient_id>')
@login_required
def patient_detail(patient_id):
    if current_user.role != 'terapista':
        flash('Acceso denegado.', 'error')
        return redirect(url_for('main.dashboard'))
    
    patient = User.query.get_or_404(patient_id)
    if patient.role != 'jugador':
        flash('Usuario no es un paciente.', 'error')
        return redirect(url_for('therapist.patients'))
    
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

@therapist_bp.route('/patients/<int:patient_id>/update', methods=['POST'])
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


