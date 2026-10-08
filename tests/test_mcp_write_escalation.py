"""Regresión: el modelo local inventaba «Sesión programada…» sin llamar ninguna herramienta."""

from app.services import mcp_service

FAKE = 'Creando la sesión...\n\nSesión Programada:\nFecha: 2026-10-08\nLa sesión está lista.'


def _patch_local(monkeypatch, remote, replies):
    calls = []

    def fake_chat(messages, **kw):
        calls.append(kw)
        return replies.pop(0), ('groq' if 'ollama' in kw.get('exclude', ()) else 'ollama')

    monkeypatch.setattr(mcp_service, '_is_ollama_primary', lambda: True)
    monkeypatch.setattr(mcp_service, '_remote_ok', lambda: remote)
    monkeypatch.setattr(mcp_service, 'llm_chat', fake_chat)
    monkeypatch.setattr(mcp_service, '_select_local_tools', lambda tools, message, user_role=None: tools[:3])
    monkeypatch.setattr(mcp_service, '_build_local_system_prompt', lambda *a, **k: 'local')
    monkeypatch.setattr(mcp_service, '_force_intent_tool', lambda *a, **k: None)
    return calls


def test_write_request_goes_to_remote_and_asks_confirmation(app, monkeypatch):
    call = '<function=batch_create_sessions{"patient_id": 3, "dates": ["2026-10-09"]}</function>'
    calls = _patch_local(monkeypatch, remote=True, replies=[call])
    out = mcp_service.MCPService().process_message('crea una sesión para Odyta mañana de 10 a 11', 'admin', 1)
    assert calls[0].get('exclude') == ('ollama',)  # el turno de escritura no usa el modelo local
    assert out.get('requires_confirmation') and out['pending_tool']['name'] == 'batch_create_sessions'


def test_fake_action_without_remote_is_never_shown_as_done(app, monkeypatch):
    _patch_local(monkeypatch, remote=False, replies=[FAKE, FAKE, FAKE])
    out = mcp_service.MCPService().process_message('crea una sesión para Odyta mañana de 10 a 11', 'admin', 1)
    assert out['response'] == mcp_service.HONEST_NO_ACTION
    assert 'Programada' not in out['response']


def test_reads_stay_local(app, monkeypatch):
    calls = _patch_local(monkeypatch, remote=True, replies=['Hay 4 pacientes.'])
    monkeypatch.setattr(mcp_service, '_DATA_CLAIM_RE', mcp_service.re.compile('zzz_nunca'))
    mcp_service.MCPService().process_message('¿qué hora es en el centro?', 'admin', 1)
    assert 'exclude' not in calls[0]


def test_write_intent_detection():
    assert mcp_service.wants_write('quisiera crear un usuario bb')
    assert mcp_service.wants_write('registra un pago de 50 soles')
    assert mcp_service.wants_write('Odyta, a las 10', history=[{'role': 'user', 'content': 'programa una sesión'}])
    assert not mcp_service.wants_write('¿cuántos pacientes hay?')
