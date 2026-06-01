from flask import request
from flask_login import current_user
from flask_socketio import join_room, emit
from datetime import datetime
from app.extensions import socketio, db
from app.models import User, Message, Chat, ChatParticipant

online_users = {}

@socketio.on('connect')
def handle_connect():
    if current_user.is_authenticated:
        user_id = current_user.id
        if user_id not in online_users:
            online_users[user_id] = set()
        online_users[user_id].add(request.sid)

        # Enviar lista completa de usuarios online al que se conecta
        emit('users:online', {'user_ids': list(online_users.keys())})

        chats = Chat.query.join(ChatParticipant).filter(ChatParticipant.user_id == user_id).all()
        for chat in chats:
            join_room(f'chat_{chat.id}')

        emit('user:online', {
            'user_id': user_id,
            'username': current_user.username
        }, broadcast=True, include_self=False)

        return True
    return False

@socketio.on('disconnect')
def handle_disconnect():
    if current_user.is_authenticated:
        user_id = current_user.id
        if user_id in online_users:
            online_users[user_id].discard(request.sid)
            if not online_users[user_id]:
                del online_users[user_id]
                emit('user:offline', {
                    'user_id': user_id,
                    'last_seen': datetime.utcnow().isoformat()
                }, broadcast=True, include_self=False)

@socketio.on('chat:join')
def handle_chat_join(data):
    chat_id = data.get('chat_id')
    if current_user.is_authenticated and chat_id:
        participant = ChatParticipant.query.filter_by(chat_id=chat_id, user_id=current_user.id).first()
        if participant:
            join_room(f'chat_{chat_id}')

@socketio.on('typing:start')
def handle_typing_start(data):
    chat_id = data.get('chat_id')
    if current_user.is_authenticated and chat_id:
        emit('user:typing', {
            'user_id': current_user.id,
            'username': current_user.username,
            'chat_id': chat_id
        }, room=f'chat_{chat_id}', include_self=False)

@socketio.on('typing:stop')
def handle_typing_stop(data):
    chat_id = data.get('chat_id')
    if current_user.is_authenticated and chat_id:
        emit('user:stop_typing', {
            'user_id': current_user.id,
            'chat_id': chat_id
        }, room=f'chat_{chat_id}', include_self=False)

@socketio.on('message:read')
def handle_message_read(data):
    chat_id = data.get('chat_id')
    if current_user.is_authenticated and chat_id:
        participant = ChatParticipant.query.filter_by(chat_id=chat_id, user_id=current_user.id).first()
        if participant:
            participant.last_read_at = datetime.utcnow()
            db.session.commit()

        Message.query.filter(
            Message.chat_id == chat_id,
            Message.receiver_id == current_user.id,
            Message.status == 'delivered'
        ).update({'status': 'read', 'is_read': True})
        db.session.commit()

        emit('message:status', {
            'chat_id': chat_id,
            'user_id': current_user.id,
            'status': 'read'
        }, room=f'chat_{chat_id}', include_self=False)


def get_online_users():
    return set(online_users.keys())
