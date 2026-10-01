"""CRM de contactos: quien recibe avisos, campanas e historial.

Todas las rutas exigen sesion de admin o supervisor, salvo el estado del
puente de WhatsApp que tambien lo exigen porque revela el numero del centro.
"""
import logging
import time
from datetime import datetime, timedelta

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request

from app.extensions import db
from app.models import User
from app.models.campaign import Campaign, CampaignSend
from app.models.message_log import MessageLog
from app.models.message_template import MessageTemplate
from app.services.messaging import MessagingService, contact_summary

logger = logging.getLogger(__name__)

crm_bp = Blueprint('crm', __name__, url_prefix='/api/crm')


@crm_bp.before_request
def _require_admin():
    """admin o supervisor. Sin esto, cualquier paciente logueado podria
    leer el numero de salida del centro y el historial de avisos."""
    try:
        verify_jwt_in_request(locations=['cookies', 'headers'])
        user = User.query.get(int(get_jwt_identity()))
    except Exception:
        return jsonify({'error': 'No autenticado'}), 401
    if not user or user.role not in ('admin', 'supervisor'):
        return jsonify({'error': 'No autorizado'}), 403
    request.user = user


def _service():
    return MessagingService(current_app.config)


def full_name(patient):
    """Nombre y apellido, o el username si estan vacios."""
    parts = [part for part in ((patient.first_name or '').strip(), (patient.last_name or '').strip()) if part]
    return ' '.join(parts) or patient.username


# ------------------------------------------------------------- contactos


@crm_bp.route('/contacts', methods=['GET'])
def list_contacts():
    """Lista pacientes con su estado de contacto.

    Por defecto solo los activos: son los que reciben avisos. Con
    ?all=1 entra tambien los dados de baja, que es como se audita a quien
    se le dejo de escribir.
    """
    q = User.query.filter_by(role='jugador')

    if request.args.get('all') != '1':
        q = q.filter(User.is_active.is_(True))

    if request.args.get('without_phone') == '1':
        q = q.filter(
            (User.phone.is_(None)) | (User.phone == '')
            | (User.guardian_contact.is_(None)) | (User.guardian_contact == '')
        )

    if request.args.get('q'):
        term = f'%{request.args["q"]}%'
        q = q.filter(
            (User.username.ilike(term))
            | (User.first_name.ilike(term))
            | (User.last_name.ilike(term))
            | (User.phone.ilike(term))
        )

    patients = q.order_by(User.first_name, User.last_name).all()
    svc = _service()

    rows = []
    for p in patients:
        ok, reason = svc.check_contactable(p, 'whatsapp')
        rows.append(
            {
                'id': p.id,
                'username': p.username,
                'name': f'{(p.first_name or "").strip()} {(p.last_name or "").strip()}'.strip() or p.username,
                'phone': p.phone,
                'guardian_contact': p.guardian_contact,
                'guardian_name': p.guardian_name,
                'effective_phone': svc.resolve_phone(p),
                'is_active': p.is_active,
                'account_status': p.account_status,
                'contactable': ok,
                'reason': reason,
                'last_message_at': (
                    db.session.query(db.func.max(MessageLog.created_at))
                    .filter(MessageLog.patient_id == p.id)
                    .scalar()
                ),
            }
        )

    return jsonify(
        {
            'summary': contact_summary(),
            'whatsapp': _whatsapp_status(),
            'contacts': rows,
        }
    )


def _whatsapp_status():
    from app.services.whatsapp_service import whatsapp_service

    return whatsapp_service.status()


@crm_bp.route('/contacts/<int:patient_id>/toggle', methods=['POST'])
def toggle_contact(patient_id):
    """Activa o desactiva el contacto de un paciente.

    Desactivar la cuenta es lo que corta los avisos: el servicio de envio
    lo comprueba antes de cada mensaje, no solo la interfaz.
    """
    patient = User.query.get(patient_id)
    if not patient:
        return jsonify({'error': 'Paciente no encontrado'}), 404

    data = request.get_json(silent=True) or {}
    activate = data.get('is_active')
    if activate is None:
        activate = not patient.is_active

    patient.is_active = bool(activate)
    patient.account_status = 'active' if activate else 'inactive'
    db.session.commit()

    svc = _service()
    ok, reason = svc.check_contactable(patient, 'whatsapp')
    logger.info(
        'Contacto de %s (id %d) -> %s por %s',
        patient.username, patient.id, 'activo' if activate else 'inactivo', request.user.username,
    )
    return jsonify(
        {
            'patient_id': patient.id,
            'is_active': patient.is_active,
            'contactable': ok,
            'reason': reason,
        }
    )


# ------------------------------------------------------------ plantillas


@crm_bp.route('/templates', methods=['GET', 'POST'])
def templates():
    if request.method == 'GET':
        rows = MessageTemplate.query.order_by(MessageTemplate.channel, MessageTemplate.key).all()
        return jsonify({'templates': [t.to_dict() for t in rows]})

    data = request.get_json(silent=True) or {}
    key = (data.get('key') or '').strip()
    channel = (data.get('channel') or '').strip()
    body = (data.get('body') or '').strip()
    label = (data.get('label') or key).strip()

    if not key or not channel or not body:
        return jsonify({'error': 'key, channel y body son obligatorios'}), 400
    if channel not in ('sms', 'whatsapp'):
        return jsonify({'error': 'El canal debe ser sms o whatsapp'}), 400

    # Se rechazan marcadores que no son {nombre}: una llave suelta rompe el
    # render en el envio y el mensaje se pierde entero.
    import re

    bad = [m for m in re.findall(r'\{([^{}]*)\}', body) if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', m)]
    if bad:
        return jsonify({'error': f'Marcadores invalidos: {", ".join(bad)}'}), 400

    tpl = MessageTemplate.query.filter_by(key=key, channel=channel).first()
    if not tpl:
        tpl = MessageTemplate(key=key, channel=channel, label=label, body=body)
        db.session.add(tpl)
    else:
        tpl.body = body
        tpl.label = label
        tpl.updated_by_id = request.user.id
    tpl.is_active = bool(data.get('is_active', True))
    db.session.commit()

    return jsonify({'template': tpl.to_dict()}), 200


@crm_bp.route('/templates/preview', methods=['POST'])
def preview_template():
    """Muestra como queda el texto con datos de ejemplo, sin enviar nada."""
    data = request.get_json(silent=True) or {}
    svc = _service()
    body = data.get('body', '')
    context = data.get('context') or {}
    defaults = {'nombre': 'María', 'monto': '380.00', 'cuota': '3 de 12', 'fecha': '15/10/2025', 'dias_atraso': '5'}
    merged = {**defaults, **context}
    return jsonify({'rendered': svc.render(body, merged), 'context': merged})


# -------------------------------------------------------------- campanas


@crm_bp.route('/campaigns', methods=['GET', 'POST'])
def campaigns():
    if request.method == 'GET':
        rows = Campaign.query.order_by(Campaign.created_at.desc()).all()
        return jsonify({'campaigns': [c.to_dict() for c in rows]})

    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    channel = (data.get('channel') or '').strip()
    message = (data.get('message') or '').strip()

    if not name or not message:
        return jsonify({'error': 'name y message son obligatorios'}), 400
    if channel not in ('sms', 'whatsapp'):
        return jsonify({'error': 'El canal debe ser sms o whatsapp'}), 400

    svc = _service()
    # Se arma el texto final en la base de datos: las campanas no cambian
    # solas si despues se edita la plantilla.
    body = data.get('message')
    if data.get('render', True):
        body = svc.render(body, {'nombre': '{nombre}'})

    campaign = Campaign(
        name=name,
        channel=channel,
        message=body,
        template_key=data.get('template_key'),
        segment=data.get('segment', 'active'),
        status='draft',
        created_by_id=request.user.id,
    )
    db.session.add(campaign)
    db.session.commit()

    if data.get('patient_ids'):
        patients = User.query.filter(User.id.in_(data['patient_ids']), User.role == 'jugador').all()
    else:
        patients = svc.build_recipients(campaign)

    prep = svc.prepare_campaign(campaign, patients)
    return jsonify({'campaign': campaign.to_dict(), **prep}), 201


@crm_bp.route('/campaigns/<int:campaign_id>/recipients', methods=['GET'])
def campaign_recipients(campaign_id):
    campaign = Campaign.query.get(campaign_id)
    if not campaign:
        return jsonify({'error': 'Campana no encontrada'}), 404

    rows = (
        db.session.query(CampaignSend, User)
        .join(User, User.id == CampaignSend.patient_id)
        .filter(CampaignSend.campaign_id == campaign_id)
        .order_by(CampaignSend.status, User.first_name)
        .all()
    )
    return jsonify(
        {
            'campaign': campaign.to_dict(),
            'recipients': [
                {
                    **cs.to_dict(),
                    'name': full_name(u),
                }
                for cs, u in rows
            ],
        }
    )


@crm_bp.route('/campaigns/<int:campaign_id>/send', methods=['POST'])
def send_campaign(campaign_id):
    """Lanza el envio. Con ?dry_run=1 solo calcula a quien le tocaria."""
    campaign = Campaign.query.get(campaign_id)
    if not campaign:
        return jsonify({'error': 'Campana no encontrada'}), 404
    if campaign.status in ('sent', 'cancelled'):
        return jsonify({'error': f'La campana ya esta en estado {campaign.status}'}), 400

    svc = _service()
    data = request.get_json(silent=True) or {}

    if request.args.get('dry_run') == '1' or data.get('dry_run'):
        rows = CampaignSend.query.filter_by(campaign_id=campaign_id).all()
        return jsonify(
            {
                'dry_run': True,
                'would_send': sum(1 for r in rows if r.status == 'pending'),
                'skipped': sum(1 for r in rows if r.status == 'skipped'),
                'reasons': sorted({r.skip_reason for r in rows if r.status == 'skipped' and r.skip_reason}),
            }
        )

    result = svc.run_campaign(campaign_id, sent_by_id=request.user.id, max_messages=data.get('max_messages'))
    return jsonify(result)


@crm_bp.route('/campaigns/<int:campaign_id>', methods=['DELETE'])
def cancel_campaign(campaign_id):
    campaign = Campaign.query.get(campaign_id)
    if not campaign:
        return jsonify({'error': 'Campana no encontrada'}), 404
    if campaign.status == 'sent':
        return jsonify({'error': 'La campana ya se completo'}), 400

    campaign.status = 'cancelled'
    CampaignSend.query.filter_by(campaign_id=campaign_id, status='pending').update({'status': 'skipped', 'skip_reason': 'Campana cancelada'})
    db.session.commit()
    return jsonify({'campaign': campaign.to_dict()})


# ----------------------------------------------------------------- envio


@crm_bp.route('/send', methods=['POST'])
def send_message():
    """Envio individual a un paciente."""
    data = request.get_json(silent=True) or {}
    patient_id = data.get('patient_id')
    message = (data.get('message') or '').strip()
    channel = (data.get('channel') or 'whatsapp').lower()

    if not patient_id or not message:
        return jsonify({'error': 'patient_id y message son obligatorios'}), 400

    svc = _service()
    result = svc.send_to_patient(
        patient_id, message, channel=channel, sent_by_id=request.user.id,
        template_key=data.get('template_key'), trigger='manual',
    )
    return jsonify(result), 200 if result['status'] == 'sent' else 400


# -------------------------------------------------------------- historial


@crm_bp.route('/history', methods=['GET'])
def history():
    q = MessageLog.query
    if request.args.get('patient_id'):
        q = q.filter(MessageLog.patient_id == request.args['patient_id'])
    if request.args.get('channel'):
        q = q.filter(MessageLog.channel == request.args['channel'])
    if request.args.get('status'):
        q = q.filter(MessageLog.status == request.args['status'])

    days = int(request.args.get('days', 30))
    since = datetime.utcnow() - timedelta(days=days)
    q = q.filter(MessageLog.created_at >= since)

    limit = min(int(request.args.get('limit', 100)), 500)
    rows = q.order_by(MessageLog.created_at.desc()).limit(limit).all()

    return jsonify({'messages': [m.to_dict() for m in rows], 'stats': _service().stats()})


@crm_bp.route('/whatsapp/status', methods=['GET'])
def whatsapp_status():
    """Estado del puente y de que numero sale la comunicacion."""
    from app.services.whatsapp_service import whatsapp_service

    return jsonify(whatsapp_service.status())


@crm_bp.route('/whatsapp/start', methods=['POST'])
def whatsapp_start():
    from app.services.whatsapp_service import whatsapp_service

    started = whatsapp_service.start()
    return jsonify({'started': started, 'status': whatsapp_service.status()})


@crm_bp.route('/whatsapp/qr', methods=['GET'])
def whatsapp_qr():
    """Devuelve el QR para escanear desde el celular.

    El puente se arranca aqui y se deja vivo: el QR caduca a los ~30s, asi
    que se genera al pedirlo y no antes. Si la sesion ya estaba guardada no
    hay nada que escanear y se informa eso en vez de un QR muerto.
    """
    from app.services.whatsapp_service import whatsapp_service

    service = whatsapp_service

    if service.is_connected:
        return jsonify({
            'connected': True,
            'phone': service.connected_phone,
            'qr': None,
            'message': 'Ya esta conectado, no hay nada que escanear',
        })

    service.start()

    # El puente anuncia el QR por stdout en cuanto se conecta. Se espera a que
    # llegue, con techo para no dejar la peticion colgada.
    limite = time.time() + 25
    while time.time() < limite:
        if service.qr_code:
            return jsonify({
                'connected': False,
                'qr': service.qr_code,
                'phone': None,
                'message': 'Escanea con WhatsApp > Dispositivos vinculados',
            })
        if service.needs_qr:
            return jsonify({
                'connected': False,
                'qr': None,
                'phone': None,
                'message': service.last_error or 'Hay que volver a escanear el QR',
            })
        if service.is_banned:
            return jsonify({
                'connected': False,
                'qr': None,
                'phone': None,
                'message': 'WhatsApp baneo este numero',
            }), 409
        time.sleep(0.5)

    return jsonify({
        'connected': False,
        'qr': None,
        'phone': None,
        'message': 'No se pudo generar el QR. Revisa que el puente de WhatsApp este corriendo.',
    }), 503
