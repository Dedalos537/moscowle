"""Definiciones del resumen financiero. 'Deuda vencida' debe contar lo mismo que el
reporte de deudores (solo pacientes activos con plan: monto > 0 y fecha de
vencimiento) y 'ingreso real' solo lo efectivamente cobrado. Se mide por
diferencias porque la BD de pruebas se comparte entre tests."""

import uuid
from datetime import date, datetime, timedelta

from app.extensions import db
from app.models import User
from app.models.payment import Payment
from app.services.financial_service import FinancialService
from app.services.payment_service import PaymentService


def _patient(session, **kw):
    tag = uuid.uuid4().hex[:8]
    defaults = dict(
        username=f'p{tag}',
        email=f'{tag}@fin.test',
        password='x',
        role='jugador',
        is_active=True,
        payment_amount=100.0,
        payment_plan='monthly',
        payment_due_date=date.today() - timedelta(days=3),
    )
    defaults.update(kw)
    u = User(**defaults)
    session.add(u)
    session.commit()
    return u


def _summary():
    return PaymentService().get_financial_summary()


def test_overdue_counts_active_patient_with_plan(session):
    before = _summary()
    _patient(session)
    after = _summary()
    assert after['overdue_users_count'] == before['overdue_users_count'] + 1
    assert after['overdue_amount'] == before['overdue_amount'] + 100.0


def test_overdue_ignores_inactive_patients(session):
    before = _summary()
    _patient(session, is_active=False, payment_amount=500.0)
    after = _summary()
    assert after['overdue_users_count'] == before['overdue_users_count']
    assert after['overdue_amount'] == before['overdue_amount']


def test_overdue_ignores_patients_without_plan_amount(session):
    before = _summary()
    _patient(session, payment_amount=0.0)
    _patient(session, payment_amount=None)
    after = _summary()
    assert after['overdue_users_count'] == before['overdue_users_count']


def test_overdue_matches_the_debtors_report(session):
    """Una sola definicion de deuda: el resumen coincide con 'vencidos' del reporte."""
    _patient(session)
    _patient(session, is_active=False, payment_amount=900.0)
    summary = _summary()
    report = FinancialService().build_debt_report()['summary']
    assert summary['overdue_users_count'] == report['vencidos']


def test_income_real_counts_only_collected_payments(session):
    patient = _patient(session, payment_due_date=None)
    before = _summary()['income_real']
    now = datetime.utcnow()
    for status, amount in (('completed', 50.0), ('paid', 30.0), ('pending', 70.0), ('overdue', 90.0)):
        db.session.add(Payment(patient_id=patient.id, amount=amount, date=now, method='cash', status=status))
    db.session.commit()
    assert _summary()['income_real'] == before + 80.0


def test_income_real_counts_legacy_null_status_as_collected(session):
    patient = _patient(session, payment_due_date=None)
    before = _summary()['income_real']
    db.session.add(Payment(patient_id=patient.id, amount=40.0, date=datetime.utcnow(), method='cash', status=None))
    db.session.commit()
    assert _summary()['income_real'] == before + 40.0
