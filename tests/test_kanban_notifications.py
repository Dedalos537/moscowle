import json

import pytest

from app.extensions import bcrypt
from app.models import User
from app.models.notification_group import NotificationGroup, NotificationItem


@pytest.fixture
def admin_client(client, test_user):
    resp = client.post(
        '/api/login',
        content_type='application/json',
        data=json.dumps({'email': 'test@example.com', 'password': 'password123'}),
    )
    assert resp.status_code == 200
    return client


@pytest.fixture
def assignee(session):
    User.query.filter(User.email.ilike('%@kanban.test')).delete()
    session.flush()
    user = User(
        username='Terapeuta Kanban',
        email='therapist@kanban.test',
        password=bcrypt.generate_password_hash('secret123').decode('utf-8'),
        role='terapista',
    )
    session.add(user)
    session.commit()
    return user


def _create_task(admin_client, assignee_id, title='Tarea de prueba'):
    resp = admin_client.post(
        '/api/kanban/tasks',
        content_type='application/json',
        data=json.dumps({'title': title, 'assigned_to_id': assignee_id}),
    )
    assert resp.status_code == 201
    return resp.get_json()


def test_create_task_notifies_assignee(admin_client, assignee):
    task = _create_task(admin_client, assignee.id)
    group = NotificationGroup.query.filter_by(user_id=assignee.id, group_key=f'kanban:{task["id"]}').first()
    assert group is not None
    assert group.priority == 'normal'
    assert group.count == 1
    assert group.title == 'Nueva tarea asignada'
    item = NotificationItem.query.filter_by(group_id=group.id).first()
    assert 'Tarea de prueba' in item.message


def test_move_task_notifies_high(admin_client, assignee):
    task = _create_task(admin_client, assignee.id)
    resp = admin_client.patch(
        f'/api/kanban/tasks/{task["id"]}',
        content_type='application/json',
        data=json.dumps({'column': 'in-progress'}),
    )
    assert resp.status_code == 200
    group = NotificationGroup.query.filter_by(user_id=assignee.id, group_key=f'kanban:{task["id"]}').first()
    assert group is not None
    assert group.count >= 2
    assert group.priority == 'high'
    latest = NotificationItem.query.filter_by(group_id=group.id).order_by(NotificationItem.id.desc()).first()
    assert 'Por hacer' in latest.message
    assert 'En progreso' in latest.message


def test_self_assigned_task_does_not_notify_creator(admin_client, test_user):
    resp = admin_client.post(
        '/api/kanban/tasks',
        content_type='application/json',
        data=json.dumps({'title': 'Tarea propia', 'assigned_to_id': test_user.id}),
    )
    assert resp.status_code == 201
    task = resp.get_json()
    group = NotificationGroup.query.filter_by(user_id=test_user.id, group_key=f'kanban:{task["id"]}').first()
    assert group is None
