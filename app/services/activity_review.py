"""Revisión de actividad por usuario (PRP 012): lo pendiente según su rol y lo hecho (línea de tiempo).

- Pendientes: reglas por rol en `PENDING_RULES`. Cada una cuenta para TODOS los usuarios con una sola consulta
  agregada (la lista no hace N consultas) y lista el detalle para uno.
- Hecho: se arma de las tablas que ya existen (sesiones de acceso, citas, pagos, gastos, tareas, incidencias,
  solicitudes, impresiones, IA, cambios de estado) + `activity_event` para las ediciones sin rastro propio.
- Nunca se expone contenido clínico, de mensajes ni contraseñas.
"""

from datetime import datetime, timedelta

from sqlalchemy import func

from app.extensions import db
from app.models import (
    ActionRequest,
    Appointment,
    Expense,
    Incidente,
    Installment,
    KanbanTask,
    PasswordReset,
    Payment,
    PrintJob,
    User,
    UserSession,
)
from app.models.activity_event import ActivityEvent
from app.models.ai_external_call import AiExternalCall
from app.models.appointment import AppointmentGame
from app.models.contract import Contract
from app.models.user_status_log import UserStatusLog

CLOSED_INCIDENT = ('RESUELTO', 'CERRADO')
STAFF = ('admin', 'supervisor')
RETENTION_DAYS = 180


def _now():
    return datetime.utcnow()


# ── Pendientes ───────────────────────────────────────────────────────────────
# Los enlaces son del panel de admin: quien revisa la actividad es el admin, no la persona revisada.
# Cada regla: (clave, roles, etiqueta, severidad, link por rol, query(uid|None) -> columnas (user_id, n, oldest)).
def _q_sessions_unclosed():
    limit = _now() - timedelta(hours=3)
    return db.session.query(
        Appointment.therapist_id, func.count(Appointment.id), func.min(Appointment.start_time)
    ).filter(Appointment.status == 'scheduled', Appointment.start_time < limit, Appointment.is_active.isnot(False))


def _q_sessions_no_notes():
    since = _now() - timedelta(days=30)
    return db.session.query(
        Appointment.therapist_id, func.count(Appointment.id), func.min(Appointment.start_time)
    ).filter(
        Appointment.status == 'completed',
        Appointment.start_time >= since,
        Appointment.is_active.isnot(False),
        (Appointment.notes.is_(None)) | (func.trim(Appointment.notes) == ''),
    )


def _q_tasks_overdue():
    return db.session.query(
        KanbanTask.assigned_to_id, func.count(KanbanTask.id), func.min(KanbanTask.created_at)
    ).filter(KanbanTask.is_active.isnot(False), KanbanTask.column != 'done', KanbanTask.is_expired.is_(True))


def _q_incidents_open():
    return db.session.query(
        Incidente.responsable_id, func.count(Incidente.id_incidente), func.min(Incidente.fecha_creacion)
    ).filter(Incidente.estado.notin_(CLOSED_INCIDENT), Incidente.is_active.isnot(False))


def _q_incidents_sla():
    return _q_incidents_open().filter(Incidente.fecha_limite_sla.isnot(None), Incidente.fecha_limite_sla < _now())


def _q_installments_overdue():
    today = _now().date()
    return (
        db.session.query(Contract.patient_id, func.count(Installment.id), func.min(Installment.due_date))
        .join(Contract, Contract.id == Installment.contract_id)
        .filter(
            Installment.status.in_(('pending', 'partial')),
            Installment.due_date < today,
            Installment.is_active.isnot(False),
            Contract.status == 'active',
        )
    )


def _q_games_pending():
    return (
        db.session.query(Appointment.patient_id, func.count(AppointmentGame.id), func.min(Appointment.start_time))
        .join(Appointment, Appointment.id == AppointmentGame.appointment_id)
        .filter(
            AppointmentGame.status == 'pending',
            AppointmentGame.is_active.isnot(False),
            Appointment.start_time < _now(),
        )
    )


# Pendientes globales del equipo (no tienen dueño): se muestran a cada admin/supervisor.
def _team_requests():
    q = db.session.query(func.count(ActionRequest.id), func.min(ActionRequest.created_at))
    return q.filter(ActionRequest.status == 'pending').one()


def _team_resets():
    q = db.session.query(func.count(PasswordReset.id), func.min(PasswordReset.created_at))
    return q.filter(PasswordReset.status == 'awaiting_approval').one()


def _team_unassigned_incidents():
    q = db.session.query(func.count(Incidente.id_incidente), func.min(Incidente.fecha_creacion))
    return q.filter(
        Incidente.responsable_id.is_(None), Incidente.estado.notin_(CLOSED_INCIDENT), Incidente.is_active.isnot(False)
    ).one()


def _team_unassigned_payments():
    q = db.session.query(func.count(Payment.id), func.min(Payment.date))
    return q.filter(Payment.kind == 'unassigned', Payment.is_active.isnot(False)).one()


OWNED_RULES = [
    # clave, roles, etiqueta, severidad, link por rol, consulta, columna de usuario
    (
        'sessions_unclosed',
        ('terapista',),
        'sesiones pasadas sin cerrar',
        'high',
        '/admin/sessions',
        _q_sessions_unclosed,
    ),
    (
        'sessions_no_notes',
        ('terapista',),
        'sesiones completadas sin notas (30 días)',
        'low',
        '/admin/sessions',
        _q_sessions_no_notes,
    ),
    (
        'tasks_overdue',
        ('terapista', 'admin', 'supervisor'),
        'tareas vencidas',
        'medium',
        '/admin/kanban',
        _q_tasks_overdue,
    ),
    (
        'incidents_sla',
        ('terapista', 'admin', 'supervisor'),
        'incidencias asignadas fuera de SLA',
        'high',
        '/admin/settings?section=incidents',
        _q_incidents_sla,
    ),
    (
        'incidents_open',
        ('terapista', 'admin', 'supervisor'),
        'incidencias asignadas abiertas',
        'medium',
        '/admin/settings?section=incidents',
        _q_incidents_open,
    ),
    ('installments_overdue', ('jugador',), 'cuotas vencidas', 'high', '/admin/finanzas', _q_installments_overdue),
    ('games_pending', ('jugador',), 'juegos asignados sin jugar', 'low', '/admin/sessions', _q_games_pending),
]

TEAM_RULES = [
    ('requests_pending', 'solicitudes por aprobar', 'medium', '/admin/settings?section=requests', _team_requests),
    ('resets_pending', 'restablecimientos de contraseña por revisar', 'medium', '/admin/password-resets', _team_resets),
    (
        'incidents_unassigned',
        'incidencias sin responsable',
        'high',
        '/admin/settings?section=incidents',
        _team_unassigned_incidents,
    ),
    (
        'payments_unassigned',
        'pagos sin clasificar (Excel de cobranza)',
        'medium',
        '/admin/finanzas',
        _team_unassigned_payments,
    ),
]

SEVERITY_RANK = {'high': 3, 'medium': 2, 'low': 1}


def _link(link, role):
    if isinstance(link, dict):
        return link.get(role) or link.get('*')
    return link


def _days(oldest):
    if not oldest:
        return None
    if not isinstance(oldest, datetime):
        oldest = datetime.combine(oldest, datetime.min.time())
    return max(0, (_now() - oldest).days)


def _profile_gaps(user):
    from app.services.email_service import recipient_for

    gaps = []
    if not recipient_for(user):
        gaps.append('sin correo real (ni propio ni del apoderado)')
    if not (user.phone or '').strip() and not (getattr(user, 'guardian_contact', '') or '').strip():
        gaps.append('sin teléfono de contacto')
    if not (getattr(user, 'guardian_name', '') or '').strip():
        gaps.append('sin apoderado registrado')
    return gaps


def pending_for(user):
    """Lista de pendientes de un usuario: [{key, label, count, days, severity, link}]."""
    items = []
    for key, roles, label, severity, link, query in OWNED_RULES:
        if user.role not in roles:
            continue
        q = query()
        col = q.column_descriptions[0]['expr']
        row = q.filter(col == user.id).group_by(col).first()
        n, oldest = (row[1], row[2]) if row else (0, None)
        if n:
            items.append(
                {
                    'key': key,
                    'label': label,
                    'count': int(n),
                    'days': _days(oldest),
                    'severity': severity,
                    'link': _link(link, user.role),
                }
            )
    if user.role in STAFF:
        for key, label, severity, link, fn in TEAM_RULES:
            n, oldest = fn()
            if n:
                items.append(
                    {
                        'key': key,
                        'label': label,
                        'count': int(n),
                        'days': _days(oldest),
                        'severity': severity,
                        'link': link,
                        'team': True,
                    }
                )
    if user.role == 'jugador':
        gaps = _profile_gaps(user)
        if gaps:
            items.append(
                {
                    'key': 'profile',
                    'label': 'perfil incompleto: ' + ', '.join(gaps),
                    'count': len(gaps),
                    'days': None,
                    'severity': 'low',
                    'link': f'/admin/patients/{user.id}',
                }
            )
    items.sort(key=lambda i: (-SEVERITY_RANK[i['severity']], -(i['days'] or 0)))
    return items


def pending_counts():
    """{user_id: {'count', 'high', 'oldest_days'}} para todos los usuarios con pocas consultas agregadas."""
    out: dict = {}

    def add(uid, n, oldest, severity):
        if not uid or not n:
            return
        row = out.setdefault(int(uid), {'count': 0, 'high': 0, 'oldest_days': 0})
        row['count'] += int(n)
        if severity == 'high':
            row['high'] += int(n)
        row['oldest_days'] = max(row['oldest_days'], _days(oldest) or 0)

    for rule in OWNED_RULES:
        key, severity, query = rule[0], rule[3], rule[5]
        if key == 'incidents_open':
            continue  # ya cuenta en «fuera de SLA» o la cuenta abajo sin duplicar
        q = query()
        col = q.column_descriptions[0]['expr']
        for uid, n, oldest in q.group_by(col).all():
            add(uid, n, oldest, severity)
    # Abiertas que NO están fuera de SLA (para no contar dos veces).
    q = _q_incidents_open().filter((Incidente.fecha_limite_sla.is_(None)) | (Incidente.fecha_limite_sla >= _now()))
    for uid, n, oldest in q.group_by(Incidente.responsable_id).all():
        add(uid, n, oldest, 'medium')
    team = [fn() for *_r, fn in TEAM_RULES]
    team_n = sum(int(n or 0) for n, _ in team)
    if team_n:
        for (uid,) in db.session.query(User.id).filter(User.role.in_(STAFF), User.is_active.isnot(False)):
            add(uid, team_n, min((o for _, o in team if o), default=None), 'medium')
    return out


def users_overview(role=None, sede_id=None, only_pending=False, query=None):
    since = _now() - timedelta(days=7)
    q = User.query.filter(User.is_active.isnot(False))
    if role:
        q = q.filter(User.role == role)
    if sede_id:
        q = q.filter(User.sede_id == int(sede_id))
    if query:
        like = f'%{query.strip()}%'
        q = q.filter((User.username.ilike(like)) | (User.email.ilike(like)) | (User.login_code.ilike(like)))
    users = q.all()
    ids = [u.id for u in users]
    last_login = (
        dict(
            db.session.query(UserSession.user_id, func.max(UserSession.created_at))
            .filter(UserSession.user_id.in_(ids))
            .group_by(UserSession.user_id)
            .all()
        )
        if ids
        else {}
    )
    actions = (
        dict(
            db.session.query(ActivityEvent.user_id, func.count(ActivityEvent.id))
            .filter(
                ActivityEvent.user_id.in_(ids),
                ActivityEvent.created_at >= since,
                ActivityEvent.action != 'activity.viewed',
            )
            .group_by(ActivityEvent.user_id)
            .all()
        )
        if ids
        else {}
    )
    pend = pending_counts()
    rows = []
    for u in users:
        p = pend.get(u.id, {'count': 0, 'high': 0, 'oldest_days': 0})
        if only_pending and not p['count']:
            continue
        ll = last_login.get(u.id)
        rows.append(
            {
                'id': u.id,
                'name': u.username or u.email,
                'login_code': u.login_code,
                'role': u.role,
                'sede_id': getattr(u, 'sede_id', None),
                'last_login': ll.isoformat() + 'Z' if ll else None,
                'actions_7d': int(actions.get(u.id, 0)),
                'pending': p['count'],
                'pending_high': p['high'],
                'pending_oldest_days': p['oldest_days'],
            }
        )
    rows.sort(key=lambda r: (-r['pending_high'], -r['pending_oldest_days'], -r['pending'], (r['name'] or '').lower()))
    return rows


# ── Hecho: línea de tiempo ───────────────────────────────────────────────────
def _ev(at, type_, icon, summary, link=None):
    return {
        'at': at.isoformat() + 'Z' if at else None,
        'type': type_,
        'icon': icon,
        'summary': summary,
        'link': link,
        '_t': at,
    }


def _sources(user, start, end):
    uid = user.id
    is_ther = user.role == 'terapista'
    yield from (
        _ev(
            s.created_at,
            'login',
            'right-to-bracket',
            f'Inició sesión{(" desde " + s.device_info[:60]) if s.device_info else ""}',
        )
        for s in UserSession.query.filter(UserSession.user_id == uid, UserSession.created_at.between(start, end))
    )
    appt_q = Appointment.query.filter(Appointment.start_time.between(start, end), Appointment.is_active.isnot(False))
    mine = appt_q.filter(Appointment.therapist_id == uid) if is_ther else appt_q.filter(Appointment.patient_id == uid)
    if user.role in ('terapista', 'jugador'):
        for a in mine:
            verb = {
                'completed': 'Sesión completada',
                'cancelled': 'Sesión cancelada',
                'scheduled': 'Sesión programada',
            }.get(a.status, f'Sesión ({a.status})')
            yield _ev(a.start_time, 'session', 'calendar-check', f'{verb}: {a.title or "sesión"}', '/admin/sessions')
    for a in Appointment.query.filter(Appointment.created_by_id == uid, Appointment.created_at.between(start, end)):
        yield _ev(
            a.created_at,
            'session_created',
            'calendar-plus',
            f'Creó la sesión «{a.title or "sesión"}»',
            '/admin/sessions',
        )
    for p in Payment.query.filter(Payment.created_by_id == uid, Payment.created_at.between(start, end)):
        yield _ev(
            p.created_at,
            'payment',
            'money-bill-wave',
            f'Registró un pago de S/ {p.amount:.2f} ({p.method or "—"})',
            '/admin/finanzas',
        )
    for e in Expense.query.filter(Expense.created_by_id == uid, Expense.created_at.between(start, end)):
        yield _ev(
            e.created_at,
            'expense',
            'receipt',
            f'Registró un gasto de S/ {e.amount:.2f} ({e.category})',
            '/admin/finanzas',
        )
    for t in KanbanTask.query.filter(KanbanTask.created_by_id == uid, KanbanTask.created_at.between(start, end)):
        yield _ev(t.created_at, 'task', 'list-check', f'Creó la tarea «{t.title[:60]}»', '/admin/kanban')
    for i in Incidente.query.filter(Incidente.user_id == uid, Incidente.fecha_creacion.between(start, end)):
        yield _ev(
            i.fecha_creacion,
            'incident',
            'triangle-exclamation',
            f'Reportó la incidencia #{i.id_incidente}: {i.titulo[:60]}',
            '/admin/settings?section=incidents',
        )
    for i in Incidente.query.filter(Incidente.responsable_id == uid, Incidente.fecha_resolucion.between(start, end)):
        yield _ev(
            i.fecha_resolucion,
            'incident_resolved',
            'circle-check',
            f'Resolvió la incidencia #{i.id_incidente}',
            '/admin/settings?section=incidents',
        )
    for r in ActionRequest.query.filter(
        ActionRequest.requester_id == uid, ActionRequest.created_at.between(start, end)
    ):
        yield _ev(
            r.created_at,
            'request',
            'paper-plane',
            f'Pidió: {r.summary[:80]} ({r.status})',
            '/admin/settings?section=requests',
        )
    for r in ActionRequest.query.filter(
        ActionRequest.reviewer_id == uid, ActionRequest.resolved_at.between(start, end)
    ):
        yield _ev(
            r.resolved_at,
            'request_reviewed',
            'clipboard-check',
            f'Revisó la solicitud: {r.summary[:80]} ({r.status})',
            '/admin/settings?section=requests',
        )
    for j in PrintJob.query.filter(PrintJob.created_by_id == uid, PrintJob.created_at.between(start, end)):
        yield _ev(
            j.created_at,
            'print',
            'print',
            f'Imprimió «{j.file_name[:60]}» ({j.copies} copia{"s" if j.copies != 1 else ""})',
            '/admin/drive',
        )
    for c in AiExternalCall.query.filter(AiExternalCall.user_id == uid, AiExternalCall.created_at.between(start, end)):
        yield _ev(
            c.created_at,
            'ai',
            'robot',
            f'Usó el asistente ({ {"chat": "chat", "vision": "lectura de imagen", "dev": "modo desarrollador"}.get(c.route, c.route) })',
        )
    for s in UserStatusLog.query.filter(
        UserStatusLog.changed_by_id == uid, UserStatusLog.changed_at.between(start, end)
    ):
        target = db.session.get(User, s.user_id)
        yield _ev(
            s.changed_at,
            'status',
            'user-gear',
            f'Cambió el estado de {target.username if target else "un usuario"} a «{s.new_status}»',
        )
    for e in ActivityEvent.query.filter(
        ActivityEvent.user_id == uid,
        ActivityEvent.created_at.between(start, end),
        ActivityEvent.action != 'activity.viewed',
    ):
        yield _ev(e.created_at, 'edit', 'pen', e.summary or e.action)


def timeline(user, start=None, end=None, types=None, page=1, per_page=50):
    end = end or _now()
    start = start or (end - timedelta(days=30))
    events = [e for e in _sources(user, start, end) if e['_t'] and (not types or e['type'] in types)]
    events.sort(key=lambda e: e['_t'], reverse=True)
    total = len(events)
    chunk = events[(page - 1) * per_page : page * per_page]
    for e in chunk:
        e.pop('_t', None)
    return {'events': chunk, 'total': total, 'page': page, 'per_page': per_page}


def daily_counts(user, days=30):
    """Acciones por día (últimos `days`) para la mini gráfica del detalle."""
    end = _now()
    start = end - timedelta(days=days)
    counts: dict = {}
    for e in _sources(user, start, end):
        if e['_t'] and e['type'] != 'login':
            k = e['_t'].date().isoformat()
            counts[k] = counts.get(k, 0) + 1
    return [
        {
            'day': (start.date() + timedelta(days=i)).isoformat(),
            'n': counts.get((start.date() + timedelta(days=i)).isoformat(), 0),
        }
        for i in range(days + 1)
    ]


def sessions_of(user):
    rows = UserSession.query.filter(
        UserSession.user_id == user.id, UserSession.revoked_at.is_(None), UserSession.expires_at > _now()
    )
    return [
        {
            'id': s.id,
            'device': s.device_info,
            'ip': s.ip_address,
            'since': s.created_at.isoformat() + 'Z' if s.created_at else None,
        }
        for s in rows
    ]


def revoke_sessions(user, by_user_id=None):
    from app.models.refresh_token import RefreshToken

    n = 0
    for s in UserSession.query.filter(UserSession.user_id == user.id, UserSession.revoked_at.is_(None)):
        s.revoke()
        n += 1
    RefreshToken.revoke_all_for_user(user.id)
    record(by_user_id, 'sessions.revoked', 'user', user.id, f'Cerró las sesiones de {user.username}')
    db.session.commit()
    return n


# ── Registro de escrituras (activity_event) ──────────────────────────────────
_VERB = {'POST': 'created', 'PUT': 'updated', 'PATCH': 'updated', 'DELETE': 'deleted'}
_VERB_ES = {'created': 'Creó', 'updated': 'Editó', 'deleted': 'Eliminó'}
_PREFIXES = (
    '/admin/api/',
    '/api/admin/',
    '/api/drive/',
    '/therapist/api/',
    '/admin/payments/',
    '/api/kanban/',
    '/mcp/opencode/status',
)
# Escrituras que no son acciones de la persona (ruido) o ya tienen su propio registro.
_SKIP = (
    '/api/drive/upload/',
    '/admin/analyze-receipt',
    '/api/kanban/tasks/<int:task_id>/timer',
    '/api/server-monitor/',
    '/admin/api/billing/import',  # BillingImport ya lo registra
)
_LABELS = {
    'users': 'usuario',
    'patients': 'paciente',
    'contracts': 'contrato',
    'installments': 'cuota',
    'payments': 'pago',
    'expenses': 'gasto',
    'sessions': 'sesión',
    'drive': 'archivo del drive',
    'kanban': 'tarea',
    'payroll': 'nómina',
    'sedes': 'sede',
    'settings': 'ajuste',
    'opencode': 'ajuste del asistente',
}


def _resource(path):
    for prefix in _PREFIXES:
        if path.startswith(prefix):
            rest = path[len(prefix) :].strip('/').split('/')
            seg = rest[0] if rest and rest[0] and not rest[0].startswith('<') else prefix.strip('/').split('/')[-1]
            return seg.replace('-', '_')
    return None


def record(user_id, action, entity_type=None, entity_id=None, summary=None, ip=None):
    role = None
    if user_id:
        u = db.session.get(User, user_id)
        role = u.role if u else None
    db.session.add(
        ActivityEvent(
            user_id=user_id,
            role=role,
            action=action[:60],
            entity_type=(entity_type or '')[:40] or None,
            entity_id=entity_id,
            summary=(summary or '')[:200] or None,
            ip=(ip or '')[:45] or None,
        )
    )


def maybe_record_request(request, response, user_id):
    """after_request: registra escrituras exitosas de las rutas de la lista blanca (sin el cuerpo)."""
    if request.method not in _VERB or response.status_code >= 400 or not user_id:
        return
    rule = request.url_rule.rule if request.url_rule else request.path
    if any(s in rule or request.path.startswith(s) for s in _SKIP):
        return
    resource = _resource(request.path)
    if not resource:
        return
    verb = _VERB[request.method]
    if 'pay' in request.path.rsplit('/', 1)[-1] and request.method == 'POST':
        verb = 'paid'
    entity_id = next((v for v in (request.view_args or {}).values() if isinstance(v, int)), None)
    label = _LABELS.get(resource, resource.replace('_', ' '))
    verb_es = {'paid': 'Registró un pago en'}.get(verb) or _VERB_ES.get(verb, verb)
    summary = f'{verb_es} {label}' + (f' #{entity_id}' if entity_id else '')
    try:
        record(
            user_id,
            f'{resource}.{verb}',
            resource,
            entity_id,
            summary,
            request.headers.get('CF-Connecting-IP') or request.remote_addr,
        )
        db.session.commit()
    except Exception:  # noqa: BLE001 - el registro nunca rompe la petición
        db.session.rollback()


def purge_old(days=RETENTION_DAYS):
    n = ActivityEvent.query.filter(ActivityEvent.created_at < _now() - timedelta(days=days)).delete(
        synchronize_session=False
    )
    db.session.commit()
    return n
