import csv
import io
import json
from datetime import datetime, timedelta

from email_validator import EmailNotValidError, validate_email
from flask import Blueprint, current_app, flash, jsonify, make_response, redirect, render_template, request, url_for
from sqlalchemy import case, func, or_

from app.auth_compat import current_user, login_required
from app.extensions import bcrypt, csrf
from app.models import Appointment, Message, MonthlyReport, QuarterlyReport, SessionMetrics, User, WeeklyReport, db
from app.services.appointment_service import AppointmentService
from app.services.dashboard_service import DashboardService
from app.services.email_service import EmailService
from app.services.game_service import GameService
from app.services.notification_service import NotificationService
from app.services.patient_service import PatientService
from app.utils import get_user_timezone, get_user_today_utc_range, localize_datetime_for_display
from app.utils import parse_datetime as _parse_datetime

pd = None
go = None
px = None


def _import_analytics_libs():
    global pd, go, px
    if pd is None:
        try:
            import pandas as pd
            import plotly.express as px
            import plotly.graph_objects as go
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


@therapist_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role != 'terapista':
        return redirect(url_for('main.dashboard'))
    return redirect('/')


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
        status_label = 'Activo'
        status_color = 'bg-green-100 text-green-700'

        if not p.is_active:
            last_metric = SessionMetrics.query.filter_by(user_id=p.id).order_by(SessionMetrics.date.desc()).first()
            last_appt = (
                Appointment.query.filter_by(patient_id=p.id, status='completed')
                .order_by(Appointment.start_time.desc())
                .first()
            )

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
                    status_color = 'bg-gray-100 text-gray-700'
                else:
                    status_label = 'Deudor'
                    status_color = 'bg-red-100 text-red-700'
            else:
                status_label = 'Deudor'
                status_color = 'bg-red-100 text-red-700'

        patients_data.append({'user': p, 'status_label': status_label, 'status_color': status_color})

    return render_template('therapist/patients.html', patients=patients_data, active_page='patients')


@therapist_bp.route('/appointments/<int:appointment_id>/review')
@login_required
def session_review(appointment_id):
    """View session details, notes, and images side-by-side"""
    if current_user.role != 'terapista':
        flash('Acceso denegado.', 'error')
        return redirect(url_for('main.dashboard'))

    appointment = Appointment.query.get_or_404(appointment_id)

    is_assigned = False
    if appointment.patient:
        is_assigned = current_user in appointment.patient.therapists

    if appointment.therapist_id != current_user.id and not is_assigned:
        flash('No tienes permiso para ver esta sesión.', 'error')
        return redirect(url_for('therapist.sessions'))

    images = appointment.session_images

    return render_template(
        'therapist/session_review.html', appointment=appointment, images=images, active_page='sessions'
    )


@therapist_bp.route('/sessions')
@login_required
def sessions():
    if current_user.role != 'terapista':
        return redirect(url_for('main.dashboard'))
    return redirect('/')


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

    my_patient_ids = [p.id for p in current_user.associated_patients]

    if not my_patient_ids:
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

        avg_acc = (
            db.session.query(func.avg(SessionMetrics.accurracy))
            .filter(SessionMetrics.user_id.in_(my_patient_ids))
            .scalar()
            or 0
        )

        total_predictions = SessionMetrics.query.filter(
            SessionMetrics.user_id.in_(my_patient_ids), SessionMetrics.prediction.isnot(None)
        ).count()

        advance_predictions = SessionMetrics.query.filter(
            SessionMetrics.user_id.in_(my_patient_ids), SessionMetrics.prediction == 1
        ).count()
        success_rate = (advance_predictions / total_predictions * 100) if total_predictions > 0 else 0

        active_models_count = 1

    ai_overview = {
        'total_adaptations': total_metrics,
        'adaptations_change': 0,
        'avg_accuracy': round(avg_acc, 1),
        'accuracy_improvement': 0,
        'success_rate': round(success_rate, 1),
        'success_rate_increase': 0,
        'active_models': active_models_count,
        'insight': 'El modelo SVM se está adaptando a los patrones de tiempo y precisión de los pacientes.',
    }

    model_performance = [
        {'name': 'Clasificación de Nivel', 'accuracy': 92},
        {'name': 'Detección de Fatiga', 'accuracy': 85},
    ]

    recent_adaptations = []
    if my_patient_ids:
        recent_metrics = (
            db.session.query(SessionMetrics, User)
            .join(User, SessionMetrics.user_id == User.id)
            .filter(SessionMetrics.user_id.in_(my_patient_ids))
            .order_by(SessionMetrics.date.desc())
            .limit(10)
            .all()
        )

        labels = {0: 'Mantener Nivel', 1: 'Avanzar Nivel', 2: 'Retroceder/Apoyo'}

        for m, u in recent_metrics:
            recent_adaptations.append(
                {
                    'patient_name': u.username or u.email,
                    'patient_avatar': f'https://ui-avatars.com/api/?name={(u.username or "User").replace(" ", "+")}&background=random',
                    'game_type': m.game_name,
                    'prev_level': '?',
                    'new_level': labels.get(m.prediction, 'Desconocido'),
                    'reason': f'Precisión: {m.accurracy:.1f}%, Tiempo: {m.avg_time:.2f}s',
                    'timestamp': m.date.strftime('%d/%m %H:%M'),
                    'confidence': 90,
                }
            )

    difficulty_adaptation_data = {}
    patient_progress_data = {}
    adaptation_frequency_data = {}

    if go is None or pd is None or px is None:
        pass

    else:
        last_30_days = datetime.utcnow() - timedelta(days=30)

        if my_patient_ids:
            try:
                top_patients = (
                    db.session.query(SessionMetrics.user_id, func.count(SessionMetrics.id))
                    .filter(SessionMetrics.user_id.in_(my_patient_ids))
                    .group_by(SessionMetrics.user_id)
                    .order_by(func.count(SessionMetrics.id).desc())
                    .limit(5)
                    .all()
                )

                top_patient_ids = [p[0] for p in top_patients]

                if top_patient_ids:
                    metrics_data = (
                        SessionMetrics.query.filter(
                            SessionMetrics.date >= last_30_days, SessionMetrics.user_id.in_(top_patient_ids)
                        )
                        .order_by(SessionMetrics.date)
                        .all()
                    )

                    patient_data = {}
                    names_map = {u.id: u.username for u in User.query.filter(User.id.in_(top_patient_ids)).all()}

                    for m in metrics_data:
                        p_name = names_map.get(m.user_id, 'User')
                        if p_name not in patient_data:
                            patient_data[p_name] = {'x': [], 'y': []}
                        patient_data[p_name]['x'].append(m.date.isoformat())
                        patient_data[p_name]['y'].append(m.prediction)

                    if patient_data:
                        fig_difficulty = go.Figure()
                        for name, data in patient_data.items():
                            fig_difficulty.add_trace(
                                go.Scatter(x=data['x'], y=data['y'], name=name, mode='lines+markers')
                            )
                        fig_difficulty.update_layout(
                            title='Adaptación de Nivel (Últimos 30 días)',
                            xaxis_title='Fecha',
                            yaxis_title='Decisión IA (0=Mantener, 1=Avanzar, 2=Apoyo)',
                            template='plotly_white',
                            legend_title_text='Pacientes',
                        )
                        difficulty_adaptation_data = json.loads(fig_difficulty.to_json())
            except Exception:
                pass

        if my_patient_ids:
            try:
                subq = (
                    db.session.query(SessionMetrics.user_id, func.max(SessionMetrics.date).label('max_date'))
                    .filter(SessionMetrics.user_id.in_(my_patient_ids))
                    .group_by(SessionMetrics.user_id)
                    .subquery()
                )

                latest_metrics = (
                    db.session.query(SessionMetrics)
                    .join(subq, (SessionMetrics.user_id == subq.c.user_id) & (SessionMetrics.date == subq.c.max_date))
                    .all()
                )

                pred_counts = {0: 0, 1: 0, 2: 0}
                for m in latest_metrics:
                    if m.prediction in pred_counts:
                        pred_counts[m.prediction] += 1

                df_progress = pd.DataFrame(
                    {
                        'Decisión': ['Mantener', 'Avanzar', 'Apoyo'],
                        'Pacientes': [pred_counts[0], pred_counts[1], pred_counts[2]],
                    }
                )

                fig_progress = px.bar(
                    df_progress,
                    x='Decisión',
                    y='Pacientes',
                    title='Estado Actual de Pacientes',
                    template='plotly_white',
                    color='Decisión',
                )
                patient_progress_data = json.loads(fig_progress.to_json())
            except Exception:
                pass

        if my_patient_ids:
            try:
                game_counts = (
                    db.session.query(SessionMetrics.game_name, func.count(SessionMetrics.id))
                    .filter(SessionMetrics.user_id.in_(my_patient_ids))
                    .group_by(SessionMetrics.game_name)
                    .all()
                )

                if game_counts:
                    df_adaptation = pd.DataFrame(game_counts, columns=['Juego', 'Frecuencia'])
                    fig_adaptation = px.pie(
                        df_adaptation,
                        values='Frecuencia',
                        names='Juego',
                        title='Juegos Más Jugados',
                        hole=0.3,
                        template='plotly_white',
                    )
                    adaptation_frequency_data = json.loads(fig_adaptation.to_json())
            except Exception:
                pass

    return render_template(
        'therapist/analytics.html',
        ai_overview=ai_overview,
        model_performance=model_performance,
        recent_adaptations=recent_adaptations,
        difficulty_adaptation_data=difficulty_adaptation_data,
        patient_progress_data=patient_progress_data,
        adaptation_frequency_data=adaptation_frequency_data,
        active_page='analytics',
    )


@therapist_bp.route('/reports')
@login_required
def reports():
    _import_analytics_libs()
    if current_user.role != 'terapista':
        flash('Acceso denegado.', 'error')
        return redirect(url_for('main.dashboard'))

    start = request.args.get('start')
    end = request.args.get('end')
    start_dt = _parse_datetime(start) if start else None
    end_dt = _parse_datetime(end) if end else None

    my_patient_ids = [p.id for p in current_user.associated_patients]

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
    active_patients_change = 0

    monthly_progress_chart = {}
    sessions_per_day_chart = {}
    game_performance_chart = {}

    if my_patient_ids:
        avg_last_30 = (
            db.session.query(func.avg(SessionMetrics.accurracy))
            .filter(SessionMetrics.user_id.in_(my_patient_ids), SessionMetrics.date >= last_30)
            .scalar()
            or 0
        )
        avg_prev_30 = (
            db.session.query(func.avg(SessionMetrics.accurracy))
            .filter(
                SessionMetrics.user_id.in_(my_patient_ids),
                SessionMetrics.date >= prev_60,
                SessionMetrics.date < last_30,
            )
            .scalar()
            or 0
        )

        if avg_prev_30:
            improvement_rate = round(avg_last_30, 1)
            improvement_rate_change = round(((avg_last_30 - avg_prev_30) / avg_prev_30) * 100, 1)
        else:
            improvement_rate = round(avg_last_30, 1)

        avg_session_time = (
            db.session.query(func.avg(SessionMetrics.avg_time))
            .filter(SessionMetrics.user_id.in_(my_patient_ids))
            .scalar()
            or 0
        )

        completed_objectives = SessionMetrics.query.filter(
            SessionMetrics.user_id.in_(my_patient_ids), SessionMetrics.accurracy >= 80
        ).count()

        active_patients = len([p for p in current_user.associated_patients if p.is_active])

        if db.engine.dialect.name == 'sqlite':
            month_col = func.strftime('%Y-%m', SessionMetrics.date).label('Mes')
        else:
            month_col = func.date_format(SessionMetrics.date, '%Y-%m').label('Mes')

        q_monthly = db.session.query(month_col, func.avg(SessionMetrics.accurracy).label('Progreso')).filter(
            SessionMetrics.user_id.in_(my_patient_ids)
        )

        if start_dt:
            q_monthly = q_monthly.filter(SessionMetrics.date >= start_dt)
        if end_dt:
            q_monthly = q_monthly.filter(SessionMetrics.date <= end_dt)

        q_monthly = q_monthly.group_by(month_col)
        df_monthly = pd.read_sql(q_monthly.statement, db.engine)

        if df_monthly.empty:
            df_monthly = pd.DataFrame({'Mes': [], 'Progreso': []})

        fig_monthly = go.Figure()
        fig_monthly.add_trace(
            go.Scatter(
                x=df_monthly['Mes'],
                y=df_monthly['Progreso'],
                mode='lines',
                line=dict(color='#75a83a', width=3),
                fill='tozeroy',
                fillcolor='rgba(117, 168, 58, 0.1)',
            )
        )
        monthly_progress_chart = json.loads(fig_monthly.to_json())

        if db.engine.dialect.name == 'sqlite':
            weekday_col = func.strftime('%w', Appointment.start_time).label('weekday')
        else:
            weekday_col = (func.dayofweek(Appointment.start_time) - 1).label('weekday')

        q_sessions = (
            db.session.query(weekday_col, func.count(Appointment.id).label('count'))
            .filter(Appointment.therapist_id == current_user.id)
            .group_by(weekday_col)
        )
        if start_dt:
            q_sessions = q_sessions.filter(Appointment.start_time >= start_dt)
        if end_dt:
            q_sessions = q_sessions.filter(Appointment.start_time <= end_dt)
        df_sessions = pd.read_sql(q_sessions.statement, db.engine)

        if not df_sessions.empty:
            df_sessions['weekday'] = df_sessions['weekday'].astype(str).str.split('.').str[0]

        weekday_map = {'1': 'Lun', '2': 'Mar', '3': 'Mié', '4': 'Jue', '5': 'Vie', '6': 'Sáb', '0': 'Dom'}
        if not df_sessions.empty:
            df_sessions['Día'] = df_sessions['weekday'].map(weekday_map)
            df_sessions['Sesiones'] = df_sessions['count']
            fig_sessions = go.Figure()
            fig_sessions.add_trace(
                go.Bar(
                    x=df_sessions['Día'],
                    y=df_sessions['Sesiones'],
                    marker_color='#75a83a',
                    marker_line_width=0,
                    width=0.6,
                )
            )
            fig_sessions.update_traces(marker_cornerradius=8)
            sessions_per_day_chart = json.loads(fig_sessions.to_json())
        else:
            sessions_per_day_chart = {}

        q_games = db.session.query(
            SessionMetrics.game_name.label('Juego'), func.count(SessionMetrics.id).label('Rendimiento')
        ).filter(SessionMetrics.user_id.in_(my_patient_ids))

        if start_dt:
            q_games = q_games.filter(SessionMetrics.date >= start_dt)
        if end_dt:
            q_games = q_games.filter(SessionMetrics.date <= end_dt)

        q_games = q_games.group_by(SessionMetrics.game_name)
        df_games = pd.read_sql(q_games.statement, db.engine)

        if not df_games.empty:
            colors = ['#75a83a', '#3b82f6', '#8b5cf6', '#f59e0b']
            fig_games = go.Figure(
                data=[go.Pie(labels=df_games['Juego'], values=df_games['Rendimiento'], hole=0.4, marker_colors=colors)]
            )
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
        'active_patients_change': active_patients_change,
    }

    q_pred = db.session.query(SessionMetrics.prediction, func.count(SessionMetrics.id).label('cnt'))
    if my_patient_ids:
        q_pred = q_pred.filter(SessionMetrics.user_id.in_(my_patient_ids))

    if start_dt:
        q_pred = q_pred.filter(SessionMetrics.date >= start_dt)
    if end_dt:
        q_pred = q_pred.filter(SessionMetrics.date <= end_dt)
    q_pred = q_pred.group_by(SessionMetrics.prediction)
    df_pred = pd.read_sql(q_pred.statement, db.engine)

    difficulty_analysis = [
        {'name': 'Fácil', 'percentage': int(df_pred['cnt'].sum()) if not df_pred.empty else 0, 'color': 'bg-green-500'}
    ]

    q_insights = db.session.query(
        SessionMetrics.user_id.label('uid'), func.avg(SessionMetrics.accurracy).label('acc')
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
            patient_insights.append(
                {
                    'title': 'Mejor Rendimiento',
                    'description': f'{user.username} - Acc: {round(row["acc"], 1)}%',
                    'icon': 'fas fa-star',
                    'icon_color': 'text-olive',
                    'bg_color': 'bg-green-50',
                }
            )

    detailed_reports = []
    users = current_user.associated_patients.filter_by(role='jugador').all()

    for u in users:
        latest = SessionMetrics.query.filter_by(user_id=u.id).order_by(SessionMetrics.date.desc()).first()
        if latest:
            detailed_reports.append(
                {
                    'id': str(u.id),
                    'name': u.username,
                    'avatar': f'https://ui-avatars.com/api/?name={u.username.replace(" ", "+")}',
                    'last_session': latest.date.strftime('%d %b %Y %H:%M')
                    if hasattr(latest, 'date') and latest.date
                    else '',
                    'progress': int(round(latest.accurracy or 0)),
                    'total_time': f'{round(latest.avg_time or 0, 1)}s',
                    'status': 'Activo' if u.is_active else 'Pausado',
                }
            )

    return render_template(
        'therapist/reports.html',
        overview_stats=overview_stats,
        monthly_progress_chart=monthly_progress_chart,
        sessions_per_day_chart=sessions_per_day_chart,
        game_performance_chart=game_performance_chart,
        difficulty_analysis=difficulty_analysis,
        patient_insights=patient_insights,
        detailed_reports=detailed_reports,
        start=start or '',
        end=end or '',
        active_page='reports',
    )


@therapist_bp.route('/reports/export', methods=['GET'])
@login_required
def export_reports():
    if current_user.role not in ('terapista', 'admin', 'supervisor'):
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

    appts = (
        Appointment.query.filter(
            Appointment.therapist_id == current_user.id,
            Appointment.start_time >= start_dt,
            Appointment.start_time <= end_dt,
        )
        .order_by(Appointment.start_time.asc())
        .all()
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            'appointment_id',
            'patient_id',
            'patient_name',
            'start_time',
            'end_time',
            'status',
            'location',
            'notes',
            'games',
            'patient_total_sessions',
            'patient_avg_accuracy',
            'patient_avg_time',
            'patient_last_session',
        ]
    )

    for a in appts:
        pid = a.patient_id
        patient = a.patient
        total_sessions = SessionMetrics.query.filter(
            SessionMetrics.user_id == pid, SessionMetrics.date >= start_dt, SessionMetrics.date <= end_dt
        ).count()
        avg_acc = (
            db.session.query(func.avg(SessionMetrics.accurracy))
            .filter(SessionMetrics.user_id == pid, SessionMetrics.date >= start_dt, SessionMetrics.date <= end_dt)
            .scalar()
            or 0
        )
        avg_time = (
            db.session.query(func.avg(SessionMetrics.avg_time))
            .filter(SessionMetrics.user_id == pid, SessionMetrics.date >= start_dt, SessionMetrics.date <= end_dt)
            .scalar()
            or 0
        )
        last_session = db.session.query(func.max(SessionMetrics.date)).filter(SessionMetrics.user_id == pid).scalar()
        last_session_str = last_session.isoformat() if last_session else ''
        try:
            games_list = json.loads(a.games) if a.games else []
        except Exception:
            games_list = []

        writer.writerow(
            [
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
                f'{float(avg_acc):.2f}',
                f'{float(avg_time):.2f}',
                last_session_str,
            ]
        )

    csv_data = output.getvalue()
    output.close()

    filename = f'reports_{current_user.id}_{datetime.utcnow().strftime("%Y%m%d")}.csv'
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

    unread_expr = func.sum(case(((Message.is_read == False) & (Message.receiver_id == current_user.id), 1), else_=0))

    conversations_query = (
        db.session.query(
            User.id,
            User.username,
            User.email,
            func.max(Message.created_at).label('last_message'),
            unread_expr.label('unread_count'),
        )
        .join(
            Message,
            or_(
                (Message.sender_id == User.id) & (Message.receiver_id == current_user.id),
                (Message.receiver_id == User.id) & (Message.sender_id == current_user.id),
            ),
        )
        .filter(User.role == 'jugador')
        .group_by(User.id)
        .order_by(func.max(Message.created_at).desc())
        .all()
    )

    conversations = [
        {'user_id': c[0], 'username': c[1], 'email': c[2], 'last_message': c[3], 'unread_count': c[4]}
        for c in conversations_query
    ]

    return render_template('therapist/messages.html', conversations=conversations, active_page='messages')


@therapist_bp.route('/messages/<int:user_id>')
@login_required
def conversation(user_id):
    if current_user.role != 'terapista':
        flash('Acceso denegado', 'error')
        return redirect(url_for('main.dashboard'))

    other_user = User.query.get_or_404(user_id)

    messages = (
        Message.query.filter(
            or_(
                (Message.sender_id == current_user.id) & (Message.receiver_id == user_id),
                (Message.sender_id == user_id) & (Message.receiver_id == current_user.id),
            )
        )
        .order_by(Message.created_at.asc())
        .all()
    )

    Message.query.filter(
        Message.receiver_id == current_user.id, Message.sender_id == user_id, Message.is_read == False
    ).update({'is_read': True})
    db.session.commit()

    return render_template(
        'therapist/conversation.html', other_user=other_user, messages=messages, active_page='messages'
    )


@therapist_bp.route('/profile')
@login_required
def profile():
    if current_user.role != 'terapista':
        return redirect(url_for('main.dashboard'))

    patients_count = User.query.filter_by(assigned_therapist_id=current_user.id, role='jugador', is_active=True).count()
    sessions_count = Appointment.query.filter_by(therapist_id=current_user.id).count()
    upcoming_appointments = Appointment.query.filter(
        Appointment.therapist_id == current_user.id,
        Appointment.status == 'scheduled',
        Appointment.start_time >= datetime.utcnow(),
    ).count()

    return render_template(
        'therapist/profile.html',
        active_page='profile',
        patients_count=patients_count,
        sessions_count=sessions_count,
        upcoming_appointments=upcoming_appointments,
    )


@therapist_bp.route('/patients/add', methods=['POST'])
@login_required
def add_patient():
    if current_user.role != 'terapista':
        return jsonify({'success': False, 'message': 'Acceso denegado'}), 403

    email = request.form.get('email', '').strip().lower()
    username = request.form.get('username', '').strip()

    import uuid

    is_full_account = False
    password = None
    if not email:
        if not username:
            flash('Tienes que poner el nombre del paciente si no hay email.', 'error')
            return redirect(url_for('therapist.patients'))
        email = f'noemail_{uuid.uuid4().hex[:8]}@local'
        password = uuid.uuid4().hex
        is_full_account = False
    else:
        try:
            valid = validate_email(email)
            email = valid.email
        except EmailNotValidError:
            flash('Ese correo no es válido, revisa.', 'error')
            return redirect(url_for('therapist.patients'))
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Ese correo ya está registrado.', 'error')
            return redirect(url_for('therapist.patients'))
        password = EmailService.generate_password()
        is_full_account = True
    hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
    new_patient = User(
        username=username or email.split('@')[0],
        email=email,
        password=hashed_pw,
        role='jugador',
        is_active=is_full_account,
        assigned_therapist_id=current_user.id,
    )
    new_patient.therapists.append(current_user)
    db.session.add(new_patient)
    db.session.commit()
    if is_full_account:
        notification_service.create_notification(
            user_id=current_user.id,
            message=f'Paciente {new_patient.username} agregado. Email: {email} | Contraseña: {password}',
            link=url_for('therapist.patients'),
        )
        email_sent = EmailService.send_welcome_email(email, password, new_patient.username)
        if email_sent:
            flash(
                f'Paciente {new_patient.username} agregado.<br>'
                f'Email: <strong>{email}</strong><br>'
                f'Contraseña: <strong>{password}</strong><br>'
                f'<small>El paciente recibe las credenciales por correo.</small>',
                'success',
            )
        else:
            flash(
                f'Paciente {new_patient.username} agregado.<br>'
                f'No se pudo enviar el correo.<br>'
                f'Email: <strong>{email}</strong><br>'
                f'Contraseña: <strong>{password}</strong><br>'
                f'<small>Comparte estas credenciales con el paciente.</small>',
                'warning',
            )
    else:
        flash(
            f'Paciente {new_patient.username} creado (presencial/sin email).<br>'
            f'<small>Registro creado para gestionar terapias y pagos.</small><br>'
            f'<small>La cuenta no tiene acceso al sistema. Para activarla, edita el perfil y añade un email.</small>',
            'success',
        )

    return redirect(url_for('therapist.patients'))


@therapist_bp.route('/patients/toggle/<int:patient_id>', methods=['POST'])
@login_required
def toggle_patient_status(patient_id):
    if current_user.role != 'terapista':
        return jsonify({'success': False, 'message': 'Acceso denegado'}), 403

    patient = User.query.get_or_404(patient_id)
    patient.is_active = not patient.is_active
    db.session.commit()

    status_message = 'activado' if patient.is_active else 'desactivado'
    notification_service.create_notification(
        user_id=current_user.id,
        message=f'El paciente {patient.username} ha sido {status_message}.',
        link=url_for('therapist.patients'),
    )

    return jsonify({'success': True, 'is_active': patient.is_active})


@therapist_bp.route('/patients/delete/<int:patient_id>', methods=['POST'])
@login_required
def delete_patient(patient_id):
    if current_user.role != 'terapista':
        return jsonify({'success': False, 'message': 'Acceso denegado'}), 403

    patient = User.query.get_or_404(patient_id)

    if patient.role == 'terapista':
        return jsonify({'success': False, 'message': 'No se puede eliminar un terapeuta'}), 403

    patient_username = patient.username

    try:
        SessionMetrics.query.filter_by(user_id=patient_id).delete()
        Appointment.query.filter_by(patient_id=patient_id).delete()
        db.session.delete(patient)

        notification_service.create_notification(
            user_id=current_user.id, message=f'El paciente {patient_username} ha sido eliminado permanentemente.'
        )

        db.session.commit()
        flash('Paciente eliminado, listo.', 'success')
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
    if current_user.role not in ['terapista', 'admin', 'supervisor']:
        flash('Acceso denegado.', 'error')
        return redirect(url_for('main.dashboard'))

    patient = User.query.get_or_404(patient_id)
    if patient.role != 'jugador':
        flash('Usuario no es un paciente.', 'error')
        return redirect(url_for('therapist.patients'))

    total_sessions = SessionMetrics.query.filter_by(user_id=patient_id).count()
    avg_accuracy = db.session.query(func.avg(SessionMetrics.accurracy)).filter_by(user_id=patient_id).scalar() or 0
    avg_time = db.session.query(func.avg(SessionMetrics.avg_time)).filter_by(user_id=patient_id).scalar() or 0

    recent_sessions = (
        SessionMetrics.query.filter_by(user_id=patient_id).order_by(SessionMetrics.date.desc()).limit(10).all()
    )

    history_appointments = (
        Appointment.query.filter(Appointment.patient_id == patient_id).order_by(Appointment.start_time.desc()).all()
    )

    all_sessions_query = SessionMetrics.query.filter_by(user_id=patient_id).order_by(SessionMetrics.date.asc()).all()
    all_sessions = []
    for s in all_sessions_query:
        all_sessions.append({'date': s.date.isoformat(), 'accurracy': s.accurracy, 'avg_time': s.avg_time})

    upcoming_appointments = (
        Appointment.query.filter(
            Appointment.patient_id == patient_id,
            Appointment.start_time >= datetime.utcnow(),
            Appointment.status == 'scheduled',
        )
        .order_by(Appointment.start_time)
        .limit(5)
        .all()
    )

    completed_appointments = Appointment.query.filter(
        Appointment.patient_id == patient_id, Appointment.status == 'completed'
    ).count()

    return render_template(
        'therapist/patient_detail.html',
        patient=patient,
        total_sessions=total_sessions,
        avg_accuracy=round(avg_accuracy, 1),
        avg_time=round(avg_time, 2),
        recent_sessions=recent_sessions,
        history_appointments=history_appointments,
        all_sessions=all_sessions,
        upcoming_appointments=upcoming_appointments,
        completed_appointments=completed_appointments,
        active_page='patients',
    )


@therapist_bp.route('/patients/<int:patient_id>/update', methods=['POST'])
@login_required
def update_patient(patient_id):
    if current_user.role not in ['terapista', 'admin', 'supervisor']:
        return jsonify({'success': False, 'message': 'Acceso denegado'}), 403

    patient = User.query.get_or_404(patient_id)
    if patient.role != 'jugador':
        return jsonify({'success': False, 'message': 'Usuario no es un paciente'}), 403

    data = request.json

    from app.utils.sanitizer import sanitize_text

    if 'phone' in data:
        patient.phone = sanitize_text(data['phone'], 20)
    if 'date_of_birth' in data and data['date_of_birth']:
        try:
            patient.date_of_birth = datetime.strptime(data['date_of_birth'], '%Y-%m-%d').date()
        except:
            pass
    if 'guardian_name' in data:
        patient.guardian_name = sanitize_text(data['guardian_name'], 200)
    if 'guardian_contact' in data:
        patient.guardian_contact = sanitize_text(data['guardian_contact'], 200)
    if 'therapy_goals' in data:
        patient.therapy_goals = sanitize_text(data['therapy_goals'], 2000)
    if 'notes' in data:
        patient.notes = sanitize_text(data['notes'], 2000)

    if 'email' in data and data['email']:
        new_email = data['email'].strip().lower()
        if new_email != patient.email and new_email:
            exists = User.query.filter_by(email=new_email).first()
            if exists:
                return jsonify({'success': False, 'message': 'El correo ya está registrado por otro usuario'}), 400

            was_placeholder = patient.email.startswith('noemail_') or patient.email.startswith('temp_')

            patient.email = new_email

            if was_placeholder:
                password = EmailService.generate_password()
                patient.password = bcrypt.generate_password_hash(password).decode('utf-8')
                patient.is_active = True
                try:
                    EmailService.send_welcome_email(new_email, password, patient.username)
                    db.session.commit()
                    return jsonify(
                        {
                            'success': True,
                            'message': 'Cuenta activada. Credenciales enviadas por correo.',
                            'new_credentials': {'email': new_email, 'password': password},
                        }
                    )
                except Exception:
                    pass

    db.session.commit()

    return jsonify({'success': True, 'message': 'Paciente actualizado, listo'})


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
        Appointment.status == 'scheduled',
    ).count()

    completed_sessions = Appointment.query.filter(
        Appointment.therapist_id == current_user.id, Appointment.status == 'completed'
    ).count()

    pending_sessions = Appointment.query.filter(
        Appointment.therapist_id == current_user.id, Appointment.status == 'scheduled', Appointment.start_time > now
    ).count()

    active_patients = User.query.filter(
        User.assigned_therapist_id == current_user.id, User.role == 'jugador', User.is_active == True
    ).count()

    return jsonify(
        {
            'sessions_today': sessions_today,
            'completed_sessions': completed_sessions,
            'pending_sessions': pending_sessions,
            'active_patients': active_patients,
        }
    )


@therapist_bp.route('/api/conversations')
@login_required
def api_conversations():
    if current_user.role != 'terapista':
        return jsonify({'error': 'Acceso denegado'}), 403
    try:
        unread_expr = func.sum(
            case(((Message.is_read == False) & (Message.receiver_id == current_user.id), 1), else_=0)
        )

        conv_query = (
            db.session.query(
                User.id,
                User.username,
                User.email,
                func.max(Message.created_at).label('last_message'),
                unread_expr.label('unread_count'),
            )
            .join(
                Message,
                or_(
                    (Message.sender_id == User.id) & (Message.receiver_id == current_user.id),
                    (Message.receiver_id == User.id) & (Message.sender_id == current_user.id),
                ),
            )
            .group_by(User.id)
            .order_by(func.max(Message.created_at).desc())
            .all()
        )

        conversations = [
            {
                'user_id': c[0],
                'username': c[1],
                'email': c[2],
                'last_message': c[3].isoformat() if c[3] else None,
                'unread_count': c[4] or 0,
            }
            for c in conv_query
        ]

        return jsonify({'conversations': conversations})
    except Exception as e:
        current_app.logger.error(f'Error in therapist conversations: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'error': 'Error al cargar conversaciones'}), 500


@therapist_bp.route('/api/messages/<int:user_id>')
@login_required
def api_conversation_thread(user_id):
    if current_user.role != 'terapista':
        return jsonify({'error': 'Acceso denegado'}), 403
    try:
        other_user = User.query.get_or_404(user_id)

        messages = (
            Message.query.filter(
                or_(
                    (Message.sender_id == current_user.id) & (Message.receiver_id == user_id),
                    (Message.sender_id == user_id) & (Message.receiver_id == current_user.id),
                )
            )
            .order_by(Message.created_at.asc())
            .all()
        )

        Message.query.filter(
            Message.receiver_id == current_user.id, Message.sender_id == user_id, Message.is_read == False
        ).update({'is_read': True})
        db.session.commit()

        return jsonify(
            {
                'other_user': {
                    'id': other_user.id,
                    'username': other_user.username,
                    'email': other_user.email,
                },
                'messages': [
                    {
                        'id': m.id,
                        'sender_id': m.sender_id,
                        'receiver_id': m.receiver_id,
                        'body': m.body,
                        'file_url': m.file_url,
                        'file_type': m.attachment_type,
                        'created_at': m.created_at.isoformat() if m.created_at else None,
                        'is_read': m.is_read,
                    }
                    for m in messages
                ],
            }
        )
    except Exception as e:
        current_app.logger.error(f'Error in therapist messages for user {user_id}: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'error': 'Error al cargar mensajes'}), 500


@therapist_bp.route('/api/profile')
@login_required
def api_profile():
    if current_user.role != 'terapista':
        return jsonify({'error': 'Acceso denegado'}), 403

    patients_count = User.query.filter_by(assigned_therapist_id=current_user.id, role='jugador', is_active=True).count()

    sessions_count = Appointment.query.filter_by(therapist_id=current_user.id).count()

    upcoming_appointments = Appointment.query.filter(
        Appointment.therapist_id == current_user.id,
        Appointment.status == 'scheduled',
        Appointment.start_time >= datetime.utcnow(),
    ).count()

    return jsonify(
        {
            'id': current_user.id,
            'username': current_user.username,
            'email': current_user.email,
            'timezone': getattr(current_user, 'timezone', 'America/Lima'),
            'created_at': current_user.created_at.isoformat()
            if hasattr(current_user, 'created_at') and current_user.created_at
            else None,
            'patients_count': patients_count,
            'sessions_count': sessions_count,
            'upcoming_appointments': upcoming_appointments,
        }
    )


@therapist_bp.route('/api/profile', methods=['PUT'])
@csrf.exempt
@login_required
def api_update_profile():
    if current_user.role != 'terapista':
        return jsonify({'error': 'Acceso denegado'}), 403

    data = request.get_json(silent=True) or {}

    allowed_tz = {
        'America/Lima',
        'America/New_York',
        'America/Mexico_City',
        'America/Bogota',
        'America/Argentina/Buenos_Aires',
        'America/Santiago',
        'Europe/Madrid',
    }
    timezone = (data.get('timezone') or '').strip()
    if timezone and timezone not in allowed_tz:
        return jsonify({'success': False, 'message': 'Zona horaria inválida'}), 400

    if 'username' in data and data['username']:
        current_user.username = data['username'].strip()
    if timezone:
        current_user.timezone = timezone

    if 'new_password' in data and data['new_password']:
        current_user.password = bcrypt.generate_password_hash(data['new_password']).decode('utf-8')

    db.session.commit()

    return jsonify(
        {
            'success': True,
            'message': 'Perfil actualizado correctamente',
            'timezone': getattr(current_user, 'timezone', None) or 'America/Lima',
        }
    )


@therapist_bp.route('/api/weekly-reports/pending', methods=['GET'])
@login_required
def api_weekly_reports_pending():
    try:
        therapist_id = current_user.id
        if current_user.role == 'terapista':
            pass
        elif current_user.role in ('admin', 'supervisor'):
            therapist_id = request.args.get('therapist_id', type=int) or therapist_id
        else:
            return jsonify({'error': 'Acceso denegado'}), 403

        from sqlalchemy import inspect as sa_inspect

        from app.extensions import db
        from app.models import Notification, WeeklyReport

        inspector = sa_inspect(db.engine)
        if 'weekly_report' not in inspector.get_table_names():
            db.create_all()
            current_app.logger.info('Auto-migration: created tables on-demand')

        today = datetime.utcnow().date()
        monday = today - timedelta(days=today.weekday())
        week_end = monday + timedelta(days=6)

        week_start_dt = datetime(monday.year, monday.month, monday.day)
        week_end_dt = datetime(week_end.year, week_end.month, week_end.day) + timedelta(days=1)

        from app.models import Appointment

        patients_with_sessions = {
            row[0]
            for row in db.session.query(Appointment.patient_id)
            .filter(
                Appointment.therapist_id == therapist_id,
                Appointment.status == 'completed',
                Appointment.start_time >= week_start_dt,
                Appointment.start_time < week_end_dt,
                Appointment.patient_id.isnot(None),
            )
            .distinct()
            .all()
        }

        patients_with_reports = {
            row[0]
            for row in db.session.query(WeeklyReport.patient_id)
            .filter(WeeklyReport.therapist_id == therapist_id, WeeklyReport.week_start == monday)
            .distinct()
            .all()
        }

        missing_weekly = patients_with_sessions - patients_with_reports
        reports = len(missing_weekly)
        notification = (
            Notification.query.filter(
                Notification.user_id == current_user.id, Notification.type == 'reportes', Notification.is_read == False
            )
            .order_by(Notification.timestamp.desc())
            .first()
        )
        return jsonify(
            {
                'success': True,
                'has_pending': reports > 0,
                'reports_count': reports,
                'has_notification': notification is not None,
                'week_start': monday.isoformat(),
                'week_end': week_end.isoformat(),
                'label': 'Pacientes con sesiones esta semana sin reporte semanal',
            }
        )
    except Exception as e:
        current_app.logger.error(f'Error in weekly-reports/pending: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'error': 'Error al consultar reportes'}), 500


@therapist_bp.route('/efficiency', methods=['GET'])
@login_required
def therapist_efficiency():
    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'success': False, 'error': 'Acceso denegado'}), 403
    try:
        therapist_id = request.args.get('therapist_id', type=int)
        from app.services.dashboard_service import DashboardService

        ds = DashboardService()
        therapists = (
            [User.query.get(therapist_id)]
            if therapist_id
            else User.query.filter_by(role='terapista', is_active=True).all()
        )
        breakdown = []
        for t in therapists:
            if not t:
                continue
            eff = ds.get_therapist_efficiency(t.id)
            breakdown.append(
                {
                    'therapist_id': t.id,
                    'therapist_name': t.username,
                    'audit_score': eff.get('avg_audit_score', 0),
                    'feedback_score': eff.get('avg_feedback_score', 0),
                    'efficiency': eff.get('efficiency', 0),
                }
            )
        return jsonify({'success': True, 'breakdown': breakdown})
    except Exception as e:
        current_app.logger.error(f'Error in therapist/efficiency: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'error': 'Error al obtener eficiencia'}), 500


@therapist_bp.route('/api/analytics')
@login_required
def api_analytics():
    if current_user.role != 'terapista':
        return jsonify({'success': False, 'error': 'Acceso denegado'}), 403

    my_patient_ids = [p.id for p in current_user.associated_patients]

    kpi = {
        'adaptations_count': 0,
        'avg_accuracy': 0,
        'success_rate': 0,
        'active_models': 1,
    }
    difficulty_matrix = []
    prediction_distribution = []
    model_confidence = []
    recent_adaptations = []

    if my_patient_ids:
        total_metrics = SessionMetrics.query.filter(SessionMetrics.user_id.in_(my_patient_ids)).count()
        avg_acc = (
            db.session.query(func.avg(SessionMetrics.accurracy))
            .filter(SessionMetrics.user_id.in_(my_patient_ids))
            .scalar()
            or 0
        )
        total_predictions = SessionMetrics.query.filter(
            SessionMetrics.user_id.in_(my_patient_ids), SessionMetrics.prediction.isnot(None)
        ).count()
        advance = SessionMetrics.query.filter(
            SessionMetrics.user_id.in_(my_patient_ids), SessionMetrics.prediction == 1
        ).count()
        success_rate = (advance / total_predictions * 100) if total_predictions > 0 else 0

        kpi = {
            'adaptations_count': total_metrics,
            'avg_accuracy': round(avg_acc, 1),
            'success_rate': round(success_rate, 1),
            'active_models': 1,
        }

        games = (
            db.session.query(SessionMetrics.game_name)
            .filter(SessionMetrics.user_id.in_(my_patient_ids))
            .distinct()
            .all()
        )
        dm = []
        for (game,) in games:
            levels_q = (
                db.session.query(
                    SessionMetrics.prediction, func.avg(SessionMetrics.accurracy), func.count(SessionMetrics.id)
                )
                .filter(SessionMetrics.user_id.in_(my_patient_ids), SessionMetrics.game_name == game)
                .group_by(SessionMetrics.prediction)
                .all()
            )
            levels = []
            label_map = {0: 'Mantener', 1: 'Avanzar', 2: 'Apoyo'}
            for pred, acc, cnt in levels_q:
                if pred is not None:
                    levels.append(
                        {'level': label_map.get(pred, str(pred)), 'accuracy': round(float(acc), 1), 'count': cnt}
                    )
            dm.append({'game': game, 'levels': levels})
        difficulty_matrix = dm

        dist = (
            db.session.query(SessionMetrics.prediction, func.count(SessionMetrics.id))
            .filter(SessionMetrics.user_id.in_(my_patient_ids), SessionMetrics.prediction.isnot(None))
            .group_by(SessionMetrics.prediction)
            .all()
        )
        dist_map = {0: 'Mantener', 1: 'Avanzar', 2: 'Apoyo'}
        prediction_distribution = [{'label': dist_map.get(p, str(p)), 'value': c} for p, c in dist]

        model_confidence = [
            {'model': 'SVM', 'confidence': 88},
            {'model': 'Random Forest', 'confidence': 76},
        ]

        recent = (
            db.session.query(SessionMetrics, User)
            .join(User, SessionMetrics.user_id == User.id)
            .filter(SessionMetrics.user_id.in_(my_patient_ids))
            .order_by(SessionMetrics.date.desc())
            .limit(10)
            .all()
        )
        impact_map = {0: 'neutral', 1: 'positive', 2: 'negative'}
        for m, u in recent:
            recent_adaptations.append(
                {
                    'date': m.date.isoformat() if m.date else '',
                    'description': f'{u.username}: {m.game_name} → {"Avanzar" if m.prediction == 1 else "Mantener" if m.prediction == 0 else "Apoyo"}',
                    'impact': impact_map.get(m.prediction, 'neutral'),
                }
            )

    return jsonify(
        {
            'success': True,
            'data': {
                'kpi': kpi,
                'difficulty_matrix': difficulty_matrix,
                'prediction_distribution': prediction_distribution,
                'model_confidence': model_confidence,
                'recent_adaptations': recent_adaptations,
            },
        }
    )


@therapist_bp.route('/api/reports/overview')
@login_required
def api_reports_overview():
    if current_user.role != 'terapista':
        return jsonify({'success': False, 'error': 'Acceso denegado'}), 403

    my_patient_ids = [p.id for p in current_user.associated_patients]
    now = datetime.utcnow()
    last_30 = now - timedelta(days=30)

    improvement_rate = 0
    avg_session_time = 0
    completed_objectives = 0
    active_patients = 0

    if my_patient_ids:
        avg_acc = (
            db.session.query(func.avg(SessionMetrics.accurracy))
            .filter(SessionMetrics.user_id.in_(my_patient_ids), SessionMetrics.date >= last_30)
            .scalar()
            or 0
        )
        improvement_rate = round(avg_acc, 1)
        avg_session_time = round(
            db.session.query(func.avg(SessionMetrics.avg_time))
            .filter(SessionMetrics.user_id.in_(my_patient_ids))
            .scalar()
            or 0,
            1,
        )
        completed_objectives = SessionMetrics.query.filter(
            SessionMetrics.user_id.in_(my_patient_ids), SessionMetrics.accurracy >= 80
        ).count()
        active_patients = len([p for p in current_user.associated_patients if p.is_active])

    return jsonify(
        {
            'success': True,
            'data': {
                'improvement_rate': improvement_rate,
                'avg_session_time_minutes': avg_session_time,
                'completed_objectives': completed_objectives,
                'active_patients': active_patients,
            },
        }
    )


@therapist_bp.route('/api/reports/detailed')
@login_required
def api_reports_detailed():
    if current_user.role != 'terapista':
        return jsonify({'success': False, 'error': 'Acceso denegado'}), 403

    start = request.args.get('start')
    end = request.args.get('end')
    start_dt = _parse_datetime(start) if start else None
    end_dt = _parse_datetime(end) if end else None

    my_patient_ids = [p.id for p in current_user.associated_patients]
    reports = []

    for uid in my_patient_ids:
        user = User.query.get(uid)
        if not user:
            continue
        q = SessionMetrics.query.filter(SessionMetrics.user_id == uid)
        if start_dt:
            q = q.filter(SessionMetrics.date >= start_dt)
        if end_dt:
            q = q.filter(SessionMetrics.date <= end_dt)
        all_m = q.all()
        sessions_count = len(all_m)
        avg_acc = sum(m.accurracy for m in all_m if m.accurracy) / sessions_count if sessions_count else 0
        total_plays = sum(m.avg_time or 0 for m in all_m)

        reports.append(
            {
                'patient_id': uid,
                'patient_name': user.username,
                'sessions_count': sessions_count,
                'avg_accuracy': round(avg_acc, 1),
                'total_plays': round(total_plays, 1),
            }
        )

    return jsonify({'success': True, 'data': reports})


@therapist_bp.route('/api/appointments/<int:year>/<int:month>')
@login_required
def api_appointments_month(year, month):
    if current_user.role != 'terapista':
        return jsonify({'success': False, 'error': 'Acceso denegado'}), 403

    start_dt = datetime(year, month, 1)
    if month == 12:
        end_dt = datetime(year + 1, 1, 1)
    else:
        end_dt = datetime(year, month + 1, 1)

    appts = (
        Appointment.query.filter(
            Appointment.therapist_id == current_user.id,
            Appointment.start_time >= start_dt,
            Appointment.start_time < end_dt,
        )
        .order_by(Appointment.start_time)
        .all()
    )

    tz_name = get_user_timezone(current_user)

    return jsonify(
        {
            'success': True,
            'data': [
                {
                    'id': a.id,
                    'title': a.title or (a.patient.username if a.patient else 'Sesión'),
                    'start': (
                        localize_datetime_for_display(a.start_time, tz_name).isoformat() if a.start_time else None
                    ),
                    'end': (localize_datetime_for_display(a.end_time, tz_name).isoformat() if a.end_time else None),
                    'status': a.status,
                    'attendance': a.attendance,
                    'patient': {'id': a.patient.id, 'name': a.patient.username} if a.patient else None,
                    'location': a.location,
                    'notes': a.notes,
                }
                for a in appts
            ],
        }
    )


@therapist_bp.route('/api/patient-stats')
@login_required
def api_patient_stats():
    if current_user.role != 'terapista':
        return jsonify({'success': False, 'error': 'Acceso denegado'}), 403

    my_patient_ids = [p.id for p in current_user.associated_patients]
    stats = []

    for uid in my_patient_ids:
        user = User.query.get(uid)
        if not user:
            continue
        total = SessionMetrics.query.filter_by(user_id=uid).count()
        completed = Appointment.query.filter_by(patient_id=uid, status='completed').count()
        avg_acc = db.session.query(func.avg(SessionMetrics.accurracy)).filter_by(user_id=uid).scalar() or 0

        improvement = 0
        if total >= 4:
            half = total // 2
            all_m = SessionMetrics.query.filter_by(user_id=uid).order_by(SessionMetrics.date).all()
            first_half = sum(m.accurracy for m in all_m[:half] if m.accurracy) / half
            second_half = sum(m.accurracy for m in all_m[half:] if m.accurracy) / (total - half)
            improvement = round(second_half - first_half, 1)

        stats.append(
            {
                'patient_id': uid,
                'patient_name': user.username,
                'total_sessions': total,
                'completed_sessions': completed,
                'avg_accuracy': round(float(avg_acc), 1),
                'improvement': improvement,
            }
        )

    return jsonify({'success': True, 'data': stats})


@therapist_bp.route('/api/reports/generate-weekly', methods=['POST'])
@login_required
def therapist_generate_weekly():
    if current_user.role != 'terapista':
        return jsonify({'success': False, 'error': 'Acceso denegado'}), 403
    from app.services.report_service import ReportService

    rs = ReportService()
    week_start, _ = rs.get_this_week_range()
    therapist_id = current_user.id
    patients = current_user.associated_patients.filter_by(role='jugador').all()
    generated = []
    for patient in patients:
        try:
            r = rs.generate_patient_weekly_report(patient.id, therapist_id, week_start)
            generated.append(r)
        except Exception as e:
            current_app.logger.warning(f'Weekly report error {patient.id}: {e}')
    return jsonify(
        {'success': True, 'message': f'{len(generated)} reportes semanales generados', 'count': len(generated)}
    )


@therapist_bp.route('/api/reports/generate-monthly', methods=['POST'])
@login_required
def therapist_generate_monthly():
    if current_user.role != 'terapista':
        return jsonify({'success': False, 'error': 'Acceso denegado'}), 403
    from app.services.report_service import ReportService

    rs = ReportService()
    today = datetime.utcnow()
    year = today.year
    month = today.month
    therapist_id = current_user.id
    patients = current_user.associated_patients.filter_by(role='jugador').all()
    generated = []
    for patient in patients:
        try:
            r = rs.generate_monthly_report(patient.id, therapist_id, year, month)
            generated.append(r)
        except Exception as e:
            current_app.logger.warning(f'Monthly report error {patient.id}: {e}')
    return jsonify(
        {'success': True, 'message': f'{len(generated)} reportes mensuales generados', 'count': len(generated)}
    )


@therapist_bp.route('/api/reports/generate-quarterly', methods=['POST'])
@login_required
def therapist_generate_quarterly():
    if current_user.role != 'terapista':
        return jsonify({'success': False, 'error': 'Acceso denegado'}), 403
    from app.services.report_service import ReportService

    rs = ReportService()
    today = datetime.utcnow()
    year = today.year
    quarter = (today.month - 1) // 3 + 1
    therapist_id = current_user.id
    patients = current_user.associated_patients.filter_by(role='jugador').all()
    generated = []
    for patient in patients:
        try:
            r = rs.generate_quarterly_report(patient.id, therapist_id, year, quarter)
            generated.append(r)
        except Exception as e:
            current_app.logger.warning(f'Quarterly report error {patient.id}: {e}')
    return jsonify(
        {'success': True, 'message': f'{len(generated)} reportes trimestrales generados', 'count': len(generated)}
    )


@therapist_bp.route('/api/reports/structured/<int:patient_id>')
@login_required
def api_structured_reports(patient_id):
    if current_user.role != 'terapista':
        return jsonify({'success': False, 'error': 'Acceso denegado'}), 403
    patient = User.query.get(patient_id)
    if not patient or patient not in current_user.associated_patients:
        return jsonify({'success': False, 'error': 'Paciente no encontrado'}), 404

    weekly = (
        WeeklyReport.query.filter(WeeklyReport.patient_id == patient_id, WeeklyReport.therapist_id == current_user.id)
        .order_by(WeeklyReport.week_start.desc())
        .limit(12)
        .all()
    )

    monthly = (
        MonthlyReport.query.filter(
            MonthlyReport.patient_id == patient_id, MonthlyReport.therapist_id == current_user.id
        )
        .order_by(MonthlyReport.year.desc(), MonthlyReport.month.desc())
        .limit(12)
        .all()
    )

    quarterly = (
        QuarterlyReport.query.filter(
            QuarterlyReport.patient_id == patient_id, QuarterlyReport.therapist_id == current_user.id
        )
        .order_by(QuarterlyReport.year.desc(), QuarterlyReport.quarter.desc())
        .limit(12)
        .all()
    )

    return jsonify(
        {
            'success': True,
            'patient': {'id': patient.id, 'name': patient.username},
            'weekly': [
                {
                    'id': r.id,
                    'week_start': r.week_start.isoformat() if r.week_start else None,
                    'week_end': r.week_end.isoformat() if r.week_end else None,
                    'report_text': r.report_text[:2000] if r.report_text else None,
                    'objectives_met': r.objectives_met,
                    'total_objectives': r.total_objectives,
                }
                for r in weekly
            ],
            'monthly': [
                {
                    'id': r.id,
                    'month': r.month,
                    'year': r.year,
                    'report_text': r.report_text[:2000] if r.report_text else None,
                    'objectives_met': r.objectives_met,
                    'total_objectives': r.total_objectives,
                }
                for r in monthly
            ],
            'quarterly': [
                {
                    'id': r.id,
                    'quarter': r.quarter,
                    'year': r.year,
                    'report_text': r.report_text[:2000] if r.report_text else None,
                    'objectives_met': r.objectives_met,
                    'total_objectives': r.total_objectives,
                }
                for r in quarterly
            ],
        }
    )
