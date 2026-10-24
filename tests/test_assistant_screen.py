"""PRP 015: pantalla del asistente (bloques con los números del sistema, conversaciones y reportes programados)."""

import uuid
from datetime import datetime

from flask_jwt_extended import create_access_token

from app.extensions import db
from app.models import Payment, Sede, User
from app.models.assistant_thread import AssistantSchedule, AssistantThread
from app.services import assistant_analytics as analytics
from app.services import assistant_service as svc


def _user(role, name=None, **kw):
    tag = uuid.uuid4().hex[:8]
    u = User(username=name or f'{role[:3]}{tag}', email=f'{tag}@gmail.com', password='x', role=role, **kw)
    db.session.add(u)
    db.session.commit()
    return u


def _sede(name=None):
    s = Sede(name=name or f'Sede {uuid.uuid4().hex[:4]}')
    db.session.add(s)
    db.session.commit()
    return s


def _h(u):
    return {'Authorization': 'Bearer ' + create_access_token(identity=str(u.id))}


def test_intents_and_periods():
    n = analytics._norm
    assert analytics._intent(n('Compara las sedes este trimestre')) == 'by_sede'
    assert analytics._intent(n('¿Quiénes deben cuotas?')) == 'debtors'
    assert analytics._intent(n('pagos por método')) == 'payment_methods'
    assert analytics._intent(n('¿Cómo vamos este mes?')) == 'summary'
    assert analytics._intent(n('cuéntame un chiste')) is None
    assert analytics._period(n('este trimestre')) == 'quarter'
    assert analytics._period(n('en el año')) == 'year'
    assert analytics._metrics(n('ingresos y asistencia'))[:2] == ['revenue', 'attendance']


def test_summary_blocks_use_dashboard_numbers(app):
    admin = _user('admin')
    pat = _user('jugador')
    db.session.add(Payment(patient_id=pat.id, amount=150, method='yape', status='completed', date=datetime.utcnow()))
    db.session.commit()
    res = analytics.answer('¿Cómo vamos este mes?', admin)
    kinds = [b['type'] for b in res['blocks']]
    assert kinds[:2] == ['text', 'kpis'] and res['sources'][0]['scope'] == 'todo el centro'
    revenue = next(i for i in res['blocks'][1]['items'] if i['key'] == 'revenue')
    from app.services import center_dashboard

    pulse = {k['key']: k for k in center_dashboard.dashboard('month')['pulse']}
    assert revenue['value'] == pulse['revenue']['value']  # mismo número que el Dashboard


def test_supervisor_is_limited_to_own_sede(app):
    mine, other = _sede('Mía'), _sede('Otra')
    sup = _user('supervisor', sede_id=mine.id)
    db.session.add(
        Payment(
            patient_id=_user('jugador', sede_id=other.id).id,
            amount=999,
            method='cash',
            status='completed',
            date=datetime.utcnow(),
        )
    )
    db.session.commit()
    assert analytics.scope_for(sup) == mine.id
    res = analytics.answer('Compara las sedes', sup)
    assert 'solo tu sede' in res['blocks'][0]['md']
    assert all(b['type'] != 'table' or 'Comparativo de sedes' != b.get('title') for b in res['blocks'])
    pm = analytics.answer('pagos por método este mes', sup)
    assert all('999' not in str(b) for b in pm['blocks'])  # el pago de otra sede no aparece


def test_supervisor_without_sede_gets_clear_error(client, app):
    sup = _user('supervisor')
    r = client.post('/api/assistant/ask', json={'question': '¿cómo vamos?'}, headers=_h(sup))
    assert r.status_code == 403 and 'sede' in r.get_json()['message']


def test_ask_saves_thread_and_sharing_rules(client, app):
    admin, other_admin = _user('admin'), _user('admin')
    sede = _sede()
    sup = _user('supervisor', sede_id=sede.id)
    r = client.post('/api/assistant/ask', json={'question': '¿Cómo vamos este mes?'}, headers=_h(admin))
    assert r.status_code == 200, r.get_json()
    tid = r.get_json()['thread']['id']
    # privada: nadie más la ve
    assert client.get(f'/api/assistant/threads/{tid}', headers=_h(other_admin)).status_code == 404
    client.patch(f'/api/assistant/threads/{tid}', json={'shared': True, 'pinned': True}, headers=_h(admin))
    assert client.get(f'/api/assistant/threads/{tid}', headers=_h(other_admin)).status_code == 200
    # compartida por un admin (datos de todo el centro): el supervisor no la ve
    assert client.get(f'/api/assistant/threads/{tid}', headers=_h(sup)).status_code == 404
    # solo el autor la cambia
    assert (
        client.patch(f'/api/assistant/threads/{tid}', json={'title': 'x'}, headers=_h(other_admin)).status_code == 403
    )
    thread = client.get(f'/api/assistant/threads/{tid}', headers=_h(admin)).get_json()
    assert [m['role'] for m in thread['messages']] == ['user', 'assistant'] and thread['pinned']


def test_therapist_cannot_use_the_screen(client, app):
    assert client.get('/api/assistant/threads', headers=_h(_user('terapista'))).status_code == 403


def test_schedule_runs_once_and_appends_to_thread(app, monkeypatch):
    admin = _user('admin')
    thread, _ = svc.ask(admin, '¿Cómo vamos este mes?')
    s = svc.create_schedule(
        admin,
        {
            'question': '¿Cómo vamos este mes?',
            'cadence': 'daily',
            'hour': 8,
            'channel': 'email',
            'thread_id': thread.id,
        },
    )
    sent = []
    monkeypatch.setattr(svc, '_send_email', lambda user, subject, text: sent.append(subject))
    from zoneinfo import ZoneInfo

    at8 = datetime(2026, 10, 26, 8, 5, tzinfo=ZoneInfo('America/Lima'))
    assert svc.run_schedules(at8) >= 1
    assert svc.run_schedules(at8) == 0 or sent.count(sent[0]) == 1  # no se repite en la misma hora
    assert db.session.get(AssistantSchedule, s.id).last_run_at is not None
    assert db.session.get(AssistantThread, thread.id).messages.count() == 3


def test_only_data_questions_can_be_scheduled(app):
    admin = _user('admin')
    try:
        svc.create_schedule(admin, {'question': 'cuéntame un chiste'})
        raise AssertionError('debió rechazarse')
    except svc.AssistantError as exc:
        assert 'datos del centro' in str(exc)


def _fake_ai(monkeypatch, replies):
    from app.routes import mcp_routes

    calls = []

    def fake(message, user_role, user_id, mode='grande', history=None, **kw):
        calls.append({'message': message, 'history': history})
        return replies.pop(0)

    monkeypatch.setattr(mcp_routes.mcp_service, 'process_message', fake)
    return calls


def test_pending_action_becomes_a_form_and_runs_on_confirm(app, monkeypatch):
    admin = _user('admin')
    _fake_ai(
        monkeypatch,
        [
            {
                'response': 'Acción pendiente de confirmación.',
                'requires_confirmation': True,
                'pending_tool': {'name': 'create_user', 'args': {'role': 'jugador', 'username': 'Cesar Jesús Gamboa'}},
            }
        ],
    )
    thread, answer = svc.ask(admin, 'crea un usuario jugador Cesar Jesús Gamboa')
    action = next(b for b in answer.blocks if b['type'] == 'action')
    keys = {f['key'] for f in action['fields']}
    assert action['tool'] == 'create_user' and {'username', 'role'} <= keys
    assert action['args']['username'] == 'Cesar Jesús Gamboa' and action['status'] == 'pending'

    ran = []
    monkeypatch.setattr(
        'app.services.tools_registry.execute_tool',
        lambda name, args, user_id=None, role=None: (
            ran.append((name, args, role)) or {'success': True, 'message': 'Usuario creado.'}
        ),
    )
    updated, reply = svc.run_action(
        admin, answer.id, {'role': 'jugador', 'username': 'Cesar Jesús Gamboa', 'email': ''}
    )
    assert ran == [('create_user', {'role': 'jugador', 'username': 'Cesar Jesús Gamboa'}, 'admin')]  # vacíos fuera
    assert next(b for b in updated.blocks if b['type'] == 'action')['status'] == 'done'
    assert 'Usuario creado' in reply.text
    try:
        svc.run_action(admin, answer.id, {})
        raise AssertionError('no debía repetirse')
    except svc.AssistantError as exc:
        assert 'ya se hizo' in str(exc)


def test_follow_up_stays_with_the_ai_conversation(app, monkeypatch):
    admin = _user('admin')
    calls = _fake_ai(
        monkeypatch,
        [
            {'response': '¿Qué rol tendrá?', 'provider': 'opencode'},
            {'response': 'Falta el correo.', 'provider': 'opencode'},
        ],
    )
    thread, _ = svc.ask(admin, 'tengo una duda con los permisos de un usuario')
    _, follow = svc.ask(admin, '¿qué falta?', thread.id)
    assert follow.blocks[0]['md'] == 'Falta el correo.'  # antes se iba al análisis de «asistencia»
    assert len(calls) == 2 and calls[1]['history']  # con el historial de la conversación
    # un pedido de datos explícito sí pasa al análisis aunque venga de la IA
    _, data = svc.ask(admin, 'compara las sedes este mes', thread.id)
    assert data.model == analytics.MODEL_NAME


def test_action_and_capability_questions_go_to_ai(app):
    admin = _user('admin')
    for q in (
        'Realmente, qué puedes hacer? puedes crear un usuario, su contrato, y guardar las sesiones?',
        'registra un pago de 50 soles',
        'agenda sesiones para Liam',
    ):
        assert analytics.answer(q, admin) is None, q
    assert analytics.answer('¿Cómo vamos este mes con las sesiones?', admin) is not None


def test_action_fields_pick_people_by_name(app):
    pat = _user('jugador')
    block = svc.action_block('create_service_contract', {}, _user('admin'))
    field = next(f for f in block['fields'] if f['key'] == 'patient_id')
    assert field['type'] == 'enum' and field['searchable'] and field['label'] == 'Paciente'
    assert any(o['value'] == pat.id and o['label'].startswith(pat.username) for o in field['options'])
    assert len(block['title']) <= 44 and 'con' not in block['title'].split()


def test_pending_action_saved_before_gets_todays_form(app):
    admin = _user('admin')
    _user('jugador')
    old = {
        'type': 'action',
        'tool': 'create_service_contract',
        'status': 'pending',
        'args': {'start_date': '2026-10-23'},
        'fields': [{'key': 'patient_id', 'label': 'ID del paciente', 'type': 'integer', 'required': True}],
    }
    [fresh] = svc._fresh_blocks([old], admin)
    patient = next(f for f in fresh['fields'] if f['key'] == 'patient_id')
    assert patient['type'] == 'enum' and patient['options'] and fresh['args'] == old['args']


def _sse(resp):
    import json

    return [json.loads(line[6:]) for line in resp.get_data(as_text=True).splitlines() if line.startswith('data: ')]


def test_stream_quick_form_without_waiting_for_the_model(client, app, monkeypatch):
    admin = _user('admin')
    pat = _user(
        'jugador', name=f'Liam Gonzales {uuid.uuid4().hex[:4].translate(str.maketrans("0123456789", "ghijklmnop"))}'
    )
    db.session.commit()

    def boom(*a, **k):
        raise AssertionError('no debe llamar a la IA para abrir un formulario conocido')

    monkeypatch.setattr(svc, '_general_ai', boom)
    r = client.post('/api/assistant/ask/stream', json={'question': 'quisiera crear un usuario'}, headers=_h(admin))
    assert r.status_code == 200 and r.mimetype == 'text/event-stream'
    done = _sse(r)[-1]
    assert done['type'] == 'done'
    block = done['message']['blocks'][1]
    assert block['type'] == 'action' and block['tool'] == 'create_user'

    r = client.post(
        '/api/assistant/ask/stream',
        json={'question': f'hazme un contrato para {pat.username}'},
        headers=_h(admin),
    )
    block = _sse(r)[-1]['message']['blocks'][1]
    assert block['tool'] == 'create_service_contract' and block['args']['patient_id'] == pat.id


def test_stream_shows_mimo_steps_and_confirm_form(client, app, monkeypatch):
    from app.services import opencode_agent

    admin = _user('admin')
    db.session.commit()

    def fake_run(user, message, **kw):
        yield {'type': 'thinking', 'content': 'Buscando al paciente'}
        yield {'type': 'tool_call', 'name': 'list_patients', 'args': {}}
        yield {'type': 'tool_result', 'name': 'list_patients', 'result': {}, 'success': True}
        yield {'type': 'confirm', 'name': 'create_user', 'args': {'username': 'Jorge Manuel Gregorio'}}
        yield {'type': 'done', 'tool_calls': []}

    monkeypatch.setattr(opencode_agent, 'enabled_for', lambda u: True)
    monkeypatch.setattr(opencode_agent, 'run', fake_run)
    r = client.post('/api/assistant/ask/stream', json={'question': 'el de Jorge, por favor'}, headers=_h(admin))
    evs = _sse(r)
    steps = [e['text'] for e in evs if e['type'] == 'step']
    assert 'Buscando al paciente' in steps and any(s.startswith('Consultando') for s in steps)
    msg = evs[-1]['message']
    assert msg['model'] == 'MiMo (opencode)'
    assert msg['blocks'][1]['tool'] == 'create_user' and msg['blocks'][1]['args']['username'] == 'Jorge Manuel Gregorio'


def test_quick_action_skips_questions():
    class U:
        role = 'admin'

    assert svc.quick_action('¿cuántos pacientes nuevos hubo?', U()) is None
    assert svc.quick_action('cómo se crea un contrato', U()) is None


def test_create_user_from_form_without_email(app):
    from app.services.tools_registry import execute_tool

    admin = _user('admin')
    name = f'Jorge Prueba {uuid.uuid4().hex[:6]}'
    res = execute_tool(
        'create_user', {'username': name, 'role': 'jugador', 'email': None}, user_id=admin.id, role='admin'
    )
    assert 'error' not in res, res
    assert User.query.filter_by(username=name).first() is not None


def _action_message(admin, blocks):
    thread = AssistantThread(user_id=admin.id, title='Alta')
    db.session.add(thread)
    db.session.flush()
    from app.models.assistant_thread import AssistantMessage

    m = AssistantMessage(thread_id=thread.id, role='assistant', text='', blocks=blocks, model='formulario')
    db.session.add(m)
    db.session.commit()
    return m


def test_create_patient_form_matches_users_panel(app):
    admin = _user('admin')
    block = svc.action_block('create_user', {'role': 'jugador'}, admin)
    keys = [f['key'] for f in block['fields']]
    for k in ('modality', 'payment_amount', 'generate_schedule', 'start_date', 'start_time', 'therapist_id',
              'days_of_week', 'guardian_type', 'guardian_dni', 'salary_base'):  # fmt: skip
        assert k in keys, k
    sections = {f['key']: f['section'] for f in block['fields']}
    assert sections['modality'] == 'Plan y horario' and sections['guardian_dni'] == 'Apoderado'
    salary = next(f for f in block['fields'] if f['key'] == 'salary_base')
    assert salary['show_if'] == {'role': ['terapista']}
    modality = next(f for f in block['fields'] if f['key'] == 'modality')
    assert modality['options'][1]['label'].startswith('2x')
    assert block['args']['generate_schedule'] is True  # como el panel


def test_patient_without_plan_proposes_contract_and_sessions(app):
    admin = _user('admin')
    ther = _user('terapista')
    m = _action_message(admin, [svc.action_block('create_user', {'role': 'jugador'}, admin)])
    name = f'Paciente Flujo {uuid.uuid4().hex[:5]}'
    _, reply = svc.run_action(admin, m.id, {'username': name, 'role': 'jugador', 'therapist_id': ther.id})
    tools = [b['tool'] for b in reply.blocks if b['type'] == 'action']
    assert tools == ['create_service_contract', 'schedule_patient_plan']
    pat = User.query.filter_by(username=name).first()
    sched = reply.blocks[-1]
    assert sched['args']['patient_id'] == pat.id and sched['args']['therapist_id'] == ther.id

    # Confirmar el segundo formulario (las sesiones) de esa misma respuesta.
    from app.models import Appointment

    idx = len(reply.blocks) - 1
    _, done = svc.run_action(
        admin,
        reply.id,
        {
            'patient_id': pat.id,
            'therapist_id': ther.id,
            'modality': 2,
            'start_date': '2027-03-01',
            'start_time': '09:00',
            'days_of_week': [0, 3],
        },  # fmt: skip
        idx,
    )
    assert Appointment.query.filter_by(patient_id=pat.id).count() == 8
    db.session.refresh(reply)
    assert reply.blocks[idx]['status'] == 'done' and reply.blocks[1 if reply.blocks[0]['type'] == 'text' else 0]
    assert next(b for b in reply.blocks if b['type'] == 'action')['status'] == 'pending'  # el contrato sigue ahí
    # Ya tiene sesiones: después del contrato no vuelve a proponerlas.
    assert not [b for b in done.blocks if b['type'] == 'action' and b['tool'] == 'schedule_patient_plan']


def test_patient_with_plan_gets_contract_and_sessions_at_once(app):
    from app.models import Appointment
    from app.models.contract import Contract

    admin = _user('admin')
    ther = _user('terapista')
    m = _action_message(admin, [svc.action_block('create_user', {'role': 'jugador'}, admin)])
    name = f'Paciente Plan {uuid.uuid4().hex[:5]}'
    _, reply = svc.run_action(
        admin,
        m.id,
        {
            'username': name,
            'role': 'jugador',
            'modality': 1,
            'payment_amount': 400,
            'payment_frequency': 'monthly',
            'plan_type': 'individual',
            'generate_schedule': True,
            'start_date': '2027-03-02',
            'start_time': '10:00',
            'therapist_id': ther.id,
            'days_of_week': [1],
        },  # fmt: skip
    )
    pat = User.query.filter_by(username=name).first()
    assert Contract.query.filter_by(patient_id=pat.id).count() == 1
    assert Appointment.query.filter_by(patient_id=pat.id).count() == 4
    assert not [b for b in reply.blocks if b['type'] == 'action']
    assert 'ya tiene su contrato' in ' '.join(b.get('md', '') for b in reply.blocks)


def test_walk_in_patient_appears_by_name_in_follow_up(app):
    admin = _user('admin')
    m = _action_message(admin, [svc.action_block('create_user', {'role': 'jugador'}, admin)])
    name = f'Presencial Uno {uuid.uuid4().hex[:4]}'
    _, reply = svc.run_action(admin, m.id, {'username': name, 'role': 'jugador'})
    assert '(ID' not in reply.text
    contract = next(b for b in reply.blocks if b['type'] == 'action')
    field = next(f for f in contract['fields'] if f['key'] == 'patient_id')
    pid = contract['args']['patient_id']
    assert any(o['value'] == pid and o['label'].startswith(name) for o in field['options'])
