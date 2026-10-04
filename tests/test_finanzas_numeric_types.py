"""Tipos numericos en la nomina de terapeutas.

`SUM()` en MySQL devuelve Decimal. Si ese valor llega crudo a `jsonify`,
Flask lo serializa como string (`{"worked_hours": "4"}`) y Angular revienta
con `TypeError: t.worked_hours.toFixed is not a function`, cortando el render
de la tabla de nomina en finanzas.html y expenses.html.
"""

from decimal import Decimal

import pytest
from flask_jwt_extended import create_access_token

from app.extensions import db
from app.models import User
from app.routes.admin import payments

NUMERIC_FIELDS = ('rate', 'worked_hours', 'projected_pay', 'paid', 'balance')


@pytest.fixture
def finance_admin(session):
    user = User.query.filter_by(email='fin_types_admin@example.com').first()
    if user is None:
        user = User(
            username='fin_types_admin',
            email='fin_types_admin@example.com',
            password='x',
            role='admin',
        )
        db.session.add(user)
    user.role = 'admin'
    session.commit()
    return user


def _decimal_financials(therapist):
    """Resultado tipico de finance_service cuando hay horas facturables."""
    return [
        {
            'therapist': therapist,
            'rate': Decimal('35.5'),
            'contract_hours': 40,
            'worked_hours': Decimal('4'),
            'projected_pay': Decimal('142.00'),
            'paid': Decimal('0.00'),
            'balance': Decimal('142.00'),
        }
    ]


def test_therapist_financials_json_numbers_not_strings(client, finance_admin, monkeypatch):
    monkeypatch.setattr(
        payments.finance_service,
        'get_therapist_financials',
        lambda **kwargs: _decimal_financials(finance_admin),
    )

    token = create_access_token(identity=str(finance_admin.id))
    resp = client.get('/admin/api/therapist-financials', headers={'Authorization': f'Bearer {token}'})

    assert resp.status_code == 200, resp.get_data(as_text=True)
    row = resp.get_json()['data'][0]

    bad = {k: row[k] for k in NUMERIC_FIELDS if isinstance(row[k], str)}
    assert not bad, f'el backend manda strings numericos y Angular revienta con ".toFixed is not a function": {bad}'
    for key in NUMERIC_FIELDS:
        assert isinstance(row[key], (int, float)), f'{key}={row[key]!r} no es numerico'
