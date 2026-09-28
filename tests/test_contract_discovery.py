"""La IA local no podia responder 'quienes no tienen contrato ni por que'.

No habia ninguna tool que listara a los pacientes sin contrato vigente, ni
ninguna que dijera con que condiciones se crearia uno. Sin eso, el modelo
respondia con lo que tenia a mano y por eso dijo 'ninguno sin contrato'.

'is_active' y 'status' pueden no coincidir: varias filas de contract tienen
is_active en NULL, asi que un contrato vigente puede ser cualquiera de los dos.
"""
import pytest

_CREADOS = []


@pytest.fixture(autouse=True)
def _limpiar(db, session):
    from app.models.contract import Contract
    from app.models.user import User, patient_therapist

    session.rollback()
    yield
    session.rollback()
    session.execute(patient_therapist.delete())
    Contract.query.delete(synchronize_session=False)
    User.query.filter(User.username.in_(_CREADOS)).delete(synchronize_session=False)
    session.commit()
    _CREADOS.clear()


def _paciente(session, username, **extra):
    from app.models.user import User

    u = User(username=username, email=f'{username}@x.com', password='x',
             role='jugador', is_active=True, **extra)
    session.add(u)
    session.commit()
    _CREADOS.append(username)
    return u


def _contrato(session, pid, is_active=None, status='active', total=4560.0):
    from app.models.contract import Contract

    session.add(Contract(
        patient_id=pid, total_amount=total, installment_amount=380.0,
        installment_count=12, is_active=is_active, status=status,
    ))
    session.commit()


def _listar(**kw):
    from app.services.tools_registry import execute_tool

    r = execute_tool('list_patients', kw, user_id=1, role='admin')
    assert r.get('success'), r
    return {p['username'] for p in r['patients']}


def test_filtra_who_no_tiene_contrato_vigente(db, session):
    con = _paciente(session, 'con_contrato')
    sin = _paciente(session, 'sin_contrato')
    cancelado = _paciente(session, 'contrato_cancelado')
    _contrato(session, con.id, is_active=True, status='active')
    _contrato(session, cancelado.id, is_active=False, status='cancelled')

    sin_contrato = _listar(without_active_contract=True)
    assert sin.username in sin_contrato
    assert cancelado.username in sin_contrato, 'un contrato cancelado no es vigente'
    assert con.username not in sin_contrato

    con_contrato = _listar(without_active_contract=False)
    assert con.username in con_contrato
    assert sin.username not in con_contrato


def test_is_active_en_null_sigue_siendo_vigente(db, session):
    """En produccion varias filas tienen is_active NULL y status active."""
    p = _paciente(session, 'is_active_null')
    _contrato(session, p.id, is_active=None, status='active')
    assert p.username not in _listar(without_active_contract=True), (
        'con status active el contrato esta vigente, aunque is_active sea NULL'
    )


def test_la_ia_no_tiene_que_inventar_el_precio(db, session):
    from app.services.tools_registry import execute_tool

    p = _paciente(session, 'con_historico', sessions_total=8, sessions_remaining=0)
    _contrato(session, p.id, is_active=True, status='active', total=4560.0)

    r = execute_tool('get_contract_suggestion', {'patient_id': p.id}, user_id=1, role='admin')
    s = r['suggestion']
    assert s['suggested_total_amount'] == 4560.0
    assert s['suggested_installment_count'] == 12
    assert s['has_active_contract'] is True
    assert 'renovar' in s['action'], 'tiene contrato y cero sesiones: toca renovar'


def test_sin_datos_avisa_que_hay_que_preguntar(db, session):
    from app.services.tools_registry import execute_tool

    p = _paciente(session, 'ficha_vacia')
    r = execute_tool('get_contract_suggestion', {'patient_id': p.id}, user_id=1, role='admin')
    assert r['suggestion']['needs_human_input'] is True, (
        'sin contrato previo ni plan de pago hay que preguntar, no adivinar'
    )
