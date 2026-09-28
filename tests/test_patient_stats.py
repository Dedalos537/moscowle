"""get_patient_stats mintio en produccion.

Devolvio active_contracts=9 y without_contract=-5. El 9 era el numero de
contratos de TODO el centro, restado de los 4 pacientes del informe, asi que
el '-5' no podia ser un numero de pacientes. El bot leyo eso y respondio
"9 contratos vigentes y ningun paciente sin contrato", que es lo contrario de
la realidad: 50 de 51 pacientes no tenian contrato vigente.
"""
import pytest

_CREADOS = []


@pytest.fixture(autouse=True)
def _limpiar(db, session):
    """La BD de test es de sesion: sin esto el segundo test ve el primero."""
    yield
    from app.models.contract import Contract
    from app.models.user import User, patient_therapist

    session.rollback()
    session.execute(patient_therapist.delete())
    Contract.query.delete(synchronize_session=False)
    User.query.filter(User.username.in_(_CREADOS)).delete(synchronize_session=False)
    session.commit()
    _CREADOS.clear()


@pytest.fixture
def stats(db, session):
    from app.models.contract import Contract
    from app.models.user import User

    def _paciente(username, activo=True, contrato=None):
        u = User(
            username=username, email=f'{username}@x.com', password='x',
            role='jugador', is_active=activo,
        )
        session.add(u)
        session.commit()
        _CREADOS.append(username)
        if contrato is not None:
            session.add(Contract(
                patient_id=u.id, total_amount=100.0, installment_amount=25.0,
                installment_count=4, is_active=contrato,
                status='active' if contrato else 'cancelled',
            ))
            session.commit()
        return u

    return _paciente


def _stats(**kw):
    from app.services.tools_registry import execute_tool

    r = execute_tool('get_patient_stats', kw, user_id=1, role='admin')
    assert r.get('success'), r
    return r


def test_un_numero_de_pacientes_nunca_es_negativo(db, session, stats):
    """La regresion: sin contrato daba -5."""
    for i in range(3):
        stats(f'solo_activo_{i}', activo=True)
    s = _stats()['stats']
    assert s['without_contract'] >= 0, 'un numero de pacientes no puede ser negativo'
    assert s['without_contract'] == s['total'], 'sin contratos, todos lo estan'


def test_el_rango_cuadra_con_el_total(db, session, stats):
    a = stats('con_contrato', activo=True, contrato=True)
    b = stats('sin_contrato', activo=True)
    c = stats('contrato_cancelado', activo=True, contrato=False)
    s = _stats()['stats']
    assert s['total'] == 3
    assert s['with_active_contract'] == 1, 'solo el contrato vigente cuenta'
    assert s['without_contract'] == 2
    assert s['with_active_contract'] + s['without_contract'] == s['total'], 'el rango debe cuadrar'


def test_responde_cuantos_pacientes_hay_en_total(db, session, stats):
    """Habia 51 pacientes y 4 activos. Decir 'hay 4' sin mas es mentir."""
    stats('activo_1', activo=True)
    stats('baja_1', activo=False)
    stats('baja_2', activo=False)

    s = _stats()['stats']
    assert s['total'] == 1, 'por defecto solo los activos'
    assert _stats()['scope'] == 'solo pacientes activos', 'el ambito debe decirse'

    todos = _stats(include_inactive=True)['stats']
    assert todos['total'] == 3
    assert _stats(include_inactive=True)['scope'] == 'todos los pacientes'
