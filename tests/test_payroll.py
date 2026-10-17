"""Nómina por periodo: lo pagado se aplica al mes que se liquida y las sesiones sin duración no valen 0."""

import uuid
from datetime import date, datetime

import pytest

from app.extensions import db
from app.models import Appointment, User
from app.models.billing import PayrollPeriod
from app.models.payment import Expense
from app.services import payroll

_MADE: list = []


def _user(role, **kw):
    tag = uuid.uuid4().hex[:8]
    u = User(username=f'{role[:3]}{tag}', email=f'{tag}@pay.test', password='x', role=role, **kw)
    db.session.add(u)
    db.session.commit()
    _MADE.append(u)
    return u


@pytest.fixture(autouse=True)
def clean(app):
    _MADE.clear()
    yield
    db.session.rollback()
    ids = [u.id for u in _MADE]
    if ids:
        Expense.query.filter(Expense.therapist_id.in_(ids)).delete(synchronize_session=False)
        PayrollPeriod.query.filter(PayrollPeriod.therapist_id.in_(ids)).delete(synchronize_session=False)
        Appointment.query.filter(Appointment.therapist_id.in_(ids)).delete(synchronize_session=False)
        for u in User.query.filter(User.id.in_(ids)):
            u.is_active = False
        db.session.commit()


def _session(t, p, when, minutes):
    db.session.add(
        Appointment(
            therapist_id=t.id,
            patient_id=p.id,
            title='Terapia',
            start_time=when,
            status='completed',
            duration_minutes=minutes,
        )
    )


def test_period_amount_uses_standard_duration_for_missing_ones(app):
    t = _user('terapista', salary_base=2000, contract_hours=100)  # 20 por hora
    p = _user('jugador')
    _session(t, p, datetime(2026, 4, 6, 15), 60)
    _session(t, p, datetime(2026, 4, 13, 15), None)  # sin duración: cuenta 45 min
    _session(t, p, datetime(2026, 4, 20, 15), 30)
    db.session.commit()
    row = payroll.sync(t, '2026-04')
    assert row.hours == pytest.approx(2.25) and row.amount_due == pytest.approx(45.0)
    assert row.sessions == 3 and row.sessions_without_duration == 1
    assert row.due_date == date(2026, 5, 5)


def test_paying_april_in_may_settles_april_without_overpaying_may(app):
    t = _user('terapista', salary_base=2000, contract_hours=100)
    p = _user('jugador')
    _session(t, p, datetime(2026, 4, 6, 15), 60)
    _session(t, p, datetime(2026, 5, 6, 15), 60)
    db.session.commit()
    _, april = payroll.pay(t.id, '2026-04', 20, 'Transferencia', date_=datetime(2026, 5, 5, 10))
    assert april['status'] == 'paid' and april['balance'] == 0
    may = payroll.serialize(payroll.sync(t, '2026-05'), t, today=date(2026, 5, 20))
    assert may['paid'] == 0 and may['balance'] == pytest.approx(20)  # antes el pago de abril «sobrepagaba» mayo


def test_legacy_payments_without_period_count_in_their_month(app):
    t = _user('terapista', salary_base=2000, contract_hours=100)
    p = _user('jugador')
    _session(t, p, datetime(2026, 3, 10, 15), 120)
    db.session.add(Expense(category='therapist_payment', amount=15, date=datetime(2026, 3, 28), therapist_id=t.id))
    db.session.commit()
    info = payroll.serialize(payroll.sync(t, '2026-03'), t, today=date(2026, 4, 30))
    assert info['paid'] == 15 and info['balance'] == pytest.approx(25) and info['status'] == 'overdue'
