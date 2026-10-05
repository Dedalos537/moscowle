"""Listado de gastos: un gasto borrado (baja logica) no debe aparecer ni sumar, y el
filtro por mes incluye el dia 1 del mes pedido pero NO el dia 1 del mes siguiente."""

import uuid
from datetime import datetime

from flask_jwt_extended import create_access_token

from app.extensions import db
from app.models import User
from app.models.payment import Expense


def _admin(session):
    tag = uuid.uuid4().hex[:8]
    u = User(username=f'a{tag}', email=f'{tag}@exp.test', password='x', role='admin')
    session.add(u)
    session.commit()
    return u


def _expense(when, active=True):
    e = Expense(
        category='operational', amount=10.0, date=when, description=f'gasto-{uuid.uuid4().hex[:6]}', is_active=active
    )
    db.session.add(e)
    db.session.commit()
    return e


def _ids(client, admin, query=''):
    token = create_access_token(identity=str(admin.id))
    r = client.get(f'/admin/api/expenses{query}', headers={'Authorization': f'Bearer {token}'})
    assert r.status_code == 200, r.get_data(as_text=True)
    return {row['id'] for row in r.get_json()['data']}


def test_soft_deleted_expense_is_not_listed(client, session):
    admin = _admin(session)
    alive = _expense(datetime(2031, 4, 10))
    deleted = _expense(datetime(2031, 4, 11), active=False)
    ids = _ids(client, admin)
    assert alive.id in ids
    assert deleted.id not in ids


def test_month_filter_excludes_first_day_of_next_month(client, session):
    admin = _admin(session)
    first_day = _expense(datetime(2031, 7, 1))
    last_day = _expense(datetime(2031, 7, 31))
    next_first = _expense(datetime(2031, 8, 1))
    ids = _ids(client, admin, '?month=2031-07')
    assert first_day.id in ids and last_day.id in ids
    assert next_first.id not in ids


def test_last_day_afternoon_is_included_and_next_midnight_is_not(client, session):
    admin = _admin(session)
    afternoon = _expense(datetime(2031, 9, 30, 15, 30))
    next_midnight = _expense(datetime(2031, 10, 1, 0, 0))
    ids = _ids(client, admin, '?month=2031-09')
    assert afternoon.id in ids and next_midnight.id not in ids


def test_december_month_filter_excludes_january_first(client, session):
    admin = _admin(session)
    dec = _expense(datetime(2031, 12, 15))
    jan_first = _expense(datetime(2032, 1, 1))
    ids = _ids(client, admin, '?month=2031-12')
    assert dec.id in ids and jan_first.id not in ids
