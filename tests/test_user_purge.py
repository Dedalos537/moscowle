"""Borrar un usuario no debe fallar por filas que apuntan a él (antes: 500 si tenía contrato, juegos, grupos…)."""

import uuid
from datetime import date, datetime, timedelta

from sqlalchemy import func, select

from app.extensions import db
from app.models import Appointment, Payment, User
from app.models.appointment import AppointmentGame
from app.models.billing import PaymentAllocation
from app.models.contract import Contract, Installment
from app.models.game import Game
from app.services.user_purge import _referencing, purge_user


def _u(role, **kw):
    u = User(
        username=f'{role}-{uuid.uuid4().hex[:6]}', email=f'{uuid.uuid4().hex[:8]}@x.com', role=role, password='x', **kw
    )
    db.session.add(u)
    db.session.flush()
    return u


def test_purge_patient_with_contract_games_and_payments(app):
    ther = _u('terapista')
    pat = _u('jugador', assigned_therapist_id=ther.id, created_by_id=ther.id)
    c = Contract(patient_id=pat.id, total_amount=300, installment_amount=100, created_by_id=ther.id)
    db.session.add(c)
    db.session.flush()
    inst = Installment(contract_id=c.id, number=1, due_date=date.today(), amount=100)
    pay = Payment(patient_id=pat.id, amount=100, method='yape', status='completed', date=datetime.utcnow())
    db.session.add_all([inst, pay])
    db.session.flush()
    db.session.add(PaymentAllocation(payment_id=pay.id, installment_id=inst.id, amount=100))
    appt = Appointment(
        patient_id=pat.id,
        therapist_id=ther.id,
        title='Terapia',
        start_time=datetime.utcnow(),
        end_time=datetime.utcnow() + timedelta(hours=1),
    )
    game = Game(title='Memoria', filename=f'm-{uuid.uuid4().hex[:6]}.html')
    db.session.add_all([appt, game])
    db.session.flush()
    db.session.add(AppointmentGame(appointment_id=appt.id, game_id=game.id))
    db.session.commit()
    pid, appt_id, contract_id, ther_id, game_id = pat.id, appt.id, c.id, ther.id, game.id

    purge_user(pat)
    db.session.commit()

    assert db.session.get(User, pid) is None
    for child, col in _referencing(User.__table__):
        assert db.session.scalar(select(func.count()).select_from(child).where(col == pid)) == 0, child.name
    assert AppointmentGame.query.filter_by(appointment_id=appt_id).count() == 0
    assert Installment.query.filter_by(contract_id=contract_id).count() == 0
    # Lo que solo lo mencionaba queda; el terapeuta y el juego siguen.
    assert db.session.get(User, ther_id) is not None and db.session.get(Game, game_id) is not None


def test_purge_therapist_keeps_patient_but_unassigns(app):
    ther = _u('terapista')
    pat = _u('jugador', assigned_therapist_id=ther.id)
    db.session.commit()
    purge_user(ther)
    db.session.commit()
    db.session.refresh(pat)
    assert pat.assigned_therapist_id is None
