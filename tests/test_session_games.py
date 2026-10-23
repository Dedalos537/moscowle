"""Juegos de la sesión: opcionales al programar, jugables desde la cuenta del terapeuta o del paciente."""

import uuid
from datetime import datetime

from flask_jwt_extended import create_access_token

from app.extensions import db
from app.models import Appointment, Game, SessionMetrics, User
from app.models.appointment import AppointmentGame


def _user(role):
    tag = uuid.uuid4().hex[:8]
    u = User(username=f'{role[:3]}{tag}', email=f'{tag}@gmail.com', password='x', role=role)
    db.session.add(u)
    db.session.commit()
    return u


def _h(u):
    return {'Authorization': 'Bearer ' + create_access_token(identity=str(u.id))}


def _game():
    tag = uuid.uuid4().hex[:6]
    g = Game(title=f'Memoria {tag}', filename=f'memoria_{tag}.html', is_active=True)
    db.session.add(g)
    db.session.commit()
    return g


def _session(ther, pat, games):
    appt = Appointment(
        therapist_id=ther.id, patient_id=pat.id, title='Sesión', start_time=datetime.utcnow(), status='scheduled'
    )
    db.session.add(appt)
    db.session.flush()
    from app.services.appointment_service import AppointmentService

    AppointmentService.attach_games(appt, games)
    db.session.commit()
    return appt


def _play(client, who, appt, game, accuracy=80):
    return client.post(
        '/api/save_game',
        json={
            'game_name': game.filename,
            'game_id': game.id,
            'accuracy': accuracy,
            'avg_time': 2,
            'session_id': appt.id,
        },
        headers=_h(who),
    )


def test_therapist_play_is_saved_to_the_patient(client, app):
    ther, pat = _user('terapista'), _user('jugador')
    g1, g2 = _game(), _game()
    appt = _session(ther, pat, [g1, g2])
    assert _play(client, ther, appt, g1).status_code == 200
    m = SessionMetrics.query.filter_by(session_id=appt.id).one()
    assert m.user_id == pat.id  # la partida es del paciente aunque jugó desde la cuenta del terapeuta
    ag = AppointmentGame.query.filter_by(appointment_id=appt.id, game_id=g1.id).one()
    assert ag.status == 'completed'
    assert db.session.get(Appointment, appt.id).status == 'scheduled'  # falta el segundo juego


def test_repeating_one_game_does_not_close_the_session(client, app):
    ther, pat = _user('terapista'), _user('jugador')
    g1, g2 = _game(), _game()
    appt = _session(ther, pat, [g1, g2])
    _play(client, pat, appt, g1)
    _play(client, pat, appt, g1)  # antes: 2 partidas >= 2 juegos y se cerraba
    assert db.session.get(Appointment, appt.id).status == 'scheduled'
    _play(client, ther, appt, g2)
    assert db.session.get(Appointment, appt.id).status == 'completed'


def test_other_therapist_cannot_play_someone_elses_session(client, app):
    ther, other, pat = _user('terapista'), _user('terapista'), _user('jugador')
    g = _game()
    appt = _session(ther, pat, [g])
    assert _play(client, other, appt, g).status_code == 403


def test_session_detail_shows_each_game_status(client, app):
    ther, pat = _user('terapista'), _user('jugador')
    g1, g2 = _game(), _game()
    appt = _session(ther, pat, [g1, g2])
    _play(client, ther, appt, g1, accuracy=91.26)
    data = client.get(f'/api/sessions/{appt.id}', headers=_h(ther)).get_json()
    by_id = {g['game_id']: g for g in data['game_status']}
    assert by_id[g1.id]['status'] == 'completed' and by_id[g1.id]['accuracy'] == 91.3
    assert by_id[g2.id]['status'] == 'pending'


def test_batch_create_attaches_optional_games(client, app):
    admin, ther, pat = _user('admin'), _user('terapista'), _user('jugador')
    g = _game()
    day = '2027-03-10'  # miércoles sin feriado
    payload = {
        'therapist_id': ther.id,
        'patient_id': pat.id,
        'dates': [day],
        'start_time': '10:00',
        'end_time': '11:00',
        'games': [g.filename],
    }
    res = client.post('/admin/api/sessions/batch', json=payload, headers=_h(admin))
    assert res.status_code == 200, res.get_json()
    sid = res.get_json()['session_ids'][0]
    assert [ag.game_id for ag in AppointmentGame.query.filter_by(appointment_id=sid)] == [g.id]
    # sin juegos también se puede (son opcionales)
    payload.update(games=[], dates=['2027-03-11'])
    assert client.post('/admin/api/sessions/batch', json=payload, headers=_h(admin)).status_code == 200
