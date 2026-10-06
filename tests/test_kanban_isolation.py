import json

import pytest

from app.extensions import bcrypt
from app.models import KanbanTask, User
from app.models.user import patient_therapist


def _mk(session, email, role, name):
    u = User(
        username=name,
        email=email,
        password=bcrypt.generate_password_hash('secret123').decode('utf-8'),
        role=role,
    )
    session.add(u)
    session.flush()
    return u


@pytest.fixture(autouse=True)
def _fresh_login_per_request(app):
    """El `g` del app context de sesión cachea el usuario de Flask-Login entre peticiones; se limpia solo aquí."""

    def _clear(exc):
        from flask import g

        g.pop('_login_user', None)

    funcs = app.teardown_request_funcs.setdefault(None, [])
    funcs.append(_clear)
    yield
    funcs.remove(_clear)


@pytest.fixture
def world(session, test_user):
    session.execute(patient_therapist.delete())
    User.query.filter(User.email.ilike('%@kbiso.test')).delete()
    KanbanTask.query.delete()
    session.flush()
    sara = _mk(session, 'sara@kbiso.test', 'terapista', 'Sara')
    luis = _mk(session, 'luis@kbiso.test', 'terapista', 'Luis')
    pac_sara = _mk(session, 'pac1@kbiso.test', 'jugador', 'PacSara')
    pac_luis = _mk(session, 'pac2@kbiso.test', 'jugador', 'PacLuis')
    sara.associated_patients.append(pac_sara)
    luis.associated_patients.append(pac_luis)
    session.commit()
    return {'admin': test_user, 'sara': sara, 'luis': luis, 'pac_sara': pac_sara, 'pac_luis': pac_luis}


def _login(app, email, password='secret123'):
    client = app.test_client()
    r = client.post(
        '/api/login', content_type='application/json', data=json.dumps({'email': email, 'password': password})
    )
    assert r.status_code == 200, r.get_data(as_text=True)
    return client


def _post(client, payload):
    return client.post('/api/kanban/tasks', content_type='application/json', data=json.dumps(payload))


def _titles(client, query=''):
    r = client.get('/api/kanban/tasks' + query)
    assert r.status_code == 200
    return sorted(t['title'] for t in r.get_json())


def test_each_user_sees_only_their_own_board(app, world):
    client = _login(app, 'test@example.com', 'password123')
    assert _post(client, {'title': 'Para Sara', 'assigned_to_id': world['sara'].id}).status_code == 201
    assert _post(client, {'title': 'Para Luis', 'assigned_to_id': world['luis'].id}).status_code == 201
    assert _titles(client) == ['Para Luis', 'Para Sara']  # admin ve todo
    client = _login(app, 'sara@kbiso.test')
    assert _titles(client) == ['Para Sara']
    client = _login(app, 'luis@kbiso.test')
    assert _titles(client) == ['Para Luis']


def test_admin_filters_by_user_role_and_mine(app, world):
    client = _login(app, 'test@example.com', 'password123')
    _post(client, {'title': 'T-sara', 'assigned_to_id': world['sara'].id})
    _post(client, {'title': 'T-pac', 'assigned_to_id': world['pac_sara'].id})
    _post(client, {'title': 'T-mia'})  # personal del admin
    assert _titles(client, f'?assigned_to={world["sara"].id}') == ['T-sara']
    assert _titles(client, '?role=jugador') == ['T-pac']
    assert _titles(client, '?role=terapista') == ['T-sara']
    assert _titles(client, '?mine=1') == ['T-mia']


def test_admin_broadcast_creates_one_copy_per_recipient(app, world):
    client = _login(app, 'test@example.com', 'password123')
    r = _post(client, {'title': 'General terapeutas', 'audience': 'terapista'})
    assert r.status_code == 201 and r.get_json()['created'] >= 2
    client = _login(app, 'sara@kbiso.test')
    assert _titles(client) == ['General terapeutas']
    client.get('/api/kanban/tasks')
    # mover la copia de Sara no afecta la de Luis
    tid = client.get('/api/kanban/tasks').get_json()[0]['id']
    client.patch(f'/api/kanban/tasks/{tid}', content_type='application/json', data=json.dumps({'column': 'done'}))
    client = _login(app, 'luis@kbiso.test')
    assert client.get('/api/kanban/tasks').get_json()[0]['column'] == 'todo'


def test_therapist_can_only_assign_to_own_patients(app, world):
    client = _login(app, 'sara@kbiso.test')
    assert _post(client, {'title': 'ok', 'assigned_to_id': world['pac_sara'].id}).status_code == 201
    assert _post(client, {'title': 'no', 'assigned_to_id': world['pac_luis'].id}).status_code == 403
    assert _post(client, {'title': 'no-admin', 'assigned_to_id': world['admin'].id}).status_code == 403
    assert _post(client, {'title': 'no-bcast', 'audience': 'terapista'}).status_code == 403
    r = _post(client, {'title': 'Para mis pacientes', 'audience': 'my_patients'})
    assert r.status_code == 201 and r.get_json()['created'] == 1
    ids = {u['id'] for u in client.get('/api/kanban/assignees').get_json()['users']}
    assert ids == {world['pac_sara'].id}


def test_cannot_touch_someone_elses_task(app, world):
    client = _login(app, 'test@example.com', 'password123')
    tid = _post(client, {'title': 'Solo Luis', 'assigned_to_id': world['luis'].id}).get_json()['id']
    client = _login(app, 'sara@kbiso.test')

    def patch(body):
        return client.patch(f'/api/kanban/tasks/{tid}', content_type='application/json', data=json.dumps(body))

    assert patch({'column': 'done'}).status_code == 403
    assert client.delete(f'/api/kanban/tasks/{tid}').status_code == 403
    assert client.get(f'/api/kanban/tasks/{tid}/attachments').status_code == 403
    client = _login(app, 'luis@kbiso.test')
    assert client.delete(f'/api/kanban/tasks/{tid}').status_code == 403  # asignado, pero no creador
    assert patch({'column': 'review'}).status_code == 200


def test_patient_sees_only_own_tasks_and_cannot_create(app, world):
    client = _login(app, 'sara@kbiso.test')
    _post(client, {'title': 'Tarea paciente', 'assigned_to_id': world['pac_sara'].id})
    client = _login(app, 'pac1@kbiso.test')
    assert _titles(client) == ['Tarea paciente']
    assert _post(client, {'title': 'x'}).status_code == 403
    assert client.get('/api/kanban/stats').get_json()['total'] == 1


def _move(client, tid, column):
    return client.patch(
        f'/api/kanban/tasks/{tid}', content_type='application/json', data=json.dumps({'column': column})
    )


def _task(client, tid):
    return next(t for t in client.get('/api/kanban/tasks').get_json() if t['id'] == tid)


def test_review_notifies_admin_who_created_the_task(app, world):
    from app.models.notification_group import NotificationGroup, NotificationItem

    client = _login(app, 'test@example.com', 'password123')
    tid = _post(client, {'title': 'Informe mensual', 'assigned_to_id': world['sara'].id}).get_json()['id']
    client = _login(app, 'sara@kbiso.test')
    assert _move(client, tid, 'review').status_code == 200
    group = NotificationGroup.query.filter_by(user_id=world['admin'].id, group_key=f'kanban:{tid}').first()
    assert group is not None, 'el admin creador debe enterarse de que su tarea pasó a revisión'
    last = NotificationItem.query.filter_by(group_id=group.id).order_by(NotificationItem.id.desc()).first()
    assert 'Revisión' in last.message and 'Sara' in last.message
    # quien mueve la tarea no se notifica a sí mismo
    assert (
        NotificationGroup.query.filter_by(user_id=world['sara'].id, group_key=f'kanban:{tid}').count() == 1
    )  # solo el aviso de creación


def test_timer_runs_only_in_progress_and_freezes_in_review(app, world):
    from datetime import timedelta

    from app.extensions import db
    from app.routes.kanban_routes import _now

    client = _login(app, 'test@example.com', 'password123')
    tid = _post(client, {'title': 'Con límite', 'assigned_to_id': world['sara'].id, 'max_minutes': 60}).get_json()['id']
    assert _task(client, tid)['timer_running'] is False

    _move(client, tid, 'in-progress')
    t = _task(client, tid)
    assert t['timer_running'] is True

    # simula 10 minutos de trabajo
    row = db.session.get(KanbanTask, tid)
    row.timer_start = _now() - timedelta(minutes=10)
    db.session.commit()

    _move(client, tid, 'review')
    t = _task(client, tid)
    assert t['timer_running'] is False and t['timer_start'] is None
    frozen = t['elapsed_seconds']
    assert 590 <= frozen <= 620

    # en revisión no avanza ni vence aunque pase el tiempo
    row = db.session.get(KanbanTask, tid)
    assert row.timer_start is None
    assert _task(client, tid)['elapsed_seconds'] == frozen

    # al volver a progreso retoma desde lo consumido
    _move(client, tid, 'in-progress')
    t = _task(client, tid)
    assert t['timer_running'] is True and t['elapsed_seconds'] >= frozen

    _move(client, tid, 'done')
    t = _task(client, tid)
    assert t['timer_running'] is False and t['is_expired'] is False


def test_extend_does_not_start_timer_outside_progress(app, world):
    client = _login(app, 'test@example.com', 'password123')
    tid = _post(client, {'title': 'Extender', 'assigned_to_id': world['sara'].id, 'max_minutes': 30}).get_json()['id']
    r = client.patch(
        f'/api/kanban/tasks/{tid}/extend', content_type='application/json', data=json.dumps({'minutes': 15})
    )
    assert r.status_code == 200
    body = r.get_json()
    assert body['max_minutes'] == 45 and body['timer_running'] is False
