"""Pruebas de exposicion de tools por rol.

El paciente (rol 'jugador') debe quedarse con el chatbot informativo: datos de
la sede, su hora y sus propias notificaciones. Las tools que leen o escriben
datos de la BD (listados, sesiones, pagos, mensajes masivos) no deben estar
disponibles para ese rol, porque varias no filtran por el usuario solicitante:
por ejemplo get_payment_history(patient_id) devolvia el historial de pagos de
CUALQUIER paciente y register_payment(patient_id)Writing pagos de cualquiera.
"""

import pytest

from app.services.tools_registry import (
    ROLES_ALL,
    TOOL_REGISTRY,
    execute_tool,
    get_tools_for_mode,
)

# Tools que el chatbot informativo del paciente puede seguir usando
PERMITIDAS_PACIENTE = {
    'get_current_datetime',
    'get_notifications',
    'mark_notifications_read',
    'list_sedes',
}

# Tools que exponen datos o escrituras de la BD: solo personal
STAFF_ONLY = {
    'search_patients',
    'list_users',
    'get_sessions',
    'get_payment_history',
    'register_payment',
    'broadcast_message',
    'list_patients',
    'get_sessions_day',
    'list_patient_groups',
    'send_direct_message',
}


class TestToolsNoExpuestasAlPaciente:
    @pytest.mark.parametrize('name', sorted(STAFF_ONLY))
    def test_no_esta_en_la_lista_del_paciente(self, name):
        assert 'jugador' not in TOOL_REGISTRY[name]['roles'], (
            f'{name} sigue disponible para el rol jugador'
        )

    def test_el_paciente_no_recibe_tools_de_la_bd(self):
        tools = {t['function']['name'] for t in get_tools_for_mode('grande', 'jugador')}
        filtradas = tools & STAFF_ONLY
        assert not filtradas, f'el paciente todavia recibe: {sorted(filtradas)}'

    def test_el_paciente_conserva_el_chatbot_informativo(self):
        tools = {t['function']['name'] for t in get_tools_for_mode('grande', 'jugador')}
        assert tools == PERMITIDAS_PACIENTE, (
            f'se perdio o se sumo una tool para el paciente: {sorted(tools)}'
        )

    def test_el_staff_conserva_su_acceso(self):
        """Restringir al paciente no debe quitarle nada al personal."""
        for rol in ('admin', 'supervisor', 'terapista'):
            tools = {t['function']['name'] for t in get_tools_for_mode('grande', rol)}
            faltan = STAFF_ONLY - tools
            assert not faltan, f'el rol {rol} perdio: {sorted(faltan)}'

    def test_escrituras_abiertas_al_paciente_son_solo_las_seguras(self):
        """De las tools de escritura, el paciente solo usa las que ya son
        seguras por construccion:sobre sus propias notificaciones
        (mark-read pasa su _user_id y la API filtra por el usuario)."""
        seguras = {'mark_notifications_read'}
        exposed = {
            name
            for name, entry in TOOL_REGISTRY.items()
            if entry['category'] == 'write' and 'jugador' in entry['roles']
        }
        assert exposed <= seguras, f'escrituras abiertas al paciente: {sorted(exposed - seguras)}'
        assert not (exposed - seguras), 'el paciente no deberia escribir datos del centro'

    def test_no_queda_ninguna_tool_abierta_a_todos_menos_las_cuatro(self):
        abiertas = [n for n, v in TOOL_REGISTRY.items() if set(v['roles']) == ROLES_ALL]
        assert sorted(abiertas) == sorted(PERMITIDAS_PACIENTE), (
            f'quedan tools sin restringir: {sorted(abiertas)}'
        )


class TestEjecucionRechazadaPorRol:
    @pytest.mark.parametrize('name', sorted(STAFF_ONLY))
    def test_execute_tool_rechaza_al_paciente(self, name):
        resultado = execute_tool(name, {}, user_id=1, role='jugador')
        assert 'error' in resultado, f'{name} se ejecuto con rol jugador'
        assert 'permisos' in str(resultado['error']).lower()

    def test_lectura_de_pagos_de_otro_paciente_bloqueada(self):
        """El ataque concreto: pedir el historial de pagos de otro paciente."""
        resultado = execute_tool('get_payment_history', {'patient_id': 14}, user_id=1, role='jugador')
        assert 'error' in resultado
        assert 'permisos' in str(resultado['error']).lower()

    def test_registro_de_pago_bloqueado(self):
        resultado = execute_tool(
            'register_payment',
            {'patient_id': 14, 'amount': 1, 'method': 'Efectivo', 'payment_date': '2026-09-27'},
            user_id=1,
            role='jugador',
        )
        assert 'error' in resultado
        assert 'permisos' in str(resultado['error']).lower()


class TestSedesParaElPaciente:
    """Las sedes son informacion publica y el chatbot informativo las necesita.

    Regresion: la tool pedia /api/admin/sedes, que exige admin o supervisor, asi
    que para el rol jugador devolvia 403 y terminaba reportando 0 sedes, que es
    justamente el dato que hace que el bot invente una cantidad de sedes.
    """

    def test_el_paciente_recibe_las_sedes_reales(self, app, session):
        from app.models.user import Sede

        # is_active en NULL es un caso real de sedes creadas antes del default
        for nombre, activo in (('Sede Test Activa', True), ('Sede Test Null', None)):
            if not Sede.query.filter_by(name=nombre).first():
                session.add(Sede(name=nombre, address='Direccion de prueba', is_active=activo))
        session.commit()

        from app.services.tools_registry import execute_tool

        resultado = execute_tool('list_sedes', {}, user_id=1, role='jugador')

        assert 'error' not in resultado, resultado
        assert resultado['count'] >= 2, f'se perdieron las sedes: {resultado}'
        nombres = {s['name'] for s in resultado['sedes']}
        assert 'Sede Test Activa' in nombres
        assert 'Sede Test Null' in nombres, 'una sede con is_active NULL debe listarse'

    def test_una_sede_inactiva_no_se_lista(self, app, session):
        from app.models.user import Sede

        if not Sede.query.filter_by(name='Sede Test Inactiva').first():
            session.add(Sede(name='Sede Test Inactiva', address='x', is_active=False))
        session.commit()

        from app.services.tools_registry import execute_tool

        resultado = execute_tool('list_sedes', {}, user_id=1, role='jugador')

        nombres = {s['name'] for s in resultado['sedes']}
        # no puede pasar vacio: tiene que listar algo y descartar la inactiva
        assert 'Sede Test Activa' in nombres, 'no listo ninguna sede activa'
        assert 'Sede Test Inactiva' not in nombres, 'listo una sede desactivada'
