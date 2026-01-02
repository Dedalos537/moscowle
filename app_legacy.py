from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from flask_mail import Mail, Message as MailMessage
from authlib.integrations.flask_client import OAuth
from models import SessionMetrics, db, User, Notification, Appointment, Message
from schemas import CreateUserSchema, UpdateUserSchema, AssignTherapistSchema, SendMessageSchema
from ai_service import predict_level, get_cluster, train_model
from datetime import datetime, timedelta
from sqlalchemy import func, or_
import json
import io
import csv
from flask import make_response
from email_validator import validate_email, EmailNotValidError
import requests
import json
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
app.config['GEMINI_API_KEY'] = os.getenv('GEMINI_API_KEY')

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
            f"Hola {username or recipient_email},\n\n"
            f"Tu cuenta ha sido creada exitosamente en Moscowle.\n\n"
            f"Credenciales de acceso:\n"
            f"Correo: {recipient_email}\n"
            f"Contraseña temporal: {plain_password}\n\n"
            f"Inicia sesión y cambia tu contraseña temporal por una más segura desde tu perfil.\n\n"
            "Saludos,\nEquipo Moscowle"
        )
        msg = MailMessage(subject=subject, recipients=[recipient_email], body=body)
        mail.send(msg)
        app.logger.info(f"Welcome email sent successfully to {recipient_email}")
        return True
    except Exception as e:
        app.logger.error(f"Failed to send welcome email to {recipient_email}: {str(e)}")
        return False

def send_password_change_email(recipient_email: str, new_password: str, username: str):
    """Send an email notifying password change with the new password. Skips if mail is not configured."""
    if not app.config.get('MAIL_USERNAME') or not app.config.get('MAIL_PASSWORD'):
        app.logger.warning("Email not configured. Skipping password change email.")
        return False
    try:
        subject = "Cambio de contraseña en Moscowle"
        body = (
            f"Hola {username or recipient_email},\n\n"
            f"Tu contraseña ha sido actualizada exitosamente.\n\n"
            f"Nueva contraseña: {new_password}\n\n"
            "Si no realizaste este cambio, por favor contacta al administrador de inmediato.\n\n"
            "Saludos,\nEquipo Moscowle"
        )
        msg = MailMessage(subject=subject, recipients=[recipient_email], body=body)
        mail.send(msg)
        app.logger.info(f"Password change email sent to {recipient_email}")
        return True
    except Exception as e:
        app.logger.error(f"Failed to send password change email to {recipient_email}: {str(e)}")
        return False

# Lightweight credential validation for live login feedback
@app.route('/api/auth/validate', methods=['POST'])
def api_auth_validate():
    try:
        data = request.get_json(silent=True) or {}
        email = (data.get('email') or '').strip().lower()
        password = data.get('password') or ''
        if not email or not password:
            return jsonify({'valid': False})
        user = User.query.filter_by(email=email).first()
        if not user or not user.is_active:
            return jsonify({'valid': False})
        try:
            is_ok = bcrypt.check_password_hash(user.password, password)
        except Exception:
            return jsonify({'valid': False})
        return jsonify({'valid': bool(is_ok)})
    except Exception as e:
        app.logger.warning(f"/api/auth/validate error: {e}")
        return jsonify({'valid': False})

    try:
        subject = "Cambio de contraseña en Moscowle"
        body = (
            f"Hola {username or recipient_email},\n\n"
            f"Tu contraseña ha sido actualizada exitosamente.\n\n"
            f"Nueva contraseña: {new_password}\n\n"
            "Si no realizaste este cambio, por favor contacta al administrador de inmediato.\n\n"
            "Saludos,\nEquipo Moscowle"
        )
        msg = MailMessage(subject=subject, recipients=[recipient_email], body=body)
        mail.send(msg)
        app.logger.info(f"Password change email sent to {recipient_email}")
        return True
    except Exception as e:
        app.logger.error(f"Failed to send password change email to {recipient_email}: {str(e)}")
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
    # Lightweight SQLite schema migration for newly added columns
    try:
        from sqlalchemy import text
        conn = db.engine.connect()
        # Check columns via PRAGMA and add if missing
        def has_column(table, col):
            rows = conn.execute(text(f"PRAGMA table_info({table})")).mappings().all()
            return any(r['name'] == col for r in rows)
        # user.game_profile
        if not has_column('user', 'game_profile'):
            conn.execute(text("ALTER TABLE user ADD COLUMN game_profile TEXT"))
        # user.assigned_therapist_id
        if not has_column('user', 'assigned_therapist_id'):
            conn.execute(text("ALTER TABLE user ADD COLUMN assigned_therapist_id INTEGER REFERENCES user(id)"))
        # appointment.games
        if not has_column('appointment', 'games'):
            conn.execute(text("ALTER TABLE appointment ADD COLUMN games TEXT"))
        # sessionmetrics.session_id
        if not has_column('session_metrics', 'session_id'):
            conn.execute(text("ALTER TABLE session_metrics ADD COLUMN session_id INTEGER REFERENCES appointment(id)"))
        conn.close()
    except Exception as e:
        # Log but continue; in dev environments manual migration may be needed
        app.logger.warning(f"Schema migration warning: {e}")
    train_model()
    
    # Create admin user (real admin)
    admin_email_env = (os.getenv('ADMIN_EMAIL') or '').strip()
    try:
        admin_email = validate_email(admin_email_env).email if admin_email_env else 'diegocenteno537@gmail.com'
    except EmailNotValidError:
        app.logger.warning(f"Invalid ADMIN_EMAIL '{admin_email_env}' in .env; using default fallback email.")
        admin_email = 'diegocenteno537@gmail.com'
    admin_password = os.getenv('ADMIN_PASSWORD') or 'Rucula_530'
    admin = User.query.filter_by(email=admin_email).first()
    if not admin:
        hashed_pw = bcrypt.generate_password_hash(admin_password).decode('utf-8')
        admin = User(
            username='Administrador',
            email=admin_email,
            password=hashed_pw,
            role='admin',
            is_active=True
        )
        db.session.add(admin)
        db.session.commit()
        print(f"Admin user created: {admin_email}")
    else:
        changed = False
        if admin.role != 'admin':
            admin.role = 'admin'
            changed = True
        if not admin.is_active:
            admin.is_active = True
            changed = True
        # Optional password reset if env flag set
        if os.getenv('ADMIN_FORCE_RESET') == '1':
            admin.password = bcrypt.generate_password_hash(admin_password).decode('utf-8')
            changed = True
        if changed:
            db.session.commit()
            print(f"Admin user ensured/updated: {admin_email}")

    # Ensure no other users remain with admin role (avoid mixing therapist as admin)
    # Ensure no other users remain with admin role (avoid mixing therapist as admin)
    # try:
    #     from sqlalchemy import and_
    #     others = User.query.filter(and_(User.role == 'admin', User.email != admin_email)).all()
    #     demoted = 0
    #     for u in others:
    #         u.role = 'terapista'
    #         if not u.is_active:
    #             u.is_active = True
    #         demoted += 1
    #     if demoted:
    #         db.session.commit()
    #         print(f"Demoted {demoted} non-primary admin user(s) to 'terapista'.")
    # except Exception as e:
    #     app.logger.warning(f"Role normalization warning: {e}")

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

#@app.route('/login/google')
#def login_google():
 #   if not os.getenv('GOOGLE_CLIENT_ID') or os.getenv('GOOGLE_CLIENT_ID') == 'your_google_client_id_here':
  #      flash('Error: Google Login no configurado. Revisa el archivo .env', 'error')
   #     return redirect(url_for('login'))
   # redirect_uri = url_for('authorize_google', _external=True)
   # return google.authorize_redirect(redirect_uri)

#@app.route('/authorize/google')
#def authorize_google():
 #   try:
  #      token = google.authorize_access_token()
   #     user_info = token.get('userinfo')
        
    #    if user_info:
      #      email = user_info.get('email')
     #      name = user_info.get('name', email.split('@')[0])
      #      oauth_id = user_info.get('sub')
            
            # Check if user exists
       #     user = User.query.filter_by(email=email).first()
            
        #    if user:
         #       if user.oauth_provider != 'google':
          #          user.oauth_provider = 'google'
           #         user.oauth_id = oauth_id
            #        db.session.commit()
             #   login_user(user)
              #  return redirect(url_for('dashboard'))
           # else:
           #     flash('Tu cuenta no está registrada. Por favor, contacta al administrador.', 'error')
            #    return redirect(url_for('login'))
    #except Exception as e:
     #   print(f"Error in Google OAuth: {str(e)}")
      #  flash('Error al iniciar sesión con Google.', 'error')
       # return redirect(url_for('login'))

#@app.route('/login/microsoft')
#def login_microsoft():
    #if not os.getenv('MICROSOFT_CLIENT_ID') or os.getenv('MICROSOFT_CLIENT_ID') == 'your_microsoft_client_id_here':
        #flash('Error: Microsoft Login no configurado. Revisa el archivo .env', 'error')
       # return redirect(url_for('login'))
    #redirect_uri = url_for('authorize_microsoft', _external=True)
    #return microsoft.authorize_redirect(redirect_uri)

#@app.route('/authorize/microsoft')
#def authorize_microsoft():
    #try:
        #token = microsoft.authorize_access_token()
        #user_info = token.get('userinfo')
        
        #if user_info:
         #   email = user_info.get('email')
          #  name = user_info.get('name', email.split('@')[0])
           # oauth_id = user_info.get('sub')
            
            # Check if user exists
            #user = User.query.filter_by(email=email).first()
            
            #if user:
             #   if user.oauth_provider != 'microsoft':
              #      user.oauth_provider = 'microsoft'
               #     user.oauth_id = oauth_id
                #    db.session.commit()
                #login_user(user)
                #return redirect(url_for('dashboard'))
            #else:
             #   flash('Tu cuenta no está registrada. Por favor, contacta al administrador.', 'error')
              #  return redirect(url_for('login'))
   #except Exception as e:
    #    print(f"Error in Microsoft OAuth: {str(e)}")
     #   flash('Error al iniciar sesión con Microsoft.', 'error')
      #  return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'admin':
        # Admin overview: counts and quick stats
        therapists = User.query.filter_by(role='terapista').count()
        patients = User.query.filter_by(role='jugador').count()
        sessions_total = Appointment.query.count()
        avg_acc = db.session.query(func.avg(SessionMetrics.accurracy)).scalar() or 0
        overview = {
            'therapists': therapists,
            'patients': patients,
            'sessions_total': sessions_total,
            'avg_accuracy': round(avg_acc, 1)
        }
        try:
            return render_template(
                'admin/dashboard.html',
                overview=overview,
                active_page='admin_dashboard',
            )
        except Exception as e:
            app.logger.error(f"Error rendering admin dashboard: {e}")
            flash('Error cargando el panel de administración. Intenta más tarde.', 'error')
            return redirect(url_for('dashboard'))
    elif current_user.role == 'terapista':
        # Stats from DB
        active_patients = User.query.filter_by(role='jugador', is_active=True, assigned_therapist_id=current_user.id).count()
        total_sessions = Appointment.query.filter_by(therapist_id=current_user.id).count()

        # IA precision: average of SessionMetrics.accurracy for therapist's patients
        avg_acc_query = db.session.query(func.avg(SessionMetrics.accurracy))\
            .join(User, SessionMetrics.user_id == User.id)\
            .filter(User.role == 'jugador', User.assigned_therapist_id == current_user.id).scalar()
        ia_precision = round(avg_acc_query or 0, 1)

        # Improvement rate: compare avg accuracy last 30 days vs previous 30 days (simple proxy)
        now = datetime.utcnow()
        last_30 = now - timedelta(days=30)
        prev_60 = now - timedelta(days=60)
        
        avg_last_30 = db.session.query(func.avg(SessionMetrics.accurracy))\
            .join(User, SessionMetrics.user_id == User.id)\
            .filter(SessionMetrics.date >= last_30, User.assigned_therapist_id == current_user.id).scalar()
            
        avg_prev_30 = db.session.query(func.avg(SessionMetrics.accurracy))\
            .join(User, SessionMetrics.user_id == User.id)\
            .filter(SessionMetrics.date >= prev_60, SessionMetrics.date < last_30, User.assigned_therapist_id == current_user.id).scalar()
            
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
        patients_query = User.query.filter_by(role='jugador', is_active=True, assigned_therapist_id=current_user.id).all()
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
                    "avatar": f"https://ui-avatars.com/api/?name={(p.username or 'User').replace(' ', '+')}&background=random",
                    "name": p.username or 'Usuario',
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
                    "avatar": f"https://ui-avatars.com/api/?name={(p.username or 'User').replace(' ', '+')}&background=random",
                    "name": p.username or 'Usuario',
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

# Therapist insights API: weekly progress and alerts
@app.route('/api/therapist/insights')
@login_required
def therapist_insights():
    if current_user.role != 'terapista':
        return jsonify({'error': 'Acceso denegado'}), 403

    # Build last 7 days average accuracy for all active patients
    today = datetime.utcnow().date()
    days = [today - timedelta(days=i) for i in range(6, -1, -1)]
    series = []
    for d in days:
        day_start = datetime(d.year, d.month, d.day)
        day_end = day_start + timedelta(days=1)
        avg_acc = db.session.query(func.avg(SessionMetrics.accurracy))\
            .filter(SessionMetrics.date >= day_start, SessionMetrics.date < day_end).scalar() or 0
        series.append({'date': d.strftime('%Y-%m-%d'), 'avg_accuracy': round(avg_acc, 2)})

    # Alerts: recent risky predictions (prediction==2)
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    risky = SessionMetrics.query.filter(SessionMetrics.date >= seven_days_ago, SessionMetrics.prediction == 2)\
        .order_by(SessionMetrics.date.desc()).limit(5).all()
    alerts = []
    for r in risky:
        u = User.query.get(r.user_id)
        alerts.append({
            'type': 'red',
            'patient': (u.username or u.email),
            'message': f'Baja precisión ({int(r.accurracy)}%) en {r.game_name}. Sugerido apoyo.'
        })

    return jsonify({'weekly_progress': series, 'alerts': alerts})

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
    if current_user.role not in ('terapista', 'admin'):
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
    
    patients = User.query.filter_by(role='jugador', assigned_therapist_id=current_user.id).all()
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
                'notes': a.notes,
                'games': json.loads(a.games) if a.games else []
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
            'notes': a.notes,
            'games': json.loads(a.games) if a.games else []
        })

    return jsonify(events)


# Therapist upcoming sessions (compact list)
@app.route('/api/sessions/upcoming', methods=['GET'])
@login_required
def api_upcoming_sessions():
    if current_user.role != 'terapista':
        return jsonify({'error': 'Acceso denegado'}), 403
    now = datetime.utcnow()
    appts = Appointment.query.filter(
        Appointment.therapist_id == current_user.id,
        Appointment.start_time >= now,
        Appointment.status == 'scheduled'
    ).order_by(Appointment.start_time.asc()).limit(20).all()
    results = []
    for a in appts:
        patient = User.query.get(a.patient_id)
        results.append({
            'id': a.id,
            'patient': patient.username or patient.email,
            'start_time': a.start_time.isoformat(),
            'end_time': (a.end_time.isoformat() if a.end_time else None)
            ,'games': json.loads(a.games) if a.games else []
        })
    return jsonify(results)


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
            'notes': a.notes,
            'games': json.loads(a.games) if a.games else []
        })
    
    return jsonify(results)


@app.route('/api/games', methods=['GET'])
@login_required
def api_list_games():
    # Return list of available custom games (filenames) from static/games
    games_dir = os.path.join(app.root_path, 'static', 'games')
    try:
        files = [f for f in os.listdir(games_dir) if f.lower().endswith('.html')]
    except Exception:
        files = []
    return jsonify({'games': files})


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
    # attach games if provided (list or single value)
    try:
        games_payload = data.get('games')
        if games_payload:
            # accept comma-separated string or list
            if isinstance(games_payload, str):
                games_list = [g.strip() for g in games_payload.split(',') if g.strip()]
            elif isinstance(games_payload, list):
                games_list = games_payload
            else:
                games_list = []
            if games_list:
                appt.games = json.dumps(games_list)
    except Exception:
        pass
    db.session.add(appt)
    db.session.commit()

    # Notifications: notify therapist and patient
    try:
        create_notification(user_id=current_user.id, message=f'Sesión programada: {appt.title} — {start_time.strftime("%d %b %H:%M")}', link=url_for('sessions'))
        create_notification(user_id=patient_id, message=f'Tienes una nueva sesión programada con {current_user.username} el {start_time.strftime("%d %b %H:%M")}', link=url_for('game'))
    except Exception:
        pass

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
    try:
        create_notification(user_id=appt.patient_id, message=f'Se actualizó la sesión: {appt.title} — {appt.start_time.strftime("%d %b %H:%M") if appt.start_time else ""}', link=url_for('calendar_patient'))
    except Exception:
        pass

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

    try:
        create_notification(user_id=current_user.id, message=f'Sesión eliminada: {title}', link=url_for('sessions'))
        create_notification(user_id=patient_id, message=f'Tu sesión programada ({title}) ha sido cancelada.', link=url_for('calendar_patient'))
    except Exception:
        pass

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
    if current_user.role not in ('terapista','admin'):
        return redirect(url_for('dashboard'))
    # List saved custom games in static/games
    games_dir = os.path.join(app.root_path, 'static', 'games')
    try:
        files = [f for f in os.listdir(games_dir) if f.lower().endswith('.html')]
    except Exception:
        files = []
    return render_template('therapist/games.html', custom_games=files, active_page='games')
    
    
@app.route('/admin')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash('Acceso denegado.', 'error')
        return redirect(url_for('dashboard'))
    # Redirect to admin landing
    therapists = User.query.filter_by(role='terapista').count()
    patients = User.query.filter_by(role='jugador').count()
    sessions_total = Appointment.query.count()
    avg_acc = db.session.query(func.avg(SessionMetrics.accurracy)).scalar() or 0
    overview = {
        'therapists': therapists,
        'patients': patients,
        'sessions_total': sessions_total,
        'avg_accuracy': round(avg_acc, 1)
    }
    return render_template('admin/dashboard.html', overview=overview, active_page='admin_dashboard')

@app.route('/admin/users')
@login_required
def admin_users():
    if current_user.role != 'admin':
        flash('Acceso denegado.', 'error')
        return redirect(url_for('dashboard'))
    users = User.query.order_by(User.created_at.desc()).all()
    therapists = User.query.filter_by(role='terapista').order_by(User.username.asc()).all()
    return render_template('admin/users.html', users=users, therapists=therapists, active_page='admin_users')

@app.route('/api/admin/assign-therapist', methods=['POST'])
@login_required
def api_admin_assign_therapist():
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Acceso denegado'}), 403
    data = request.get_json(silent=True) or {}
    errors = AssignTherapistSchema().validate(data)
    if errors:
        return jsonify({'success': False, 'message': 'Datos inválidos', 'errors': errors}), 400
    patient_id = data['patient_id']
    therapist_id = data['therapist_id']
    patient = User.query.get(patient_id)
    therapist = User.query.get(therapist_id)
    if not patient or not therapist:
        return jsonify({'success': False, 'message': 'Usuario no encontrado'}), 404
    if patient.role != 'jugador' or therapist.role != 'terapista':
        return jsonify({'success': False, 'message': 'Roles inválidos para asignación'}), 400
    patient.assigned_therapist_id = therapist.id
    db.session.commit()
    # Notify patient and therapist
    try:
        create_notification(patient.id, f"Terapeuta asignado: {therapist.username}")
        create_notification(therapist.id, f"Nuevo paciente asignado: {patient.username}")
    except Exception:
        pass
    return jsonify({'success': True})

@app.route('/api/admin/create-user', methods=['POST'])
@login_required
def api_admin_create_user():
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Acceso denegado'}), 403
    data = request.get_json(silent=True) or {}
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
        app.logger.warning(f"Email inválido al crear usuario admin: {email} - {str(e)}")
        return jsonify({'success': False, 'message': 'Email inválido'}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({'success': False, 'message': 'Email ya registrado'}), 400
    temp_pw = generate_password()
    hashed_pw = bcrypt.generate_password_hash(temp_pw).decode('utf-8')
    try:
        u = User(username=username, email=email, password=hashed_pw, role=role, is_active=True)
        db.session.add(u)
        db.session.commit()
    except Exception as e:
        app.logger.error(f"Error al crear usuario: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Error al crear usuario'}), 500
    send_welcome_email(email, temp_pw, username)
    try:
        create_notification(u.id, "Tu cuenta ha sido creada", link=url_for('dashboard'))
    except Exception:
        pass
    return jsonify({'success': True, 'user': {'id': u.id, 'email': u.email, 'role': u.role}, 'temp_password': temp_pw})

@app.route('/admin/games')
@login_required
def admin_games():
    if current_user.role != 'admin':
        flash('Acceso denegado.', 'error')
        return redirect(url_for('dashboard'))
    games_dir = os.path.join(app.root_path, 'static', 'games')
    try:
        files = [f for f in os.listdir(games_dir) if f.lower().endswith('.html')]
    except Exception:
        files = []
    return render_template('admin/games.html', games=files, active_page='admin_games')

@app.route('/api/admin/games/delete', methods=['POST'])
@login_required
def api_admin_delete_game():
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Acceso denegado'}), 403
    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'success': False, 'message': 'Nombre requerido'}), 400
    games_dir = os.path.join(app.root_path, 'static', 'games')
    path = os.path.join(games_dir, name)
    try:
        if os.path.isfile(path):
            os.remove(path)
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'message': 'Archivo no encontrado'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/admin/reports')
@login_required
def admin_reports():
    if current_user.role != 'admin':
        flash('Acceso denegado.', 'error')
        return redirect(url_for('dashboard'))
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

@app.route('/admin/messages')
@login_required
def admin_messages():
    if current_user.role != 'admin':
        flash('Acceso denegado.', 'error')
        return redirect(url_for('dashboard'))
    therapists = User.query.filter_by(role='terapista', is_active=True).order_by(User.username.asc()).all()
    patients = User.query.filter_by(role='jugador', is_active=True).order_by(User.username.asc()).all()
    return render_template('admin/messages.html', therapists=therapists, patients=patients, active_page='admin_messages')

@app.route('/api/admin/messages/broadcast', methods=['POST'])
@login_required
def api_admin_broadcast():
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Acceso denegado'}), 403
    data = request.get_json(silent=True) or {}
    subject = (data.get('subject') or '').strip()
    body = (data.get('body') or '').strip()
    target = (data.get('target') or 'all').strip()  # 'all' | 'terapista' | 'jugador' | 'single'
    receiver_id = data.get('receiver_id')
    if not body:
        return jsonify({'success': False, 'message': 'Mensaje requerido'}), 400
    recipients = []
    if target == 'single' and receiver_id:
        u = User.query.get(receiver_id)
        if not u:
            return jsonify({'success': False, 'message': 'Destinatario no encontrado'}), 404
        recipients = [u]
    else:
        q = User.query
        if target in ('terapista','jugador'):
            q = q.filter_by(role=target)
        recipients = q.all()
    for u in recipients:
        msg = Message(sender_id=current_user.id, receiver_id=u.id, subject=subject, body=body)
        db.session.add(msg)
        create_notification(u.id, f"Mensaje del administrador: {subject or 'Sin asunto'}", link=url_for('messages_list'))
    db.session.commit()
    return jsonify({'success': True, 'count': len(recipients)})

@app.route('/api/admin/list-users')
@login_required
def api_admin_list_users():
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Acceso denegado'}), 403
    role = (request.args.get('role') or '').strip()
    q = User.query
    if role in ('terapista', 'jugador'):
        q = q.filter_by(role=role)
    users = [{'id': u.id, 'email': u.email, 'username': u.username, 'role': u.role} for u in q.order_by(User.username.asc()).all()]
    return jsonify({'success': True, 'users': users})

@app.route('/api/admin/update-user', methods=['POST'])
@login_required
def api_admin_update_user():
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Acceso denegado'}), 403
    data = request.get_json(silent=True) or {}
    errors = UpdateUserSchema().validate(data)
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

@app.route('/api/admin/delete-user', methods=['POST'])
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

@app.route('/analytics')
@login_required
def analytics():
    if current_user.role != 'terapista':
        flash('Acceso denegado.', 'error')
        return redirect(url_for('dashboard'))

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

@app.route('/reports')
@login_required
def reports():
    if current_user.role != 'terapista':
        flash('Acceso denegado.', 'error')
        return redirect(url_for('dashboard'))
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

@app.route('/therapist/reports')
@login_required
def therapist_reports():
    return redirect(url_for('reports'))


@app.route('/reports/export', methods=['GET'])
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
    return render_template('game.html')

@app.route('/api/save_game', methods=['POST'])
@login_required
def save_game():
    try:
        data = request.get_json() or {}
        game_name = data.get('game_name') or 'Juego'
        accuracy = float(data.get('accuracy') or 0)
        avg_time = float(data.get('avg_time') or 0)
        session_id = data.get('session_id')
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
        db.session.add(m)

        # If tied to a session, mark completed and close window
        if session_id:
            appt = Appointment.query.get(int(session_id))
            if appt:
                # Basic authorization: only therapist or the patient in the appointment can close it
                if current_user.id in (appt.patient_id, appt.therapist_id):
                    appt.status = 'completed'
                    appt.end_time = datetime.utcnow()
                    db.session.add(appt)
                    # Optional: create a notification for therapist
                    try:
                        create_notification(appt.therapist_id, f"Sesión #{appt.id} completada con {game_name}", link=url_for('patients', _external=False))
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
                app.logger.info(f"Triggering AI retraining with {len(training_data)} samples...")
                train_model(training_data)
        except Exception as e:
            app.logger.error(f"AI Retraining failed: {e}")
        # -----------------------------

        return jsonify({'status': 'ok', 'prediction': pred_code, 'recommendation': label})
    except Exception as e:
        return jsonify({'error': 'save_failed', 'detail': str(e)}), 400


# Upload custom game HTML to static/games
@app.route('/api/games/upload', methods=['POST'])
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
    dest_dir = os.path.join(app.root_path, 'static', 'games')
    os.makedirs(dest_dir, exist_ok=True)
    path = os.path.join(dest_dir, name)
    file.save(path)
    return jsonify({'status': 'ok', 'file': name, 'url': url_for('static', filename=f'games/{name}')})


# Gemini proxy for recommendations (requires GEMINI_API_KEY)
@app.route('/api/ai/gemini', methods=['POST'])
@login_required
def gemini_proxy():
    if current_user.role not in ('terapista','admin'):
        return jsonify({'error': 'Acceso denegado'}), 403
    api_key = app.config.get('GEMINI_API_KEY')
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
@app.route('/api/ai/generate_game', methods=['POST'])
@login_required
def generate_game():
    if current_user.role not in ('terapista','admin'):
        return jsonify({'error': 'Acceso denegado'}), 403
    api_key = app.config.get('GEMINI_API_KEY')
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
    dest_dir = os.path.join(app.root_path, 'static', 'games')
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
@app.route('/api/sessions/assign-games', methods=['POST'])
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
@app.route('/api/sessions/<int:session_id>/games', methods=['GET'])
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
@app.route('/api/sessions/<int:session_id>/complete', methods=['POST'])
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
        create_notification(appt.therapist_id, f"Sesión #{appt.id} completada. {plays} juegos registrados.", link=url_for('reports'))
        create_notification(appt.patient_id, f"Sesión completada. ¡Buen trabajo!", link=url_for('progress'))
    except Exception:
        pass

    return jsonify({'status': 'ok', 'updated_profile': existing})
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
    # Show personal progress charts for the logged-in patient
    # Allow only players to view their own progress
    if current_user.role != 'jugador':
        flash('Acceso denegado: esta sección es para pacientes.', 'error')
        return redirect(url_for('dashboard'))

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


@app.route('/api/resources/<int:resource_id>')
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
    # Therapist-only view
    if current_user.role != 'terapista':
        flash('Acceso no autorizado', 'error')
        return redirect(url_for('dashboard'))

    patient = User.query.get_or_404(patient_id)

    # Basic stats
    total_sessions = Appointment.query.filter(Appointment.patient_id == patient.id).count()
    completed_sessions = Appointment.query.filter(Appointment.patient_id == patient.id,
                                                  Appointment.status == 'completed').count()

    # Recent metrics (serialize to JSON-safe dicts)
    metrics_rows = SessionMetrics.query.filter(SessionMetrics.user_id == patient.id).order_by(SessionMetrics.date.desc()).limit(50).all()
    metrics = [
        {
            'id': m.id,
            'game_name': m.game_name,
            'accuracy': m.accurracy,
            'avg_time': m.avg_time,
            'prediction': m.prediction,
            'date': m.date.isoformat() if m.date else None
        } for m in metrics_rows
    ]

    # Upcoming appointments
    upcoming = Appointment.query.filter(Appointment.patient_id == patient.id,
                                        Appointment.status == 'scheduled',
                                        Appointment.start_time >= datetime.utcnow()).order_by(Appointment.start_time.asc()).limit(10).all()
    upcoming_appts = [
        {
            'id': a.id,
            'title': a.title,
            'start_time': a.start_time.isoformat() if a.start_time else None,
            'end_time': a.end_time.isoformat() if a.end_time else None,
            'location': a.location,
            'status': a.status
        } for a in upcoming
    ]

    # All sessions for charts
    all_appts = Appointment.query.filter(Appointment.patient_id == patient.id).order_by(Appointment.start_time.asc()).all()
    all_sessions = [
        {
            'id': a.id,
            'title': a.title,
            'start_time': a.start_time.isoformat() if a.start_time else None,
            'status': a.status
        } for a in all_appts
    ]

    # Player info block
    player_info = {
        'username': patient.username,
        'email': patient.email,
        'created_at': patient.created_at.strftime('%d %B, %Y') if patient.created_at else '',
        'phone': patient.phone,
        'date_of_birth': patient.date_of_birth.strftime('%d/%m/%Y') if patient.date_of_birth else '',
        'guardian_name': patient.guardian_name,
        'guardian_contact': patient.guardian_contact,
        'therapy_goals': patient.therapy_goals,
        'notes': patient.notes,
    }

    return render_template('therapist/patient_detail.html',
                           patient=patient,
                           player_info=player_info,
                           total_sessions=total_sessions,
                           completed_sessions=completed_sessions,
                           metrics=metrics,
                           upcoming_appts=upcoming_appts,
                           all_sessions=all_sessions,
                           active_page='patients')
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
    if current_user.role == 'admin':
        # Admin uses the dedicated admin messaging page
        return redirect(url_for('admin_messages'))
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
    if current_user.role == 'admin':
        return redirect(url_for('admin_profile'))
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
@app.route('/admin/profile')
@login_required
def admin_profile():
    if current_user.role != 'admin':
        flash('Acceso denegado.', 'error')
        return redirect(url_for('dashboard'))
    return render_template('admin/profile.html', active_page='admin_dashboard')

@app.route('/api/admin/profile', methods=['POST'])
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
            send_password_change_email(current_user.email, new_password, current_user.username or 'Administrador')
        except Exception:
            pass
    if changed:
        db.session.commit()
    return jsonify({'success': True})


@app.route('/profile/update', methods=['POST'])
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
        app.logger.error(f"Profile update failed for user {current_user.id}: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Error al actualizar el perfil'}), 500


@app.route('/profile/change-password', methods=['POST'])
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
            send_password_change_email(current_user.email, new_password, current_user.username)
        except Exception as e:
            app.logger.warning(f"Non-blocking: error sending password change email: {e}")
        return jsonify({'success': True, 'message': 'Contraseña actualizada correctamente'})
    except Exception as e:
        app.logger.error(f"Password change failed: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Error al cambiar la contraseña'}), 500
    


if __name__ == '__main__':
    app.run(debug=True, port=5000)
