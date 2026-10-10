"""Estado del paciente: una sola regla para `account_status` (lo que ve la coordinación) e `is_active`.

Antes se cambiaban por separado: la pantalla de Usuarios solo tocaba `account_status`, así que un paciente
«Activo» podía seguir con is_active=False (y el alta de sesiones lo rechazaba con 400) y uno «Retirado» seguía
recibiendo sesiones. Regla: activo y deudor siguen en atención; inactivo y retirado no.
"""

STATUSES = ('active', 'inactive', 'debtor', 'retired')
ATTENDING = ('active', 'debtor')


def apply_account_status(user, status):
    """Fija el estado visible y deja is_active coherente con él."""
    status = (status or 'active').strip().lower()
    if status not in STATUSES:
        raise ValueError('Estado inválido')
    user.account_status = status
    user.is_active = status in ATTENDING
    return status


def apply_is_active(user, active):
    """Activar/desactivar desde un interruptor: el estado visible acompaña sin perder «deudor» o «retirado»."""
    active = bool(active)
    user.is_active = active
    current = (user.account_status or 'active').lower()
    if active and current not in ATTENDING:
        user.account_status = 'active'
    elif not active and current in ATTENDING:
        user.account_status = 'inactive'


def sync_patient_statuses(db):
    """Corrige pacientes desfasados (idempotente). Manda el estado visible; si no hay, se toma is_active."""
    from app.models.user import User

    changed = 0
    for u in User.query.filter(User.role == 'jugador').all():
        if not u.account_status:
            u.account_status = 'active' if u.is_active is not False else 'inactive'
            changed += 1
        want = u.account_status in ATTENDING
        if bool(u.is_active) != want or u.is_active is None:
            u.is_active = want
            changed += 1
    if changed:
        db.session.commit()
    return changed
