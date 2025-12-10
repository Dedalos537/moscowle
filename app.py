from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from flask_mail import Mail, Message as MailMessage
from authlib.integrations.flask_client import OAuth
from models import SessionMetrics, db, User, Notification, Appointment, Message
from ai_service import predict_level, get_cluster, train_model
from datetime import datetime, timedelta
from sqlalchemy import func, or_
from email_validator import validate_email, EmailNotValidError
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import json
import random
import os
import secrets
import string
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'moscowle_secret')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI', 'sqlite:///moscowle.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Email configuration
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True') == 'True'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')

# Initialize extensions
db.init_app(app)
bcrypt = Bcrypt(app)
mail = Mail(app)
oauth = OAuth(app)

# Configure OAuth providers
google = oauth.register(
    name='google',
    client_id=os.getenv('GOOGLE_CLIENT_ID'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

microsoft = oauth.register(
    name='microsoft',
    client_id=os.getenv('MICROSOFT_CLIENT_ID'),
    client_secret=os.getenv('MICROSOFT_CLIENT_SECRET'),
    server_metadata_url='https://login.microsoftonline.com/common/v2.0/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def generate_password(length=12):
    """Generate a secure random password"""
    alphabet = string.ascii_letters + string.digits + string.punctuation
    password = ''.join(secrets.choice(alphabet) for i in range(length))
    return password

def send_welcome_email(recipient_email: str, plain_password: str, username: str):
    """Send a welcome email with credentials. Falls back gracefully if mail is not configured."""
    # Check if mail is properly configured
    if not app.config.get('MAIL_USERNAME') or not app.config.get('MAIL_PASSWORD'):
        app.logger.warning("Email not configured. Skipping welcome email.")
        return False
    
    try:
        subject = "Bienvenido a Moscowle"
        body = (
            f"Hola {username},\n\n"
            f"Tu cuenta ha sido creada exitosamente en Moscowle.\n\n"
            f"Tus credenciales de acceso son:\n"
            f"Correo: {recipient_email}\n"
            f"Contraseña temporal: {plain_password}\n\n"
            f"Por favor inicia sesión en el sistema y cambia tu contraseña temporal por una más segura.\n\n"
            "Saludos,\nEquipo Moscowle"
        )
        msg = MailMessage(subject=subject, recipients=[recipient_email], body=body)
        mail.send(msg)
        app.logger.info(f"Welcome email sent successfully to {recipient_email}")
        return True
    except Exception as e:
        app.logger.error(f"Failed to send welcome email to {recipient_email}: {str(e)}")
        return False
# Initialize database and admin user
with app.app_context():
    if not os.path.exists('ai_models'): 
        os.mkdir('ai_models')
    db.create_all()
    train_model()
    
    # Create admin user (therapist)
    admin_email = os.getenv('ADMIN_EMAIL')
    admin_password = os.getenv('ADMIN_PASSWORD')
    
    admin = User.query.filter_by(email=admin_email).first()
    if not admin:
        hashed_pw = bcrypt.generate_password_hash(admin_password).decode('utf-8')
        admin = User(
            username='Administrador',
            email=admin_email,
            password=hashed_pw,
            role='terapista',
            is_active=True
        )
        db.session.add(admin)
        db.session.commit()
        print(f"Admin user created: {admin_email}")

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        
        # Validate email format
        try:
            valid = validate_email(email)
            email = valid.email
        except EmailNotValidError as e:
            flash('Por favor, ingresa un correo electrónico válido.', 'error')
            return render_template('login.html')
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.is_active and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Credenciales inválidas o cuenta desactivada.', 'error')
            return render_template('login.html')
    
    return render_template('login.html')

@app.route('/login/google')
def login_google():
    if not os.getenv('GOOGLE_CLIENT_ID') or os.getenv('GOOGLE_CLIENT_ID') == 'your_google_client_id_here':
        flash('Error: Google Login no configurado. Revisa el archivo .env', 'error')
        return redirect(url_for('login'))
    redirect_uri = url_for('authorize_google', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/authorize/google')
def authorize_google():
    try:
        token = google.authorize_access_token()
        user_info = token.get('userinfo')
        
        if user_info:
            email = user_info.get('email')
            name = user_info.get('name', email.split('@')[0])
            oauth_id = user_info.get('sub')
            
            # Check if user exists
            user = User.query.filter_by(email=email).first()
            
            if user:
                if user.oauth_provider != 'google':
                    user.oauth_provider = 'google'
                    user.oauth_id = oauth_id
                    db.session.commit()
                login_user(user)
                return redirect(url_for('dashboard'))
            else:
                flash('Tu cuenta no está registrada. Por favor, contacta al administrador.', 'error')
                return redirect(url_for('login'))
    except Exception as e:
        print(f"Error in Google OAuth: {str(e)}")
        flash('Error al iniciar sesión con Google.', 'error')
        return redirect(url_for('login'))

@app.route('/login/microsoft')
def login_microsoft():
    if not os.getenv('MICROSOFT_CLIENT_ID') or os.getenv('MICROSOFT_CLIENT_ID') == 'your_microsoft_client_id_here':
        flash('Error: Microsoft Login no configurado. Revisa el archivo .env', 'error')
        return redirect(url_for('login'))
    redirect_uri = url_for('authorize_microsoft', _external=True)
    return microsoft.authorize_redirect(redirect_uri)

@app.route('/authorize/microsoft')
def authorize_microsoft():
    try:
        token = microsoft.authorize_access_token()
        user_info = token.get('userinfo')
        
        if user_info:
            email = user_info.get('email')
            name = user_info.get('name', email.split('@')[0])
            oauth_id = user_info.get('sub')
            
            # Check if user exists
            user = User.query.filter_by(email=email).first()
            
            if user:
                if user.oauth_provider != 'microsoft':
                    user.oauth_provider = 'microsoft'
                    user.oauth_id = oauth_id
                    db.session.commit()
                login_user(user)
                return redirect(url_for('dashboard'))
            else:
                flash('Tu cuenta no está registrada. Por favor, contacta al administrador.', 'error')
                return redirect(url_for('login'))
    except Exception as e:
        print(f"Error in Microsoft OAuth: {str(e)}")
        flash('Error al iniciar sesión con Microsoft.', 'error')
        return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'terapista':
        # Stats from DB
        active_patients = User.query.filter_by(role='jugador', is_active=True).count()
        total_sessions = Appointment.query.filter_by(therapist_id=current_user.id).count()

        # IA precision: average of SessionMetrics.accurracy for therapist's patients
        avg_acc_query = db.session.query(func.avg(SessionMetrics.accurracy))\
            .join(User, SessionMetrics.user_id == User.id)\
            .filter(User.role == 'jugador').scalar()
        ia_precision = round(avg_acc_query or 0, 1)

        # Improvement rate: compare avg accuracy last 30 days vs previous 30 days (simple proxy)
        now = datetime.utcnow()
        last_30 = now - timedelta(days=30)
        prev_60 = now - timedelta(days=60)
        avg_last_30 = db.session.query(func.avg(SessionMetrics.accurracy))\
            .filter(SessionMetrics.date >= last_30).scalar()
        avg_prev_30 = db.session.query(func.avg(SessionMetrics.accurracy))\
            .filter(SessionMetrics.date >= prev_60, SessionMetrics.date < last_30).scalar()
        if avg_last_30 and avg_prev_30 and avg_prev_30 != 0:
            improvement_rate = round(((avg_last_30 - avg_prev_30) / avg_prev_30) * 100, 1)
        else:
            improvement_rate = 0

        stats = {
            'active_patients': active_patients,
            'total_sessions': total_sessions,
            'ia_precision': ia_precision,
            'improvement_rate': improvement_rate
        }

        # Patient Performance from DB (show all active patients, even without metrics)
        patients_query = User.query.filter_by(role='jugador', is_active=True).all()
        patients = []
        for p in patients_query:
            metrics = SessionMetrics.query.filter_by(user_id=p.id).order_by(SessionMetrics.date.desc()).limit(10).all()
            if metrics:
                acc_list = [m.accurracy for m in metrics]
                avg_time_list = [m.avg_time for m in metrics]
                avg_acc = round(sum(acc_list) / len(acc_list), 1)
                avg_time = round(sum(avg_time_list) / len(avg_time_list), 1)
                sessions_count = SessionMetrics.query.filter_by(user_id=p.id).count()
                patients.append({
                    "avatar": f"https://ui-avatars.com/api/?name={p.username.replace(' ', '+')}&background=random",
                    "name": p.username,
                    "ptid": p.id,
                    "game": metrics[0].game_name if metrics else 'Sin actividad',
                    "level": metrics[0].prediction if metrics else 0,
                    "accuracy": avg_acc,
                    "avg_time": avg_time,
                    "sessions": sessions_count,
                    "prediction_code": metrics[0].prediction if metrics else 0
                })
            else:
                # Include patients without metrics (newly added)
                patients.append({
                    "avatar": f"https://ui-avatars.com/api/?name={p.username.replace(' ', '+')}&background=random",
                    "name": p.username,
                    "ptid": p.id,
                    "game": 'Sin actividad',
                    "level": 0,
                    "accuracy": 0,
                    "avg_time": 0,
                    "sessions": 0,
                    "prediction_code": 0
                })

        # Order by sessions desc and take top 5 (or all if less than 5)
        patients = sorted(patients, key=lambda x: x["sessions"], reverse=True)[:5]

        # Alerts: simple heuristics from metrics (keep structure)
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
        # Expanded logic for player dashboard
        total_sessions = SessionMetrics.query.filter_by(user_id=current_user.id).count()
        avg_accuracy = db.session.query(func.avg(SessionMetrics.accurracy)).filter_by(user_id=current_user.id).scalar() or 0
        avg_time = db.session.query(func.avg(SessionMetrics.avg_time)).filter_by(user_id=current_user.id).scalar() or 0
        last_played_date = db.session.query(func.max(SessionMetrics.date)).filter_by(user_id=current_user.id).scalar()
        
        # Format last played date
        if last_played_date:
            last_played = last_played_date.strftime('%d de %B, %Y')
        else:
            last_played = 'Nunca'

        # Get recent sessions (last 5)
        recent_sessions = SessionMetrics.query.filter_by(user_id=current_user.id).order_by(SessionMetrics.date.desc()).limit(5).all()
        
        # Get game-specific stats
        game_stats = db.session.query(
            SessionMetrics.game_name,
            func.count(SessionMetrics.id).label('plays'),
            func.avg(SessionMetrics.accurracy).label('avg_acc'),
            func.avg(SessionMetrics.avg_time).label('avg_time')
        ).filter_by(user_id=current_user.id).group_by(SessionMetrics.game_name).all()

        # Get upcoming appointments
        upcoming_appointments = Appointment.query.filter(
            Appointment.patient_id == current_user.id,
            Appointment.start_time >= datetime.utcnow(),
            Appointment.status == 'scheduled'
        ).order_by(Appointment.start_time).limit(3).all()

        player_stats = {
            'total_sessions': total_sessions,
            'avg_accuracy': round(avg_accuracy, 1),
            'avg_time': round(avg_time, 2),
            'last_played': last_played,
            'recent_sessions': recent_sessions,
            'game_stats': game_stats,
            'upcoming_appointments': upcoming_appointments
        }

        return render_template('patient/dashboard.html', 
                               player_stats=player_stats,
                               active_page='dashboard')

@app.route('/api/notifications')
@login_required
def get_notifications():
    notifications = Notification.query.filter_by(user_id=current_user.id, is_read=False).order_by(Notification.timestamp.desc()).all()
    return jsonify([{
        'id': n.id,
        'message': n.message,
        'timestamp': n.timestamp.strftime('%d %b, %H:%M'),
        'link': n.link
    } for n in notifications])

@app.route('/api/patients')
@login_required
def api_patients():
    if current_user.role != 'terapista':
        return jsonify({'error': 'Acceso denegado'}), 403
    patients = User.query.filter_by(role='jugador', is_active=True).order_by(User.username.asc()).all()
    return jsonify([{'id': p.id, 'username': p.username, 'email': p.email} for p in patients])

@app.route('/api/notifications/mark-read', methods=['POST'])
@login_required
def mark_notifications_read():
    try:
        Notification.query.filter_by(user_id=current_user.id, is_read=False).update({'is_read': True})
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

def create_notification(user_id, message, link=None):
    """Helper function to create a notification."""
    notification = Notification(
        user_id=user_id,
        message=message,
        link=link
    )
    db.session.add(notification)
    db.session.commit()

@app.route('/patients/manage')
@login_required
def manage_patients():
    if current_user.role != 'terapista':
        flash('Acceso denegado.', 'error')
        return redirect(url_for('dashboard'))
    
    patients = User.query.filter_by(role='jugador').all()
    return render_template('therapist/patients.html', patients=patients, active_page='patients')


def _parse_datetime(value):
    """Robust datetime parser for ISO and naive strings"""
    if not value:
        return None
    try:
        # Try ISO format first
        return datetime.fromisoformat(value)
    except Exception:
        # Try common formats
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(value, fmt)
            except Exception:
                continue
    return None


@app.route('/api/sessions', methods=['GET'])
@login_required
def api_get_sessions():
    """Return appointments between start and end (ISO dates) for calendar display."""
    if current_user.role != 'terapista':
        return jsonify({'error': 'Acceso denegado'}), 403

    start = request.args.get('start')
    end = request.args.get('end')
    # If no range provided, return a list view payload for the table
    if not start and not end:
        appts = Appointment.query.filter(Appointment.therapist_id == current_user.id)\
            .order_by(Appointment.start_time.desc()).limit(200).all()
        results = []
        for a in appts:
            results.append({
                'id': a.id,
                'title': a.title,
                'start_time': a.start_time.isoformat() if a.start_time else None,
                'end_time': a.end_time.isoformat() if a.end_time else None,
                'status': a.status,
                'patient': {'id': a.patient.id, 'name': a.patient.username} if a.patient else None,
                'location': a.location,
                'notes': a.notes
            })
        return jsonify(results)

    # Otherwise return events for calendar
    try:
        start_dt = _parse_datetime(start)
        end_dt = _parse_datetime(end)
    except Exception:
        return jsonify([])

    query = Appointment.query.filter(Appointment.therapist_id == current_user.id,
                                     Appointment.start_time >= start_dt,
                                     Appointment.start_time <= end_dt).all()

    events = []
    for a in query:
        events.append({
            'id': a.id,
            'title': a.title or (a.patient.username if a.patient else 'Sesión'),
            'start': a.start_time.isoformat(),
            'end': a.end_time.isoformat() if a.end_time else None,
            'status': a.status,
            'patient': {'id': a.patient.id, 'name': a.patient.username} if a.patient else None,
            'location': a.location,
            'notes': a.notes
        })

    return jsonify(events)


@app.route('/api/appointments/patient', methods=['GET'])
@login_required
def api_get_patient_appointments():
    """Return appointments for the current patient (jugador)."""
    if current_user.role != 'jugador':
        return jsonify({'error': 'Acceso denegado'}), 403

    start = request.args.get('start')
    end = request.args.get('end')
    
    # Base query for patient's appointments
    base_query = Appointment.query.filter(Appointment.patient_id == current_user.id)
    
    # If no range provided, return upcoming appointments
    if not start and not end:
        appts = base_query.filter(
            Appointment.start_time >= datetime.utcnow(),
            Appointment.status == 'scheduled'
        ).order_by(Appointment.start_time.asc()).limit(10).all()
    else:
        try:
            start_dt = _parse_datetime(start)
            end_dt = _parse_datetime(end)
            appts = base_query.filter(
                Appointment.start_time >= start_dt,
                Appointment.start_time <= end_dt
            ).order_by(Appointment.start_time.asc()).all()
        except Exception:
            return jsonify([])

    results = []
    for a in appts:
        results.append({
            'id': a.id,
            'title': a.title,
            'start': a.start_time.isoformat() if a.start_time else None,
            'end': a.end_time.isoformat() if a.end_time else None,
            'status': a.status,
            'therapist': {'id': a.therapist.id, 'name': a.therapist.username} if a.therapist else None,
            'location': a.location,
            'notes': a.notes
        })
    
    return jsonify(results)


@app.route('/api/sessions/day', methods=['GET'])
@login_required
def api_get_sessions_day():
    """Return sessions for a particular date (YYYY-MM-DD)."""
    if current_user.role != 'terapista':
        return jsonify({'success': False, 'message': 'Acceso denegado'}), 403

    date_str = request.args.get('date')
    if not date_str:
        return jsonify({'success': False, 'message': 'date parameter required'}), 400
    try:
        day = _parse_datetime(date_str)
        day_start = datetime(day.year, day.month, day.day)
        day_end = day_start + timedelta(days=1)
    except Exception:
        return jsonify({'success': False, 'message': 'Formato de fecha inválido'}), 400

    query = Appointment.query.filter(Appointment.therapist_id == current_user.id,
                                     Appointment.start_time >= day_start,
                                     Appointment.start_time < day_end).order_by(Appointment.start_time.asc()).all()

    results = []
    for a in query:
        results.append({
            'id': a.id,
            'title': a.title or (a.patient.username if a.patient else 'Sesión'),
            'start': a.start_time.isoformat(),
            'end': a.end_time.isoformat() if a.end_time else None,
            'status': a.status,
            'patient': {'id': a.patient.id, 'name': a.patient.username} if a.patient else None,
            'notes': a.notes,
            'location': a.location
        })

    return jsonify({'date': date_str, 'sessions': results})


@app.route('/api/sessions', methods=['POST'])
@login_required
def api_create_session():
    """Create a new appointment (therapist only). Expects JSON with patient_id, start_time, end_time, title, notes."""
    if current_user.role != 'terapista':
        return jsonify({'success': False, 'message': 'Acceso denegado'}), 403

    data = request.json or {}
    patient_id = data.get('patient_id')
    start_time = _parse_datetime(data.get('start_time'))
    end_time = _parse_datetime(data.get('end_time'))
    title = data.get('title')
    notes = data.get('notes')
    location = data.get('location')

    if not patient_id or not start_time:
        return jsonify({'success': False, 'message': 'patient_id and start_time are required'}), 400

    patient = User.query.get(patient_id)
    if not patient or patient.role != 'jugador':
        return jsonify({'success': False, 'message': 'Paciente no válido'}), 400

    appt = Appointment(
        therapist_id=current_user.id,
        patient_id=patient_id,
        title=title or f"Sesión con {patient.username}",
        start_time=start_time,
        end_time=end_time,
        notes=notes,
        location=location,
        status=data.get('status') or 'scheduled'
    )
    db.session.add(appt)
    db.session.commit()

    # Notifications: notify therapist and patient
    create_notification(user_id=current_user.id, message=f'Sesión programada: {appt.title} — {start_time.strftime("%d %b %H:%M")}', link=url_for('sessions'))
    create_notification(user_id=patient_id, message=f'Tienes una nueva sesión programada con {current_user.username} el {start_time.strftime("%d %b %H:%M")}', link=url_for('game'))

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
    return jsonify(created)


@app.route('/api/sessions/<int:session_id>', methods=['PUT'])
@login_required
def api_update_session(session_id):
    if current_user.role != 'terapista':
        return jsonify({'success': False, 'message': 'Acceso denegado'}), 403

    appt = Appointment.query.get_or_404(session_id)
    data = request.json or {}
    if 'start_time' in data:
        appt.start_time = _parse_datetime(data.get('start_time'))
    if 'end_time' in data:
        appt.end_time = _parse_datetime(data.get('end_time'))
    if 'status' in data:
        appt.status = data.get('status')
    if 'notes' in data:
        appt.notes = data.get('notes')
    if 'title' in data:
        appt.title = data.get('title')
    db.session.commit()

    # Notify patient about update
    create_notification(user_id=appt.patient_id, message=f'Se actualizó la sesión: {appt.title} — {appt.start_time.strftime("%d %b %H:%M") if appt.start_time else ""}')

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


@app.route('/api/sessions/<int:session_id>', methods=['DELETE'])
@login_required
def api_delete_session(session_id):
    if current_user.role != 'terapista':
        return jsonify({'success': False, 'message': 'Acceso denegado'}), 403

    appt = Appointment.query.get_or_404(session_id)
    patient_id = appt.patient_id
    title = appt.title
    db.session.delete(appt)
    db.session.commit()

    create_notification(user_id=current_user.id, message=f'Sesión eliminada: {title}')
    create_notification(user_id=patient_id, message=f'Tu sesión programada ({title}) ha sido cancelada.')

    return jsonify({'success': True})


@app.route('/sessions')
@login_required
def sessions():
    if current_user.role != 'terapista':
        flash('Acceso denegado.', 'error')
        return redirect(url_for('dashboard'))
    # Compute session statistics for the cards
    now = datetime.utcnow()
    today_start = datetime(now.year, now.month, now.day)
    today_end = today_start + timedelta(days=1)

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

@app.route('/games')
@login_required
def games_list():
    if current_user.role != 'terapista':
        flash('Acceso denegado.', 'error')
        return redirect(url_for('dashboard'))
    return render_template('therapist/games.html', active_page='games')

@app.route('/analytics')
@login_required
def analytics():
    if current_user.role != 'terapista':
        flash('Acceso denegado.', 'error')
        return redirect(url_for('dashboard'))

    # Dummy data for now
    ai_overview = {
        "total_adaptations": 128,
        "adaptations_change": 15,
        "avg_accuracy": 89.2,
        "accuracy_improvement": 5.4,
        "success_rate": 94.1,
        "success_rate_increase": 2.1,
        "active_models": 3,
        "insight": "El modelo de 'Reflejos Rápidos' muestra una alta precisión en la predicción de la necesidad de apoyo."
    }

    model_performance = [
        {"name": "Clasificación de Nivel", "accuracy": 92},
        {"name": "Detección de Frustración", "accuracy": 85},
        {"name": "Predicción de Abandono", "accuracy": 78},
    ]

    recent_adaptations = [
        {
            "patient_name": "Carlos Rodriguez",
            "patient_avatar": "https://ui-avatars.com/api/?name=Carlos+Rodriguez&background=random",
            "game_type": "Memoria Visual",
            "prev_level": 3,
            "new_level": 4,
            "reason": "Alta precisión sostenida",
            "timestamp": "Hace 2 horas",
            "confidence": 95
        },
        {
            "patient_name": "Ana Martinez",
            "patient_avatar": "https://ui-avatars.com/api/?name=Ana+Martinez&background=random",
            "game_type": "Reflejos Rápidos",
            "prev_level": 5,
            "new_level": 5,
            "reason": "Rendimiento inconsistente",
            "timestamp": "Hace 5 horas",
            "confidence": 88
        },
        {
            "patient_name": "Luis Garcia",
            "patient_avatar": "https://ui-avatars.com/api/?name=Luis+Garcia&background=random",
            "game_type": "Seguimiento de Objetos",
            "prev_level": 2,
            "new_level": 1,
            "reason": "Bajo tiempo de reacción",
            "timestamp": "Hace 1 día",
            "confidence": 91
        }
    ]

    # Chart data
    # 1. Difficulty Adaptation Over Time
    df_difficulty = pd.DataFrame({
        'Date': pd.to_datetime(['2023-05-01', '2023-05-02', '2023-05-03', '2023-05-04', '2023-05-05', '2023-05-06', '2023-05-07']),
        'Patient A': [3, 3, 4, 4, 4, 5, 5],
        'Patient B': [2, 3, 3, 3, 4, 4, 4],
        'Patient C': [5, 5, 5, 4, 4, 4, 3]
    })
    fig_difficulty = go.Figure()
    for col in df_difficulty.columns[1:]:
        fig_difficulty.add_trace(go.Scatter(x=df_difficulty['Date'], y=df_difficulty[col], name=col, mode='lines+markers'))
    fig_difficulty.update_layout(title='Difficulty Adaptation', xaxis_title='Date', yaxis_title='Difficulty Level', template='plotly_white', legend_title_text='Patients')
    difficulty_adaptation_data = json.loads(fig_difficulty.to_json())


    # 2. Patient Progress Distribution
    df_progress = pd.DataFrame({
        'Level': [1, 2, 3, 4, 5, 6, 7, 8],
        'Patients': [5, 8, 12, 7, 4, 2, 1, 0]
    })
    fig_progress = px.bar(df_progress, x='Level', y='Patients', title='Patient Progress Distribution', template='plotly_white')
    patient_progress_data = json.loads(fig_progress.to_json())

    # 3. Adaptation Frequency
    df_adaptation = pd.DataFrame({
        'Game Type': ['Reflejos', 'Memoria', 'Seguimiento', 'Cálculo'],
        'Frequency': [25, 18, 30, 12]
    })
    fig_adaptation = px.pie(df_adaptation, values='Frequency', names='Game Type', title='Adaptation Frequency by Game', hole=.3, template='plotly_white')
    adaptation_frequency_data = json.loads(fig_adaptation.to_json())


    return render_template('therapist/analytics.html',
                           ai_overview=ai_overview,
                           model_performance=model_performance,
                           recent_adaptations=recent_adaptations,
                           difficulty_adaptation_data=difficulty_adaptation_data,
                           patient_progress_data=patient_progress_data,
                           adaptation_frequency_data=adaptation_frequency_data,
                           active_page='analytics')

@app.route('/reports')
@login_required
def reports():
    if current_user.role != 'terapista':
        flash('Acceso denegado.', 'error')
        return redirect(url_for('dashboard'))
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
    ).group_by(func.strftime('%Y-%m', SessionMetrics.date))
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
    ).group_by(SessionMetrics.game_name)
    df_games = pd.read_sql(q_games.statement, db.engine)
    colors = ['#75a83a', '#3b82f6', '#8b5cf6', '#f59e0b']
    fig_games = go.Figure(data=[go.Pie(labels=df_games['Juego'], values=df_games['Rendimiento'], hole=.4, marker_colors=colors)])
    game_performance_chart = json.loads(fig_games.to_json())

    # Difficulty analysis buckets based on prediction
    q_pred = db.session.query(
        SessionMetrics.prediction,
        func.count(SessionMetrics.id).label('cnt')
    ).group_by(SessionMetrics.prediction)
    df_pred = pd.read_sql(q_pred.statement, db.engine)
    difficulty_analysis = [
        {'name': 'Fácil', 'percentage': int(df_pred['cnt'].sum()), 'color': 'bg-green-500'}
    ]
    # Keep layout by providing static labels; replace with refined bucketing later

    # Patient insights: top 3 by recent avg accuracy
    q_insights = db.session.query(
        SessionMetrics.user_id.label('uid'),
        func.avg(SessionMetrics.accurracy).label('acc')
    ).group_by(SessionMetrics.user_id)
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
                           active_page='reports')


@app.route('/patients/add', methods=['POST'])
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
        return redirect(url_for('manage_patients'))
    
    # Check if user already exists
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        flash('Este correo electrónico ya está registrado.', 'error')
        return redirect(url_for('manage_patients'))
    
    # Generate random password
    password = generate_password()
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
    create_notification(
        user_id=current_user.id,
        message=f'Paciente {new_patient.username} agregado. Email: {email} | Contraseña: {password}',
        link=url_for('manage_patients')
    )

    # Send email (include username so message greets them by name)
    email_sent = send_welcome_email(email, password, new_patient.username)
    
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
    
    return redirect(url_for('manage_patients'))

@app.route('/patients/toggle/<int:patient_id>', methods=['POST'])
@login_required
def toggle_patient_status(patient_id):
    if current_user.role != 'terapista':
        return jsonify({'success': False, 'message': 'Acceso denegado'}), 403
    
    patient = User.query.get_or_404(patient_id)
    patient.is_active = not patient.is_active
    db.session.commit()

    status_message = "activado" if patient.is_active else "desactivado"
    create_notification(
        user_id=current_user.id,
        message=f'El paciente {patient.username} ha sido {status_message}.',
        link=url_for('manage_patients')
    )
    
    return jsonify({'success': True, 'is_active': patient.is_active})

@app.route('/patients/delete/<int:patient_id>', methods=['POST'])
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

        create_notification(
            user_id=current_user.id,
            message=f'El paciente {patient_username} ha sido eliminado permanentemente.'
        )

        db.session.commit()
        flash('Paciente eliminado exitosamente.', 'success')
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/game')
@login_required
def game():
    return render_template('game.html')

@app.route('/api/save_game', methods=['POST'])
@login_required
def save_game():
    data = request.json
    acc = data['accuracy']
    time = data['avg_time']
    pred_code, pred_text = predict_level(acc, time)

    metric = SessionMetrics(
        user_id=current_user.id,
        game_name='Reflejos Rápidos',
        accurracy=acc,
        avg_time=time,
        prediction=pred_code
    )
    db.session.add(metric)
    db.session.commit()
    return jsonify({'recommendation': pred_text, 'code': pred_code})

@app.route('/calendar/patient')
@login_required
def calendar_patient():
    if current_user.role != 'jugador':
        flash('Acceso no autorizado', 'error')
        return redirect(url_for('dashboard'))
    return render_template('patient/calendar.html', active_page='calendar')

@app.route('/calendar/therapist')
@login_required
def calendar_therapist():
    if current_user.role != 'terapeuta':
        flash('Acceso no autorizado', 'error')
        return redirect(url_for('dashboard'))
    return render_template('therapist/calendar.html', active_page='calendar')

@app.route('/progress')
@login_required
def progress():
    if current_user.role != 'jugador':
        flash('Acceso no autorizado', 'error')
        return redirect(url_for('dashboard'))
    # Get player stats for sidebar
    total_sessions = SessionMetrics.query.filter_by(user_id=current_user.id).count()
    last_played_date = db.session.query(func.max(SessionMetrics.date)).filter_by(user_id=current_user.id).scalar()
    last_played = last_played_date.strftime('%d de %B, %Y') if last_played_date else 'Nunca'
    player_stats = {
        'total_sessions': total_sessions,
        'last_played': last_played
    }
    return render_template('patient/progress.html', active_page='progress', player_stats=player_stats)

@app.route('/my-therapist')
@login_required
def my_therapist():
    if current_user.role != 'jugador':
        flash('Acceso no autorizado', 'error')
        return redirect(url_for('dashboard'))
    # Get player stats for sidebar
    total_sessions = SessionMetrics.query.filter_by(user_id=current_user.id).count()
    last_played_date = db.session.query(func.max(SessionMetrics.date)).filter_by(user_id=current_user.id).scalar()
    last_played = last_played_date.strftime('%d de %B, %Y') if last_played_date else 'Nunca'
    player_stats = {
        'total_sessions': total_sessions,
        'last_played': last_played
    }
    return render_template('patient/my_therapist.html', active_page='therapist', player_stats=player_stats)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


# ==================== PATIENT DETAIL VIEW ====================
@app.route('/patients/<int:patient_id>')
@login_required
def patient_detail(patient_id):
    if current_user.role != 'terapista':
        flash('Acceso denegado.', 'error')
        return redirect(url_for('dashboard'))
    
    patient = User.query.get_or_404(patient_id)
    if patient.role != 'jugador':
        flash('Usuario no es un paciente.', 'error')
        return redirect(url_for('manage_patients'))
    
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


@app.route('/patients/<int:patient_id>/update', methods=['POST'])
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
@app.route('/messages')
@login_required
def messages_list():
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
        # Patient sees their therapist(s)
        therapist = User.query.filter_by(role='terapista').first()
        if not therapist:
            flash('No hay terapeutas disponibles', 'error')
            return redirect(url_for('dashboard'))
        
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


@app.route('/messages/<int:user_id>')
@login_required
def messages_conversation(user_id):
    if current_user.role != 'terapista':
        flash('Acceso denegado', 'error')
        return redirect(url_for('dashboard'))
    
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


@app.route('/api/messages/send', methods=['POST'])
@login_required
def send_message():
    data = request.json
    receiver_id = data.get('receiver_id')
    subject = data.get('subject')
    body = data.get('body')
    
    if not receiver_id or not body:
        return jsonify({'success': False, 'message': 'Faltan datos requeridos'}), 400
    
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
    create_notification(
        user_id=receiver_id,
        message=f'Nuevo mensaje de {current_user.username}',
        link=url_for('messages_list')
    )
    
    return jsonify({
        'success': True,
        'message_id': message.id,
        'created_at': message.created_at.isoformat()
    })


@app.route('/api/messages/unread-count')
@login_required
def unread_messages_count():
    count = Message.query.filter_by(receiver_id=current_user.id, is_read=False).count()
    return jsonify({'count': count})


# ==================== PROFILE MANAGEMENT ====================
@app.route('/profile')
@login_required
def profile():
    if current_user.role == 'terapista':
        # Get therapist stats
        patients_count = User.query.filter_by(id=current_user.id, is_active=True).count()
        sessions_count = SessionMetrics.query.join(User).filter(User.id == current_user.id).count()
        upcoming_appointments = Appointment.query.filter(
            Appointment.id == current_user.id,
            Appointment.status == 'scheduled'
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


@app.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    data = request.json
    
    # Update allowed fields
    if 'username' in data and data['username']:
        current_user.username = data['username']
    if 'phone' in data:
        current_user.phone = data['phone']
    if 'timezone' in data:
        current_user.timezone = data['timezone']
    
    # Only patients can update these
    if current_user.role == 'jugador':
        if 'date_of_birth' in data and data['date_of_birth']:
            try:
                current_user.date_of_birth = datetime.strptime(data['date_of_birth'], '%Y-%m-%d').date()
            except:
                pass
        if 'guardian_name' in data:
            current_user.guardian_name = data['guardian_name']
        if 'guardian_contact' in data:
            current_user.guardian_contact = data['guardian_contact']
    
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Perfil actualizado correctamente'})


@app.route('/profile/change-password', methods=['POST'])
@login_required
def change_password():
    data = request.json
    current_password = data.get('current_password')
    new_password = data.get('new_password')
    
    if not current_password or not new_password:
        return jsonify({'success': False, 'message': 'Faltan datos requeridos'}), 400
    
    # Verify current password
    if not bcrypt.check_password_hash(current_user.password, current_password):
        return jsonify({'success': False, 'message': 'Contraseña actual incorrecta'}), 401
    
    # Update password
    hashed_pw = bcrypt.generate_password_hash(new_password).decode('utf-8')
    current_user.password = hashed_pw
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Contraseña actualizada correctamente'})


if __name__ == '__main__':
    app.run(debug=True, port=5000)
