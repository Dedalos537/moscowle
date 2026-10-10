"""Mensajería en vivo: el socket se autentica con el JWT y el primer mensaje de una conversación nueva llega sin recargar."""

import uuid

from flask_jwt_extended import create_access_token

from app.extensions import db, socketio
from app.models import User


def _user(role):
    tag = uuid.uuid4().hex[:8]
    u = User(username=f'{role[:3]}{tag}', email=f'{tag}@rt.test', password='x', role=role)
    db.session.add(u)
    db.session.commit()
    return u


def test_first_message_reaches_the_receiver_live(client, app):
    therapist, patient = _user('terapista'), _user('jugador')
    # El paciente se conecta solo con su JWT (como el frontend: auth={token}); aún no tiene conversaciones.
    receiver = socketio.test_client(app, auth={'token': create_access_token(identity=str(patient.id))})
    assert receiver.is_connected()
    receiver.get_received()  # descarta users:online

    h = {'Authorization': 'Bearer ' + create_access_token(identity=str(therapist.id))}
    r = client.post('/api/chats', json={'user_id': patient.id}, headers=h)
    assert r.status_code in (200, 201), r.get_json()
    chat_id = r.get_json()['chat_id']
    r = client.post(f'/api/chats/{chat_id}/messages', data={'body': 'Hola, mañana la sesión es a las 10'}, headers=h)
    assert r.status_code in (200, 201), r.get_json()

    events = [e for e in receiver.get_received() if e['name'] == 'message:new']
    assert events, 'el receptor no recibió el mensaje en vivo'
    bodies = {e['args'][0]['message']['body'] for e in events}
    assert 'Hola, mañana la sesión es a las 10' in bodies
    receiver.disconnect()


def test_socket_without_token_stays_anonymous(app):
    anon = socketio.test_client(app)
    assert anon.is_connected()
    assert not [e for e in anon.get_received() if e['name'] == 'message:new']
    anon.disconnect()
