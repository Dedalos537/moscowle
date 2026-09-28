"""Pruebas de la rama de IA remota de MCPService.process_message.

Hallazgo: `tools` solo se asignaba dentro de la rama `if local_mode:` pero se
usaba despues en la rama remota (`_build_tool_prompt(tools)`), por lo que la
rama remota reventaba con UnboundLocalError antes de llamar al modelo.

En el entorno desplegado la ruta no se ejecutaba porque Ollama es el primario,
asi que el bug estaba latente: cualquier cambio a proveedor remoto lo activaba.
"""

import pytest

from app.services import mcp_service
from app.services.mcp_service import MCPService


@pytest.fixture
def remote(monkeypatch):
    """Fuerza la rama remota y evita llamadas de red."""
    monkeypatch.setattr(mcp_service, '_is_ollama_primary', lambda *a, **k: False)
    calls = {'llm': 0}

    def fake_llm_chat(messages, *a, **k):
        calls['llm'] += 1
        return 'respuesta de prueba', 'proveedor-falso'

    monkeypatch.setattr(mcp_service, 'llm_chat', fake_llm_chat)
    monkeypatch.setattr(mcp_service, 'get_current_date_context', lambda: 'HOY: test')
    monkeypatch.setattr(mcp_service, 'resolve_system_prompt', lambda *a, **k: 'prompt de sistema')
    calls['mcp'] = MCPService()
    return calls




class TestRamaRemotaInicializaTools:
    def test_no_debe_raises_unboundlocal(self, remote):
        """La rama remota debe construir el prompt de herramientas sin error."""
        result = remote['mcp'].process_message('¿Cuántos pacientes hay?', 'admin', 1, mode='grande')
        assert 'error' not in result or 'UnboundLocalError' not in str(result.get('error')), (
            f"la rama remota fallo: {result.get('error')}"
        )

    def test_llm_fue_invocado(self, remote):
        """Si hay UnboundLocalError el modelo nunca llega a llamarse."""
        remote['mcp'].process_message('hola', 'admin', 1, mode='grande')
        assert remote['llm'] > 0, 'el modelo remoto nunca fue invocado'

    def test_prompt_de_tools_llega_al_modelo(self, remote, monkeypatch):
        """El prompt del sistema debe incluir la lista de herramientas."""
        captured = {}

        def spy(messages, *a, **k):
            captured['system'] = messages[0]['content'] if messages else ''
            return 'ok', 'p'

        monkeypatch.setattr(mcp_service, 'llm_chat', spy)
        remote['mcp'].process_message('listar pacientes', 'admin', 1, mode='grande')
        assert 'function' in captured.get('system', '').lower(), (
            'el prompt remoto no incluia las herramientas'
        )

    def test_rama_local_sigue_funcionando(self, monkeypatch):
        """No romper la ruta local (Ollama), que es la activa en produccion."""
        monkeypatch.setattr(mcp_service, '_is_ollama_primary', lambda *a, **k: True)
        monkeypatch.setattr(mcp_service, 'llm_chat', lambda *a, **k: ('hola', 'ollama'))
        out = MCPService().process_message('hola', 'admin', 1, mode='grande')
        assert 'response' in out
