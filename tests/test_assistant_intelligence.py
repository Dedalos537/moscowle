"""Correcciones de inteligencia del asistente (post-despliegue 302db8a7).

Regresiones de producción:
* Los modelos locales (qwen/minicpm) emiten cifras SIN espacio previo
  ("Hay4", "las14:58:47") -> normalize_number_spaces + evento 'final'.
* "en qué usuario estoy" forzaba list_users sin filtro -> ninguna tool.
* "cuánto se generó el mes de octubre" no matcheaba -> get_monthly_collection.
* "pacientes del terapeuta X" elegía get_player_stats global y el modelo
  atribuía el total del centro a la persona -> get_therapist_patients.
"""

from datetime import datetime

from app.services.mcp_service import (
    _extract_role_arg,
    _extract_therapist_arg,
    _force_intent_tool,
    normalize_number_spaces,
    tool_result_context,
)
from app.services.prompt_builder import LIMA_TZ
from app.services.tool_intents import match_intent

ALLOWED = {
    'list_users',
    'get_monthly_collection',
    'get_therapist_patients',
    'get_patient_stats',
    'get_patient_detail',
    'list_expenses',
}


class TestNormalizeNumberSpaces:
    def test_hay_con_cifra_separa(self):
        assert normalize_number_spaces('Hay4 pacientes de Manuel') == 'Hay 4 pacientes de Manuel'

    def test_fecha_y_hora_separan(self):
        assert normalize_number_spaces('domingo4 de octubre de2026') == 'domingo 4 de octubre de 2026'
        assert normalize_number_spaces('a las14:58:47') == 'a las 14:58:47'

    def test_email_no_se_toca(self):
        email = 'diego.adrenalina11@gmail.com'
        assert normalize_number_spaces(f'Correo: {email} y otros.') == f'Correo: {email} y otros.'

    def test_url_no_se_toca(self):
        url = 'https://moscowle.centrojuanpabloii.com/app/2026'
        assert normalize_number_spaces(f'Ver {url} ahora') == f'Ver {url} ahora'

    def test_texto_ya_espaciado_no_cambia(self):
        txt = 'Hay 4 pacientes el 4 de octubre a las 14:58'
        assert normalize_number_spaces(txt) == txt

    def test_idempotente(self):
        once = normalize_number_spaces('Se genero2 pagos en octubre2026')
        assert normalize_number_spaces(once) == once


class TestIdentityNoForce:
    def test_pregunta_de_identidad_no_fuerza_tools(self):
        tools = [{'function': {'name': 'list_users'}}, {'function': {'name': 'get_user_detail'}}]
        for msg in (
            'en qué usuario estoy conectado?',
            '¿qué usuario soy?',
            'en qué cuenta estoy',
            'qué rol tengo yo',
        ):
            assert _force_intent_tool(msg, tools, 'admin') is None, msg


class TestMonthlyCollectionIntent:
    def test_match_del_mes_nombrado(self):
        hit = match_intent('realmente quisiera saber cuánto se generó el mes de octubre', ALLOWED)
        assert hit == ('get_monthly_collection', 'month')

    def test_force_con_mes_de_octubre(self):
        now = datetime.now(LIMA_TZ)
        tools = [{'function': {'name': 'get_monthly_collection'}}]
        tool, args = _force_intent_tool('realmente quisiera saber cuánto se generó el mes de octubre', tools, 'admin')
        assert tool == 'get_monthly_collection'
        assert args == {'month': f'{now.year}-10'}

    def test_handler_acepta_month_como_yyyy_mm(self, app):
        from app.services.tools_registry import handle_get_monthly_collection

        now = datetime.now(LIMA_TZ)
        with app.app_context():
            result = handle_get_monthly_collection(month=f'{now.year}-10')
        assert result['success'] is True
        assert result['data']['month'] == 10
        assert result['data']['year'] == now.year


class TestTherapistPatientsIntent:
    def test_match_terapeuta_nombrado(self):
        hit = match_intent('cuántos pacientes tiene el terapeuta Manuel Centeno?', ALLOWED)
        assert hit == ('get_therapist_patients', 'therapist')

    def test_extract_terapeuta_con_nombre(self):
        assert _extract_therapist_arg('cuántos pacientes tiene el terapeuta Manuel Centeno?', 'admin') == {
            'therapist_name': 'Manuel Centeno'
        }
        assert _extract_therapist_arg('pacientes de la terapista Milagros', 'admin') == {'therapist_name': 'Milagros'}

    def test_extract_sin_nombre_usa_resolutor_vacio(self):
        assert _extract_therapist_arg('cuántos pacientes tiene el terapeuta?', 'admin') == {}

    def test_force_terapeuta_con_nombre(self):
        tools = [{'function': {'name': 'get_therapist_patients'}}]
        assert _force_intent_tool('cuántos pacientes tiene el terapeuta Manuel Centeno?', tools, 'admin') == (
            'get_therapist_patients',
            {'therapist_name': 'Manuel Centeno'},
        )

    def test_force_terapeuta_sin_nombre_no_fuerza(self):
        tools = [{'function': {'name': 'get_therapist_patients'}}]
        assert _force_intent_tool('cuántos pacientes tiene el terapeuta?', tools, 'admin') is None

    def test_stats_globales_no_atribuyen_a_persona(self):
        ctx = tool_result_context('get_patient_stats', '{"stats": {"total": 4}}')
        assert 'NO se lo atribuyas' in ctx


class TestRoleArgRegression:
    def test_list_users_sigue_con_spec_role(self):
        assert match_intent('cuántos terapeutas hay', ALLOWED) == ('list_users', 'role')
        assert _extract_role_arg('cuántos terapeutas hay', 'list_users') == {'role': 'terapista'}
