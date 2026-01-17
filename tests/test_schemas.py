import pytest
from app.schemas.auth_schema import validate_login_input
from app.schemas.payment_schema import validate_payment_register


def test_login_schema_invalid():
    data, errors = validate_login_input({'email': 'bad', 'password': '123'})
    assert data is None
    assert 'email' in errors and 'password' in errors


def test_login_schema_valid():
    data, errors = validate_login_input({'email': 'user@example.com', 'password': 'secret12'})
    assert errors is None
    assert data['email'] == 'user@example.com'


def test_payment_schema_valid():
    data, errors = validate_payment_register({
        'patient_id': '1',
        'amount': '150.0',
        'method': 'card',
        'reference': 'ABC123',
        'next_due_date': '2026-02-01'
    })
    assert errors is None
    assert data['patient_id'] == 1
    assert abs(data['amount'] - 150.0) < 0.001


def test_payment_schema_invalid():
    data, errors = validate_payment_register({'patient_id': 'x', 'amount': '0', 'method': 'x'})
    assert data is None
    assert 'patient_id' in errors
