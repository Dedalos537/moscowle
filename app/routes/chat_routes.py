from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from app.extensions import db
from app.models import User, Message, Chat, ChatParticipant
from sqlalchemy import func
from app.services.notification_service import NotificationService
from app.socketio_events import online_users
from datetime import datetime
import os, uuid
from werkzeug.utils import secure_filename

chat_bp = Blueprint('chat', __name__)
notification_service = NotificationService()


def get_contact_list():
    if current_user.role == 'admin':
        return User.query.filter(User.id != current_user.id, User.is_active == True).order_by(User.role, User.username).all()
    elif current_user.role == 'terapista':
        patient_ids = [p.id for p in current_user.assigned_patients if p.is_active]
        admin_ids = [u.id for u in User.query.filter_by(role='admin', is_active=True).all()]
        ids = set(patient_ids + admin_ids)
        ids.discard(current_user.id)
        return User.query.filter(User.id.in_(ids)).all()
    else:
        admin_ids = [u.id for u in User.query.filter_by(role='admin', is_active=True).all()]
        ids = set(admin_ids)
        if current_user.assigned_therapist_id:
            ids.add(current_user.assigned_therapist_id)
        ids.discard(current_user.id)
        return User.query.filter(User.id.in_(ids)).all()


@chat_bp.route('/api/contacts')
@login_required
def list_contacts():
    contacts = get_contact_list()
    online = set(online_users.keys())
    return jsonify([{
        'id': u.id,
        'username': u.username,
        'email': u.email,
        'role': u.role,
        'avatar': u.avatar,
        'is_online': u.id in online
    } for u in contacts])


def migrate_legacy_messages():
    legacy_other_ids = db.session.query(
        func.case(
            (Message.sender_id == current_user.id, Message.receiver_id),
            else_=Message.sender_id
        ).label('other_id')
    ).filter(
        (Message.sender_id == current_user.id) | (Message.receiver_id == current_user.id),
        Message.chat_id.is_(None)
    ).distinct().all()

    for (other_id,) in legacy_other_ids:
        if other_id is None:
            continue
        other_id = int(other_id)
        chat = Chat(created_by_id=current_user.id)
        db.session.add(chat)
        db.session.flush()
        for uid in [current_user.id, other_id]:
            cp = ChatParticipant(chat_id=chat.id, user_id=uid)
            db.session.add(cp)
        Message.query.filter(
            ((Message.sender_id == current_user.id) & (Message.receiver_id == other_id)) |
            ((Message.sender_id == other_id) & (Message.receiver_id == current_user.id))
        ).update({'chat_id': chat.id}, synchronize_session=False)
    if legacy_other_ids:
        db.session.commit()


@chat_bp.route('/api/chats', methods=['GET'])
@login_required
def list_chats():
    online = set(online_users.keys())

    migrate_legacy_messages()

    chats = Chat.query.join(ChatParticipant).filter(ChatParticipant.user_id == current_user.id).order_by(Chat.created_at.desc()).all()
    result = []
    for chat in chats:
        last_msg = chat.last_message
        other = ChatParticipant.query.filter(ChatParticipant.chat_id == chat.id, ChatParticipant.user_id != current_user.id).first()
        other_user = User.query.get(other.user_id) if other else None
        result.append({
            'id': chat.id,
            'is_group': chat.is_group,
            'created_at': chat.created_at.isoformat() if chat.created_at else None,
            'other_user': {
                'id': other_user.id,
                'username': other_user.username,
                'role': other_user.role,
                'avatar': other_user.avatar,
                'is_online': other_user.id in online
            } if other_user else None,
            'unread_count': chat.unread_count_for(current_user.id),
            'last_message': {
                'id': last_msg.id,
                'body': last_msg.body,
                'sender_id': last_msg.sender_id,
                'created_at': last_msg.created_at.isoformat() if last_msg.created_at else None,
                'attachment_type': last_msg.attachment_type
            } if last_msg else None
        })

    if current_user.role == 'admin':
        from app.models import ContactMessage
        last_contact = ContactMessage.query.order_by(ContactMessage.created_at.desc()).first()
        unread_contact = ContactMessage.query.filter_by(status='unread').count()
        result.append({
            'id': -1,
            'is_group': False,
            'created_at': last_contact.created_at.isoformat() if last_contact else None,
            'other_user': {
                'id': -1,
                'username': 'Mensajes de la Web',
                'role': 'system',
                'avatar': None,
                'is_online': False
            },
            'unread_count': unread_contact,
            'last_message': {
                'id': 0,
                'body': last_contact.message[:100] if last_contact else 'Sin mensajes',
                'sender_id': -1,
                'created_at': last_contact.created_at.isoformat() if last_contact else None,
                'attachment_type': None
            } if last_contact else None
        })

    return jsonify(result)


@chat_bp.route('/api/chats', methods=['POST'])
@login_required
def create_chat():
    data = request.get_json(silent=True) or {}
    other_user_id = data.get('user_id')
    if not other_user_id:
        return jsonify({'success': False, 'message': 'user_id requerido'}), 400

    other = User.query.get(other_user_id)
    if not other or not other.is_active:
        return jsonify({'success': False, 'message': 'Usuario no encontrado'}), 404

    existing = Chat.query.join(ChatParticipant).filter(
        ChatParticipant.user_id == current_user.id
    ).filter(
        Chat.id.in_(
            db.session.query(ChatParticipant.chat_id).filter(ChatParticipant.user_id == other_user_id)
        )
    ).first()

    if existing:
        return jsonify({'success': True, 'chat_id': existing.id, 'created': False})

    chat = Chat(created_by_id=current_user.id)
    db.session.add(chat)
    db.session.flush()

    for uid in [current_user.id, other_user_id]:
        cp = ChatParticipant(chat_id=chat.id, user_id=uid)
        db.session.add(cp)

    db.session.commit()
    return jsonify({'success': True, 'chat_id': chat.id, 'created': True})


@chat_bp.route('/api/chats/<int:chat_id>/messages', methods=['GET'])
@login_required
def get_messages(chat_id):
    if chat_id == -1:
        if current_user.role != 'admin':
            return jsonify({'success': False, 'message': 'Acceso denegado'}), 403
        from app.models import ContactMessage
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 50, type=int)
        limit = min(limit, 100)
        msgs = ContactMessage.query.order_by(ContactMessage.created_at.desc()).offset((page - 1) * limit).limit(limit).all()
        msgs.reverse()
        total = ContactMessage.query.count()
        ContactMessage.query.filter_by(status='unread').update({'status': 'read'})
        db.session.commit()
        return jsonify({
            'messages': [{
                'id': m.id,
                'sender_id': -1,
                'receiver_id': current_user.id,
                'body': f"{m.first_name} {m.last_name} ({m.email}){(' - ' + m.phone) if m.phone else ''}:\n{m.message}",
                'status': 'read',
                'is_read': m.status != 'unread',
                'file_url': None,
                'attachment_type': None,
                'created_at': m.created_at.isoformat() if m.created_at else None
            } for m in msgs],
            'total': total,
            'page': page,
            'has_more': (page * limit) < total
        })

    chat = Chat.query.get(chat_id)
    if not chat:
        return jsonify({'success': False, 'message': 'Chat no encontrado'}), 404

    participant = ChatParticipant.query.filter_by(chat_id=chat_id, user_id=current_user.id).first()
    if not participant:
        return jsonify({'success': False, 'message': 'No eres participante de este chat'}), 403

    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 50, type=int)
    limit = min(limit, 100)

    messages = Message.query.filter_by(chat_id=chat_id).order_by(Message.created_at.desc()).offset((page - 1) * limit).limit(limit).all()
    messages.reverse()

    total = Message.query.filter_by(chat_id=chat_id).count()

    return jsonify({
        'messages': [{
            'id': m.id,
            'sender_id': m.sender_id,
            'receiver_id': m.receiver_id,
            'body': m.body,
            'status': m.status,
            'is_read': m.is_read,
            'file_url': m.file_url,
            'attachment_type': m.attachment_type,
            'created_at': m.created_at.isoformat() if m.created_at else None
        } for m in messages],
        'total': total,
        'page': page,
        'has_more': (page * limit) < total
    })


@chat_bp.route('/api/chats/<int:chat_id>/messages', methods=['POST'])
@login_required
def send_message(chat_id):
    chat = Chat.query.get(chat_id)
    if not chat:
        return jsonify({'success': False, 'message': 'Chat no encontrado'}), 404

    participant = ChatParticipant.query.filter_by(chat_id=chat_id, user_id=current_user.id).first()
    if not participant:
        return jsonify({'success': False, 'message': 'No eres participante de este chat'}), 403

    body = ''
    attachment_path = None
    attachment_type = None

    if request.is_json:
        data = request.get_json()
        body = (data.get('body') or '').strip()
    else:
        data = request.form.to_dict()
        body = (data.get('body') or '').strip()

        if 'file' in request.files:
            file = request.files['file']
            if file and file.filename:
                filename = secure_filename(file.filename)
                unique_filename = f"{uuid.uuid4().hex}_{filename}"
                ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
                if ext in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
                    attachment_type = 'image'
                elif ext in ['mp4', 'mov', 'webm']:
                    attachment_type = 'video'
                elif ext in ['mp3', 'wav', 'ogg', 'm4a']:
                    attachment_type = 'audio'
                else:
                    attachment_type = 'file'

                upload_folder = os.path.join(current_app.instance_path, 'uploads', 'messages')
                os.makedirs(upload_folder, exist_ok=True)
                file.save(os.path.join(upload_folder, unique_filename))
                attachment_path = unique_filename

    if not body and not attachment_path:
        return jsonify({'success': False, 'message': 'El mensaje no puede estar vacío'}), 400

    other_participants = ChatParticipant.query.filter(
        ChatParticipant.chat_id == chat_id,
        ChatParticipant.user_id != current_user.id
    ).all()
    receiver_id = other_participants[0].user_id if other_participants else current_user.id

    msg = Message(
        sender_id=current_user.id,
        receiver_id=receiver_id,
        body=body,
        chat_id=chat_id,
        status='sent',
        attachment_path=attachment_path,
        attachment_type=attachment_type
    )
    db.session.add(msg)
    db.session.commit()

    from flask_socketio import emit as sio_emit
    sio_emit('message:new', {
        'chat_id': chat_id,
        'message': {
            'id': msg.id,
            'sender_id': msg.sender_id,
            'receiver_id': msg.receiver_id,
            'body': msg.body,
            'status': msg.status,
            'is_read': msg.is_read,
            'file_url': msg.file_url,
            'attachment_type': msg.attachment_type,
            'created_at': msg.created_at.isoformat() if msg.created_at else None
        }
    }, room=f'chat_{chat_id}')

    for op in other_participants:
        try:
            notification_service.create_notification(
                user_id=op.user_id,
                title=f'Nuevo mensaje de {current_user.username}',
                message=body or 'Ha enviado un archivo adjunto',
                notif_type='message',
                link='/messages'
            )
        except Exception:
            pass
        try:
            from app.services.email_service import EmailService
            email_service = EmailService()
            receiver_user = User.query.get(op.user_id)
            if receiver_user:
                email_service.send_new_message_email(
                    receiver_user.email,
                    receiver_user.username,
                    current_user.username,
                    (body or "Ha enviado un archivo adjunto")[:100]
                )
        except Exception:
            pass

    return jsonify({
        'success': True,
        'message': {
            'id': msg.id,
            'sender_id': msg.sender_id,
            'body': msg.body,
            'status': msg.status,
            'file_url': msg.file_url,
            'attachment_type': msg.attachment_type,
            'created_at': msg.created_at.isoformat() if msg.created_at else None
        }
    })


@chat_bp.route('/api/chats/<int:chat_id>/read', methods=['PUT'])
@login_required
def mark_read(chat_id):
    if chat_id == -1:
        if current_user.role == 'admin':
            from app.models import ContactMessage
            ContactMessage.query.filter_by(status='unread').update({'status': 'read'})
            db.session.commit()
        return jsonify({'success': True})

    participant = ChatParticipant.query.filter_by(chat_id=chat_id, user_id=current_user.id).first()
    if not participant:
        return jsonify({'success': False, 'message': 'No eres participante'}), 403

    participant.last_read_at = datetime.utcnow()
    db.session.commit()

    Message.query.filter(
        Message.chat_id == chat_id,
        Message.receiver_id == current_user.id,
        Message.status.in_(['sent', 'delivered'])
    ).update({'status': 'read', 'is_read': True}, synchronize_session=False)
    db.session.commit()

    from flask_socketio import emit as sio_emit
    sio_emit('message:status', {
        'chat_id': chat_id,
        'user_id': current_user.id,
        'status': 'read'
    }, room=f'chat_{chat_id}', include_self=False)

    return jsonify({'success': True})


@chat_bp.route('/api/chats/<int:chat_id>', methods=['DELETE'])
@login_required
def delete_chat(chat_id):
    participant = ChatParticipant.query.filter_by(chat_id=chat_id, user_id=current_user.id).first()
    if not participant:
        return jsonify({'success': False, 'message': 'No eres participante'}), 403

    db.session.delete(participant)
    remaining = ChatParticipant.query.filter_by(chat_id=chat_id).count()
    if remaining == 0:
        Chat.query.filter_by(id=chat_id).delete()
    db.session.commit()
    return jsonify({'success': True})
