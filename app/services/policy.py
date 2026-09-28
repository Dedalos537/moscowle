"""Motor de politica: aislamiento por fila del acceso a datos.

Estado previo (comprobado en produccion): los permisos eran solo por rol. Un
terapista podia pedir get_payment_history(patient_id) de CUALQUIER paciente,
porque execute_tool solo comparaba el rol contra tool.roles y jamas comparaba
la fila.

Este modulo separa 'puede usar esta tool' (que ya existia) de 'puede ver este
registro' (que no existia). Son dos preguntas distintas y hacen falta las dos:

    check()         -> puedo pedir estos argumentos?
    filter_result() -> de lo que me devolvieron, que filas puedo ver?

Las dos se aplican en execute_tool, de forma que ningun handler puede saltarse
la politica por forgetting de filtrar: el filtro se aplica DESPUES del handler,
sobre el resultado, no dentro de el.

Nota sobre rendimiento: allowed_patient_ids() se calcula una vez por peticion y
se cachea por (role, user_id) durante la vida del request, para no repetir la
consulta por cada tool del turno.
"""

from flask import g

# Tools cuyo resultado es una coleccion de pacientes y hay que acotar.
_PATIENT_COLLECTION_TOOLS = {
    'list_patients',
    'search_patients',
    'get_debtors',
    'get_user_growth',
    'get_patient_stats',
}

# Tools cuyo resultado son filas que pertenecen a un paciente o terapeuta.
_SCOPED_ROW_TOOLS = {
    'get_sessions',
    'get_sessions_day',
    'get_payment_history',
    'get_upcoming_installments',
    'get_due_installments',
    'get_contracts_filtered',
    'get_contract_detail',
    'list_contracts',
    'get_therapist_patients',
}

# Claves bajo las que suele venir la coleccion a filtrar.
_COLLECTION_KEYS = (
    'patients', 'sessions', 'payments', 'installments', 'contracts',
    'results', 'items', 'debtors', 'data', 'groups',
)

# Que clave de la fila identifica a SU DONO, por tool. En 'list_patients' la
# fila ES el paciente, asi que el id de la fila es el id del paciente; en
# 'get_sessions' hay que mirar la columna del paciente o del terapeuta.
_ROW_OWNER_KEY = {
    'list_patients': 'id',
    'search_patients': 'id',
    'get_debtors': 'id',
    'get_patient_stats': 'id',
    'get_sessions': 'patient_id',
    'get_sessions_day': 'patient_id',
    'get_payment_history': 'patient_id',
    'get_upcoming_installments': 'patient_id',
    'get_due_installments': 'patient_id',
    'get_contracts_filtered': 'patient_id',
    'get_contract_detail': 'patient_id',
    'list_contracts': 'patient_id',
    'get_therapist_patients': 'id',
}

# Tools que no tocan datos de paciente: pasan intactas.
_PUBLIC_TOOLS = {'list_sedes', 'get_current_datetime', 'get_notifications', 'mark_notifications_read'}


def _cache_key(role, user_id):
    return f'_policy_scope_{role}_{user_id}'


def _get_cached(role, user_id):
    return getattr(g, _cache_key(role, user_id), None)


def _set_cached(role, user_id, value):
    try:
        setattr(g, _cache_key(role, user_id), value)
    except Exception:
        pass


class PolicyEngine:
    """Aplica la politica de alcance de filas. Sin estado entre peticiones."""

    # ------------------------------------------------------------------ #
    # Alcance
    # ------------------------------------------------------------------ #
    def allowed_patient_ids(self, role, user_id):
        """Ids de paciente visibles. None = sin restriccion.

        admin y supervisor: global (gestion del centro).
        terapista: solo los pacientes que tiene asignados.
        jugador: unicamente el mismo.
        """
        if role in ('admin', 'supervisor'):
            return None
        if user_id is None:
            return set()
        cached = _get_cached(role, user_id)
        if cached is not None:
            return cached
        try:
            from app.extensions import db
            from app.models.user import User
        except Exception:
            return set()
        try:
            if role == 'jugador':
                scope = {int(user_id)}
            else:
                rows = db.session.query(User.id).filter(
                    User.role == 'jugador',
                    User.assigned_therapist_id == int(user_id),
                    User.is_active.is_(True),
                ).all()
                scope = {r[0] for r in rows}
                # assigned_therapist_id esta desactualizado en produccion
                # (Liam y Valentina apuntaban al terapeuta 13 pero sus sesiones
                # las impartia el 1). Un terapeuta DEBE ver a quien atiende de
                # verdad, asi que el alcance se completa con sus sesiones.
                try:
                    from app.models.appointment import Appointment

                    atendidos = (
                        db.session.query(Appointment.patient_id)
                        .filter(
                            Appointment.therapist_id == int(user_id),
                            Appointment.status != 'cancelled',
                        )
                        .distinct()
                        .all()
                    )
                    scope |= {r[0] for r in atendidos if r[0] is not None}
                except Exception:
                    pass
        except Exception:
            scope = set()
        _set_cached(role, user_id, scope)
        return scope

    def can_access_patient(self, role, user_id, patient_id):
        scope = self.allowed_patient_ids(role, user_id)
        if scope is None:
            return True
        try:
            return int(patient_id) in scope
        except (TypeError, ValueError):
            return False

    def is_own_patient(self, role, user_id, patient_id):
        try:
            return int(patient_id) == int(user_id)
        except (TypeError, ValueError):
            return False

    # ------------------------------------------------------------------ #
    # Chequeo de argumentos (antes de ejecutar)
    # ------------------------------------------------------------------ #
    def check(self, tool_name, args, role, user_id):
        """Devuelve (permitido, args, motivo).

        No revela en el motivo si el paciente existe: confirmar la existencia
        de un id ajeno ya seria una fuga, asi que el mensaje es el mismo exista
        o no.
        """
        if tool_name in _PUBLIC_TOOLS:
            return True, args, ''
        args = args or {}
        scope = self.allowed_patient_ids(role, user_id)
        if scope is None:
            return True, args, ''

        for key in ('patient_id', 'user_id', 'paciente_id'):
            if key not in args or args[key] in (None, ''):
                continue
            value = args[key]
            # Solo hay que comprobarlo si el id se refiere a un paciente.
            if key == 'patient_id' or self._looks_like_patient_id(value):
                if not self.can_access_patient(role, user_id, value):
                    return (
                        False,
                        args,
                        'No tienes acceso a ese paciente: no esta en tu alcance.',
                    )
        return True, args, ''

    def _looks_like_patient_id(self, value):
        try:
            int(value)
            return True
        except (TypeError, ValueError):
            return False

    # ------------------------------------------------------------------ #
    # Filtrado de resultados (despues de ejecutar)
    # ------------------------------------------------------------------ #
    def filter_result(self, tool_name, result, role, user_id):
        """Acota las filas que el handler devolvio.

        Se aplica sobre el resultado y no dentro de cada handler, de modo que un
        handler nuevo no pueda saltarselo por olvido.
        """
        if not isinstance(result, dict):
            return result
        if tool_name in _PUBLIC_TOOLS:
            return result
        scope = self.allowed_patient_ids(role, user_id)
        if scope is None:
            return result
        if tool_name not in _PATIENT_COLLECTION_TOOLS and tool_name not in _SCOPED_ROW_TOOLS:
            return result

        for key in _COLLECTION_KEYS:
            filas = result.get(key)
            if not isinstance(filas, list):
                continue
            filtradas = [f for f in filas if self._row_visible(f, tool_name, role, user_id, scope)]
            if len(filtradas) == len(filas):
                continue
            result = dict(result)
            result[key] = filtradas
            # El count tiene que acompanar al filtrado: si no, el bot ve
            # "count: 99" con 0 filas y eso ya es una pista de la fuga.
            for counter in ('count', 'total', 'total_payments', 'total_sessions'):
                if counter in result and isinstance(result[counter], int):
                    result[counter] = len(filtradas)
                    break
        return result

    def _row_visible(self, row, tool_name, role, user_id, scope):
        """Una fila es visible si su dueño esta en el alcance.

        Para el terapeuta hay dos caminos legitimos: que el paciente sea suyo,
        o que el sea quien imparte la sesion. En la practica coinciden, pero
        durante una reasignacion no, y negar el trabajo que el propio terapeuta
        esta haciendo seria tan incorrecto como exponerlo.
        """
        if not isinstance(row, dict):
            return False
        owner_key = _ROW_OWNER_KEY.get(tool_name, 'patient_id')
        raw = row.get(owner_key)
        if raw is None:
            # El paciente suele venir anidado: {'patient': {'id': 14, ...}}.
            # get_sessions_day lo devuelve asi, y buscar solo en patient_id
            # ocultaba la agenda entera de la terapeuta.
            anidado = row.get('patient')
            if isinstance(anidado, dict):
                raw = anidado.get('id')
            elif isinstance(row.get('paciente'), dict):
                raw = row['paciente'].get('id')
        try:
            owner_id = int(raw) if raw is not None else None
        except (TypeError, ValueError):
            return False
        if owner_id is None:
            # Sin propietario identificable no se puede probar la pertenencia:
            # no se expone.
            return False
        if owner_id in scope:
            return True
        if role == 'terapista' and owner_id == int(user_id):
            return True
        # El terapeuta tambien ve las filas donde el aparece como terapeuta.
        if role == 'terapista':
            for key in ('therapist_id', 'terapista_id'):
                val = row.get(key)
                try:
                    if val is not None and int(val) == int(user_id):
                        return True
                except (TypeError, ValueError):
                    continue
        return False


_policy = PolicyEngine()


def get_policy():
    return _policy
