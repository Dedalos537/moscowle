"""PRP 009: opencode como cerebro del asistente. Moscowle ejecuta las tools; opencode solo decide el paso."""

import json
import uuid

import pytest

from app.extensions import db
from app.models import User
from app.models.system_setting import SystemSetting
from app.services import opencode_agent, opencode_client
from app.services.ai_privacy import Vault
from app.services.opencode_client import OpencodeForbiddenError, OpencodeUnavailableError

_MADE: list = []


def _user(role):
    tag = uuid.uuid4().hex[:8]
    u = User(username=f'{role[:3]}{tag}', email=f'{tag}@oc.test', password='x', role=role)
    db.session.add(u)
    db.session.commit()
    _MADE.append(u)
    return u


@pytest.fixture(autouse=True)
def env(app, monkeypatch):
    _MADE.clear()
    monkeypatch.setenv('OPENCODE_URL', 'http://127.0.0.1:4096')
    monkeypatch.setenv('OPENCODE_PASSWORD', 'x')
    opencode_client.unblock('chat')
    opencode_agent._sessions.clear()
    monkeypatch.setattr(opencode_client, 'create_session', lambda title, inst='chat': 'ses_test')
    monkeypatch.setattr(opencode_client, 'delete_session', lambda sid, inst='chat': None)
    yield
    db.session.rollback()
    SystemSetting.query.filter(SystemSetting.key.like('ai.%')).delete(synchronize_session=False)
    for u in User.query.filter(User.id.in_([u.id for u in _MADE])):
        u.is_active = False
    db.session.commit()
    opencode_agent._sessions.clear()


def _enable():
    opencode_agent.save_settings({'enabled': True})


def _script(monkeypatch, steps):
    """Respuestas sucesivas del modelo; una Exception en la lista se lanza en ese turno."""
    sent = []

    def fake_send(sid, text, images=(), timeout=90, inst='chat'):
        sent.append(text)
        step = steps.pop(0)
        if isinstance(step, Exception):
            raise step
        return {
            'text': '```json\n' + json.dumps(step) + '\n```',
            'tools': [],
            'tokens': {'input': 10},
            'permissions': [],
        }

    monkeypatch.setattr(opencode_client, 'send', fake_send)
    return sent


def test_client_refuses_routes_outside_the_whitelist():
    with pytest.raises(OpencodeForbiddenError):
        opencode_client._request('POST', '/session/ses_abc/shell', json_body={'command': 'id'})
    with pytest.raises(OpencodeForbiddenError):
        opencode_client._request('PATCH', '/config', json_body={})


def test_dev_mode_only_approves_read_only_commands():
    ok = opencode_client.dev_command_allowed
    assert ok('journalctl -u moscowle -n 200 --no-pager')
    assert ok('systemctl status moscowle')
    assert ok('git -C /home/diego/moscowle_ia log -n 5')
    assert not ok('cat /home/diego/moscowle_ia/.env')
    assert not ok('journalctl -u moscowle; rm -rf /')
    assert not ok('systemctl restart moscowle')
    assert not ok('grep -rn PASSWORD /home/diego/moscowle_ia/app')


def test_vault_masks_people_and_drops_clinical_notes():
    v = Vault()
    masked = v.mask(
        {'patient_name': 'Ana Torres', 'email': 'ana@x.pe', 'notes': 'Diagnóstico TEA', 'amount': 150},
        names=('Ana Torres',),
    )
    assert masked['patient_name'].startswith('«P') and masked['email'].startswith('«E')
    assert masked['notes'] == '[omitido]' and masked['amount'] == 150
    text = v.mask_text('¿Cuánto debe ana torres? escríbele a ana@x.pe o al 987 654 321', names=('Ana Torres',))
    assert 'Ana' not in text and 'ana@' not in text and '987' not in text
    assert v.unmask(f'{masked["patient_name"]} debe S/ 150') == 'Ana Torres debe S/ 150'


def test_only_enabled_roles_go_through_opencode(app):
    admin, ther = _user('admin'), _user('terapista')
    assert not opencode_agent.enabled_for(admin)  # apagado por defecto
    _enable()
    assert opencode_agent.enabled_for(admin) and not opencode_agent.enabled_for(ther)
    opencode_client.block('cuota', 60)
    assert not opencode_agent.enabled_for(admin)  # en pausa: cadena actual


def test_read_tool_runs_in_the_loop_and_write_tool_waits_for_confirmation(app, monkeypatch):
    from app.services import tools_registry

    admin = _user('admin')
    _enable()
    ran = []
    monkeypatch.setattr(
        tools_registry, 'execute_tool', lambda name, args, user_id=None, role=None: ran.append(name) or {'sedes': []}
    )
    _script(
        monkeypatch,
        [
            {'kind': 'tool', 'tool': 'list_sedes', 'args': {}, 'reason': 'Ver sedes'},
            {'kind': 'tool', 'tool': 'create_expense', 'args': {'amount': 50, 'category': 'material'}},
        ],
    )
    events = list(opencode_agent.run(admin, 'registra 50 de material en la sede principal'))
    assert ran == ['list_sedes']  # la de escritura NO se ejecutó
    done = events[-1]
    assert done['type'] == 'done' and done['pending_confirm']['name'] == 'create_expense'
    assert any(e['type'] == 'confirm' for e in events)


def test_confirmed_write_runs_once_and_model_only_writes_the_summary(app, monkeypatch):
    from app.services import tools_registry

    admin = _user('admin')
    _enable()
    ran = []
    monkeypatch.setattr(
        tools_registry, 'execute_tool', lambda name, args, user_id=None, role=None: ran.append(name) or {'id': 7}
    )
    _script(monkeypatch, [{'kind': 'answer', 'answer': 'Gasto registrado ✅'}])
    events = list(opencode_agent.run(admin, 'sí', confirmed_tool={'name': 'create_expense', 'args': {'amount': 50}}))
    assert ran == ['create_expense'] and events[-2] == {'type': 'final', 'content': 'Gasto registrado ✅'}


def test_unavailable_before_any_tool_falls_back_but_after_a_tool_it_does_not(app, monkeypatch):
    from app.services import tools_registry

    admin = _user('admin')
    _enable()
    _script(monkeypatch, [OpencodeUnavailableError('FreeTierError')])
    with pytest.raises(OpencodeUnavailableError):
        list(opencode_agent.run(admin, 'hola'))

    opencode_client.unblock('chat')
    monkeypatch.setattr(tools_registry, 'execute_tool', lambda *a, **k: {'sedes': []})
    _script(monkeypatch, [{'kind': 'tool', 'tool': 'list_sedes', 'args': {}}, OpencodeUnavailableError('quota')])
    events = list(opencode_agent.run(admin, 'sedes'))
    assert events[-2]['type'] == 'final' and 'list_sedes' in events[-2]['content']


def test_names_never_reach_the_model(app, monkeypatch):
    from app.services import ai_privacy, tools_registry

    admin = _user('admin')
    _enable()
    monkeypatch.setattr(ai_privacy, 'known_names', lambda ttl=300: ('Lucía Quispe Rojas',))
    monkeypatch.setattr(
        tools_registry,
        'execute_tool',
        lambda name, args, user_id=None, role=None: {'patients': [{'name': 'Lucía Quispe Rojas', 'notes': 'TDAH'}]},
    )
    sent = _script(
        monkeypatch,
        [
            {'kind': 'tool', 'tool': 'search_patients', 'args': {'query': '«P1»'}},
            {'kind': 'answer', 'answer': '«P1» está al día.'},
        ],
    )
    events = list(opencode_agent.run(admin, '¿Lucía Quispe Rojas está al día?'))
    assert all('Lucía' not in t and 'TDAH' not in t for t in sent)
    call = next(e for e in events if e['type'] == 'tool_call')
    assert call['args'] == {'query': 'Lucía Quispe Rojas'}  # la tool recibe el valor real
    assert events[-2]['content'] == 'Lucía Quispe Rojas está al día.'


def test_stream_route_uses_opencode_for_admin(app, client, monkeypatch):
    from flask_jwt_extended import create_access_token

    admin = _user('admin')
    _enable()
    _script(monkeypatch, [{'kind': 'answer', 'answer': '¡Hola! ¿En qué te ayudo?'}])
    headers = {'Authorization': 'Bearer ' + create_access_token(identity=str(admin.id))}
    body = client.post('/mcp/chat/stream', json={'message': 'hola'}, headers=headers).get_data(as_text=True)
    events = [json.loads(line[6:]) for line in body.splitlines() if line.startswith('data: ')]
    assert {'type': 'final', 'content': '¡Hola! ¿En qué te ayudo?'} in events
    assert events[-1]['type'] == 'done' and events[-1]['provider'] == 'opencode'


def test_list_users_reports_the_real_total_not_the_page(app):
    """El asistente decía 50 con 61 usuarios: el total salía de una lista cortada en 50."""
    from app.services.mcp_service import _trim_tool_result
    from app.services.tools_registry import handle_list_users

    for _ in range(3):
        _user('jugador')
    out = handle_list_users()
    assert out['count'] == User.query.count()
    assert sum(out['by_role'].values()) == out['count'] and out['active'] + out['inactive'] == out['count']
    trimmed = _trim_tool_result(out)  # texto (puede venir truncado): el total va antes que la lista
    assert f'"count": {out["count"]}' in trimmed and '"by_role"' in trimmed


def test_small_panel_is_read_only_and_points_to_full_screen(app, monkeypatch):
    """En el panel pequeño no hay tools de escritura; al pasar a pantalla completa MiMo recibe el catálogo completo."""
    admin = _user('admin')
    _enable()
    sent = _script(monkeypatch, [{'kind': 'answer', 'answer': 'a'}, {'kind': 'answer', 'answer': 'b'}])
    list(opencode_agent.run(admin, 'crea un usuario', mode='chiquito'))
    list(opencode_agent.run(admin, 'crea un usuario', mode='grande'))
    small, full = sent
    assert 'PANTALLA COMPLETA' in small and '- create_user(' not in small
    assert 'MODO COMPLETO' in full and '- create_user(' in full  # sesión nueva, catálogo con escritura


def test_catalog_shows_the_fields_inside_a_list_of_sessions():
    """MiMo no sabía armar batch_create_sessions: el catálogo no mostraba los campos de cada sesión."""
    from app.services.tools_registry import get_tools_for_mode

    cat = opencode_agent._catalog(get_tools_for_mode('grande', 'admin'))
    line = next(ln for ln in cat.splitlines() if ln.startswith('- batch_create_sessions('))
    assert 'patient_id:integer' in line and 'day:string (YYYY-MM-DD)' in line and 'time:string (HH:MM)' in line


def test_every_message_carries_today_with_weekday_and_calendar(app, monkeypatch):
    from datetime import date

    from app.services import report_service

    admin = _user('admin')
    _enable()
    monkeypatch.setattr(report_service, 'lima_today', lambda: date(2026, 10, 19))
    sent = _script(monkeypatch, [{'kind': 'answer', 'answer': 'ok'}])
    list(opencode_agent.run(admin, 'agenda lunes, miércoles y viernes'))
    assert '[Hoy: lunes 2026-10-19 (Lima).' in sent[0] and 'mi 2026-10-21' in sent[0] and 'vi 2026-10-23' in sent[0]


def test_asking_to_confirm_in_text_is_corrected_into_a_tool_proposal(app, monkeypatch):
    """«Por favor, confirma las sesiones» sin proponer la tool no creaba nada."""
    from app.services import tools_registry

    admin = _user('admin')
    _enable()
    ran = []
    monkeypatch.setattr(tools_registry, 'execute_tool', lambda *a, **k: ran.append(a[0]) or {'ok': True})
    sessions = [{'patient_id': 80, 'day': '2026-10-21', 'time': '11:00'}]
    _script(
        monkeypatch,
        [
            {'kind': 'answer', 'answer': 'Sesión del miércoles 21/10 a las 11:00. Por favor, confirma las sesiones.'},
            {'kind': 'tool', 'tool': 'batch_create_sessions', 'args': {'sessions': sessions}},
        ],
    )
    events = list(opencode_agent.run(admin, 'crea las sesiones'))
    assert ran == [] and events[-1]['pending_confirm']['name'] == 'batch_create_sessions'


def test_after_confirming_one_action_the_next_one_is_proposed(app, monkeypatch):
    """«Ajusta la cuota y crea las sesiones»: tras confirmar la primera, se propone la segunda."""
    from app.services import tools_registry

    admin = _user('admin')
    _enable()
    ran = []
    monkeypatch.setattr(tools_registry, 'execute_tool', lambda *a, **k: ran.append(a[0]) or {'success': True})
    sessions = [{'patient_id': 80, 'day': '2026-10-21', 'time': '11:00'}]
    sent = _script(monkeypatch, [{'kind': 'tool', 'tool': 'batch_create_sessions', 'args': {'sessions': sessions}}])
    events = list(
        opencode_agent.run(
            admin, 'sí', confirmed_tool={'name': 'update_installment', 'args': {'installment_id': 1, 'amount': 225}}
        )
    )
    assert ran == ['update_installment'] and 'OTRA acción pendiente' in sent[0]
    assert events[-1]['pending_confirm']['name'] == 'batch_create_sessions'


def test_adjust_installment_changes_unpaid_installment_and_keeps_paid_ones(app):
    from datetime import date

    from app.models import Contract, Installment
    from app.services import billing

    patient = _user('jugador')
    c = billing.create_plan(patient.id, 550, 19, date(2026, 10, 19), installments=3)
    first = sorted(c.installments, key=lambda i: i.number)[0]
    inst, changes = billing.adjust_installment(first.id, amount=225, reason='Mes prorrateado: 6 sesiones')
    assert inst.amount == 225 and 'S/ 550.00 → S/ 225.00' in changes[0] and 'prorrateado' in inst.notes
    assert db.session.get(Contract, c.id).total_amount == pytest.approx(225 + 550 * 2)
    inst.status = 'paid'
    db.session.commit()
    with pytest.raises(billing.BillingError):
        billing.adjust_installment(first.id, amount=300)
    Installment.query.filter_by(contract_id=c.id).delete()
    Contract.query.filter_by(id=c.id).delete()
    db.session.commit()
