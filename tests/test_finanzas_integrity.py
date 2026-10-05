"""Integridad de Finanzas: borrar un pago deshace su efecto en la cuota que saldo (antes la
cuota quedaba 'pagada' sin dinero, o el borrado fallaba por la FK payment_id en MySQL);
un gasto exige monto > 0 y se puede editar; el listado de pagos avisa si se trunca."""

import uuid
from datetime import date, datetime

import pytest
from flask_jwt_extended import create_access_token

from app.extensions import db
from app.models import User
from app.models.contract import Contract, Installment
from app.models.payment import Expense, Payment
from app.services.contract_service import ContractService


def _user(session, role):
    tag = uuid.uuid4().hex[:8]
    u = User(username=f'{role[:3]}{tag}', email=f'{tag}@fin.test', password='x', role=role)
    session.add(u)
    session.commit()
    return u


def _call(client, user, method, path, **kw):
    token = create_access_token(identity=str(user.id))
    return getattr(client, method)(path, headers={'Authorization': f'Bearer {token}'}, **kw)


@pytest.fixture
def paid_installment(session):
    patient = _user(session, 'jugador')
    contract = Contract(patient_id=patient.id, total_amount=400.0, installment_amount=100.0)
    session.add(contract)
    session.flush()
    inst = Installment(contract_id=contract.id, number=1, due_date=date(2031, 3, 1), amount=100.0)
    session.add(inst)
    session.commit()
    ok, payment = ContractService().pay_installment(inst.id, 100.0, 'cash')
    assert ok, payment
    db.session.refresh(inst)
    assert inst.status == 'paid' and inst.paid_amount == 100.0
    return inst, payment


# ---------------------------------------------------------- borrar pago
def test_deleting_payment_reverts_the_installment(client, session, paid_installment):
    inst, payment = paid_installment
    admin = _user(session, 'admin')
    r = _call(client, admin, 'post', f'/admin/api/payments/delete/{payment.id}')
    assert r.status_code == 200, r.get_data(as_text=True)
    db.session.expire_all()
    fresh = db.session.get(Installment, inst.id)
    assert db.session.get(Payment, payment.id) is None
    assert fresh.status == 'pending' and (fresh.paid_amount or 0) == 0
    assert fresh.payment_id is None and fresh.paid_date is None


def test_deleting_one_of_two_payments_leaves_partial(client, session):
    patient = _user(session, 'jugador')
    contract = Contract(patient_id=patient.id, total_amount=400.0, installment_amount=100.0)
    session.add(contract)
    session.flush()
    inst = Installment(contract_id=contract.id, number=1, due_date=date(2031, 4, 1), amount=100.0)
    session.add(inst)
    session.commit()
    service = ContractService()
    _, first = service.pay_installment(inst.id, 40.0, 'cash')
    _, second = service.pay_installment(inst.id, 60.0, 'cash')
    admin = _user(session, 'admin')
    assert _call(client, admin, 'post', f'/admin/api/payments/delete/{second.id}').status_code == 200
    db.session.expire_all()
    fresh = db.session.get(Installment, inst.id)
    assert fresh.paid_amount == 40.0 and fresh.status == 'partial'


# ------------------------------------------------------------- gastos
@pytest.mark.parametrize('amount', ['0', '-5', 'abc', ''])
def test_expense_requires_positive_amount(client, session, amount):
    admin = _user(session, 'admin')
    r = _call(
        client,
        admin,
        'post',
        '/admin/api/expenses/create',
        json={'category': 'operational', 'amount': amount, 'date': '2031-05-01', 'description': 'x'},
    )
    assert r.status_code == 400


def test_expense_can_be_edited(client, session):
    admin = _user(session, 'admin')
    exp = Expense(category='operational', amount=10.0, date=datetime(2031, 5, 2), description='luz')
    session.add(exp)
    session.commit()
    r = _call(client, admin, 'put', f'/admin/api/expenses/{exp.id}', json={'amount': 25.5, 'description': 'luz y agua'})
    assert r.status_code == 200, r.get_data(as_text=True)
    db.session.expire_all()
    fresh = db.session.get(Expense, exp.id)
    assert fresh.amount == 25.5 and fresh.description == 'luz y agua'


def test_expense_edit_rejects_bad_amount_and_inactive(client, session):
    admin = _user(session, 'admin')
    exp = Expense(category='operational', amount=10.0, date=datetime(2031, 5, 3), description='x')
    gone = Expense(category='operational', amount=10.0, date=datetime(2031, 5, 4), description='y', is_active=False)
    session.add_all([exp, gone])
    session.commit()
    assert _call(client, admin, 'put', f'/admin/api/expenses/{exp.id}', json={'amount': -1}).status_code == 400
    assert _call(client, admin, 'put', f'/admin/api/expenses/{gone.id}', json={'amount': 5}).status_code == 404


def test_expense_edit_requires_admin_or_supervisor(client, session):
    therapist = _user(session, 'terapista')
    exp = Expense(category='operational', amount=10.0, date=datetime(2031, 5, 5), description='x')
    session.add(exp)
    session.commit()
    assert _call(client, therapist, 'put', f'/admin/api/expenses/{exp.id}', json={'amount': 9}).status_code == 403


# ------------------------------------------------------ listado de pagos
def test_payments_list_reports_truncation(client, session):
    admin = _user(session, 'admin')
    patient = _user(session, 'jugador')
    for _ in range(3):
        session.add(Payment(patient_id=patient.id, amount=1.0, date=datetime(2031, 6, 1), method='cash'))
    session.commit()
    body = _call(client, admin, 'get', '/admin/api/payments/all?limit=2').get_json()
    assert len(body['payments']) == 2 and body['truncated'] is True and body['total'] >= 3
    full = _call(client, admin, 'get', '/admin/api/payments/all').get_json()
    assert 'truncated' in full and full['total'] >= 3
