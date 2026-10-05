"""Resolución de argumentos del router determinista + contexto de síntesis.

Regresión de producción (PRP 007): ``match_intent`` devolvía
``('list_users', None)`` para "cuántos terapeutas hay", así que la tool se
ejecutaba SIN filtro de rol y devolvía los 50 usuarios de todos los roles.
Ahora arg_spec='role' cruda con el enum real de la tool.
"""

from app.services.mcp_service import (
    _extract_role_arg,
    _force_intent_tool,
    tool_result_context,
)
from app.services.tool_intents import match_intent

ALLOWED = {'list_users', 'list_expenses', 'get_debtors', 'list_sedes'}


class TestMatchIntentArgSpec:
    def test_terapeutas_devuelve_spec_role(self):
        assert match_intent('cuántos terapeutas hay', ALLOWED) == ('list_users', 'role')

    def test_consulta_sin_rol_sigue_sin_spec(self):
        assert match_intent('cuántos usuarios hay', ALLOWED) == ('list_users', 'role')

    def test_tools_de_mes_conservan_arg_spec(self):
        assert match_intent('gastos de este mes', ALLOWED) == ('list_expenses', 'month')


class TestExtractRoleArg:
    def test_terapeutas_mapea_a_terapista(self):
        assert _extract_role_arg('cuántos terapeutas hay y cómo se llaman', 'list_users') == {'role': 'terapista'}

    def test_pacientes_mapea_a_jugador(self):
        assert _extract_role_arg('lista de pacientes activos', 'list_users') == {'role': 'jugador'}

    def test_administradores_mapea_a_admin(self):
        assert _extract_role_arg('cuántos administradores hay', 'list_users') == {'role': 'admin'}

    def test_sin_rol_en_el_mensaje_devuelve_vacio(self):
        assert _extract_role_arg('cuántos usuarios hay', 'list_users') == {}

    def test_tool_sin_param_role_devuelve_vacio(self):
        assert _extract_role_arg('cuántos terapeutas hay', 'get_debtors') == {}

    def test_valor_fuera_del_enum_no_se_envia(self):
        # 'bots' no existe en el enum de list_users: un valor fuera del enum
        # jamás debe construirse como argumento.
        assert _extract_role_arg('cuántos bots hay', 'list_users') == {}


class TestForceIntentTool:
    def _tools(self):
        return [
            {'function': {'name': 'list_users'}},
            {'function': {'name': 'list_expenses'}},
        ]

    def test_fuerza_list_users_con_filtro_de_rol(self):
        assert _force_intent_tool('cuántos terapeutas hay y cómo se llaman', self._tools(), 'admin') == (
            'list_users',
            {'role': 'terapista'},
        )

    def test_fuerza_list_users_sin_filtro_si_no_hay_rol(self):
        assert _force_intent_tool('cuántos usuarios hay', self._tools(), 'admin') == (
            'list_users',
            {},
        )

    def test_arg_spec_de_mes_sigue_funcionando(self):
        tool, args = _force_intent_tool('gastos de este mes', self._tools(), 'admin')
        assert tool == 'list_expenses'
        assert args.get('month', '').endswith('-' + __import__('datetime').datetime.now().strftime('%m'))


class TestToolResultContext:
    def test_exige_conteo_primero_y_copia_exacta(self):
        ctx = tool_result_context('list_users', '{"count": 12}')
        assert '[REAL Tool list_users result' in ctx
        assert 'Hay N' in ctx
        assert 'EXACTAMENTE' in ctx
        assert 'mostrando X de Y' in ctx

    def test_already_executed_prohibiere_repetir_la_tool(self):
        ctx = tool_result_context('list_users', '{}', already_executed=True)
        assert 'NO la llames de nuevo' in ctx
        assert 'NO la llames de nuevo' not in tool_result_context('list_users', '{}')
