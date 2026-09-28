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
    # Otro modulo puede haber dejado objetos sin commitear en la sesion: un
    # commit dentro de este test los volcaria y descuadraria los totales.
    session.rollback()
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


def _delta(antes, despues, campo):
    """Diferencia respecto a la foto previa.

    La BD de test es de sesion y otros archivos dejan jugadores dentro, asi
    que afirmar totales absolutos hacia fallar en la suite completa y pasar
    en aislamiento. Lo que importa es el cambio que provoca lo que anadimos.
    """
    return despues[campo] - antes[campo]


def test_un_numero_de_pacientes_nunca_es_negativo(db, session, stats):
    """La regresión: sin contrato daba -5."""
    for i in range(3):
        stats(f'solo_activo_{i}', activo=True)
    s = _stats()['stats']
    assert s['without_contract'] >= 0, 'un numero de pacientes no puede ser negativo'
    assert (
        s['with_active_contract'] + s['without_contract'] == s['total']
    ), f"el rango no cuadra: {s['with_active_contract']} + {s['without_contract']} != {s['total']}"


def test_cuenta_pacientes_no_contratos_del_centro(db, session, stats):
    """El fallo real: 4 pacientes del informe menos 9 contratos del centro."""
    antes = _stats()['stats']
    for i in range(3):
        stats(f'sin_contrato_{i}', activo=True)
    d = _stats()['stats']
    assert d['without_contract'] - antes['without_contract'] == 3, (
        'los contratos del centro no pueden restarse de los pacientes del informe'
    )


def test_solo_cuenta_el_contrato_vigente(db, session, stats):
    antes = _stats()['stats']
    stats('con_contrato', activo=True, contrato=True)
    stats('contrato_cancelado', activo=True, contrato=False)
    d = _stats()['stats']
    assert _delta(antes, d, 'with_active_contract') == 1, (
        'un contrato cancelado no es un contrato vigente'
    )
    assert _delta(antes, d, 'without_contract') == 1


def test_el_ambito_se_dice_y_se_pide_explicito(db, session, stats):
    """Habia 51 pacientes y 4 activos. Decir 'hay 4' sin mas es mentir."""
    antes = _stats()['stats']
    stats('activo_1', activo=True)
    stats('baja_1', activo=False)
    stats('baja_2', activo=False)

    activos = _stats()['stats']
    assert _delta(antes, activos, 'total') == 1, 'por defecto solo los activos'
    assert _stats()['scope'] == 'solo pacientes activos', 'el ambito debe decirse'

    todos = _stats(include_inactive=True)['stats']
    assert _stats(include_inactive=True)['scope'] == 'todos los pacientes'
    assert todos['total'] > activos['total'], (
        'los dados de baja tienen que aparecer cuando se piden: '
        f'activos={activos["total"]} todos={todos["total"]}'
    )
