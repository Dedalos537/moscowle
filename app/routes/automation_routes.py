"""Avisos automáticos a padres (recordatorios de sesión y cobranza): interruptor global, modo prueba y prueba de envío."""

from datetime import datetime, timedelta

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.extensions import db
from app.models import MessageLog, User
from app.services import automation_settings
from app.services.messaging import MessagingService
from app.utils.decorators import admin_required, admin_write_required

automation_bp = Blueprint('automation', __name__, url_prefix='/api/automation')


@automation_bp.route('/settings', methods=['GET'])
@jwt_required()
@admin_required
def get_settings():
    since = datetime.utcnow() - timedelta(hours=24)
    rows = (
        db.session.query(MessageLog.channel, MessageLog.status, db.func.count(MessageLog.id))
        .filter(MessageLog.trigger == 'automated', MessageLog.created_at >= since)
        .group_by(MessageLog.channel, MessageLog.status)
        .all()
    )
    last_24h = {}
    for channel, status, n in rows:
        last_24h.setdefault(channel, {})[status] = n
    return jsonify(
        {**automation_settings.get(), 'pilot_patient': automation_settings.pilot_patient(), 'last_24h': last_24h}
    )


@automation_bp.route('/settings', methods=['PUT'])
@jwt_required()
@admin_write_required
def update_settings():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({'error': 'Cuerpo JSON inválido'}), 400
    cfg, errors = automation_settings.update(data, user_id=int(get_jwt_identity()))
    if errors:
        return jsonify({'error': 'Revisa los campos marcados', 'fields': errors}), 400
    return jsonify({**cfg, 'pilot_patient': automation_settings.pilot_patient()})


@automation_bp.route('/patients', methods=['GET'])
@jwt_required()
@admin_required
def search_patients():
    """Pacientes para elegir el piloto: se muestra a qué número le llegaría el aviso."""
    q = (request.args.get('q') or '').strip()
    query = User.query.filter(User.role == 'jugador', User.is_active.is_(True))
    if q:
        query = query.filter(db.or_(User.username.ilike(f'%{q}%'), User.email.ilike(f'%{q}%')))
    rows = query.order_by(User.username.asc()).limit(20).all()
    return jsonify(
        [
            {
                'id': p.id,
                'username': p.username,
                'phone': MessagingService.resolve_phone(p) or None,
            }
            for p in rows
        ]
    )


@automation_bp.route('/test', methods=['POST'])
@jwt_required()
@admin_write_required
def send_test():
    """Envía un mensaje de prueba REAL al apoderado de un paciente (por defecto, el piloto)."""
    data = request.get_json(silent=True) or {}
    channel = (data.get('channel') or 'whatsapp').lower()
    if channel not in ('whatsapp', 'sms', 'email'):
        return jsonify({'error': 'El canal debe ser whatsapp, sms o email'}), 400
    patient_id = data.get('patient_id') or automation_settings.get()['pilot_patient_id']
    patient = db.session.get(User, int(patient_id)) if str(patient_id or '').isdigit() else None
    if not patient or patient.role != 'jugador':
        return jsonify({'error': 'Elige un paciente para la prueba'}), 400
    if (data.get('kind') or 'session') == 'debt':
        # Cobranza de prueba: usa las plantillas configuradas con datos de ejemplo, para ver cómo llegará de verdad.
        from app.services.sms_whatsapp_service import SMSWhatsAppService

        templates = SMSWhatsAppService()
        args = (patient.username, 120, datetime.now().strftime('%d/%m/%Y'), 3)
        text = (
            templates._get_whatsapp_template_body(*args)
            if channel == 'whatsapp'
            else templates._get_sms_template_body(*args)
        )
        text = f'[PRUEBA] {text}'
    else:
        text = (
            f'Hola {patient.username}, este es un mensaje de PRUEBA del Centro Juan Pablo II. '
            'Si lo recibiste, los avisos automáticos funcionan. No necesitas responder.'
        )
    if channel == 'email':
        address = MessagingService.resolve_email(patient)
        if not address:
            return jsonify({'error': 'El paciente y su apoderado no tienen correo registrado'}), 422
        ok = MessagingService.send_email(patient, 'Prueba · Centro Juan Pablo II', text)
        return jsonify(
            {
                'status': 'sent' if ok else 'failed',
                'reason': None if ok else 'El servidor de correo no lo aceptó',
                'phone': address,
                'patient': patient.username,
            }
        ), (200 if ok else 502)
    result = MessagingService().send_to_patient(
        patient.id,
        text,
        channel=channel,
        sent_by_id=int(get_jwt_identity()),
        trigger='manual',
        enforce_repeat_check=False,
    )
    status = result.get('status')
    code = 200 if status == 'sent' else (422 if status == 'skipped' else 502)
    return jsonify(
        {'status': status, 'reason': result.get('reason'), 'phone': result.get('phone'), 'patient': patient.username}
    ), code
