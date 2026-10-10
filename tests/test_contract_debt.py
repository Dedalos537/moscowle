"""Deuda por cuotas de contrato en el panel, el reporte de deudores y el resumen diario (opción «a»)."""

import uuid
from datetime import datetime, timedelta

import pytest

from app.extensions import db
from app.models import User
from app.models.contract import Contract, Installment
from app.services.contract_debt import contract_debt
from app.services.financial_service import FinancialService
from app.services.payment_service import PaymentService

TODAY = datetime.utcnow().date()
_CREATED = {'users': [], 'contracts': []}


@pytest.fixture(autouse=True)
def _cleanup(app):
    """La base de pruebas es compartida y SQLite reutiliza ids de usuarios borrados: si los contratos quedaran,
    otra prueba podría heredar la deuda de un paciente con el mismo id."""
    yield
    db.session.rollback()
    ids = _CREATED['contracts']
    if ids:
        Installment.query.filter(Installment.contract_id.in_(ids)).delete(synchronize_session=False)
        Contract.query.filter(Contract.id.in_(ids)).delete(synchronize_session=False)
    if _CREATED['users']:
        User.query.filter(User.id.in_(_CREATED['users'])).delete(synchronize_session=False)
    db.session.commit()
    _CREATED['users'].clear()
    _CREATED['contracts'].clear()


def _patient(**kw):
    tag = uuid.uuid4().hex[:8]
    u = User(username=f'pac{tag}', email=f'{tag}@cd.test', password='x', role='jugador', is_active=True, **kw)
    db.session.add(u)
    db.session.commit()
    _CREATED['users'].append(u.id)
    return u


def _contract(patient, *installments):
    c = Contract(patient_id=patient.id, name='Plan', total_amount=600, installment_amount=200, status='active')
    db.session.add(c)
    db.session.flush()
    for n, (due, amount, paid, status) in enumerate(installments, 1):
        db.session.add(
            Installment(contract_id=c.id, number=n, due_date=due, amount=amount, paid_amount=paid, status=status)
        )
    db.session.commit()
    _CREATED['contracts'].append(c.id)
    return c


def _scenario():
    a = _patient()  # contrato con cuota vencida a medio pagar: debe 150
    _contract(a, (TODAY - timedelta(days=10), 200, 50, 'partial'), (TODAY + timedelta(days=20), 200, 0, 'pending'))
    b = _patient(payment_amount=100, payment_due_date=TODAY - timedelta(days=3))  # sin contrato, plan vencido
    c = _patient(payment_amount=300, payment_due_date=TODAY - timedelta(days=40))  # contrato al día: no cuenta el plan
    _contract(c, (TODAY - timedelta(days=5), 200, 200, 'paid'), (TODAY + timedelta(days=25), 200, 0, 'pending'))
    d = _patient()  # contrato con cuota en 3 días: por vencer
    _contract(d, (TODAY + timedelta(days=3), 180, 0, 'pending'))
    return a, b, c, d


def test_contract_debt_reads_unpaid_overdue_installments(app):
    a, b, c, d = _scenario()
    debts = contract_debt(TODAY, [a.id, b.id, c.id, d.id])
    assert set(debts) == {a.id, c.id, d.id}  # b no tiene contrato
    assert debts[a.id].overdue_amount == 150.0 and debts[a.id].overdue_count == 1
    assert not debts[c.id].is_overdue and not debts[d.id].is_overdue
    assert debts[d.id].next_due == TODAY + timedelta(days=3)


def test_summary_and_debt_report_include_contracts_without_double_counting(app):
    a, b, c, d = _scenario()
    ids = {a.id, b.id, c.id, d.id}

    summary = PaymentService().get_financial_summary()
    # Otros tests pueden dejar pacientes; se mira la contribución de este escenario a través del reporte.
    report = FinancialService().build_debt_report()
    rows = {r['id']: r for s in report['por_sede'].values() for r in s['deudores'] if r['id'] in ids}

    assert rows[a.id]['estado'] == 'vencido' and rows[a.id]['monto'] == 150.0 and rows[a.id]['origen'] == 'contrato'
    assert rows[a.id]['dias_adeudo'] == 10 and rows[a.id]['cuotas_vencidas'] == 1
    assert rows[b.id]['estado'] == 'vencido' and rows[b.id]['monto'] == 100.0 and rows[b.id]['origen'] == 'plan'
    assert rows[c.id]['estado'] == 'al_dia'  # el plan viejo vencido no cuenta: manda el contrato
    assert rows[d.id]['estado'] == 'proximo' and rows[d.id]['monto'] == 180.0

    # El resumen del panel suma lo mismo (a: 150 por contrato, b: 100 por plan; c no).
    assert summary['overdue_amount'] >= 250.0
    counted = {r['id'] for r in rows.values() if r['estado'] == 'vencido'}
    assert counted == {a.id, b.id}


def test_daily_digest_uses_the_same_overdue_figure(app):
    _scenario()
    from app.services.daily_digest_service import _gather_bsc_data

    admin = User(
        username='adm' + uuid.uuid4().hex[:6], email=uuid.uuid4().hex[:8] + '@cd.test', password='x', role='admin'
    )
    db.session.add(admin)
    db.session.commit()
    _CREATED['users'].append(admin.id)
    summary = PaymentService().get_financial_summary()
    fin = _gather_bsc_data(admin)['financial']
    assert fin['overdue_amount'] == float(summary['overdue_amount'])
    assert fin['overdue_count'] == summary['overdue_users_count']
