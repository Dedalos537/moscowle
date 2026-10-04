"""Regresiones del asistente IA y de la IA de mensajería.

1. El stream de `/mcp/chat/stream` no debe enviar la respuesta dos veces.
2. `/api/files/ai-preview` no debe quedar bloqueado por CSRF (sus rutas
   hermanas de chat_bp llevan @csrf.exempt; esta se quedó sin él).
"""

import json

from flask_jwt_extended import create_access_token

CHUNKS = ['Hola', '! ¿En', ' qué puedo ayudarte?']


def _parse_sse(raw: bytes):
    events = []
    for line in raw.decode('utf-8').splitlines():
        if line.startswith('data: '):
            events.append(json.loads(line[6:]))
    return events


def _assemble_like_frontend(events):
    """Replica exacta de ai-chat.ts / chat.ts: chunk y text se CONCATENAN."""
    out = ''
    for ev in events:
        if ev.get('type') in ('chunk', 'text') and ev.get('content'):
            out += ev['content']
    return out


def test_smalltalk_stream_answer_is_not_duplicated(client, test_user, monkeypatch):
    monkeypatch.setattr('app.routes.mcp_routes._is_ollama_primary', lambda: True)
    monkeypatch.setattr('app.routes.mcp_routes.llm_chat_stream', lambda *a, **k: iter(CHUNKS))

    token = create_access_token(identity=str(test_user.id))
    resp = client.post(
        '/mcp/chat/stream',
        json={'message': 'hola', 'mode': 'chiquito', 'history': []},
        headers={'Authorization': f'Bearer {token}'},
    )

    assert resp.status_code == 200, resp.get_data(as_text=True)
    events = _parse_sse(resp.data)
    assert events, 'el stream no devolvió eventos'

    assembled = _assemble_like_frontend(events)
    expected = ''.join(CHUNKS)
    assert assembled == expected, f'el asistente respondió la misma frase dos veces: {assembled!r}'


def test_ai_preview_is_not_blocked_by_csrf(app, client, test_user):
    token = create_access_token(identity=str(test_user.id))
    csrf_was = app.config.get('WTF_CSRF_ENABLED', False)
    app.config['WTF_CSRF_ENABLED'] = True
    try:
        resp = client.post(
            '/api/files/ai-preview',
            json={'message_id': 999999},
            headers={'Authorization': f'Bearer {token}'},
        )
    finally:
        app.config['WTF_CSRF_ENABLED'] = csrf_was

    body = resp.get_data(as_text=True)
    assert 'csrf' not in body.lower(), (
        f'/api/files/ai-preview sigue bloqueado por CSRF (status={resp.status_code}): {body[:300]}'
    )
