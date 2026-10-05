"""Pruebas del system prompt generado (prompt_builder).

El catálogo de herramientas y el bloque de acceso se generan desde el
registro: el prompt NO puede listar tools que el rol no tiene (antes el
catálogo estaba escrito a mano en SYSTEM_PROMPTS/_build_tool_prompt y se
desincronizaba del registro real).
"""

from app.services.prompt_builder import (
    build_system_prompt,
    build_tool_catalog,
    get_current_date_context,
)
from app.services.tools_registry import get_tools_for_mode


class TestCatalogoGenerado:
    def test_solo_lista_tools_permitidas_del_rol(self):
        """Terapeista ve sus 19 tools y NUNCA delete_user ni logs del servidor."""
        tools = get_tools_for_mode('grande', 'terapista')
        prompt = build_system_prompt('terapista', user_id=1, mode='grande', tools=tools)
        for t in tools:
            assert t['function']['name'] in prompt, f'falta {t["function"]["name"]}'
        assert 'delete_user' not in prompt
        assert 'get_server_logs' not in prompt

    def test_admin_ve_su_catalogo_completo(self):
        tools = get_tools_for_mode('grande', 'admin')
        prompt = build_system_prompt('admin', user_id=1, mode='grande', tools=tools)
        assert 'delete_user' in prompt
        assert 'get_server_logs' in prompt
        # Ninguna tool fuera de la lista permitida se cuela en el catálogo
        names = {t['function']['name'] for t in tools}
        catalog = build_tool_catalog(tools)
        for line in catalog.splitlines():
            if line.startswith('- '):
                assert line[2:].split(':', 1)[0] in names

    def test_catalogo_agrupa_por_categoria(self):
        tools = get_tools_for_mode('grande', 'admin')
        catalog = build_tool_catalog(tools)
        assert 'CONSULTAS' in catalog
        assert 'ACCIONES' in catalog

    def test_catalogo_incluye_params_requeridos(self):
        catalog = build_tool_catalog(get_tools_for_mode('grande', 'admin'))
        # search_patients exige query (marcada con *)
        assert 'search_patients' in catalog
        assert 'query*' in catalog


class TestModoCompactoLocal:
    def test_prompt_local_cabe_en_presupuesto(self):
        """Modo Ollama: catálogo de 1 línea por tool y < ~1200 tokens."""
        tools = get_tools_for_mode('grande', 'terapista')[:8]
        prompt = build_system_prompt('terapista', user_id=1, mode='grande', tools=tools, compact=True)
        assert len(prompt) < 6000, 'el prompt local desborda el prefill de CPU'
        for t in tools:
            assert t['function']['name'] in prompt

    def test_prompt_local_sin_params_largos(self):
        tools = get_tools_for_mode('grande', 'terapista')[:5]
        catalog = build_tool_catalog(tools, compact=True)
        assert 'params:' not in catalog  # compacto: una línea por tool sin params


class TestFechaYAcceso:
    def test_prompt_remoto_menciona_la_fecha(self):
        prompt = build_system_prompt('admin', user_id=1, mode='grande', tools=get_tools_for_mode('grande', 'admin'))
        assert 'Hoy es' in prompt
        assert 'America/Lima' in prompt

    def test_prompt_local_menciona_la_fecha(self):
        prompt = build_system_prompt(
            'admin', user_id=1, mode='grande', tools=get_tools_for_mode('grande', 'admin'), compact=True
        )
        assert 'Hoy es' in prompt

    def test_bloque_aceso_lista_solo_las_tools_del_turno(self):
        tools = get_tools_for_mode('grande', 'terapista')
        prompt = build_system_prompt('terapista', user_id=1, mode='grande', tools=tools)
        assert 'ACCESO Y PERMISOS' in prompt
        assert 'delete_user' not in prompt.split('ACCESO Y PERMISOS')[-1]

    def test_fecha_es_la_de_lima(self):
        ctx = get_current_date_context()
        assert 'Hoy es' in ctx and 'America/Lima' in ctx


class TestFallbackDelAdmin:
    def test_config_del_admin_gana_y_personalidad_es_fallback(self, monkeypatch):
        from app.services import prompt_builder

        tools = get_tools_for_mode('grande', 'jugador')

        monkeypatch.setattr(prompt_builder, 'get_configured_system_prompt', lambda: 'PROMPT DEL ADMIN')
        prompt = prompt_builder.build_system_prompt('jugador', user_id=1, mode='grande', tools=tools)
        assert 'PROMPT DEL ADMIN' in prompt

        monkeypatch.setattr(prompt_builder, 'get_configured_system_prompt', lambda: None)
        prompt = prompt_builder.build_system_prompt('jugador', user_id=1, mode='grande', tools=tools)
        assert 'Diego' in prompt  # PERSONALITY_PROMPT de fallback
