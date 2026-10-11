"""Catálogo de juegos y niveles de KPI: el paciente juega pero nunca ve KPIs; el equipo ve niveles."""

import json
import uuid
from datetime import datetime, timedelta

import pytest
from flask_jwt_extended import create_access_token

from app.extensions import db
from app.models import Game, SessionMetrics, User
from app.services import game_kpis


def _user(role, **kw):
    tag = uuid.uuid4().hex[:8]
    u = User(username=f'{role[:3]}{tag}', email=f'{tag}@gc.test', password='x', role=role, **kw)
    db.session.add(u)
    db.session.commit()
    return u


def _h(u):
    return {'Authorization': 'Bearer ' + create_access_token(identity=str(u.id))}


@pytest.fixture
def game(app):
    with app.app_context():
        g = Game(title='Plataformas test', filename=f'test_{uuid.uuid4().hex[:6]}.html', filetype='html')
        g.meta = json.dumps({'kind': 'platformer'})
        db.session.add(g)
        db.session.commit()
        yield g
        SessionMetrics.query.filter_by(game_id=g.id).delete()
        db.session.delete(g)
        db.session.commit()


def _play(user, game, days_ago=0, **kpis):
    m = SessionMetrics(
        user_id=user.id,
        game_id=game.id,
        game_name=game.filename,
        accurracy=0,
        avg_time=0,
        prediction=0,
        date=datetime.utcnow() - timedelta(days=days_ago),
        details=json.dumps({'kpis': kpis}),
    )
    db.session.add(m)
    db.session.commit()
    return m


def test_patient_catalog_has_no_kpis(client, game, monkeypatch):
    from app.services import game_catalog

    monkeypatch.setattr(game_catalog, 'file_exists', lambda g: True)
    patient = _user('jugador')
    body = client.get('/api/games/catalog', headers=_h(patient)).get_json()
    assert body['success']
    mine = next(g for g in body['games'] if g['id'] == game.id)
    assert 'kpis' not in mine
    assert 'kpi_catalog' not in body and 'levels' not in body
    assert mine['play_url'] == f'/static/games/{game.filename}'


def test_staff_catalog_includes_kpi_profile(client, game):
    therapist = _user('terapista')
    body = client.get('/api/games/catalog', headers=_h(therapist)).get_json()
    mine = next(g for g in body['games'] if g['id'] == game.id)
    assert set(mine['kpis']) == {'completion', 'errors', 'collected'}
    assert [lvl['id'] for lvl in body['levels']] == ['inicial', 'en_proceso', 'logrado', 'destacado']


def test_profile_validation_respects_direction():
    assert game_kpis.validate_profile({'errors': [6, 3, 1]}) == {'errors': [6.0, 3.0, 1.0]}
    with pytest.raises(game_kpis.KpiError, match='de mayor a menor'):
        game_kpis.validate_profile({'errors': [1, 3, 6]})
    with pytest.raises(game_kpis.KpiError, match='de menor a mayor'):
        game_kpis.validate_profile({'completion': [90, 50, 20]})
    with pytest.raises(game_kpis.KpiError, match='no pasa de 100'):
        game_kpis.validate_profile({'completion': [50, 80, 120]})
    with pytest.raises(game_kpis.KpiError, match='desconocido'):
        game_kpis.validate_profile({'magia': [1, 2, 3]})


def test_levels_use_median_of_recent_plays(client, game):
    patient = _user('jugador')
    for completion, errors in ((100, 0), (90, 1), (95, 0), (20, 9), (88, 1)):
        _play(patient, game, completion=completion, errors=errors, collected=60)
    lv = game_kpis.patient_levels(game, patient.id)
    by_key = {k['key']: k for k in lv['kpis']}
    assert by_key['completion']['value'] == 90 and by_key['completion']['level'] == 'destacado'
    assert by_key['errors']['value'] == 1 and by_key['errors']['level'] == 'destacado'
    assert by_key['collected']['level'] == 'logrado'
    assert lv['level'] == 'destacado' and lv['plays'] == 5


def test_therapist_sees_only_their_patients(client, game):
    therapist = _user('terapista')
    mine = _user('jugador', assigned_therapist_id=therapist.id)
    other = _user('jugador')
    _play(mine, game, completion=50, errors=3)
    _play(other, game, completion=50, errors=3)

    body = client.get(f'/api/games/{game.id}/levels', headers=_h(therapist)).get_json()
    assert [p['patient_id'] for p in body['patients']] == [mine.id]
    assert client.get(f'/api/games/levels/patient/{other.id}', headers=_h(therapist)).status_code == 403
    assert client.get(f'/api/games/levels/patient/{mine.id}', headers=_h(therapist)).status_code == 200

    admin = _user('admin')
    ids = {
        p['patient_id'] for p in client.get(f'/api/games/{game.id}/levels', headers=_h(admin)).get_json()['patients']
    }
    assert {mine.id, other.id} <= ids


def test_patient_cannot_read_levels(client, game):
    patient = _user('jugador')
    _play(patient, game, completion=50)
    assert client.get(f'/api/games/{game.id}/levels', headers=_h(patient)).status_code == 403
    assert client.get(f'/api/games/levels/patient/{patient.id}', headers=_h(patient)).status_code == 403


def test_admin_edits_profile_and_others_cannot(client, game):
    admin = _user('admin')
    r = client.patch(
        f'/api/games/{game.id}', json={'kpis': {'completion': [30, 60, 90]}, 'area': 'Motricidad'}, headers=_h(admin)
    )
    assert r.status_code == 200
    assert r.get_json()['game']['kpis'] == {'completion': [30.0, 60.0, 90.0]}
    assert r.get_json()['game']['area'] == 'Motricidad'

    bad = client.patch(f'/api/games/{game.id}', json={'kpis': {'errors': [1, 2, 3]}}, headers=_h(admin))
    assert bad.status_code == 400

    reset = client.patch(f'/api/games/{game.id}', json={'kpis': None}, headers=_h(admin)).get_json()
    assert set(reset['game']['kpis']) == {'completion', 'errors', 'collected'}

    for role in ('terapista', 'supervisor', 'jugador'):
        u = _user(role)
        assert client.patch(f'/api/games/{game.id}', json={'title': 'x'}, headers=_h(u)).status_code == 403


def test_save_game_stores_kpis_and_hides_assessment_from_patient(client, game):
    patient = _user('jugador')
    r = client.post(
        '/api/save_game',
        json={
            'game_name': game.filename,
            'game_id': game.id,
            'accuracy': 70,
            'avg_time': 3,
            'kpis': {'completion': 50, 'errors': 2, 'evil': 9},
        },
        headers=_h(patient),
    )
    assert r.status_code == 200
    assert r.get_json() == {'status': 'ok'}
    m = SessionMetrics.query.filter_by(user_id=patient.id).one()
    assert m.game_id == game.id
    assert json.loads(m.details)['kpis'] == {'completion': 50.0, 'errors': 2.0}


def test_game_with_history_is_archived_not_deleted(client, game):
    admin = _user('admin')
    _play(_user('jugador'), game, completion=10)
    body = client.delete(f'/api/games/{game.id}', headers=_h(admin)).get_json()
    assert body['archived'] is True
    assert db.session.get(Game, game.id).is_active is False


def test_patient_progress_has_no_clinical_kpis(client):
    patient = _user('jugador')
    body = client.get('/patient/api/progress', headers=_h(patient)).get_json()['data']
    assert 'accuracy_data' not in body and 'time_data' not in body
    assert 'precisi' not in body['weekly_summary'].lower()
    assert all('title' in a for a in body['achievements'])
    dash = client.get('/patient/api/dashboard', headers=_h(patient)).get_json()['data']['player_stats']
    assert 'avg_accuracy' not in dash and 'avg_time' not in dash


def test_games_can_be_embedded_by_the_player(client):
    r = client.get('/static/games/vendor/moscowle-bridge.js')
    assert r.status_code == 200
    csp = r.headers['Content-Security-Policy']
    assert 'https://moscowle.centrojuanpabloii.com' in csp and "'wasm-unsafe-eval'" in csp and 'blob:' in csp
    assert 'X-Frame-Options' not in r.headers
    # El resto del sitio conserva su política.
    assert client.get('/api/health').headers.get('X-Frame-Options') in ('DENY', 'SAMEORIGIN')
