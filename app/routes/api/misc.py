from flask import Blueprint, request, jsonify, current_app, url_for
from flask_login import login_required, current_user
from app.models import db, User, Notification, Appointment, Message, Game, SessionMetrics, SessionImage, ContactMessage, Sede, Payment
from app.services.appointment_service import AppointmentService
from app.services.game_service import GameService
from app.services.admin_service import AdminService
from app.services.notification_service import NotificationService
from app.services.patient_service import PatientService
from app.services.dashboard_service import DashboardService
from app.services.report_service import ReportService
import json, os, time, warnings
warnings.filterwarnings('ignore', message='.*google.generativeai.*ended.*')
try:
    import google.generativeai as genai
except ImportError:
    genai = None
try:
    from groq import Groq
except ImportError:
    Groq = None
try:
    import ollama
    _ollama_client = ollama.Client(host='http://127.0.0.1:11434')
    _ollama_client.list()
except Exception:
    _ollama_client = None
from app.services.google_drive_service import GoogleDriveService
from app.services.ai_service import predict_level, start_async_training
from app.utils import get_user_today_utc_range, get_user_now, localize_datetime_for_display, get_user_timezone
from app.schemas import AssignTherapistSchema, UpdateUserSchema, SendMessageSchema
from app.extensions import bcrypt, limiter, csrf
from app.services.email_service import EmailService
from app.services.financial_service import FinancialService
from app.utils.api_helpers import api_response
from app.services.availability_service import AvailabilityService
from datetime import datetime, timedelta, timezone
import json
import os
import uuid
from werkzeug.utils import secure_filename
import requests
from sqlalchemy import or_, func


from app.routes.api import api_bp


appointment_service = AppointmentService()
game_service = GameService()
admin_service = AdminService()
notification_service = NotificationService()
patient_service = PatientService()
dashboard_service = DashboardService()
report_service = ReportService()
drive_service = GoogleDriveService()
fs = FinancialService()

LIMA_TZ = timezone(timedelta(hours=-5))

def _parse_json(raw):
    if '```json' in raw: raw = raw.split('```json')[1].split('```')[0]
    elif '```' in raw: raw = raw.split('```')[1].split('```')[0]
    start = raw.find('{'); end = raw.rfind('}')
    if start != -1 and end != -1: raw = raw[start:end+1]
    try: return json.loads(raw)
    except Exception: return None

def analyze_contact_message_ai(name, email, message, service_interest):
    result = {'sentiment': 'neutral', 'detected_intent': 'consulta', 'suggested_response': '', 'confidence': 'media', 'provider': None}
    prompt = f"""Analiza este mensaje de contacto de un cliente potencial y responde SOLO con JSON válido:
Nombre: {name}
Email: {email}
Mensaje: {message}
Servicio de interés: {service_interest or 'No especificado'}
Responde con este JSON exacto (sin markdown):
{{"sentiment": "positivo"|"neutral"|"negativo", "detected_intent": "agendar_cita"|"informacion"|"consulta"|"queja"|"seguimiento", "suggested_response": "texto cortés de respuesta sugerida", "confidence": "alta"|"media"|"baja"}}"""
    providers = []
    if _ollama_client:
        providers.append(('ollama', lambda: _ollama_client.chat(model='llama3.2', messages=[{'role': 'user', 'content': prompt}], options={'temperature': 0.0})['message']['content']))
    if genai and os.environ.get('GEMINI_API_KEY'):
        providers.append(('gemini', lambda: (genai.configure(api_key=os.environ['GEMINI_API_KEY']), genai.GenerativeModel('gemini-1.5-flash').generate_content(prompt).text)[1]))
    if Groq and os.environ.get('GROQ_API_KEY'):
        providers.append(('groq', lambda: Groq(api_key=os.environ['GROQ_API_KEY']).chat.completions.create(model='llama-3.2-3b-preview', messages=[{'role': 'user', 'content': prompt}], temperature=0.0, max_tokens=300).choices[0].message.content))
    for name, fn in providers:
        try:
            t0 = time.time()
            raw = fn()
            parsed = _parse_json(raw)
            if parsed:
                parsed['provider'] = name
                parsed['response_time'] = round(time.time() - t0, 2)
                result.update(parsed)
                break
        except Exception:
            continue
    return json.dumps(result, ensure_ascii=False)

def _parse_datetime(value):
    """Parsea fechas como sea. Sin timezone asume Lima (UTC-5). Devuelve UTC pa la BD."""
    if not value:
        return None
    try:
        if value.endswith('Z'):
            value = value[:-1] + '+00:00'
        dt = datetime.fromisoformat(value)
        if dt.tzinfo:
            return dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt.replace(tzinfo=LIMA_TZ).astimezone(timezone.utc).replace(tzinfo=None)
    except Exception:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(value, fmt)
                return dt.replace(tzinfo=LIMA_TZ).astimezone(timezone.utc).replace(tzinfo=None)
            except Exception:
                continue
    return None

@api_bp.route('/time', methods=['GET'])
def api_time():
    now_local = datetime.now()
    now_utc = datetime.utcnow()
    return jsonify({
        'server_time_local': now_local.isoformat(),
        'server_time_utc': now_utc.isoformat(),
        'timezone': 'America/Lima',
        'utc_offset_minutes': -300,
        'is_dst': False,
    })

@api_bp.route('/therapist/insights')
@login_required
def therapist_insights():
    if current_user.role != 'terapista':
        return jsonify({'error': 'Acceso denegado'}), 403
    try:
        data = dashboard_service.get_therapist_insights(current_user)
        return jsonify(data)
    except Exception as e:
        current_app.logger.error(f"Error in therapist_insights: {str(e)}")
        return jsonify({"error": str(e), "data": []}), 500

@api_bp.route('/patients')
@login_required
def api_patients():
    if current_user.role not in ('terapista', 'admin', 'supervisor'):
        return jsonify({'error': 'Acceso denegado'}), 403
    therapist_id = request.args.get('therapist_id')
    if current_user.role == 'terapista':
        patients = patient_service.get_therapist_patients(current_user.id)
    elif therapist_id and current_user.role in ('admin', 'supervisor'):
        try:
            from app.models import User
            t_user = User.query.get(int(therapist_id))
            if t_user and t_user.role == 'terapista':
                patients = patient_service.user_repo.get_all_patients_by_therapist(int(therapist_id))
            else:
                patients = []
        except:
            patients = []
    else:
        from app.models import User
        patients = User.query.filter_by(role='jugador', is_active=True).order_by(User.username.asc()).all()
    return jsonify([{'id': p.id, 'username': p.username, 'email': p.email} for p in patients])

@api_bp.route('/ai/gemini', methods=['POST'])
@limiter.limit("10 per minute")
@login_required
def gemini_proxy():
    if current_user.role not in ('terapista', 'admin', 'supervisor'):
        return jsonify({'error': 'Acceso denegado'}), 403
    api_key = current_app.config.get('GEMINI_API_KEY')
    payload = request.get_json() or {}
    prompt = payload.get('prompt')
    context = payload.get('context')
    if not prompt:
        return jsonify({'error': 'Falta el prompt'}), 400
    if not api_key:
        acc = (context or {}).get('accuracy') or 0
        avg = (context or {}).get('avg_time') or 0
        _, label = predict_level(acc, avg)
        return jsonify({'status': 'no_external', 'recommendation': label})
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
            return jsonify({'error': 'Gemini falló', 'details': resp.text}), 500
    except Exception as e:
        return jsonify({'error': 'Gemini no respondió', 'detail': str(e)}), 500

@api_bp.route('/messages/send', methods=['POST'])
@login_required
@csrf.exempt
def send_message():
    if request.is_json:
        data = request.get_json()
    else:
        data = request.form.to_dict()

    receiver_id = data.get('receiver_id')
    body = data.get('body', '')
    subject = data.get('subject')
    
    if not receiver_id:
        return jsonify({'success': False, 'message': 'Datos incompletos'}), 400
    
    receiver = User.query.get(receiver_id)
    if not receiver:
        return jsonify({'success': False, 'message': 'Destinatario no encontrado'}), 404
    
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
            
            # Storing filename only, path is managed by frontend/template
            attachment_path = unique_filename

    if not body and not attachment_path:
         return jsonify({'success': False, 'message': 'El mensaje no puede estar vacío'}), 400
    
    message = Message(
        sender_id=current_user.id,
        receiver_id=receiver_id,
        subject=subject,
        body=body,
        attachment_path=attachment_path,
        attachment_type=attachment_type
    )
    db.session.add(message)
    db.session.commit()
    
    notification_service.create_notification(
        user_id=receiver_id,
        title=f'Nuevo mensaje de {current_user.username}',
        message=body or 'Has recibido un archivo adjunto',
        notif_type='message',
        link=url_for('main.messages_list')
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
        pass # Non-critical
    
    return jsonify({
        'success': True,
        'message_id': message.id,
        'created_at': message.created_at.isoformat(),
        'attachment_path': attachment_path,
        'attachment_type': attachment_type
    })

@api_bp.route('/messages/unread-count')
@login_required
def unread_messages_count():
    count = Message.query.filter_by(receiver_id=current_user.id, is_read=False).count()
    return jsonify({'count': count})

@api_bp.route('/public/contact', methods=['POST'])
@csrf.exempt
def contact_message():
    data = request.get_json() or {}
    required_fields = ['first_name', 'last_name', 'email', 'message']
    for field in required_fields:
        if field not in data or not data[field]:
            return jsonify({'error': f'Falta el campo {field}'}), 400

    new_msg = ContactMessage(
        first_name=data.get('first_name'),
        last_name=data.get('last_name'),
        email=data.get('email'),
        phone=data.get('phone'),
        subject=data.get('subject', 'Consulta Web'),
        message=data.get('message'),
        service_interest=data.get('service_interest'),
        urgency=data.get('urgency', 'medium'),
        status='unread'
    )
    
    try:
        analysis = analyze_contact_message_ai(
            f"{data.get('first_name')} {data.get('last_name')}",
            data.get('email', ''),
            data.get('message', ''),
            data.get('service_interest')
        )
        new_msg.ai_analysis = analysis
    except Exception as e:
        current_app.logger.warning(f"AI analysis failed for contact message: {e}")
        new_msg.ai_analysis = json.dumps({'sentiment': 'neutral', 'detected_intent': 'consulta', 'error': str(e)[:100]})

    try:
        db.session.add(new_msg)
        db.session.commit()

        admins = User.query.filter_by(role='admin', is_active=True).all()
        for admin in admins:
            try:
                notification_service.create_notification(
                    admin.id,
                    f"Nuevo contacto: {data.get('first_name')} {data.get('last_name')} - {data.get('subject', 'Consulta Web')[:80]}",
                    title='Nuevo mensaje de contacto',
                    notif_type='message',
                    link=''
                )
            except Exception:
                pass

        return jsonify({'message': '¡Mensaje recibido! Te contactamos pronto.'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@api_bp.route('/therapist/dashboard', methods=['GET'])
@login_required
def get_therapist_dashboard():
    if current_user.role != 'terapista':
        return jsonify({'error': 'Unauthorized'}), 403

    from datetime import datetime, timedelta
    from app.models import Appointment, User, SessionAudit
    from sqlalchemy import func as sqlfunc
    from app.extensions import db

    now = datetime.now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = today + timedelta(days=1)
    
    # 1. Agenda de Hoy
    today_sessions = Appointment.query.filter(
        Appointment.therapist_id == current_user.id,
        Appointment.start_time >= today,
        Appointment.start_time < tomorrow,
        Appointment.status != 'cancelled'
    ).order_by(Appointment.start_time).all()

    agenda = []
    next_session = None
    
    for s in today_sessions:
        patient = User.query.get(s.patient_id) if s.patient_id else None
        is_current = s.start_time <= now and (s.end_time is None or s.end_time > now)
        session_info = {
            'id': s.id,
            'title': s.title or 'Sesión de Terapia',
            'patient': patient.username if patient else 'N/A',
            'start': s.start_time.strftime('%I:%M %p'),
            'location': s.location or '',
            'status': s.status,
            'is_current': is_current
        }
        agenda.append(session_info)
        if not next_session and (is_current or s.start_time > now):
            next_session = session_info

    # 2. Temas de la Sesión (Planned Text)
    planned_text = ""
    session_progress = 0
    avg_compliance = 0
    
    # Audit compliance data
    try:
        avg_cmp = db.session.query(sqlfunc.avg(SessionAudit.audit_score)).join(
            Appointment, SessionAudit.appointment_id == Appointment.id
        ).filter(
            Appointment.therapist_id == current_user.id,
            SessionAudit.audit_score.isnot(None)
        ).scalar()
        avg_compliance = float(avg_cmp) if avg_cmp else 0.0
    except Exception:
        pass

    if next_session:
        audit = SessionAudit.query.filter_by(appointment_id=next_session['id']).first()
        if audit and audit.planned_text:
            planned_text = audit.planned_text
            session_progress = int(audit.audit_score) if audit.audit_score else 0

    return jsonify({
        'success': True,
        'data': {
            'next_session': next_session,
            'agenda': agenda,
            'planned_text': planned_text,
            'session_progress': session_progress,
            'avg_compliance': avg_compliance,
            'total_students': len(set([s.patient_id for s in today_sessions]))
        }
    })

