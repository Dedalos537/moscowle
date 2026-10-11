import contextlib
import json
from datetime import UTC, datetime, timedelta

from flask import Blueprint, jsonify, request
from sqlalchemy import func, or_

from app.auth_compat import current_user, login_required
from app.extensions import bcrypt, csrf
from app.models import Message, Payment, SessionMetrics, User, db
from app.services.appointment_service import AppointmentService
from app.services.dashboard_service import DashboardService
from app.services.email_service import EmailService
from app.services.notification_service import NotificationService
from app.utils import get_user_now, get_user_today_utc_range

patient_bp = Blueprint('patient', __name__, url_prefix='/patient')
dashboard_service = DashboardService()
appointment_service = AppointmentService()
notification_service = NotificationService()


def _parse_datetime(value):
    """Parsea datetime ISO o naive"""
    if not value:
        return None
    try:
        if value.endswith('Z'):
            value = value[:-1] + '+00:00'
        dt = datetime.fromisoformat(value)
        if dt.tzinfo:
            dt = dt.astimezone(UTC).replace(tzinfo=None)
        return dt
    except Exception:
        for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d'):
            try:
                return datetime.strptime(value, fmt)
            except Exception:  # noqa: S112 - fallo esperado y sin consecuencia, se ignora a proposito
                continue
    return None


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
        results.append(
            {
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
            }
        )

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
        with contextlib.suppress(BaseException):
            games = json.loads(s.games) if s.games else []
        s_start_aware = s.start_time.replace(tzinfo=UTC)
        s_end_val = s.end_time or (s.start_time + timedelta(hours=1))
        s_end_aware = s_end_val.replace(tzinfo=UTC)
        is_active = s.status == 'scheduled' and s_start_aware <= now <= s_end_aware

        sessions_data.append(
            {
                'id': s.id,
                'title': s.title,
                'start_time': s_start_aware.isoformat(),
                'therapist': s.therapist.username if s.therapist else 'Terapeuta',
                'status': s.status,
                'is_active': is_active,
                'games': games,
            }
        )

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

    return jsonify(
        {
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
            },
        }
    )


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
            SessionMetrics.user_id == current_user.id, SessionMetrics.date >= start_dt, SessionMetrics.date < end_dt
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
    overall_avg_acc = (
        db.session.query(func.avg(SessionMetrics.accurracy)).filter(SessionMetrics.user_id == current_user.id).scalar()
        or 0
    )

    achievements = {
        'first_session': total_sessions >= 1,
        'five_day_streak': False,
        'ten_sessions': total_sessions >= 10,
        'expert': total_sessions >= 50,
    }

    weekly_summary = (
        f'Has completado {total_sessions} sesiones con un promedio de {int(overall_avg_acc)}% de precision.'
    )

    return jsonify(
        {
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
            },
        }
    )


@patient_bp.route('/api/payments', methods=['GET'])
@login_required
def api_patient_payments():
    """Historial de pagos del paciente como JSON"""
    if current_user.role != 'jugador':
        return jsonify({'success': False, 'error': 'Acceso denegado'}), 403

    payments = Payment.query.filter_by(patient_id=current_user.id).order_by(Payment.date.desc()).all()

    return jsonify(
        {
            'success': True,
            'data': [
                {
                    'id': p.id,
                    'amount': p.amount,
                    'date': p.date.isoformat() if p.date else None,
                    'method': p.method,
                    'status': p.status,
                }
                for p in payments
            ],
        }
    )


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

    return jsonify(
        {
            'success': True,
            'data': {
                'id': therapist.id,
                'username': therapist.username,
                'email': therapist.email,
                'phone': therapist.phone,
            },
        }
    )


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

    messages = (
        Message.query.filter(
            or_(
                (Message.sender_id == current_user.id) & (Message.receiver_id == therapist.id),
                (Message.sender_id == therapist.id) & (Message.receiver_id == current_user.id),
            )
        )
        .order_by(Message.created_at.asc())
        .all()
    )

    return jsonify(
        {
            'success': True,
            'messages': [
                {
                    'id': m.id,
                    'sender_id': m.sender_id,
                    'sender_name': m.sender.username if m.sender else '',
                    'body': m.body,
                    'file_url': m.file_url,
                    'file_type': m.attachment_type,
                    'created_at': m.created_at.isoformat() if m.created_at else None,
                    'is_read': m.is_read,
                    'is_from_patient': m.sender_id == current_user.id,
                }
                for m in messages
            ],
        }
    )


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
    body = data.get('body', '')

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
            from app.services import attachments

            try:
                attachment_path, attachment_type = attachments.save(file)
            except attachments.AttachmentError as exc:
                return jsonify({'success': False, 'error': str(exc)}), 400

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
            (body or 'Has recibido un archivo adjunto')[:100] + ('...' if body and len(body) > 100 else ''),
        )
    except Exception:  # noqa: S110 - fallo esperado y sin consecuencia, se ignora a proposito
        pass

    return jsonify(
        {
            'success': True,
            'message_id': msg.id,
            'created_at': msg.created_at.isoformat() if msg.created_at else None,
            'attachment_type': attachment_type,
        }
    )


@patient_bp.route('/api/profile/update', methods=['POST'])
@login_required
def api_patient_update_profile():
    """Actualiza perfil del paciente vía JSON"""
    if current_user.role != 'jugador':
        return jsonify({'success': False, 'error': 'Acceso denegado'}), 403

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
        return jsonify({'success': False, 'error': 'Zona horaria inválida'}), 400

    if 'username' in data and data['username']:
        current_user.username = data['username'].strip()
    if 'phone' in data:
        current_user.phone = data['phone']
    if timezone:
        current_user.timezone = timezone
    if 'new_password' in data and data['new_password']:
        current_user.password = bcrypt.generate_password_hash(data['new_password']).decode('utf-8')

    db.session.commit()
    return jsonify(
        {
            'success': True,
            'message': 'Perfil actualizado',
            'timezone': getattr(current_user, 'timezone', None) or 'America/Lima',
        }
    )
