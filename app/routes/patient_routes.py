from flask import Blueprint, render_template, redirect, url_for, flash, current_app, jsonify, request
from app.auth_compat import login_required, current_user
from app.models import SessionMetrics, db, User, Message, Appointment, Payment
from app.services.dashboard_service import DashboardService
from app.services.appointment_service import AppointmentService
from app.services.notification_service import NotificationService
from app.services.email_service import EmailService
from app.utils import get_user_today_utc_range, get_user_now, get_user_timezone, parse_datetime as _parse_datetime
from app.utils.sanitizer import sanitize_text
from app.extensions import csrf
from sqlalchemy import func, or_
from werkzeug.utils import secure_filename
import os, json, uuid
from datetime import datetime, timedelta, timezone

patient_bp = Blueprint('patient', __name__, url_prefix='/patient')
dashboard_service = DashboardService()
appointment_service = AppointmentService()
notification_service = NotificationService()

@patient_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role != 'jugador':
        return redirect(url_for('main.dashboard'))
        
    player_stats = dashboard_service.get_player_stats(current_user.id)
    
    # Calculate payment status for dashboard widget
    today = datetime.utcnow().date()
    payment_status = {
        'due_date': current_user.payment_due_date,
        'amount': current_user.payment_amount or 0,
        'is_overdue': False,
        'days_overdue': 0,
        'days_until': 0
    }
    
    if current_user.payment_due_date:
        delta = (current_user.payment_due_date - today).days
        if delta < 0:
            payment_status['is_overdue'] = True
            payment_status['days_overdue'] = abs(delta)
        else:
            payment_status['days_until'] = delta

    # Get today's sessions for the dashboard
    today_start, today_end = get_user_today_utc_range(current_user)
    today_sessions = appointment_service.get_patient_appointments(current_user.id, today_start, today_end)
    
    now = get_user_now(current_user)

    sessions_data = []
    for s in today_sessions:
        games = []
        try:
            games = json.loads(s.games) if s.games else []
        except:
            games = []
        
        # Localize DB times to UTC for comparison with aware 'now'
        # DB stores naive UTC
        s_start_aware = s.start_time.replace(tzinfo=timezone.utc)
        s_end_val = s.end_time or (s.start_time + timedelta(hours=1))
        s_end_aware = s_end_val.replace(tzinfo=timezone.utc)

        is_active = False
        if s.status == 'scheduled':
            # Strict time window check: start_time <= now <= end_time
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
                           payment_status=payment_status,
                           active_page='dashboard',
                           now=now)

@patient_bp.route('/payments')
@login_required
def payments():
    if current_user.role != 'jugador':
        return redirect(url_for('main.dashboard'))
    
    payments = Payment.query.filter_by(patient_id=current_user.id).order_by(Payment.date.desc()).all()
    
    # Calculate overdue days if any
    today = datetime.utcnow().date()
    days_overdue = 0
    days_until = 0
    is_overdue = False
    
    if current_user.payment_due_date:
        delta = (current_user.payment_due_date - today).days
        if delta < 0:
            is_overdue = True
            days_overdue = abs(delta)
        else:
            days_until = delta
            
    return render_template('patient/payments.html', 
                           payments=payments, 
                           days_overdue=days_overdue, 
                           days_until=days_until,
                           is_overdue=is_overdue,
                           active_page='patient_payments')

@patient_bp.route('/sessions')
@login_required
def sessions():
    if current_user.role != 'jugador':
        flash('Acceso denegado', 'error')
        return redirect(url_for('main.dashboard'))
    
    sessions = appointment_service.get_patient_appointments(current_user.id, limit=20)
    
    sessions_data = []
    now = datetime.utcnow()
    user_tz = get_user_timezone(current_user)
    
    for s in sessions:
        games = []
        try:
            games = json.loads(s.games) if s.games else []
        except:
            games = []
            
        is_active = False
        if s.status == 'scheduled':
            end_time = s.end_time or (s.start_time + timedelta(hours=1))
            # Strict check: only active if within the scheduled window
            if s.start_time <= now <= end_time:
                is_active = True
        
        s_start_utc = s.start_time.replace(tzinfo=timezone.utc)
        s_start_local = s_start_utc.astimezone(user_tz)

        sessions_data.append({
            'id': s.id,
            'title': s.title,
            'start_time': s_start_local,
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
    # Fallback removed: Do not show random therapist if none assigned

    # Recent messages from admin or assigned therapist
    recent_messages = []
    try:
        recent_q = Message.query.join(User, Message.sender).filter(
            Message.receiver_id == current_user.id,
            or_(User.role.in_(['admin', 'supervisor']), User.id == current_user.assigned_therapist_id)
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

    # Patient sees assigned therapist
    therapist = None
    if current_user.assigned_therapist_id:
        therapist = User.query.get(current_user.assigned_therapist_id)
        
    if not therapist:
        flash('No tienes un terapeuta asignado para enviar mensajes.', 'warning')
        return redirect(url_for('patient.my_therapist'))
    
    messages = Message.query.filter(
        or_(
            (Message.sender_id == current_user.id) & (Message.receiver_id == therapist.id),
            (Message.sender_id == therapist.id) & (Message.receiver_id == current_user.id)
        )
    ).order_by(Message.created_at.asc()).all()
    
    Message.query.filter(
        Message.receiver_id == current_user.id,
        Message.sender_id == therapist.id,
        Message.is_read == False
    ).update({'is_read': True})
    db.session.commit()
    
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
        
    total_sessions = SessionMetrics.query.filter_by(user_id=current_user.id).count()
    last_played_date = db.session.query(func.max(SessionMetrics.date)).filter_by(user_id=current_user.id).scalar()
    last_played = last_played_date.strftime('%d de %B, %Y') if last_played_date else 'Nunca'
    player_stats = {
        'total_sessions': total_sessions,
        'last_played': last_played
    }
    return render_template('patient/profile.html', player_stats=player_stats, active_page='profile')


@patient_bp.route('/api/sessions', methods=['GET'])
@login_required
def api_patient_sessions():
    """Sesiones del paciente como JSON"""
    if current_user.role != 'jugador':
        return jsonify({'success': False, 'error': 'Acceso denegado'}), 403

    start = request.args.get('start')
    end = request.args.get('end')
    
    try:
        start_dt = _parse_datetime(start) if start else None
        end_dt = _parse_datetime(end) if end else None
    except Exception:
        start_dt = None
        end_dt = None

    sessions = appointment_service.get_patient_appointments(current_user.id, start_dt, end_dt)

    results = []
    for s in sessions:
        results.append({
            'id': s.id,
            'title': s.title or 'Sesion',
            'start_time': s.start_time.isoformat() if s.start_time else None,
            'end_time': s.end_time.isoformat() if s.end_time else None,
            'status': s.status,
            'attendance': s.attendance,
            'therapist': s.therapist.username if s.therapist else '',
            'therapist_id': s.therapist_id,
            'notes': s.notes,
            'games': json.loads(s.games) if s.games else [],
        })

    return jsonify({'success': True, 'data': results})


@patient_bp.route('/api/dashboard', methods=['GET'])
@login_required
def api_patient_dashboard():
    """Dashboard del paciente como JSON"""
    if current_user.role != 'jugador':
        return jsonify({'success': False, 'error': 'Acceso denegado'}), 403

    player_stats = dashboard_service.get_player_stats(current_user.id)

    today_start, today_end = get_user_today_utc_range(current_user)
    today_sessions = appointment_service.get_patient_appointments(current_user.id, today_start, today_end)

    sessions_data = []
    now = get_user_now(current_user)
    for s in today_sessions:
        games = []
        try:
            games = json.loads(s.games) if s.games else []
        except:
            pass
        s_start_aware = s.start_time.replace(tzinfo=timezone.utc)
        s_end_val = s.end_time or (s.start_time + timedelta(hours=1))
        s_end_aware = s_end_val.replace(tzinfo=timezone.utc)
        is_active = s.status == 'scheduled' and s_start_aware <= now <= s_end_aware

        sessions_data.append({
            'id': s.id,
            'title': s.title,
            'start_time': s_start_aware.isoformat(),
            'therapist': s.therapist.username if s.therapist else 'Terapeuta',
            'status': s.status,
            'is_active': is_active,
            'games': games,
        })

    today = datetime.utcnow().date()
    payment_status = {
        'is_overdue': False,
        'days_overdue': 0,
        'next_due_date': current_user.payment_due_date.isoformat() if current_user.payment_due_date else None,
        'pending_amount': current_user.payment_amount or 0,
    }
    if current_user.payment_due_date:
        delta = (current_user.payment_due_date - today).days
        if delta < 0:
            payment_status['is_overdue'] = True
            payment_status['days_overdue'] = abs(delta)

    return jsonify({
        'success': True,
        'data': {
            'player_stats': {
                'total_sessions': player_stats['total_sessions'],
                'avg_accuracy': player_stats['avg_accuracy'],
                'avg_time': player_stats['avg_time'],
                'games_played': player_stats['total_sessions'],
            },
            'today_sessions': sessions_data,
            'payment_status': payment_status,
        }
    })


@patient_bp.route('/api/progress', methods=['GET'])
@login_required
def api_patient_progress():
    """Progreso del paciente como JSON"""
    if current_user.role != 'jugador':
        return jsonify({'success': False, 'error': 'Acceso denegado'}), 403

    today = datetime.utcnow().date()
    days = [today - timedelta(days=i) for i in range(6, -1, -1)]
    labels = [d.strftime('%a') for d in days]
    accuracy_data = []
    time_data = []

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
        else:
            avg_acc = 0
            avg_time = 0
        accuracy_data.append(avg_acc)
        time_data.append(avg_time)

    total_sessions = SessionMetrics.query.filter(SessionMetrics.user_id == current_user.id).count()
    overall_avg_acc = db.session.query(func.avg(SessionMetrics.accurracy)).filter(SessionMetrics.user_id == current_user.id).scalar() or 0

    achievements = {
        'first_session': total_sessions >= 1,
        'five_day_streak': False,
        'ten_sessions': total_sessions >= 10,
        'expert': total_sessions >= 50,
    }

    weekly_summary = f"Has completado {total_sessions} sesiones con un promedio de {int(overall_avg_acc)}% de precision."

    return jsonify({
        'success': True,
        'data': {
            'labels': labels,
            'accuracy_data': accuracy_data,
            'time_data': time_data,
            'weekly_summary': weekly_summary,
            'achievements': [
                {'name': 'Primera sesion', 'achieved': achievements['first_session']},
                {'name': '5 dias consecutivos', 'achieved': achievements['five_day_streak']},
                {'name': '10 sesiones', 'achieved': achievements['ten_sessions']},
                {'name': 'Experto', 'achieved': achievements['expert']},
            ],
        }
    })


@patient_bp.route('/api/payments', methods=['GET'])
@login_required
def api_patient_payments():
    """Historial de pagos del paciente como JSON"""
    if current_user.role != 'jugador':
        return jsonify({'success': False, 'error': 'Acceso denegado'}), 403

    payments = Payment.query.filter_by(patient_id=current_user.id).order_by(Payment.date.desc()).all()

    return jsonify({
        'success': True,
        'data': [{
            'id': p.id,
            'amount': p.amount,
            'date': p.date.isoformat() if p.date else None,
            'method': p.method,
            'status': p.status,
        } for p in payments]
    })


@patient_bp.route('/api/my-therapist', methods=['GET'])
@login_required
def api_patient_my_therapist():
    """Terapeuta asignado del paciente como JSON"""
    if current_user.role != 'jugador':
        return jsonify({'success': False, 'error': 'Acceso denegado'}), 403

    therapist = None
    if current_user.assigned_therapist_id:
        therapist = User.query.get(current_user.assigned_therapist_id)

    if not therapist:
        return jsonify({'success': False, 'error': 'No tienes un terapeuta asignado'}), 404

    return jsonify({
        'success': True,
        'data': {
            'id': therapist.id,
            'username': therapist.username,
            'email': therapist.email,
            'phone': therapist.phone,
        }
    })


@patient_bp.route('/api/messages', methods=['GET'])
@login_required
def api_patient_messages():
    """Mensajes del paciente como JSON"""
    if current_user.role != 'jugador':
        return jsonify({'success': False, 'error': 'Acceso denegado'}), 403

    therapist = None
    if current_user.assigned_therapist_id:
        therapist = User.query.get(current_user.assigned_therapist_id)

    if not therapist:
        return jsonify({'success': True, 'messages': []})

    messages = Message.query.filter(
        or_(
            (Message.sender_id == current_user.id) & (Message.receiver_id == therapist.id),
            (Message.sender_id == therapist.id) & (Message.receiver_id == current_user.id)
        )
    ).order_by(Message.created_at.asc()).all()

    return jsonify({
        'success': True,
        'messages': [{
            'id': m.id,
            'sender_id': m.sender_id,
            'sender_name': m.sender.username if m.sender else '',
            'body': m.body,
            'file_url': m.file_url,
            'file_type': m.attachment_type,
            'created_at': m.created_at.isoformat() if m.created_at else None,
            'is_read': m.is_read,
            'is_from_patient': m.sender_id == current_user.id,
        } for m in messages]
    })


@patient_bp.route('/api/messages/send', methods=['POST'])
@login_required
@csrf.exempt
def api_patient_send_message():
    """Paciente manda mensaje a su terapeuta"""
    if current_user.role != 'jugador':
        return jsonify({'success': False, 'error': 'Acceso denegado'}), 403

    if request.is_json:
        data = request.get_json()
    else:
        data = request.form.to_dict()

    receiver_id = data.get('receiver_id')
    body = sanitize_text(data.get('body', ''))

    if not receiver_id:
        return jsonify({'success': False, 'error': 'receiver_id requerido'}), 400

    if not body and 'file' not in request.files:
        return jsonify({'success': False, 'error': 'El mensaje no puede estar vacío'}), 400

    receiver = User.query.get(receiver_id)
    if not receiver:
        return jsonify({'success': False, 'error': 'Destinatario no encontrado'}), 404

    attachment_path = None
    attachment_type = None

    if 'file' in request.files:
        file = request.files['file']
        if file and file.filename:
            filename = secure_filename(file.filename)
            unique_filename = f"{uuid.uuid4().hex}_{filename}"

            ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
            if ext in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
                attachment_type = 'image'
            elif ext in ['mp4', 'mov', 'webm']:
                attachment_type = 'video'
            elif ext in ['mp3', 'wav', 'ogg', 'm4a']:
                attachment_type = 'audio'
            else:
                attachment_type = 'file'

            upload_folder = os.path.join(current_app.instance_path, 'uploads', 'messages')
            os.makedirs(upload_folder, exist_ok=True)
            file.save(os.path.join(upload_folder, unique_filename))
            attachment_path = unique_filename

    msg = Message(
        sender_id=current_user.id,
        receiver_id=receiver_id,
        body=body,
        attachment_path=attachment_path,
        attachment_type=attachment_type,
    )
    db.session.add(msg)
    db.session.commit()

    notification_service.create_notification(
        user_id=receiver_id,
        title=f'Nuevo mensaje de {current_user.username}',
        message=body or 'Has recibido un archivo adjunto',
        notif_type='message',
    )

    try:
        email_service = EmailService()
        email_service.send_new_message_email(
            receiver.email,
            receiver.username,
            current_user.username,
            (body or "Has recibido un archivo adjunto")[:100] + ('...' if body and len(body) > 100 else '')
        )
    except Exception:
        pass

    return jsonify({
        'success': True,
        'message_id': msg.id,
        'created_at': msg.created_at.isoformat() if msg.created_at else None,
        'attachment_type': attachment_type,
    })


@patient_bp.route('/api/profile/update', methods=['POST'])
@login_required
def api_patient_update_profile():
    """Actualiza perfil del paciente vía JSON"""
    if current_user.role != 'jugador':
        return jsonify({'success': False, 'error': 'Acceso denegado'}), 403

    data = request.get_json(silent=True) or {}

    if 'username' in data and data['username']:
        current_user.username = data['username'].strip()
    if 'phone' in data:
        current_user.phone = data['phone']
    if 'new_password' in data and data['new_password']:
        current_user.password = bcrypt.generate_password_hash(data['new_password']).decode('utf-8')

    db.session.commit()
    return jsonify({'success': True, 'message': 'Perfil actualizado'})

