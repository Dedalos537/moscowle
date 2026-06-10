from app.routes.api._shared import (
    db, User, Notification, Appointment, Message, Game, SessionMetrics,
    SessionImage, ContactMessage, Sede, Payment, json, os, time, warnings,
    AppointmentService, GameService, AdminService, NotificationService,
    PatientService, DashboardService, ReportService, GoogleDriveService,
    FinancialService, genai, Groq, _ollama_client, predict_level,
    start_async_training, get_user_today_utc_range, get_user_now,
    localize_datetime_for_display, get_user_timezone, bcrypt, limiter, csrf,
    EmailService, api_response, AvailabilityService, requests, or_, func,
    appointment_service, game_service, admin_service, notification_service,
    patient_service, dashboard_service, report_service, drive_service, fs,
    _parse_json, _parse_datetime, analyze_contact_message_ai,
    AssignTherapistSchema, UpdateUserSchema, SendMessageSchema,
    uuid, secure_filename, datetime, timedelta, timezone,
    login_required, current_user, request, jsonify, current_app, url_for,
)
from app.routes.api import api_bp

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

