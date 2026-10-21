"""Quién recibe qué, según su rol (PRP 011 · audiencia por rol).

Regla general: lo técnico (servidor, latencia, red, accesos, IA) es solo para el equipo que administra el sistema;
lo clínico y operativo, para quien lo atiende; lo del paciente, para el paciente o su apoderado. Un terapeuta nunca
recibe un aviso de latencia del servidor, aunque por error lo hayan puesto como responsable de esa incidencia.
"""

STAFF = frozenset({'admin', 'supervisor'})

# Categorías de incidencia que son del sistema (no de la atención).
TECH_CATEGORIES = frozenset({'SOFTWARE', 'HARDWARE', 'RED', 'ACCESOS'})
# Subcategorías que crea la detección automática (CrisisMonitor / incident_detection_service).
AUTO_SUBCATEGORIES = ('api_', 'latency', 'latencia', 'timeout', 'db_', 'disk', 'memory', 'cpu', 'error_rate')

# Tipo de aviso (notification_kinds / correos) → roles que pueden recibirlo.
KIND_ROLES = {
    'server.alert': STAFF,
    'mimo.paused': STAFF,
    'sla.breach': STAFF,
    'incident.escalated': STAFF,
    'report.ready': STAFF,
    'payment.overdue': STAFF,  # el resumen de cuotas vencidas (al paciente le llega su propio recordatorio)
    'payroll.due': STAFF | {'terapista'},
    'crisis.alert': STAFF | {'terapista'},
    'security.event': STAFF | {'terapista', 'jugador'},  # cada quien el de su propia cuenta
}


def is_technical_incident(incidente):
    cat = (getattr(incidente, 'categoria', '') or '').upper()
    sub = (getattr(incidente, 'subcategoria', '') or '').lower()
    return cat in TECH_CATEGORIES or any(sub.startswith(p) or p in sub for p in AUTO_SUBCATEGORIES)


def incident_roles(incidente):
    """Roles que pueden recibir avisos de esta incidencia (además de quien la reportó, por su propio caso)."""
    return STAFF if is_technical_incident(incidente) else STAFF | {'terapista'}


def may_receive_incident(user, incidente):
    return bool(user and user.is_active is not False and user.role in incident_roles(incidente))


def may_receive_kind(user, kind):
    roles = KIND_ROLES.get(kind)
    return bool(user) and (roles is None or user.role in roles)
