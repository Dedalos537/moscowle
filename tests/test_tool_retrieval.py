"""Pruebas del recuperador de herramientas.

Regresion del problema reportado: "cuantos alumnos hay por sede, asignados a que
terapeutas" devolvia las tools de 'usuarios' (search_patients, list_users,
create_user, delete_user...) y NUNCA ofrecia get_sede_stats, que es la tool
que responde exactamente eso. La causa era _select_local_tools, que solo hacia
coincidencia de palabras clave y seccionaba el catalogo al azar.

Estas pruebas fijan el comportamiento correcto del recuperador.
"""

import pytest

from app.services.retrieval import ToolRetriever
from app.services.tools_registry import TOOL_REGISTRY

# Consultas reales que fallaban, textuales.
CASOS = [
    # (consulta, tool que debe ganar, tools que NO debe ofrecer)
    (
        'cuántos alumnos hay por sede, asignados a qué terapeutas?',
        'get_sede_stats',
        {'delete_user', 'create_user'},
    ),
    (
        'cuántas sedes hay?',
        'list_sedes',
        set(),
    ),
    (
        'sedes talara y piura',
        'get_sede_stats',
        set(),
    ),
    (
        'cómo va el desempeño de la sede Cayma frente a las metas',
        'get_sede_scorecard',
        {'delete_user', 'create_user'},
    ),
    (
        'cuánto me deben los pacientes',
        'get_debtors',
        {'delete_user', 'cancel_contract'},
    ),
    (
        'quiero registrar un pago de 200 soles',
        'register_payment',
        set(),
    ),
    (
        'qué sesiones hay hoy',
        'get_sessions_day',
        set(),
    ),
    (
        'borrar el usuario de Juan',
        'delete_user',
        set(),
    ),
]


@pytest.fixture(scope='module')
def retriever():
    return ToolRetriever(TOOL_REGISTRY)


class TestRecuperacionDeIntencion:
    @pytest.mark.parametrize('consulta,esperada,prohibidas', CASOS)
    def test_encuentra_la_tool_correcta(self, retriever, consulta, esperada, prohibidas):
        nombres = [t.name for t in retriever.search(consulta, role='admin', k=6)]
        assert esperada in nombres, f'no ofrecio {esperada}. Ofrecio: {nombres}'

    @pytest.mark.parametrize('consulta,esperada,prohibidas', CASOS)
    def test_no_ofrece_tools_contrarias(self, retriever, consulta, esperada, prohibidas):
        nombres = {t.name for t in retriever.search(consulta, role='admin', k=6)}
        assert not (nombres & prohibidas), f'ofrecio tools contraindicadas: {nombres & prohibidas}'

    def test_una_consulta_de_conteo_no_ofrece_borrados(self, retriever):
        """El fallo original: preguntar 'cuántos' ofrecia delete_user."""
        for consulta in ('cuántos alumnos hay por sede', 'cuántas sedes hay', 'quién me debe'):
            nombres = {t.name for t in retriever.search(consulta, role='admin', k=6)}
            destructivas = {n for n in nombres if TOOL_REGISTRY[n]['category'] == 'write'} - {
                'register_payment',
                'edit_payment',
                'send_payment_reminder',
            }
            assert not destructivas, f'"{consulta}" ofrecio escrituras: {destructivas}'

    def test_una_consulta_de_escritura_no_ofrece_solo_lectura_pura(self, retriever):
        nombres = {t.name for t in retriever.search('elimina al paciente 45', role='admin', k=6)}
        assert nombres & {'delete_user', 'cancel_contract', 'delete_patient'}, nombres


class TestRecuperadorRespetaElRol:
    def test_el_paciente_nunca_ve_tools_de_escritura(self, retriever):
        for consulta in (
            'elimina al usuario 4',
            'borra el contrato',
            'registra un pago',
            'cuántos alumnos hay',
        ):
            nombres = {t.name for t in retriever.search(consulta, role='jugador', k=6)}
            restringidas = nombres & set(TOOL_REGISTRY) - {
                'get_current_datetime',
                'get_notifications',
                'mark_notifications_read',
                'list_sedes',
            }
            assert not restringidas, f'"{consulta}" Leak al paciente: {restringidas}'

    def test_el_paciente_sigue_pudiendo_consultar_sedes(self, retriever):
        nombres = {t.name for t in retriever.search('cuántas sedes hay', role='jugador', k=6)}
        assert 'list_sedes' in nombres


class TestTopKYTamanoDelPrompt:
    def test_el_prompt_se_reduce_a_k_tools(self, retriever):
        resultados = retriever.search('quiero un resumen financiero completo', role='admin', k=6)
        assert len(resultados) <= 6

    def test_el_prompt_local_es_mucho_menor_que_el_catalogo_completo(self, retriever):
        """Debe quedar en el orden de miles de caracteres, no decenas de miles."""
        import json

        completo = json.dumps(
            [
                {'name': t.name, 'description': t.description}
                for t in retriever.search('resumen financiero', role='admin', k=6)
            ],
            ensure_ascii=False,
        )
        catalogo = json.dumps(
            [{'name': n, 'description': d['description']} for n, d in TOOL_REGISTRY.items()],
            ensure_ascii=False,
        )
        assert len(completo) < len(catalogo) / 4, (
            f'el prompt sigue siendo casi el catalogo: {len(completo)} vs {len(catalogo)}'
        )

    def test_si_no_hay_coincidencia_devuelve_herramientas_de_lectura_seguras(self, retriever):
        resultados = retriever.search('xyzzy plugh', role='admin', k=6)
        assert resultados, 'debe devolver algo aunque no entienda la consulta'
        assert all(TOOL_REGISTRY[t.name]['category'] == 'read' for t in resultados)
