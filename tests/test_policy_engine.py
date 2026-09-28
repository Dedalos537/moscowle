"""Pruebas del motor de politica (aislamiento por fila).

Comprobado en produccion antes de este trabajo: get_payment_history(patient_id)
no comparaba el paciente pedido con quien pregunta, asi que un terapeuta podia
leer los pagos de CUALQUIER paciente. Los permisos por rol existian; los
permisos por fila no.

Regla acordada: el terapeuta solo ve sus pacientes asignados. Supervisor y
admin mantienen vista global. El jugador solo se ve a si mismo.
"""

import pytest


class TestAlcanceDeFilas:
    def test_el_admin_no_tiene_restriccion(self, policy):
        assert policy.allowed_patient_ids('admin', 1) is None

    def test_el_supervisor_no_tiene_restriccion(self, policy):
        assert policy.allowed_patient_ids('supervisor', 2) is None

    def test_el_terapista_solo_ve_sus_pacientes(
        self, policy, therapist_with_patients, patient_of_therapist,
    ):
        ids = policy.allowed_patient_ids('terapista', therapist_with_patients.id)
        assert ids is not None, 'el terapeuta debe tener un conjunto acotado'
        assert patient_of_therapist.id in ids
        assert ids == {patient_of_therapist.id}, f'vio pacientes de mas: {ids}'

    def test_el_jugador_solo_se_ve_a_si_mismo(self, policy):
        assert policy.allowed_patient_ids('jugador', 42) == {42}

    def test_un_terapista_no_puede_ver_un_paciente_ajeno(self, policy, therapist_with_patients, other_patient):
        assert not policy.can_access_patient('terapista', therapist_with_patients.id, other_patient.id)


class TestBloqueoDeArgumentos:
    def test_terapista_no_puede_pedir_pagos_de_otro_paciente(self, policy, therapist_with_patients, other_patient):
        permitido, args, motivo = policy.check(
            'get_payment_history', {'patient_id': other_patient.id},
            role='terapista', user_id=therapist_with_patients.id,
        )
        assert not permitido
        assert 'paciente' in motivo.lower()

    def test_terapista_si_puede_pedir_pagos_de_su_paciente(self, policy, therapist_with_patients, patient_of_therapist):
        permitido, args, motivo = policy.check(
            'get_payment_history', {'patient_id': patient_of_therapist.id},
            role='terapista', user_id=therapist_with_patients.id,
        )
        assert permitido, motivo

    def test_el_jugador_no_puede_leer_ningun_otro_paciente(self, policy, patient_of_therapist):
        permitido, _, motivo = policy.check(
            'get_payment_history', {'patient_id': patient_of_therapist.id},
            role='jugador', user_id=999,
        )
        assert not permitido

    def test_el_admin_puede_ver_cualquier_paciente(self, policy, other_patient):
        permitido, _, _ = policy.check(
            'get_payment_history', {'patient_id': other_patient.id}, role='admin', user_id=1,
        )
        assert permitido

    def test_una_tool_sin_paciente_no_se_afecta(self, policy, therapist_with_patients):
        permitido, _, motivo = policy.check(
            'list_sedes', {}, role='terapista', user_id=therapist_with_patients.id,
        )
        assert permitido, motivo


class TestFiltradoDeResultados:
    def test_list_patients_del_terapista_solo_trae_sus_pacientes(
        self, policy, therapist_with_patients, patient_of_therapist, other_patient,
    ):
        resultado = {
            'success': True,
            'count': 2,
            'patients': [
                {'id': patient_of_therapist.id, 'username': 'suyo'},
                {'id': other_patient.id, 'username': 'ajeno'},
            ],
        }
        filtrado = policy.filter_result(
            'list_patients', resultado, role='terapista', user_id=therapist_with_patients.id,
        )
        ids = {p['id'] for p in filtrado['patients']}
        assert ids == {patient_of_therapist.id}
        assert filtrado['count'] == 1, 'el count debe corresponder a lo filtrado'

    def test_el_admin_ve_el_listado_completo(self, policy, patient_of_therapist, other_patient):
        resultado = {'patients': [{'id': patient_of_therapist.id}, {'id': other_patient.id}]}
        filtrado = policy.filter_result('list_patients', resultado, role='admin', user_id=1)
        assert len(filtrado['patients']) == 2

    def test_sesiones_del_terapista_solo_suyas(
        self, policy, therapist_with_patients, patient_of_therapist, other_patient,
    ):
        resultado = {
            'sessions': [
                {'id': 1, 'therapist_id': therapist_with_patients.id, 'patient_id': patient_of_therapist.id},
                {'id': 2, 'therapist_id': 999, 'patient_id': other_patient.id},
            ]
        }
        filtrado = policy.filter_result(
            'get_sessions_day', resultado, role='terapista', user_id=therapist_with_patients.id,
        )
        assert [s['id'] for s in filtrado['sessions']] == [1]

    def test_el_jugador_solo_ve_sus_propias_sesiones(self, policy):
        resultado = {
            'sessions': [
                {'id': 1, 'patient_id': 7},
                {'id': 2, 'patient_id': 8},
            ]
        }
        filtrado = policy.filter_result('get_sessions', resultado, role='jugador', user_id=7)
        assert [s['id'] for s in filtrado['sessions']] == [1]

    def test_una_tool_sin_datos_de_paciente_pasa_intacta(self, policy, therapist_with_patients):
        resultado = {'success': True, 'count': 2, 'sedes': [{'id': 1}, {'id': 2}]}
        assert policy.filter_result('list_sedes', resultado, role='terapista', user_id=therapist_with_patients.id) is resultado

    def test_el_filtrado_recalcula_count_si_existe(self, policy, therapist_with_patients, other_patient):
        resultado = {'count': 99, 'patients': [{'id': other_patient.id}]}
        filtrado = policy.filter_result('list_patients', resultado, role='terapista', user_id=therapist_with_patients.id)
        assert filtrado['patients'] == []
        assert filtrado['count'] == 0, 'un count de 99 sobre 0 filas delata la fuga'


class TestIntegracionConExecuteTool:
    def test_ejecutar_una_tool_ajena_a_rol_lo_bloquea(self, policy):
        from app.services.tools_registry import execute_tool

        r = execute_tool('get_payment_history', {'patient_id': 1}, user_id=500, role='jugador')
        assert 'error' in r
        assert 'permisos' in r['error'].lower()

    def test_el_mensaje_de_error_no_revela_ids_existentes(self, policy, other_patient):
        _, _, motivo = policy.check(
            'get_payment_history', {'patient_id': other_patient.id},
            role='terapista', user_id=9999,
        )
        # No debe confirmar si ese paciente existe: seria un oraculo de existencia.
        assert str(other_patient.id) not in motivo or 'no asignado' in motivo.lower()


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #
@pytest.fixture
def policy():
    from app.services.policy import get_policy

    return get_policy()


def _mk_user(session, username, email, role, **extra):
    """Crea un usuario y lo borra al terminar el test (la BD es de sesion)."""
    from app.models.user import User

    u = User(username=username, email=email, password='x', role=role, is_active=True, **extra)
    session.add(u)
    session.commit()
    return u


@pytest.fixture(autouse=True)
def _cleanup_users(db, session):
    """La BD de test es de sesion: sin esto el segundo test choca en UNIQUE."""
    from app.models.user import User

    usernames = [
        'terapista_scope', 'paciente_suyo', 'paciente_ajeno', 'paciente_secreto',
    ]
    yield
    # La politica cachea el alcance en flask.g, que en produccion es por
    # request pero aqui la app context es de sesion: hay que limpiarlo.
    from flask import g

    # dir(g) NO lista los atributos dinamicos de flask.g: hay que ir a __dict__.
    for attr in [a for a in g.__dict__ if a.startswith('_policy_scope_')]:
        delattr(g, attr)
    session.rollback()
    User.query.filter(User.username.in_(usernames)).delete(synchronize_session=False)
    session.commit()


@pytest.fixture
def therapist_with_patients(db, session):
    return _mk_user(session, 'terapista_scope', 'ts@x.com', 'terapista')


@pytest.fixture
def patient_of_therapist(db, session, therapist_with_patients):
    return _mk_user(
        session, 'paciente_suyo', 'ps@x.com', 'jugador',
        assigned_therapist_id=therapist_with_patients.id,
    )


@pytest.fixture
def other_patient(db, session):
    return _mk_user(session, 'paciente_ajeno', 'pa@x.com', 'jugador')


class TestCasosRealesDeProduccion:
    """Regresiones detectadas al verificar en el servidor real.

    1. get_sessions_day devuelve el paciente ANIDADO (patient: {id: 14}), no
       en patient_id plano. Con solo patient_id, el filtro no encontraba al
       dueño y ocultaba TODA la agenda de la terapeuta (count: 0 con 2
       sesiones reales).
    2. Los pacientes que una terapeuta atiende de verdad no siempre coinciden
       con User.assigned_therapist_id: Liam (14) y Valentina (42) tenian
       assigned_therapist_id=13 pero sus sesiones las impartia el terapeuta 1.
       El alcance tiene que derivarse tambien de las sesiones.
    """

    def test_el_alcance_incluye_a_quien_atiende_por_sesiones(
        self, policy, session, therapist_with_patients, patient_of_therapist,
    ):
        from datetime import datetime, timedelta

        from app.models.appointment import Appointment

        # Un paciente cuyo assigned_therapist_id NO es este terapeuta...
        huerfano = _mk_user(
            session, 'paciente_por_sesion', 'ph@x.com', 'jugador',
            assigned_therapist_id=999,
        )
        # ...pero con una sesion impartida por el terapeuta.
        session.add(
            Appointment(
                patient_id=huerfano.id,
                therapist_id=therapist_with_patients.id,
                title='Sesion impartida',
                start_time=datetime.utcnow() + timedelta(days=1),
                end_time=datetime.utcnow() + timedelta(days=1, hours=1),
                status='scheduled',
            )
        )
        session.commit()

        ids = policy.allowed_patient_ids('terapista', therapist_with_patients.id)
        assert huerfano.id in ids, (
            'el terapeuta no ve a quien atiende de verdad: '
            'assigned_therapist_id esta desactualizado'
        )

    def test_una_sesion_con_paciente_anidado_no_se_oculta(
        self, policy, session, therapist_with_patients, patient_of_therapist,
    ):
        """La forma real del payload: patient: {id, name} en vez de patient_id."""
        from datetime import datetime, timedelta

        from app.models.appointment import Appointment

        session.add(
            Appointment(
                patient_id=patient_of_therapist.id,
                therapist_id=therapist_with_patists if False else therapist_with_patients.id,
                title='Sesion',
                start_time=datetime.utcnow() + timedelta(days=1),
                end_time=datetime.utcnow() + timedelta(days=1, hours=1),
                status='scheduled',
            )
        )
        session.commit()

        resultado = policy.filter_result(
            'get_sessions_day',
            {'count': 1, 'sessions': [{'id': 1, 'patient': {'id': patient_of_therapist.id, 'name': 'x'}}]},
            role='terapista',
            user_id=therapist_with_patients.id,
        )
        assert len(resultado['sessions']) == 1, 'oculto una sesion legitima por buscar solo patient_id'
