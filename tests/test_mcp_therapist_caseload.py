import pytest

from app.extensions import bcrypt
from app.models import User
from app.services.tools_registry import CORE_TOOL_NAMES, TOOL_REGISTRY, execute_tool


@pytest.fixture
def therapist_and_patients(session):
    User.query.filter(User.email.ilike('%@mcp.test')).delete()
    session.flush()

    therapist = User(
        username='Milagros Barrutia',
        email='milagros@mcp.test',
        password=bcrypt.generate_password_hash('secret123').decode('utf-8'),
        role='terapista',
    )
    session.add(therapist)
    session.flush()

    p1 = User(
        username='Paciente Uno',
        email='p1@mcp.test',
        password=bcrypt.generate_password_hash('secret123').decode('utf-8'),
        role='jugador',
        assigned_therapist_id=therapist.id,
    )
    p2 = User(
        username='Paciente Dos',
        email='p2@mcp.test',
        password=bcrypt.generate_password_hash('secret123').decode('utf-8'),
        role='jugador',
        assigned_therapist_id=therapist.id,
    )
    inactive = User(
        username='Paciente Inactivo',
        email='pinactivo@mcp.test',
        password=bcrypt.generate_password_hash('secret123').decode('utf-8'),
        role='jugador',
        assigned_therapist_id=therapist.id,
        is_active=False,
    )
    other = User(
        username='Paciente Suelto',
        email='psuelto@mcp.test',
        password=bcrypt.generate_password_hash('secret123').decode('utf-8'),
        role='jugador',
    )
    session.add_all([p1, p2, inactive, other])
    session.commit()
    return {'therapist': therapist, 'active': [p1, p2]}


def test_tool_registered_as_core():
    assert 'get_therapist_patients' in CORE_TOOL_NAMES
    assert TOOL_REGISTRY['get_therapist_patients']['category'] == 'read'


def test_counts_only_active_assigned_patients(session, therapist_and_patients):
    result = execute_tool(
        'get_therapist_patients',
        {'therapist_name': 'Milagros'},
        user_id=None,
        role='admin',
    )
    assert result['success'] is True
    assert result['therapist']['username'] == 'Milagros Barrutia'
    assert result['count'] == 2
    names = {p['username'] for p in result['patients']}
    assert names == {'Paciente Uno', 'Paciente Dos'}


def test_unknown_therapist_returns_error(session, therapist_and_patients):
    result = execute_tool(
        'get_therapist_patients',
        {'therapist_name': 'Noexiste'},
        user_id=None,
        role='admin',
    )
    assert 'error' in result


def test_short_name_returns_error(session, therapist_and_patients):
    result = execute_tool(
        'get_therapist_patients',
        {'therapist_name': 'M'},
        user_id=None,
        role='admin',
    )
    assert 'error' in result


def test_missing_param_returns_error(session, therapist_and_patients):
    result = execute_tool('get_therapist_patients', {}, user_id=None, role='admin')
    assert 'error' in result
