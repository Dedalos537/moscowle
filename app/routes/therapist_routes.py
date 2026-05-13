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
from sqlalchemy import func, or_, case
import json
import io
import csv
from email_validator import validate_email, EmailNotValidError
import os
from datetime import datetime, timedelta, timezone

# Lazy imports for heavy analytics libraries
pd = None
go = None
px = None

def _import_analytics_libs():
    global pd, go, px
    if pd is None:
        try:
            import pandas as pd
            import plotly.graph_objects as go
            import plotly.express as px
        except ImportError:
            pd = None
            go = None
            px = None

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
    # Filter by my patients only
    my_patient_ids = [p.id for p in current_user.associated_patients]
    if my_patient_ids:
        low_accuracy_users = db.session.query(User.username)\
            .join(SessionMetrics, SessionMetrics.user_id == User.id)\
            .filter(User.id.in_(my_patient_ids), SessionMetrics.accurracy < 60)\
            .limit(5).all()
        for name_tuple in low_accuracy_users:
            alerts.append({"patient": name_tuple[0], "message": "Rendimiento bajo detectado", "type": "red"})

    # Audit compliance data
    try:
        from app.models import SessionAudit
        from sqlalchemy import func as sqlfunc
        avg_compliance = db.session.query(sqlfunc.avg(SessionAudit.audit_score)).join(
            Appointment, SessionAudit.appointment_id == Appointment.id
        ).filter(
            Appointment.therapist_id == current_user.id,
            SessionAudit.audit_score.isnot(None)
        ).scalar() or 0
        total_audits = SessionAudit.query.join(
            Appointment, SessionAudit.appointment_id == Appointment.id
        ).filter(
            Appointment.therapist_id == current_user.id,
            SessionAudit.audit_score.isnot(None)
        ).count()
    except Exception:
        avg_compliance = 0
        total_audits = 0

    # Today's sessions (agenda)
    from datetime import datetime, timedelta
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = today + timedelta(days=1)
    today_sessions = Appointment.query.filter(
        Appointment.therapist_id == current_user.id,
        Appointment.start_time >= today,
        Appointment.start_time < tomorrow,
        Appointment.status != 'cancelled'
    ).order_by(Appointment.start_time).all()

    agenda = []
    next_session = None
    now = datetime.now()
    for s in today_sessions:
        patient = User.query.get(s.patient_id)
        is_current = s.start_time <= now and (s.end_time is None or s.end_time > now)
        session_info = {
            'id': s.id,
            'title': s.title or 'Sesion de Terapia',
            'patient': patient.username if patient else 'N/A',
            'start': s.start_time.strftime('%I:%M %p'),
            'location': s.location or '',
            'status': s.status,
            'is_current': is_current
        }
        agenda.append(session_info)
        if not next_session and (is_current or s.start_time > now):
            next_session = session_info

    # Recent audit objectives for the current/next session
    session_objectives = []
    session_progress = 0
    if next_session:
        try:
            audit = SessionAudit.query.filter_by(appointment_id=next_session['id']).first()
            if audit:
                session_progress = int(audit.audit_score or 0)
                if audit.audit_report_json and isinstance(audit.audit_report_json, dict):
                    for obj in audit.audit_report_json.get('objectives', []):
                        session_objectives.append({
                            'name': obj.get('name', ''),
                            'status': obj.get('status', 'pendiente')
                        })
        except Exception:
            pass

    return render_template('therapist/dashboard.html',
                           stats=stats,
                           patients=patients,
                           alerts=alerts,
                           avg_compliance=round(avg_compliance, 1),
                           total_audits=total_audits,
                           agenda=agenda,
                           next_session=next_session,
                           session_objectives=session_objectives,
                           session_progress=session_progress,
                           planned_text=None,
                           today_date=now.strftime('%d %b'),
                           active_page='dashboard')

@therapist_bp.route('/patients')
@login_required
def patients():
    if current_user.role != 'terapista':
        flash('Acceso denegado.', 'error')
        return redirect(url_for('main.dashboard'))
    
    patients_list = patient_service.get_therapist_patients(current_user.id)
    patients_data = []

    now = datetime.utcnow()

    for p in patients_list:
        # Default Active Status
        status_label = 'Activo'
        status_color = 'bg-green-100 text-green-700'
        
        # If Inactive (is_active=False)
        if not p.is_active:
            # Check last activity (SessionMetrics or Appointment)
            last_metric = SessionMetrics.query.filter_by(user_id=p.id).order_by(SessionMetrics.date.desc()).first()
            last_appt = Appointment.query.filter_by(patient_id=p.id, status='completed').order_by(Appointment.start_time.desc()).first()
            
            last_date = None
            if last_metric and last_appt:
                last_date = max(last_metric.date, last_appt.start_time)
            elif last_metric:
                last_date = last_metric.date
            elif last_appt:
                last_date = last_appt.start_time
            
            if last_date:
                days_inactive = (now - last_date).days
                if days_inactive > 30:
                    status_label = 'Retirado'
                    status_color = 'bg-gray-100 text-gray-700' # Gray implies retired/gone
                else:
                    status_label = 'Deudor'
                    status_color = 'bg-red-100 text-red-700' # Red implies debt/action needed
            else:
                # No history, but inactive -> Likely just created or Deudor
                status_label = 'Deudor'
                status_color = 'bg-red-100 text-red-700'
        
        patients_data.append({
            'user': p,
            'status_label': status_label,
            'status_color': status_color
        })

    return render_template('therapist/patients.html', patients=patients_data, active_page='patients')

@therapist_bp.route('/appointments/<int:appointment_id>/review')
@login_required
def session_review(appointment_id):
    """View session details, notes, and images side-by-side"""
    if current_user.role != 'terapista':
        flash('Acceso denegado.', 'error')
        return redirect(url_for('main.dashboard'))
        
    appointment = Appointment.query.get_or_404(appointment_id)
    
    # Verify ownership or assignment
    # Allows viewing if current_user conducted the session OR is one of the patient's assigned therapists
    is_assigned = False
    if appointment.patient:
        is_assigned = current_user in appointment.patient.therapists
        
    if appointment.therapist_id != current_user.id and not is_assigned:
        flash('No tienes permiso para ver esta sesión.', 'error')
        return redirect(url_for('therapist.sessions'))
        
    # Get images
    images = appointment.session_images
    
    return render_template('therapist/session_review.html', 
                           appointment=appointment, 
                           images=images,
                           active_page='sessions')

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
    _import_analytics_libs()
    if current_user.role != 'terapista':
        flash('Acceso denegado.', 'error')
        return redirect(url_for('main.dashboard'))

    # Get my patients
    my_patient_ids = [p.id for p in current_user.associated_patients]
    
    # --- Real Data Calculation ---
    
    # 1. AI Overview
    if not my_patient_ids:
        # Default empty state
        total_metrics = 0
        avg_acc = 0
        success_rate = 0
        active_models_count = 1
        recent_adaptations = []
        difficulty_adaptation_data = {}
        patient_progress_data = {}
        adaptation_frequency_data = {}
    else:
        total_metrics = SessionMetrics.query.filter(SessionMetrics.user_id.in_(my_patient_ids)).count()
        
        # Calculate averages
        avg_acc = db.session.query(func.avg(SessionMetrics.accurracy))\
            .filter(SessionMetrics.user_id.in_(my_patient_ids)).scalar() or 0
        
        # Success rate
        total_predictions = SessionMetrics.query.filter(
            SessionMetrics.user_id.in_(my_patient_ids),
            SessionMetrics.prediction.isnot(None)
        ).count()
        
        advance_predictions = SessionMetrics.query.filter(
            SessionMetrics.user_id.in_(my_patient_ids), 
            SessionMetrics.prediction == 1
        ).count()
        success_rate = (advance_predictions / total_predictions * 100) if total_predictions > 0 else 0
        
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
    model_performance = [
        {"name": "Clasificación de Nivel", "accuracy": 92},
        {"name": "Detección de Fatiga", "accuracy": 85}, # Future feature
    ]

    # 3. Recent Adaptations (Last 10 metrics for my patients)
    recent_adaptations = []
    if my_patient_ids:
        recent_metrics = db.session.query(SessionMetrics, User)\
            .join(User, SessionMetrics.user_id == User.id)\
            .filter(SessionMetrics.user_id.in_(my_patient_ids))\
            .order_by(SessionMetrics.date.desc()).limit(10).all()
        
        labels = {0: "Mantener Nivel", 1: "Avanzar Nivel", 2: "Retroceder/Apoyo"}
        
        for m, u in recent_metrics:
            recent_adaptations.append({
                "patient_name": u.username or u.email,
                "patient_avatar": f"https://ui-avatars.com/api/?name={(u.username or 'User').replace(' ', '+')}&background=random",
                "game_type": m.game_name,
                "prev_level": "?", 
                "new_level": labels.get(m.prediction, "Desconocido"),
                "reason": f"Precisión: {m.accurracy:.1f}%, Tiempo: {m.avg_time:.2f}s",
                "timestamp": m.date.strftime("%d/%m %H:%M"),
                "confidence": 90 
            })

    # 4. Charts Data
    difficulty_adaptation_data = {}
    patient_progress_data = {}
    adaptation_frequency_data = {}
    
    if go is None or pd is None or px is None:
        pass
    
    else:
        # Chart 1: Difficulty Adaptation Over Time (Last 30 days, top 5 active patients of MINE)
        last_30_days = datetime.utcnow() - timedelta(days=30)
        
        if my_patient_ids:
            try:
                top_patients = db.session.query(SessionMetrics.user_id, func.count(SessionMetrics.id))\
                    .filter(SessionMetrics.user_id.in_(my_patient_ids))\
                    .group_by(SessionMetrics.user_id).order_by(func.count(SessionMetrics.id).desc()).limit(5).all()
                
                top_patient_ids = [p[0] for p in top_patients]
                
                if top_patient_ids:
                    metrics_data = SessionMetrics.query.filter(
                        SessionMetrics.date >= last_30_days,
                        SessionMetrics.user_id.in_(top_patient_ids)
                    ).order_by(SessionMetrics.date).all()
                    
                    patient_data = {}
                    names_map = {u.id: u.username for u in User.query.filter(User.id.in_(top_patient_ids)).all()}

                    for m in metrics_data:
                        p_name = names_map.get(m.user_id, "User")
                        if p_name not in patient_data:
                            patient_data[p_name] = {'x': [], 'y': []}
                        patient_data[p_name]['x'].append(m.date.isoformat())
                        patient_data[p_name]['y'].append(m.prediction)

                    if patient_data:
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
            except Exception:
                pass

        # Chart 2: Patient Progress Distribution
        if my_patient_ids:
            try:
                subq = db.session.query(
                    SessionMetrics.user_id, 
                    func.max(SessionMetrics.date).label('max_date')
                ).filter(SessionMetrics.user_id.in_(my_patient_ids))\
                .group_by(SessionMetrics.user_id).subquery()
                
                latest_metrics = db.session.query(SessionMetrics).join(
                    subq, 
                    (SessionMetrics.user_id == subq.c.user_id) & (SessionMetrics.date == subq.c.max_date)
                ).all()
                
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
            except Exception:
                pass

        # Chart 3: Adaptation Frequency by Game
        if my_patient_ids:
            try:
                game_counts = db.session.query(SessionMetrics.game_name, func.count(SessionMetrics.id))\
                    .filter(SessionMetrics.user_id.in_(my_patient_ids))\
                    .group_by(SessionMetrics.game_name).all()
                
                if game_counts:
                    df_adaptation = pd.DataFrame(game_counts, columns=['Juego', 'Frecuencia'])
                    fig_adaptation = px.pie(df_adaptation, values='Frecuencia', names='Juego', title='Juegos Más Jugados', hole=.3, template='plotly_white')
                    adaptation_frequency_data = json.loads(fig_adaptation.to_json())
            except Exception:
                pass

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
    _import_analytics_libs()
    if current_user.role != 'terapista':
        flash('Acceso denegado.', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Filters
    start = request.args.get('start')
    end = request.args.get('end')
    start_dt = _parse_datetime(start) if start else None
    end_dt = _parse_datetime(end) if end else None

    # Filter stats by MY patients
    my_patient_ids = [p.id for p in current_user.associated_patients]
    
    # Overview stats from DB
    now = datetime.utcnow()
    last_30 = now - timedelta(days=30)
    prev_60 = now - timedelta(days=60)
    
    improvement_rate = 0
    improvement_rate_change = 0
    avg_session_time = 0
    avg_session_time_change = 0
    completed_objectives = 0
    completed_objectives_change = 0
    active_patients = 0
    active_patients_change = 0 # Placeholder as we don't track historical patient count easily

    monthly_progress_chart = {}
    sessions_per_day_chart = {}
    game_performance_chart = {}
    
    if my_patient_ids:
        # 1. Improvement Rate
        avg_last_30 = db.session.query(func.avg(SessionMetrics.accurracy))\
            .filter(SessionMetrics.user_id.in_(my_patient_ids), SessionMetrics.date >= last_30).scalar() or 0
        avg_prev_30 = db.session.query(func.avg(SessionMetrics.accurracy))\
            .filter(SessionMetrics.user_id.in_(my_patient_ids), SessionMetrics.date >= prev_60, SessionMetrics.date < last_30).scalar() or 0
        
        if avg_prev_30:
            improvement_rate = round(avg_last_30, 1)
            improvement_rate_change = round(((avg_last_30 - avg_prev_30) / avg_prev_30) * 100, 1)
        else:
            improvement_rate = round(avg_last_30, 1)

        # 2. Avg Session Time
        avg_session_time = db.session.query(func.avg(SessionMetrics.avg_time))\
            .filter(SessionMetrics.user_id.in_(my_patient_ids)).scalar() or 0

        # 3. Completed Objectives (Accuracy >= 80)
        completed_objectives = SessionMetrics.query.filter(
            SessionMetrics.user_id.in_(my_patient_ids),
            SessionMetrics.accurracy >= 80
        ).count()

        # 4. Active Patients
        active_patients = len([p for p in current_user.associated_patients if p.is_active])


        # Chart 1: Monthly Progress
        
        # Check dialect for date formatting
        if db.engine.dialect.name == 'sqlite':
            month_col = func.strftime('%Y-%m', SessionMetrics.date).label('Mes')
        else:
            # MySQL / PostgreSQL (assuming MySQL as standard on cPanel)
            month_col = func.date_format(SessionMetrics.date, '%Y-%m').label('Mes')

        q_monthly = db.session.query(
            month_col,
            func.avg(SessionMetrics.accurracy).label('Progreso')
        ).filter(SessionMetrics.user_id.in_(my_patient_ids))

        if start_dt:
            q_monthly = q_monthly.filter(SessionMetrics.date >= start_dt)
        if end_dt:
            q_monthly = q_monthly.filter(SessionMetrics.date <= end_dt)
        
        q_monthly = q_monthly.group_by(month_col)
        df_monthly = pd.read_sql(q_monthly.statement, db.engine)
        
        if df_monthly.empty:
            df_monthly = pd.DataFrame({'Mes': [], 'Progreso': []})
        
        fig_monthly = go.Figure()
        fig_monthly.add_trace(go.Scatter(x=df_monthly['Mes'], y=df_monthly['Progreso'], mode='lines',
                                         line=dict(color='#75a83a', width=3), fill='tozeroy', fillcolor='rgba(117, 168, 58, 0.1)'))
        monthly_progress_chart = json.loads(fig_monthly.to_json())

        # Chart 2: Sessions per Day
        
        # Dialect check for weekday extraction
        if db.engine.dialect.name == 'sqlite':
            weekday_col = func.strftime('%w', Appointment.start_time).label('weekday')
        else:
            # MySQL: DAYOFWEEK() returns 1=Sun, 2=Mon...7=Sat. SQLite %w returns 0=Sun, 1=Mon...6=Sat.
            # We need to standardize. Let's stick to 0=Sun..6=Sat logic if possible, or just build separate maps.
            # But wait, let's just use Python for weekday processing if possible. Or handle mapping carefully.
            # MySQL: DAYOFWEEK(date) -> 1=Sunday, 2=Monday.
            # SQLite: strftime('%w', date) -> 0=Sunday, 1=Monday.
            # To normalize to 0=Sun, 1=Mon...: MySQL DAYOFWEEK(date) - 1
            weekday_col = (func.dayofweek(Appointment.start_time) - 1).label('weekday')

        q_sessions = db.session.query(
            weekday_col,
            func.count(Appointment.id).label('count')
        ).filter(Appointment.therapist_id == current_user.id).group_by(
            weekday_col
        )
        if start_dt:
            q_sessions = q_sessions.filter(Appointment.start_time >= start_dt)
        if end_dt:
            q_sessions = q_sessions.filter(Appointment.start_time <= end_dt)
        df_sessions = pd.read_sql(q_sessions.statement, db.engine)
        
        # Normalize weekday column to string to handle both SQLite (str) and MySQL (int)
        if not df_sessions.empty:
            df_sessions['weekday'] = df_sessions['weekday'].astype(str).str.split('.').str[0] # Handle potential float conversion
            
        weekday_map = {'1': 'Lun', '2': 'Mar', '3': 'Mié', '4': 'Jue', '5': 'Vie', '6': 'Sáb', '0': 'Dom'}
        if not df_sessions.empty:
            df_sessions['Día'] = df_sessions['weekday'].map(weekday_map)
            df_sessions['Sesiones'] = df_sessions['count']
            fig_sessions = go.Figure()
            fig_sessions.add_trace(go.Bar(x=df_sessions['Día'], y=df_sessions['Sesiones'], marker_color='#75a83a', marker_line_width=0, width=0.6))
            fig_sessions.update_traces(marker_cornerradius=8)
            sessions_per_day_chart = json.loads(fig_sessions.to_json())
        else:
            sessions_per_day_chart = {}

        # Chart 3: Game Performance
        q_games = db.session.query(
            SessionMetrics.game_name.label('Juego'),
            func.count(SessionMetrics.id).label('Rendimiento')
        ).filter(SessionMetrics.user_id.in_(my_patient_ids))

        if start_dt:
            q_games = q_games.filter(SessionMetrics.date >= start_dt)
        if end_dt:
            q_games = q_games.filter(SessionMetrics.date <= end_dt)
        
        q_games = q_games.group_by(SessionMetrics.game_name)
        df_games = pd.read_sql(q_games.statement, db.engine)
        
        if not df_games.empty:
            colors = ['#75a83a', '#3b82f6', '#8b5cf6', '#f59e0b']
            fig_games = go.Figure(data=[go.Pie(labels=df_games['Juego'], values=df_games['Rendimiento'], hole=.4, marker_colors=colors)])
            game_performance_chart = json.loads(fig_games.to_json())
        else:
             game_performance_chart = {}

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

    # Difficulty analysis buckets based on prediction
    q_pred = db.session.query(
        SessionMetrics.prediction,
        func.count(SessionMetrics.id).label('cnt')
    )
    if my_patient_ids:
        q_pred = q_pred.filter(SessionMetrics.user_id.in_(my_patient_ids))

    if start_dt:
        q_pred = q_pred.filter(SessionMetrics.date >= start_dt)
    if end_dt:
        q_pred = q_pred.filter(SessionMetrics.date <= end_dt)
    q_pred = q_pred.group_by(SessionMetrics.prediction)
    df_pred = pd.read_sql(q_pred.statement, db.engine)
    
    # Placeholder buckets since we don't have 'cnt' per level defined well yet
    difficulty_analysis = [
        {'name': 'Fácil', 'percentage': int(df_pred['cnt'].sum()) if not df_pred.empty else 0, 'color': 'bg-green-500'}
    ]

    # Patient insights: top 3 by recent avg accuracy
    q_insights = db.session.query(
        SessionMetrics.user_id.label('uid'),
        func.avg(SessionMetrics.accurracy).label('acc')
    ).filter(SessionMetrics.user_id.in_(my_patient_ids))
    
    if start_dt:
        q_insights = q_insights.filter(SessionMetrics.date >= start_dt)
    if end_dt:
        q_insights = q_insights.filter(SessionMetrics.date <= end_dt)
    q_insights = q_insights.group_by(SessionMetrics.user_id)
    df_insights = pd.read_sql(q_insights.statement, db.engine)
    patient_insights = []
    
    for _, row in df_insights.iterrows():
        user = User.query.get(row['uid'])
        if user:
            patient_insights.append({'title': 'Mejor Rendimiento', 'description': f"{user.username} - Acc: {round(row['acc'],1)}%", 'icon': 'fas fa-star', 'icon_color': 'text-olive', 'bg_color': 'bg-green-50'})

    # Detailed reports: latest metrics per patient
    detailed_reports = []
    # Use associated_patients
    users = current_user.associated_patients.filter_by(role='jugador').all()
    
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
    # Use SUM(CASE...) for cross-DB compatibility (MySQL 5.7/MariaDB don't support FILTER)
    unread_expr = func.sum(case(
        ( (Message.is_read == False) & (Message.receiver_id == current_user.id), 1 ),
        else_=0
    ))

    conversations_query = db.session.query(
        User.id, User.username, User.email,
        func.max(Message.created_at).label('last_message'),
        unread_expr.label('unread_count')
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
    
    # -----------------------------------------------------------
    # FEATURE: Permitir crear paciente SIN email (solo nombre)
    # -----------------------------------------------------------
    import uuid
    
    is_full_account = False
    password = None

    # Caso 1: No hay email -> Crear usuario "placeholder" (inactivo)
    if not email:
        if not username:
             flash('Debes ingresar al menos el Nombre del paciente si no proporcionas un email.', 'error')
             return redirect(url_for('therapist.patients'))
        
        # Generar email ficticio único para cumplir constraint unique database
        email = f"noemail_{uuid.uuid4().hex[:8]}@local"
        password = uuid.uuid4().hex # Contraseña aleatoria desconocida
        is_full_account = False
    
    # Caso 2: Sí hay email -> Validar y crear usuario activo
    else:
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
        
        password = EmailService.generate_password()
        is_full_account = True
    
    hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
    
    # Create new patient
    new_patient = User(
        username=username or email.split('@')[0],
        email=email,
        password=hashed_pw,
        role='jugador',
        is_active=is_full_account,    # Si no tiene email, no está activo
        assigned_therapist_id=current_user.id  # Asignar al terapeuta actual (Legacy primary)
    )
    # Add to new Many-to-Many relationship
    new_patient.therapists.append(current_user)
    
    db.session.add(new_patient)
    db.session.commit()

    if is_full_account:
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
    else:
        # Mensaje para usuario sin email
        flash(f'✅ Paciente {new_patient.username} creado (Modo Presencial/Sin Email).<br>'
              f'<small>Se ha creado el registro para gestionar terapias y pagos.</small><br>'
              f'<small>⚠️ La cuenta no tiene acceso al sistema. Para activarla, edita el perfil y añade un email válido.</small>', 'success')
    
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
    if current_user.role not in ['terapista', 'admin']:
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
    
    # Get all appointments for history list (not just metrics)
    history_appointments = Appointment.query.filter(
        Appointment.patient_id == patient_id
    ).order_by(Appointment.start_time.desc()).all()

    # Get all sessions for chart data
    all_sessions_query = SessionMetrics.query.filter_by(user_id=patient_id).order_by(SessionMetrics.date.asc()).all()
    all_sessions = []
    for s in all_sessions_query:
        all_sessions.append({
            'date': s.date.isoformat(),
            'accurracy': s.accurracy,
            'avg_time': s.avg_time
        })
    
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
                         history_appointments=history_appointments,
                         all_sessions=all_sessions,
                         upcoming_appointments=upcoming_appointments,
                         completed_appointments=completed_appointments,
                         active_page='patients')

@therapist_bp.route('/patients/<int:patient_id>/update', methods=['POST'])
@login_required
def update_patient(patient_id):
    if current_user.role not in ['terapista', 'admin']:
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
        
    # Activar cuenta añadiendo email
    if 'email' in data and data['email']:
        new_email = data['email'].strip().lower()
        # Solo procesar si cambia y no estaba ya tomado
        if new_email != patient.email and new_email:
            # Check exist
            exists = User.query.filter_by(email=new_email).first()
            if exists:
                return jsonify({'success': False, 'message': 'El correo ya está registrado por otro usuario'}), 400
            
            # Detectar si estamos activando una cuenta previamente "sin email"
            was_placeholder = patient.email.startswith('noemail_') or patient.email.startswith('temp_')
            
            patient.email = new_email
            
            if was_placeholder:
                # Generar credenciales reales y activar
                password = EmailService.generate_password()
                patient.password = bcrypt.generate_password_hash(password).decode('utf-8')
                patient.is_active = True
                
                # Intentar enviar correo
                try:
                    EmailService.send_welcome_email(new_email, password, patient.username)
                    # Notificar al return para mostrar en UI
                    db.session.commit()
                    return jsonify({
                        'success': True, 
                        'message': 'Cuenta activada exitosamente. Se han enviado las credenciales por correo.',
                        'new_credentials': {'email': new_email, 'password': password}
                    })
                except Exception:
                     # Fallback si falla correo
                    pass

    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Paciente actualizado correctamente'})


# ─────────────────────────────────────────────────────────────
# JSON API endpoints for Angular therapist module
# ─────────────────────────────────────────────────────────────

@therapist_bp.route('/api/dashboard-stats')
@login_required
def api_dashboard_stats():
    if current_user.role != 'terapista':
        return jsonify({'error': 'Acceso denegado'}), 403

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

    active_patients = User.query.filter(
        User.assigned_therapist_id == current_user.id,
        User.role == 'jugador',
        User.is_active == True
    ).count()

    return jsonify({
        'sessions_today': sessions_today,
        'completed_sessions': completed_sessions,
        'pending_sessions': pending_sessions,
        'active_patients': active_patients,
    })


@therapist_bp.route('/api/conversations')
@login_required
def api_conversations():
    if current_user.role != 'terapista':
        return jsonify({'error': 'Acceso denegado'}), 403

    unread_expr = func.sum(case(
        ((Message.is_read == False) & (Message.receiver_id == current_user.id), 1),
        else_=0
    ))

    conv_query = db.session.query(
        User.id, User.username, User.email,
        func.max(Message.created_at).label('last_message'),
        unread_expr.label('unread_count')
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
        'last_message': c[3].isoformat() if c[3] else None,
        'unread_count': c[4]
    } for c in conv_query]

    return jsonify({'conversations': conversations})


@therapist_bp.route('/api/messages/<int:user_id>')
@login_required
def api_conversation_thread(user_id):
    if current_user.role != 'terapista':
        return jsonify({'error': 'Acceso denegado'}), 403

    other_user = User.query.get_or_404(user_id)

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

    return jsonify({
        'other_user': {
            'id': other_user.id,
            'username': other_user.username,
            'email': other_user.email,
        },
        'messages': [{
            'id': m.id,
            'sender_id': m.sender_id,
            'receiver_id': m.receiver_id,
            'body': m.body,
            'file_url': m.file_url,
            'file_type': m.file_type,
            'created_at': m.created_at.isoformat() if m.created_at else None,
            'is_read': m.is_read,
        } for m in messages]
    })


@therapist_bp.route('/api/profile')
@login_required
def api_profile():
    if current_user.role != 'terapista':
        return jsonify({'error': 'Acceso denegado'}), 403

    patients_count = User.query.filter_by(
        assigned_therapist_id=current_user.id, role='jugador', is_active=True
    ).count()

    sessions_count = Appointment.query.filter_by(therapist_id=current_user.id).count()

    upcoming_appointments = Appointment.query.filter(
        Appointment.therapist_id == current_user.id,
        Appointment.status == 'scheduled',
        Appointment.start_time >= datetime.utcnow()
    ).count()

    return jsonify({
        'id': current_user.id,
        'username': current_user.username,
        'email': current_user.email,
        'timezone': getattr(current_user, 'timezone', 'America/Lima'),
        'created_at': current_user.created_at.isoformat() if hasattr(current_user, 'created_at') and current_user.created_at else None,
        'patients_count': patients_count,
        'sessions_count': sessions_count,
        'upcoming_appointments': upcoming_appointments,
    })


@therapist_bp.route('/api/profile', methods=['PUT'])
@login_required
def api_update_profile():
    if current_user.role != 'terapista':
        return jsonify({'error': 'Acceso denegado'}), 403

    data = request.get_json(silent=True) or {}

    if 'username' in data and data['username']:
        current_user.username = data['username'].strip()
    if 'timezone' in data:
        current_user.timezone = data['timezone']

    if 'new_password' in data and data['new_password']:
        current_user.password = bcrypt.generate_password_hash(data['new_password']).decode('utf-8')

    db.session.commit()

    return jsonify({'success': True, 'message': 'Perfil actualizado correctamente'})


