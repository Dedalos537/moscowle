"""Validar, ejecutar y avisar las solicitudes de terapeutas (sesiones, pacientes, grupos).

El terapeuta solo puede pedir para sí mismo y para sus pacientes (vínculo N:M). Al aprobar se ejecuta el mismo
código que el alta directa de la coordinación, así que las reglas (choques, feriados, estados) son las mismas.
"""

import re
from datetime import UTC, date, datetime

from app.extensions import db
from app.models.action_request import ActionRequest
from app.models.user import User

KINDS = {'sessions': 'Programar sesiones', 'patient': 'Alta de paciente', 'group': 'Nuevo grupo'}
HHMM = re.compile(r'^([01]\d|2[0-3]):[0-5]\d$')


class RequestError(ValueError):
    pass


def _clean(text, limit):
    return (str(text or '')).strip()[:limit]


def _my_patient_ids(therapist):
    return {p.id for p in therapist.associated_patients.filter_by(role='jugador').all()}


def _names(ids):
    return [u.username or u.email for u in User.query.filter(User.id.in_(ids)).all()]


def validate(kind, payload, requester):
    """Normaliza el formulario del terapeuta. Devuelve (payload, resumen) o lanza RequestError."""
    if kind not in KINDS:
        raise RequestError('Tipo de solicitud inválido.')
    if not isinstance(payload, dict):
        raise RequestError('Faltan los datos del formulario.')
    mine = _my_patient_ids(requester)

    if kind == 'sessions':
        start, end = payload.get('start_time'), payload.get('end_time')
        if not (isinstance(start, str) and HHMM.match(start) and isinstance(end, str) and HHMM.match(end)):
            raise RequestError('Indica la hora de inicio y de fin (HH:MM).')
        if end <= start:
            raise RequestError('La hora de fin debe ser posterior a la de inicio.')
        dates = payload.get('dates') or []
        try:
            dates = sorted({date.fromisoformat(d).isoformat() for d in dates})
        except (TypeError, ValueError) as e:
            raise RequestError('Fechas inválidas.') from e
        if not 1 <= len(dates) <= 10:
            raise RequestError('Elige entre 1 y 10 fechas.')
        group_id = payload.get('group_id')
        clean = {
            'therapist_id': requester.id,
            'title_prefix': _clean(payload.get('title_prefix'), 120),
            'sede': _clean(payload.get('sede'), 120),
            'session_type': payload.get('session_type')
            if payload.get('session_type') in ('individual', 'grupal', 'evaluacion')
            else 'individual',
            'dates': dates,
            'start_time': start,
            'end_time': end,
            'notes': _clean(payload.get('notes'), 2000),
            'day_notes': {
                k: _clean(v, 500) for k, v in (payload.get('day_notes') or {}).items() if k in dates and _clean(v, 500)
            },
        }
        if group_id:
            from app.models.patient_group import PatientGroup

            group = db.session.get(PatientGroup, int(group_id))
            if not group or group.therapist_id != requester.id:
                raise RequestError('Ese grupo no es tuyo.')
            clean.update(group_id=group.id, patient_ids=[m.id for m in group.members], session_type='grupal')
            who = f'grupo {group.name}'
        else:
            pid = int(payload.get('patient_id') or 0)
            if pid not in mine:
                raise RequestError('Elige uno de tus pacientes.')
            clean['patient_id'] = pid
            who = _names([pid])[0]
        n = len(dates) * (len(clean.get('patient_ids') or []) or 1)
        summary = f'{n} {"sesión" if n == 1 else "sesiones"} para {who}, {start}–{end}, desde el {dates[0]}'
        return clean, summary[:255]

    if kind == 'patient':
        name = _clean(payload.get('username'), 100)
        if len(name) < 3:
            raise RequestError('Escribe el nombre completo del paciente.')
        email = _clean(payload.get('email'), 150).lower()
        if email and (not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email) or User.query.filter_by(email=email).first()):
            raise RequestError('Ese correo no es válido o ya está registrado.')
        clean = {
            'role': 'jugador',
            'username': name,
            'email': email,
            'phone': _clean(payload.get('phone'), 50),
            'guardian_name': _clean(payload.get('guardian_name'), 150),
            'guardian_contact': _clean(payload.get('guardian_contact'), 150),
            'sede_id': payload.get('sede_id') or None,
            'notes': _clean(payload.get('notes'), 2000),
            'therapist_id': requester.id,
        }
        return clean, f'Alta de paciente: {name}'[:255]

    # group
    name = _clean(payload.get('name'), 120)
    if len(name) < 2:
        raise RequestError('Escribe el nombre del grupo.')
    members = sorted({int(m) for m in (payload.get('member_ids') or [])})
    if not members or not set(members) <= mine:
        raise RequestError('Elige al menos uno de tus pacientes para el grupo.')
    start, end = payload.get('start_time') or '', payload.get('end_time') or ''
    if (start and not HHMM.match(start)) or (end and not HHMM.match(end)) or (start and end and end <= start):
        raise RequestError('Revisa el horario del grupo.')
    clean = {
        'name': name,
        'therapist_id': requester.id,
        'member_ids': members,
        'sede_id': payload.get('sede_id') or None,
        'start_time': start or None,
        'end_time': end or None,
        'notes': _clean(payload.get('notes'), 2000),
    }
    return clean, f'Grupo «{name}» con {len(members)} {"paciente" if len(members) == 1 else "pacientes"}'[:255]


def execute(req):
    """Ejecuta la acción aprobada. Devuelve el resultado o lanza RequestError con el motivo del sistema."""
    p = dict(req.payload or {})
    if req.kind == 'sessions':
        from app.routes.admin.sessions import create_sessions_batch

        resp = create_sessions_batch(p)
        status = 200
        if isinstance(resp, tuple):
            resp, status = resp[0], resp[1]
        body = resp.get_json() or {}
        if status >= 400:
            raise RequestError(body.get('error') or 'No se pudieron crear las sesiones.')
        return {'created': body.get('created'), 'session_ids': body.get('session_ids'), 'message': body.get('message')}

    if req.kind == 'patient':
        from app.services.admin_service import AdminService

        ok, result = AdminService().create_user(p)
        if not ok:
            raise RequestError(str(result))
        user = result.get('user') if isinstance(result, dict) else None
        if user is None:
            user = User.query.filter_by(username=p['username'], role='jugador').order_by(User.id.desc()).first()
        requester = db.session.get(User, req.requester_id)
        if user and requester and requester not in user.therapists:
            user.therapists.append(requester)  # vínculo N:M: el paciente aparece en las pantallas del terapeuta
        if user and p.get('notes'):
            user.notes = p['notes']
        db.session.commit()
        return {'user_id': user.id if user else None, 'username': p['username'], 'has_email': bool(p.get('email'))}

    from app.models.patient_group import PatientGroup

    group = PatientGroup(
        name=p['name'],
        therapist_id=p['therapist_id'],
        sede_id=p.get('sede_id'),
        start_time=p.get('start_time'),
        end_time=p.get('end_time'),
        notes=p.get('notes'),
        session_dates='[]',
    )
    group.members = User.query.filter(User.id.in_(p['member_ids'])).all()
    db.session.add(group)
    db.session.commit()
    return {'group_id': group.id, 'name': group.name}


def resolve(req, reviewer, approve, note=None, overrides=None):
    if req.status != 'pending':
        raise RequestError('Esta solicitud ya fue resuelta.')
    note = _clean(note, 1000) or None
    if approve:
        if overrides:
            requester = db.session.get(User, req.requester_id)
            payload, summary = validate(req.kind, {**req.payload, **overrides}, requester)
            req.payload, req.summary = payload, summary
        try:
            req.result = execute(req)
        except RequestError as e:
            db.session.rollback()
            req = db.session.get(ActionRequest, req.id)
            req.last_error = str(e)
            db.session.commit()
            raise
        req.status = 'approved'
    else:
        if not note:
            raise RequestError('Escribe el motivo del rechazo: el terapeuta lo verá.')
        req.status = 'rejected'
    req.reviewer_id = reviewer.id
    req.review_note = note
    req.last_error = None
    req.resolved_at = datetime.now(UTC).replace(tzinfo=None)
    db.session.commit()
    _notify_requester(req)
    return req


def _notify(user_id, message, title, link, priority='normal'):
    try:
        from app.services.notification_service import NotificationService

        NotificationService().notify_user(
            user_id=user_id,
            message=message[:255],
            title=title,
            notif_type='info',
            link=link,
            category='system',
            priority=priority,
        )
    except Exception:  # noqa: BLE001 - un aviso fallido no deshace la solicitud
        pass


def notify_staff(req):
    for u in User.query.filter(User.role.in_(('admin', 'supervisor')), User.is_active.isnot(False)).all():
        name = req.requester.username if req.requester else 'Un terapeuta'
        _notify(u.id, f'{name} solicita: {req.summary}', 'Nueva solicitud', f'/admin/requests?id={req.id}', 'high')


def _notify_requester(req):
    label = KINDS.get(req.kind, 'Solicitud')
    if req.status == 'approved':
        msg = f'Aprobada: {req.summary}'
    else:
        msg = f'Rechazada: {req.summary}. Motivo: {req.review_note}'
    _notify(
        req.requester_id,
        msg,
        f'{label}: {"aprobada" if req.status == "approved" else "rechazada"}',
        f'/therapist/requests?id={req.id}',
    )
