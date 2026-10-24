"""PRP 016: fotos, documentos, informe del alumno, Drive/impresión y elegir modelo en el asistente."""

import io
import uuid
from datetime import datetime, timedelta

import pytest
from flask_jwt_extended import create_access_token
from werkzeug.datastructures import FileStorage

from app.extensions import db
from app.models import Appointment, User
from app.models.assistant_thread import AssistantMessage, AssistantThread
from app.services import assistant_files, llm_client
from app.services import assistant_service as svc


def _user(role, name=None, **kw):
    tag = uuid.uuid4().hex[:8]
    u = User(username=name or f'{role[:3]}{tag}', email=f'{tag}@gmail.com', password='x', role=role, **kw)
    db.session.add(u)
    db.session.commit()
    return u


def _h(u):
    return {'Authorization': 'Bearer ' + create_access_token(identity=str(u.id))}


@pytest.fixture
def drive_root(app, tmp_path):
    app.config['DRIVE_ROOT'] = str(tmp_path / 'drive')
    yield tmp_path / 'drive'
    app.config.pop('DRIVE_ROOT', None)


def _upload(user, name, data):
    return assistant_files.save_upload(FileStorage(io.BytesIO(data), filename=name), user)


def test_voucher_photo_becomes_payment_form_with_patient(app, monkeypatch):
    admin = _user('admin')
    pat = _user(
        'jugador', name=f'Liam Gonzales {uuid.uuid4().hex[:3].translate(str.maketrans("0123456789", "abcdefghij"))}'
    )
    att = _upload(admin, 'yape.png', b'\x89PNG fake')
    intake = {
        'doc_type': 'voucher',
        'fields': {'amount': 150, 'date': '2026-10-20', 'method': 'Yape', 'reference': 'OP123', 'payer': pat.username},
        'warnings': [],
    }
    monkeypatch.setattr(assistant_files, '_read_image', lambda *a, **k: (intake, 'MiMo (opencode)'))
    thread, answer = svc.ask(admin, '', attachment={'token': att['token'], 'name': att['name']})
    block = next(b for b in answer.blocks if b['type'] == 'action')
    assert block['tool'] == 'register_payment'
    assert (
        block['args']['patient_id'] == pat.id and block['args']['amount'] == 150 and block['args']['method'] == 'Yape'
    )
    assert block['args']['receipt_url'].startswith('/uploads/mcp/')
    assert answer.question is None and thread.messages.first().text.startswith('📎')


def test_other_users_upload_cannot_be_used(app):
    a, b = _user('admin'), _user('admin')
    att = _upload(a, 'doc.txt', b'hola')
    with pytest.raises(svc.AssistantError):
        svc.ask(b, '', attachment={'token': att['token'], 'name': 'doc.txt'})


def test_document_is_summarized_and_offered_to_drive_then_print(app, drive_root, monkeypatch):
    admin = _user('admin')
    att = _upload(admin, 'acuerdo.txt', b'Acuerdo de pago: 3 cuotas de S/ 200 desde noviembre.')
    monkeypatch.setattr(
        assistant_files, 'ai_text', lambda prompt, user, model=None: ('Es un acuerdo de pago.', 'groq (respaldo)')
    )
    _, answer = svc.ask(admin, '¿qué dice?', attachment={'token': att['token'], 'name': att['name']})
    assert answer.blocks[0]['md'] == 'Es un acuerdo de pago.' and answer.model == 'groq (respaldo)'
    save = next(b for b in answer.blocks if b['type'] == 'action')
    assert save['tool'] == 'drive_save_upload' and {f['key'] for f in save['fields']} == {'folder', 'name'}

    idx = answer.blocks.index(save)
    _, reply = svc.run_action(admin, answer.id, {'folder': 'Asistente/Acuerdos', 'name': 'acuerdo.txt'}, idx)
    file = next(b for b in reply.blocks if b['type'] == 'file')
    assert file['path'] == 'Asistente/Acuerdos/acuerdo.txt' and (drive_root / file['path']).read_text().startswith(
        'Acuerdo'
    )
    assert any(b['type'] == 'action' and b['tool'] == 'print_drive_file' for b in reply.blocks)


def test_patient_report_has_all_sessions_and_ai_part(app, drive_root, monkeypatch):
    from app.services.tools_registry import execute_tool

    admin = _user('admin')
    ther = _user('terapista')
    pat = _user('jugador', therapy_goals='Mejorar la atención', assigned_therapist_id=ther.id)
    base = datetime(2026, 9, 1, 9)
    for i in range(3):
        db.session.add(
            Appointment(
                patient_id=pat.id, therapist_id=ther.id, title=f'Sesión {i + 1}', start_time=base + timedelta(days=7 * i),
                status='completed', notes=f'Nota de la sesión {i + 1}',
            )
        )  # fmt: skip
    db.session.commit()
    monkeypatch.setattr(
        assistant_files, 'ai_text', lambda prompt, user, model=None: ('1) Resumen del caso: avanza.', 'x')
    )
    res = execute_tool('patient_report', {'patient_id': pat.id}, user_id=admin.id, role='admin')
    assert res.get('success'), res
    text = (drive_root / res['file']['path']).read_text()
    assert 'Mejorar la atención' in text and 'Nota de la sesión 3' in text and 'realizadas: 3' in text
    assert 'INFORME TERAPÉUTICO' in text and 'avanza' in text


def test_report_request_opens_form_with_patient(app):
    admin = _user('admin')
    pat = _user(
        'jugador', name=f'Valentina Ruiz {uuid.uuid4().hex[:3].translate(str.maketrans("0123456789", "abcdefghij"))}'
    )
    tool, args = svc.quick_action(f'informe de {pat.username}', admin)
    assert tool == 'patient_report' and args['patient_id'] == pat.id
    assert svc.quick_action('hazme un reporte de ingresos', admin) is None


def test_preferred_provider_goes_first(app, monkeypatch):
    chain = [{'slug': 'ollama', 'provider_type': 'ollama'}, {'slug': 'groq', 'provider_type': 'groq'}]
    monkeypatch.setattr(llm_client, '_load_db_providers', lambda: (list(chain), True))
    assert [p['slug'] for p in llm_client._configured_providers()] == ['ollama', 'groq']
    token = llm_client.PREFERRED_PROVIDER.set('groq')
    try:
        assert [p['slug'] for p in llm_client._configured_providers()] == ['groq', 'ollama']
    finally:
        llm_client.PREFERRED_PROVIDER.reset(token)


def test_models_endpoint_and_stream_with_model(client, app, monkeypatch):
    admin = _user('admin')
    r = client.get('/api/assistant/models', headers=_h(admin))
    assert r.status_code == 200 and r.get_json()['models'][0]['key'] == 'auto'

    seen = {}

    def fake(question, user, history, step=None, model=None):
        seen['model'] = model
        return {'title': 'x', 'blocks': [{'type': 'text', 'md': 'ok'}], 'sources': [], 'model': f'{model} (respaldo)'}

    monkeypatch.setattr(svc, '_general_ai', fake)
    r = client.post(
        '/api/assistant/ask/stream', json={'question': 'una duda cualquiera', 'model': 'groq'}, headers=_h(admin)
    )
    body = r.get_data(as_text=True)
    assert seen.get('model') == 'groq' and 'groq (respaldo)' in body, body[-400:]


def test_upload_endpoint_rejects_unknown_types(client, app):
    admin = _user('admin')
    r = client.post(
        '/api/assistant/upload',
        data={'file': (io.BytesIO(b'MZ'), 'virus.exe')},
        headers=_h(admin),
        content_type='multipart/form-data',
    )
    assert r.status_code == 400
    r = client.post(
        '/api/assistant/upload',
        data={'file': (io.BytesIO(b'hola'), 'nota.txt')},
        headers=_h(admin),
        content_type='multipart/form-data',
    )
    assert r.status_code == 201 and r.get_json()['token'].startswith(f'{admin.id}_')


def _unused():
    return AssistantMessage, AssistantThread
