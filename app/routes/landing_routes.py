"""API de la landing pública (centrojuanpabloii.com), separada del resto de la plataforma.

Público (sin sesión):
    GET  /api/landing/content          contenido publicado que pinta la landing
    POST /api/landing/leads            solicitud de evaluación: formulario, WhatsApp o llamada
Administración (admin; supervisor solo lectura):
    GET  /api/landing/admin/content    contenido actual, historial de versiones y valores por defecto
    PUT  /api/landing/admin/content    publica una versión nueva
    POST /api/landing/admin/content/restore/<id>
    GET  /api/landing/admin/leads      bandeja de solicitudes
    PATCH /api/landing/admin/leads/<id>
    GET  /api/landing/admin/stats
"""

import hashlib
import re
from datetime import UTC, datetime, timedelta

from flask import Blueprint, current_app, jsonify, request
from sqlalchemy import func, or_

from app.auth_compat import current_user, login_required
from app.extensions import csrf, db, limiter
from app.models.landing import LandingContentVersion, LandingLead
from app.models.user import User
from app.services import landing_content
from app.utils.decorators import admin_required, admin_write_required

landing_bp = Blueprint('landing', __name__, url_prefix='/api/landing')
csrf.exempt(landing_bp)

CHANNELS = ('form', 'whatsapp', 'call')
STATUSES = ('new', 'contacted', 'scheduled', 'discarded')
TIMES = ('manana', 'tarde', 'cualquiera')
DEDUPE_WINDOW = timedelta(minutes=30)


def _now():
    return datetime.now(UTC).replace(tzinfo=None)


def _text(value, max_len):
    if value is None:
        return None
    text = re.sub(r'[\x00-\x1f\x7f]', ' ', str(value)).strip()
    return text[:max_len] or None


def _ip_hash():
    ip = (request.headers.get('CF-Connecting-IP') or request.remote_addr or '').strip()
    salt = current_app.config.get('SECRET_KEY') or ''
    return hashlib.sha256(f'{salt}:{ip}'.encode()).hexdigest() if ip else None


# ------------------------------------------------------------------ público


@landing_bp.route('/content', methods=['GET'])
@limiter.limit('120 per minute')
def public_content():
    content, row = landing_content.current_content()
    resp = jsonify(
        {
            'success': True,
            'content': content,
            'version': row.id if row else 0,
            'updated_at': row.created_at.isoformat() if row else None,
        }
    )
    resp.headers['Cache-Control'] = 'public, max-age=60'
    return resp


@landing_bp.route('/leads', methods=['POST'])
@limiter.limit('8 per hour; 3 per minute')
def create_lead():
    data = request.get_json(silent=True) or {}
    # Campo trampa: invisible para personas, los bots lo rellenan. Se responde OK para no darles pistas.
    if data.get('website'):
        return jsonify({'success': True}), 201

    channel = data.get('channel') if data.get('channel') in CHANNELS else 'form'
    name = _text(data.get('name'), 120)
    phone = _text(data.get('phone'), 30)
    email = _text(data.get('email'), 150)
    digits = re.sub(r'\D', '', phone or '')

    if channel == 'form':
        if not name:
            return jsonify({'success': False, 'error': 'Escribe tu nombre.', 'field': 'name'}), 400
        if not 6 <= len(digits) <= 15:
            return jsonify({'success': False, 'error': 'Escribe un teléfono válido.', 'field': 'phone'}), 400
    elif phone and not 6 <= len(digits) <= 15:
        phone = None
    if email and not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
        return jsonify({'success': False, 'error': 'El correo no es válido.', 'field': 'email'}), 400

    preferred = data.get('preferred_time') if data.get('preferred_time') in TIMES else None
    fields = {
        'name': name,
        'phone': phone,
        'email': email,
        'patient_age': _text(data.get('patient_age'), 30),
        'service': _text(data.get('service'), 120),
        'preferred_time': preferred,
        'message': _text(data.get('message'), 1500),
        'source': _text(data.get('source'), 200),
    }
    ip = _ip_hash()

    # Quien toca dos veces «WhatsApp» o reenvía el formulario no debe abrir dos solicitudes.
    lead = None
    if ip:
        lead = (
            LandingLead.query.filter(
                LandingLead.ip_hash == ip,
                LandingLead.channel == channel,
                LandingLead.created_at >= _now() - DEDUPE_WINDOW,
                LandingLead.status == 'new',
            )
            .order_by(LandingLead.id.desc())
            .first()
        )
    is_new = lead is None
    if is_new:
        lead = LandingLead(channel=channel, ip_hash=ip)
        db.session.add(lead)
    for key, value in fields.items():
        if value is not None:
            setattr(lead, key, value)
    db.session.commit()

    if is_new:
        _notify_staff(lead)
    return jsonify({'success': True, 'id': lead.id}), 201


CHANNEL_LABEL = {'form': 'pide que la llamen', 'whatsapp': 'escribió por WhatsApp', 'call': 'llamó'}


def _notify_staff(lead):
    try:
        from app.services.notification_service import NotificationService

        who = lead.name or 'Una familia'
        what = f' · {lead.service}' if lead.service else ''
        message = f'{who} {CHANNEL_LABEL.get(lead.channel, "")} desde la web{what}'
        service = NotificationService()
        for user in User.query.filter(User.role.in_(('admin', 'supervisor')), User.is_active.isnot(False)).all():
            service.notify_user(
                user_id=user.id,
                message=message[:255],
                title='Solicitud de evaluación',
                notif_type='info',
                link=f'/admin/settings?section=website&lead={lead.id}',
                category='system',
                priority='high' if lead.channel == 'form' else 'normal',
            )
    except Exception:  # noqa: BLE001 - un aviso fallido no debe perder la solicitud
        current_app.logger.warning('No se pudo avisar de la solicitud %s', lead.id, exc_info=True)


# ------------------------------------------------------------- administración


def _versions():
    rows = LandingContentVersion.query.order_by(LandingContentVersion.id.desc()).limit(20).all()
    return [r.summary() for r in rows]


@landing_bp.route('/admin/content', methods=['GET'])
@login_required
@admin_required
def admin_content():
    content, row = landing_content.current_content()
    return jsonify(
        {
            'success': True,
            'content': content,
            'version': row.id if row else 0,
            'versions': _versions(),
            'default': landing_content.default_content(),
        }
    )


@landing_bp.route('/admin/content', methods=['PUT'])
@login_required
@admin_write_required
def admin_publish():
    data = request.get_json(silent=True) or {}
    content, row = landing_content.current_content()
    base = data.get('base_version')
    if base is not None and row is not None and int(base) != row.id:
        return (
            jsonify(
                {
                    'success': False,
                    'error': 'Otra persona publicó cambios mientras editabas. Recarga para ver la versión actual.',
                    'conflict': True,
                }
            ),
            409,
        )
    try:
        new_row = landing_content.publish(data.get('content'), current_user.id, data.get('note'))
    except landing_content.ContentError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    return jsonify({'success': True, 'version': new_row.id, 'versions': _versions(), 'content': new_row.content})


@landing_bp.route('/admin/content/restore/<int:version_id>', methods=['POST'])
@login_required
@admin_write_required
def admin_restore(version_id):
    old = db.session.get(LandingContentVersion, version_id)
    if old is None:
        return jsonify({'success': False, 'error': 'Versión no encontrada'}), 404
    try:
        new_row = landing_content.publish(old.content, current_user.id, f'Restaurada la versión {version_id}')
    except landing_content.ContentError as e:
        return jsonify({'success': False, 'error': f'Esa versión ya no es válida: {e}'}), 400
    return jsonify({'success': True, 'version': new_row.id, 'versions': _versions(), 'content': new_row.content})


@landing_bp.route('/admin/leads', methods=['GET'])
@login_required
@admin_required
def admin_leads():
    q = LandingLead.query
    status = request.args.get('status')
    if status in STATUSES:
        q = q.filter(LandingLead.status == status)
    elif status == 'open':
        q = q.filter(LandingLead.status.in_(('new', 'contacted')))
    channel = request.args.get('channel')
    if channel in CHANNELS:
        q = q.filter(LandingLead.channel == channel)
    # Un toque en «WhatsApp» o «Llamar» sin datos solo cuenta en las cifras; la bandeja muestra a quien dejó nombre
    # o teléfono.
    if request.args.get('contact') == '1':
        q = q.filter(or_(LandingLead.name.isnot(None), LandingLead.phone.isnot(None)))
    term = (request.args.get('q') or '').strip()
    if term:
        like = f'%{term}%'
        q = q.filter(or_(LandingLead.name.ilike(like), LandingLead.phone.ilike(like), LandingLead.service.ilike(like)))
    page = max(1, request.args.get('page', 1, type=int))
    per_page = min(100, max(10, request.args.get('per_page', 30, type=int)))
    total = q.count()
    rows = q.order_by(LandingLead.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
    return jsonify({'success': True, 'leads': [r.to_dict() for r in rows], 'total': total, 'page': page})


@landing_bp.route('/admin/leads/<int:lead_id>', methods=['PATCH'])
@login_required
@admin_write_required
def admin_update_lead(lead_id):
    lead = db.session.get(LandingLead, lead_id)
    if lead is None:
        return jsonify({'success': False, 'error': 'Solicitud no encontrada'}), 404
    data = request.get_json(silent=True) or {}
    if 'status' in data:
        if data['status'] not in STATUSES:
            return jsonify({'success': False, 'error': 'Estado no válido'}), 400
        lead.status = data['status']
        lead.handled_by = current_user.id
    if 'staff_note' in data:
        lead.staff_note = _text(data.get('staff_note'), 2000)
    db.session.commit()
    return jsonify({'success': True, 'lead': lead.to_dict()})


@landing_bp.route('/admin/stats', methods=['GET'])
@login_required
@admin_required
def admin_stats():
    since = _now() - timedelta(days=30)
    by_channel = dict(
        db.session.query(LandingLead.channel, func.count(LandingLead.id))
        .filter(LandingLead.created_at >= since)
        .group_by(LandingLead.channel)
        .all()
    )
    by_status = dict(
        db.session.query(LandingLead.status, func.count(LandingLead.id)).group_by(LandingLead.status).all()
    )
    return jsonify(
        {
            'success': True,
            'last_30_days': {c: by_channel.get(c, 0) for c in CHANNELS},
            'by_status': {s: by_status.get(s, 0) for s in STATUSES},
        }
    )
