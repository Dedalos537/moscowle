"""Pruebas del matching de intencion a tools MCP (tool_intents).

Cubre la decision de que tool despertar para un mensaje en espanol, sin LLM.
La matriz es deliberadamente amplia: cada caso es una queja o confusion real
observada en conversaciones (sedes vs usuarios, resumen financiero vs
terapeuta, contadores vs listas, saludos que no deben invocar nada).
"""

import pytest

from app.services.tool_intents import build_intent_index, match_intent


def _match(msg: str):
    allowed = {e['name'] for e in build_intent_index()}
    got = match_intent(msg, allowed)
    return got[0] if got else None


# (mensaje, herramienta esperada)
INTENT_CASES = [
    # Sedes
    ('cuántas sedes hay', 'list_sedes'),
    ('que sedes tiene el centro', 'list_sedes'),
    ('lista de sedes', 'list_sedes'),
    ('dime las sedes del centro', 'list_sedes'),
    # Desglose por sede: alumnos y terapeutas (antes caía en el listado de pacientes)
    ('cuantos alumnos hay por sede', 'get_sede_stats'),
    ('cuántos alumnos hay por sede, asignados a qué terapeutas?', 'get_sede_stats'),
    ('pacientes por terapeuta en cada sede', 'get_sede_stats'),
    ('cuantos pacientes hay', 'get_patient_stats'),
    # Desempeño de sedes (Balanced Scorecard): no debe confundirse con la lista de sedes
    ('como va el desempeño de las sedes', 'get_sede_scorecard'),
    ('qué sede rinde mejor este mes', 'get_sede_scorecard'),
    ('cumplimiento de metas por sede', 'get_sede_scorecard'),
    ('balanced scorecard de cayma', 'get_sede_scorecard'),
    # Sesiones / agenda (con y sin pista temporal)
    ('sesiones de hoy', 'get_sessions_day'),
    ('que sesiones hay', 'get_sessions'),
    ('agenda de mañana', 'get_sessions_day'),
    ('sesiones del dia', 'get_sessions_day'),
    ('que hay el lunes', 'get_sessions_day'),
    # Conteos de pacientes
    ('cuántos pacientes hay', 'get_patient_stats'),
    ('numero de pacientes', 'get_patient_stats'),
    ('total de pacientes', 'get_patient_stats'),
    # Gastos
    ('gastos de setiembre', 'list_expenses'),
    ('gastos del mes', 'list_expenses'),
    ('gastos de este mes', 'list_expenses'),
    # Deudores / morosos (sin obligar a nombrar "deudores")
    ('cuánto debe juan', 'get_debtors'),
    ('reporte de morosos', 'get_debtors'),
    ('deudores por sede', 'get_debtors'),
    ('cuánta es la deuda total?', 'get_debtors'),
    ('cuántos pacientes deben', 'get_debtors'),
    ('quiénes adeudan pagos', 'get_debtors'),
    # Resumen financiero (entidad "financiero" no bloquea ingresos/ganancia)
    ('resumen financiero', 'get_financial_summary'),
    ('ingresos del mes', 'get_financial_summary'),
    ('finanzas del centro', 'get_financial_summary'),
    ('crecimiento de usuarios', 'get_user_growth'),
    # Cobranza del mes no se pierde detras del resumen financiero
    ('recaudacion del mes', 'get_monthly_collection'),
    ('cobrado este mes', 'get_monthly_collection'),
    # Conteos de usuarios por rol (list_users, no stats de terapeuta)
    ('cuántos terapeutas hay', 'list_users'),
    ('cuántos jugadores hay', 'list_users'),
    ('cuantos admins hay', 'list_users'),
    ('lista de admins', 'list_users'),
    ('usuarios activos', 'list_users'),
    # Creacion de grupo exige frase fuerte
    (
        'crea un grupo de pedro y luna y se hacen 3 sesiones el lunes',
        'create_group_sessions',
    ),
    # Conversacion comun: ninguna tool
    ('hola que tal', None),
    ('gracias, hasta luego', None),
    ('me puedes ayudar con una duda', None),
    ('cuál es tu nombre', None),
    ('como estas hoy', None),
    ('escribe un correo al cliente', None),
    ('elimina el usuario 4', None),
]


class TestMatchIntent:
    @pytest.mark.parametrize('msg,expected', INTENT_CASES)
    def test_mensaje_mapea_a_la_tool_esperada(self, msg, expected):
        assert _match(msg) == expected

    def test_entidad_ajena_no_se_fuerza(self):
        """'resumen financiero' no debe caer en get_therapist_financials."""
        assert _match('resumen financiero') == 'get_financial_summary'

    def test_metrica_sin_consulta_de_conteo_no_despierta(self):
        """get_user_growth (metricas) solo con crecimiento/medida, no con 'resumen'."""
        assert _match('crecimiento de usuarios') == 'get_user_growth'
        assert _match('usuarios activos') == 'list_users'

    def test_escribir_no_desperta_tools_de_lectura(self):
        assert _match('escribe un correo al cliente') is None

    def test_indice_construye_sin_errores(self):
        index = build_intent_index()
        assert index
        for entry in index:
            assert entry['name']
            assert 'primary_noun' in entry
            assert 'entities' in entry


class TestIndiceGenerado:
    def test_cada_tool_core_de_lectura_genera_frases(self):
        """Cobertura: ninguna tool CORE de lectura se queda sin frases."""
        from app.services.tools_registry import CORE_TOOL_NAMES, TOOL_REGISTRY

        index = {e['name']: e for e in build_intent_index(tuple(CORE_TOOL_NAMES))}
        faltantes = []
        for name in CORE_TOOL_NAMES:
            entry = TOOL_REGISTRY.get(name)
            if not entry or entry.get('category') == 'write':
                continue
            if name not in index or not index[name]['phrases']:
                faltantes.append(name)
        assert not faltantes, f'tools sin frases generadas: {faltantes}'

    def test_indice_no_contiene_tools_de_escritura(self):
        from app.services.tools_registry import TOOL_REGISTRY

        index = build_intent_index()
        for entry in index:
            assert TOOL_REGISTRY[entry['name']].get('category') != 'write' or entry['name'] == 'create_group_sessions'


@pytest.mark.parametrize(
    'msg',
    [
        'reprograma la sesión 45 para el viernes',
        'cambia el teléfono del usuario 7',
        'edita el gasto 12 a 200 soles',
        'mueve la sesión de hoy a las 5',
        'cancela la sesión de mañana',
        'anula el gasto 3',
        'desactiva al usuario 9',
        'completa la sesión de hoy',
    ],
)
def test_verbo_de_escritura_nunca_fuerza_una_lectura(msg):
    """Una orden de modificar no debe resolverse con una tool de lectura
    determinista: la decide el LLM (que pasa por la puerta de confirmacion)."""
    assert _match(msg) in (None, 'create_group_sessions')
