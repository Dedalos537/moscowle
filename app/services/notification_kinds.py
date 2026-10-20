"""Tipos de notificación y cómo se muestra cada uno (PRP 011 · E2).

Fuente única de verdad: cada `kind` dice en qué formas se presenta (badge, toast, snackbar, banner, modal, push),
su ícono y su acción. El frontend (`core/notifications/notification-kinds.ts`) usa el mismo catálogo: el backend
lo sirve en `GET /api/notifications/kinds` y manda `kind` + `presentation` en cada evento.

Mientras se migran las llamadas a `notify_user`, el `kind` se infiere del `event_type` o de la categoría; lo que no
se reconozca queda como `legacy` (se ve como hasta ahora).
"""

BADGE, TOAST, SNACKBAR, BANNER, MODAL, PUSH = 'badge', 'toast', 'snackbar', 'banner', 'modal', 'push'
PRESENTATIONS = (BADGE, TOAST, SNACKBAR, BANNER, MODAL, PUSH)


def _k(category, presentation, icon, action=None, push_when='hidden'):
    """`push_when`: 'hidden' = solo si la pestaña no está visible; 'always' = también con la app abierta."""
    return {
        'category': category,
        'presentation': tuple(presentation),
        'icon': icon,
        'action': action,
        'push_when': push_when,
    }


KINDS = {
    'message.new': _k('message', [BADGE, SNACKBAR, PUSH], 'comment-dots', 'Abrir chat'),
    'payment.received': _k('payment', [BADGE, SNACKBAR], 'circle-check', 'Ver pago'),
    'payment.due': _k('payment', [BADGE], 'calendar-day'),
    'payment.overdue': _k('payment', [BADGE, BANNER], 'triangle-exclamation', 'Ver cobranza'),
    'payroll.due': _k('payment', [BADGE, SNACKBAR], 'hand-holding-dollar', 'Pagar'),
    'session.created': _k('session', [BADGE, SNACKBAR], 'calendar-plus', 'Ver agenda'),
    'session.rescheduled': _k('session', [BADGE, SNACKBAR], 'calendar-day', 'Ver agenda'),
    'session.cancelled': _k('session', [BADGE, SNACKBAR, PUSH], 'calendar-xmark', 'Ver agenda'),
    'session.completed': _k('session', [BADGE], 'calendar-check'),
    'game.completed': _k('activity', [BADGE], 'gamepad'),
    'incident.new': _k('alert', [BADGE, SNACKBAR], 'circle-exclamation', 'Ver incidencia'),
    'incident.escalated': _k('alert', [BADGE, BANNER, PUSH], 'triangle-exclamation', 'Ver incidencia'),
    'sla.breach': _k('alert', [BADGE, BANNER, PUSH], 'stopwatch', 'Ver incidencia'),
    'crisis.alert': _k('alert', [BADGE, BANNER, MODAL, PUSH], 'heart-pulse', 'Ver paciente', 'always'),
    'server.alert': _k('system', [BADGE, BANNER], 'server', 'Ver estado del servidor'),
    'mimo.paused': _k('system', [BADGE, BANNER], 'robot'),
    'security.event': _k('security', [BADGE, MODAL, PUSH], 'shield-halved', 'Revisar', 'always'),
    'report.ready': _k('report', [BADGE, TOAST], 'file-lines', 'Abrir reporte'),
    'contact.lead': _k('contact', [BADGE, SNACKBAR, PUSH], 'envelope-open-text', 'Ver solicitud'),
    'task.assigned': _k('task', [BADGE, SNACKBAR], 'list-check', 'Ver tarea'),
    'task.updated': _k('task', [BADGE], 'list-check'),
    'user.changed': _k('system', [BADGE], 'user-gear'),
    'broadcast': _k('system', [BADGE, SNACKBAR], 'tower-broadcast', 'Ver'),
    'chatbot.action': _k('system', [BADGE], 'robot'),
    'whatsapp.reminder': _k('payment', [BADGE], 'comment-dollar'),
    'action.confirmed': _k('system', [TOAST], 'circle-check'),
    'legacy': _k('system', [BADGE], 'bell'),
}

# event_type actual (notification_intelligence.compute_group_key) → kind.
EVENT_TO_KIND = {
    'message': 'message.new',
    'session_created': 'session.created',
    'session_updated': 'session.rescheduled',
    'session_completed': 'session.completed',
    'session_deleted': 'session.cancelled',
    'game_completed': 'game.completed',
    'payment_due': 'payment.due',
    'payment_overdue': 'payment.overdue',
    'incident': 'incident.new',
    'incident_escalation': 'incident.escalated',
    'sla_breach': 'sla.breach',
    'security': 'security.event',
    'report': 'report.ready',
    'contact': 'contact.lead',
    'user_assigned': 'user.changed',
    'user_toggle': 'user.changed',
    'user_deleted': 'user.changed',
    'chatbot_action': 'chatbot.action',
    'broadcast': 'broadcast',
    'whatsapp_reminder': 'whatsapp.reminder',
    'task_created': 'task.assigned',
    'task_updated': 'task.updated',
    'task_moved': 'task.updated',
    'task_deleted': 'task.updated',
}


def resolve_kind(kind=None, event_type=None, category=None, metadata=None):
    """El `kind` explícito gana; si no, se infiere del event_type; si no, `legacy`."""
    if kind in KINDS:
        return kind
    meta_kind = (metadata or {}).get('kind') if isinstance(metadata, dict) else None
    if meta_kind in KINDS:
        return meta_kind
    if event_type in EVENT_TO_KIND:
        return EVENT_TO_KIND[event_type]
    if (metadata or {}).get('alertname') if isinstance(metadata, dict) else False:
        return 'server.alert'
    return 'legacy'


def presentation_for(kind, priority='normal', resolved=False):
    """Formas en que se muestra. `urgent` sube a banner + push; `high` agrega snackbar si no tenía interrupción."""
    spec = KINDS.get(kind, KINDS['legacy'])
    shown = list(spec['presentation'])
    if resolved:
        # Un «resuelto» (p. ej. servidor recuperado) avisa sin alarmar: quita banner/modal, deja un toast.
        shown = [p for p in shown if p not in (BANNER, MODAL)]
        if TOAST not in shown:
            shown.append(TOAST)
    elif priority == 'urgent':
        for p in (BANNER, PUSH):
            if p not in shown:
                shown.append(p)
    elif priority == 'high' and not ({TOAST, SNACKBAR, BANNER, MODAL} & set(shown)):
        shown.append(TOAST)
    if BADGE not in shown and kind != 'action.confirmed':
        shown.insert(0, BADGE)
    return shown


def describe(kind, priority='normal', link=None, resolved=False):
    spec = KINDS.get(kind, KINDS['legacy'])
    action = {'label': spec['action'], 'link': link} if spec['action'] and link else None
    return {
        'kind': kind,
        'presentation': presentation_for(kind, priority, resolved),
        'icon': spec['icon'],
        'action': action,
        'push_when': spec['push_when'],
    }


def catalog():
    """Para el frontend: el catálogo completo (`GET /api/notifications/kinds`)."""
    return {
        k: {
            'category': v['category'],
            'presentation': list(v['presentation']),
            'icon': v['icon'],
            'action': v['action'],
            'push_when': v['push_when'],
        }
        for k, v in KINDS.items()
    }
