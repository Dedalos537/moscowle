"""Alcance por session_id: un terapeuta solo toca sesiones propias o de sus
pacientes. complete/cancel/update_session_plan reciben session_id, no patient_id."""

import uuid
from datetime import datetime, timedelta

import pytest

from app.models import User
from app.models.appointment import Appointment
from app.services.policy import PolicyEngine


def _user(session, name, role, **kw):
    u = User(username=name, email=f'{name}-{uuid.uuid4().hex[:8]}@scope.test', password='x', role=role, **kw)
    session.add(u)
    session.flush()
    return u


@pytest.fixture
def world(session):
    ter_a = _user(session, 'terA', 'terapista')
    ter_b = _user(session, 'terB', 'terapista')
    pat_a = _user(session, 'patA', 'jugador', assigned_therapist_id=ter_a.id)
    pat_b = _user(session, 'patB', 'jugador', assigned_therapist_id=ter_b.id)
    when = datetime.utcnow() + timedelta(days=1)
    own = Appointment(therapist_id=ter_a.id, patient_id=pat_a.id, start_time=when)
    foreign = Appointment(therapist_id=ter_b.id, patient_id=pat_b.id, start_time=when)
    session.add_all([own, foreign])
    session.commit()
    return {'ter_a': ter_a, 'pat_a': pat_a, 'own': own, 'foreign': foreign}


@pytest.mark.parametrize('key', ['session_id', 'appointment_id'])
def test_therapist_blocked_on_foreign_session(world, key):
    ok, _, motivo = PolicyEngine().check(
        'complete_session', {key: world['foreign'].id}, role='terapista', user_id=world['ter_a'].id
    )
    assert not ok and 'alcance' in motivo


def test_therapist_allowed_on_own_session(world):
    ok, _, _ = PolicyEngine().check(
        'cancel_session', {'session_id': world['own'].id}, role='terapista', user_id=world['ter_a'].id
    )
    assert ok


def test_missing_session_denied_same_message(world):
    ok, _, motivo = PolicyEngine().check(
        'cancel_session', {'session_id': 999999}, role='terapista', user_id=world['ter_a'].id
    )
    assert not ok and 'alcance' in motivo


def test_patient_blocked_on_session_of_other_patient(world):
    ok, _, _ = PolicyEngine().check(
        'cancel_session', {'session_id': world['foreign'].id}, role='jugador', user_id=world['pat_a'].id
    )
    assert not ok


def test_admin_unrestricted(world):
    ok, _, _ = PolicyEngine().check('complete_session', {'session_id': world['foreign'].id}, role='admin', user_id=1)
    assert ok
