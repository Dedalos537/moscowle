"""Contrato del stream `/mcp/chat/stream`: traza estructurada de eventos.

Garantiza que el frontend pueda pintar la tarjeta "Pensamiento y herramientas":

1. Cada evento ``thinking`` lleva ``step`` estructurado (y conserva ``content``).
2. El ``done`` final incluye la traza completa (``trace``).
3. Los ``chunk``/``text`` solo llevan texto final (nunca estado de progreso),
   así la burbuja del asistente no se "redacta" con prefijos.
"""

import json

from flask_jwt_extended import create_access_token

ROUTE_CHUNKS = ['<function=list_users{"role": "terapista"}</function>']
FINAL_CHUNKS = ['Hay ', '5 terapeutas ', 'activos.']

MCP = 'app.routes.mcp_routes'


def _parse_sse(raw: bytes):
    events = []
    for line in raw.decode('utf-8').splitlines():
        if line.startswith('data: '):
            events.append(json.loads(line[6:]))
    return events


def _fake_llm(messages, **kwargs):
    """Fase route emite el tool_call; fase resume emite la respuesta final."""
    if kwargs.get('phase') == 'route':
        return iter(ROUTE_CHUNKS)
    return iter(FINAL_CHUNKS)


def _stream(client, test_user, monkeypatch, message='cuántos terapeutas hay?'):
    monkeypatch.setattr(f'{MCP}._is_ollama_primary', lambda: True)
    monkeypatch.setattr(f'{MCP}._is_smalltalk', lambda _m: False)
    monkeypatch.setattr(f'{MCP}._force_intent_tool', lambda *a, **k: None)
    monkeypatch.setattr(f'{MCP}.llm_chat_stream', _fake_llm)
    monkeypatch.setattr(
        f'{MCP}.execute_tool',
        lambda name, args, **kw: {'count': 5, 'role': args.get('role')},
    )

    token = create_access_token(identity=str(test_user.id))
    resp = client.post(
        '/mcp/chat/stream',
        json={'message': message, 'mode': 'grande', 'history': []},
        headers={'Authorization': f'Bearer {token}'},
    )
    assert resp.status_code == 200, resp.get_data(as_text=True)
    return _parse_sse(resp.data)


def test_thinking_events_carry_structured_step(client, test_user, monkeypatch):
    events = _stream(client, test_user, monkeypatch)

    thinking = [e for e in events if e['type'] == 'thinking']
    assert thinking, 'no hubo eventos thinking'
    for ev in thinking:
        assert 'content' in ev, 'se perdió el payload legacy de thinking'
        step = ev.get('step')
        assert step and step.get('kind') and step.get('text'), f'thinking sin step: {ev}'

    kinds = {ev['step']['kind'] for ev in thinking}
    assert 'route' in kinds, f'falta el paso de ruteo: {kinds}'


def test_done_includes_full_trace(client, test_user, monkeypatch):
    events = _stream(client, test_user, monkeypatch)

    done = [e for e in events if e['type'] == 'done']
    assert len(done) == 1, f'esperaba un único done: {len(done)}'
    trace = done[0].get('trace')
    assert isinstance(trace, list) and trace, 'done sin traza'
    kinds = [s['kind'] for s in trace]
    assert 'route' in kinds and 'tool' in kinds and 'result' in kinds, f'traza incompleta: {kinds}'
    tools = [s['tool'] for s in trace if s['kind'] == 'tool']
    assert 'list_users' in tools, f'la traza no registra la tool ejecutada: {tools}'
    tool_results = [s for s in trace if s['kind'] == 'result']
    assert tool_results and tool_results[0].get('ok') is True, 'falta el resultado de la tool'

    call = next(e for e in events if e['type'] == 'tool_call')
    res = next(e for e in events if e['type'] == 'tool_result')
    assert call['name'] == 'list_users'
    assert res['success'] is True


def test_chunks_carry_final_answer_only(client, test_user, monkeypatch):
    events = _stream(client, test_user, monkeypatch)

    text = ''.join(e['content'] for e in events if e['type'] in ('chunk', 'text') and e.get('content'))
    assert text == ''.join(FINAL_CHUNKS), f'respuesta alterada: {text!r}'

    state_markers = ('Evaluando', 'Procesando', 'Analizando', 'Reintentando')
    leaked = [m for m in state_markers if m in text]
    assert not leaked, f'el estado se filtró a la burbuja: {leaked}'


def test_trace_builder_events_are_legacy_compatible():
    from app.services.mcp_trace import TraceBuilder

    trace = TraceBuilder()
    raw = trace.thinking('Evaluando tu petición...')
    payload = json.loads(raw.removeprefix('data: ').strip())
    assert payload == {
        'type': 'thinking',
        'content': 'Evaluando tu petición...',
        'step': {'kind': 'route', 'text': 'Evaluando tu petición...'},
    }

    trace.tool_call('list_users', {'role': 'terapista'})
    trace.tool_result('list_users', True)
    steps = trace.as_list()
    assert [s['kind'] for s in steps] == ['route', 'tool', 'result']
    assert steps[1]['tool'] == 'list_users'
    assert steps[2]['ok'] is True

    trace.thinking('x', kind='desconocido')
    assert trace.as_list()[-1]['kind'] == 'route', 'kind inválido debe caer en route'
