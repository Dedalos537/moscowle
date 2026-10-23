"""Herramientas del asistente para terapeutas y pacientes: siempre sobre el usuario con sesión."""

import uuid
from datetime import datetime, timedelta

from app.extensions import db
from app.models import Appointment, User
from app.models.action_request import ActionRequest
from app.services.tools_registry import execute_tool


def _user(role, **kw):
    tag = uuid.uuid4().hex[:8]
    u = User(username=f'{role[:3]}{tag}', email=f'{tag}@gmail.com', password='x', role=role, **kw)
    db.session.add(u)
    db.session.commit()
    return u


def _link(ther, pat):
    ther.associated_patients.append(pat)
    db.session.commit()


def test_overview_lists_who_has_no_upcoming_session(app):
    ther, a, b = _user('terapista'), _user('jugador'), _user('jugador')
    _link(ther, a)
    _link(ther, b)
    db.session.add(
        Appointment(
            therapist_id=ther.id, patient_id=a.id, start_time=datetime.utcnow() + timedelta(days=2), status='scheduled'
        )
    )
    db.session.commit()
    r = execute_tool('my_patients_overview', {'only_without_upcoming': True}, user_id=ther.id, role='terapista')
    assert r['total_patients'] == 2 and r['without_upcoming_session'] == 1
    assert [p['patient_id'] for p in r['patients']] == [b.id]


def test_request_sessions_only_for_my_patients(app):
    ther, mine, other = _user('terapista'), _user('jugador'), _user('jugador')
    _link(ther, mine)
    ok = execute_tool(
        'request_sessions',
        {'patient_id': mine.id, 'dates': ['2027-03-10'], 'start_time': '10:00', 'end_time': '11:00'},
        user_id=ther.id,
        role='terapista',
    )
    assert ok.get('success'), ok
    assert ActionRequest.query.get(ok['request_id']).requester_id == ther.id
    bad = execute_tool(
        'request_sessions',
        {'patient_id': other.id, 'dates': ['2027-03-10'], 'start_time': '10:00', 'end_time': '11:00'},
        user_id=ther.id,
        role='terapista',
    )
    assert not bad.get('success')


def test_signup_request_and_status(app):
    ther = _user('terapista')
    r = execute_tool('request_patient_signup', {'username': 'Niño Nuevo Pérez'}, user_id=ther.id, role='terapista')
    assert r.get('success'), r
    mine = execute_tool('list_my_requests', {}, user_id=ther.id, role='terapista')
    assert mine['requests'][0]['status'] == 'en revisión'


def test_patient_tools_are_only_for_patients_and_only_their_data(app):
    ther, pat, other = _user('terapista'), _user('jugador'), _user('jugador')
    db.session.add(
        Appointment(
            therapist_id=ther.id,
            patient_id=other.id,
            start_time=datetime.utcnow() + timedelta(days=1),
            status='scheduled',
        )
    )
    db.session.commit()
    mine = execute_tool('my_sessions', {}, user_id=pat.id, role='jugador')
    assert mine['upcoming'] == []  # la sesión es de otro paciente
    denied = execute_tool('my_sessions', {}, user_id=ther.id, role='terapista')
    assert 'error' in denied


def test_mimo_follows_assistant_visibility(app, monkeypatch):
    from app.services import opencode_agent

    monkeypatch.setattr(opencode_agent.oc, 'configured', lambda inst: True)
    monkeypatch.setattr(opencode_agent.oc, 'blocked', lambda inst: False)
    monkeypatch.setattr(opencode_agent, 'settings', lambda: {'enabled': True, 'roles': ['admin']})
    ther = _user('terapista')
    monkeypatch.setattr('app.routes.api.assistant.visible_for', lambda role: role == 'terapista')
    assert opencode_agent.enabled_for(ther) is True
    monkeypatch.setattr('app.routes.api.assistant.visible_for', lambda role: False)
    assert opencode_agent.enabled_for(ther) is False
