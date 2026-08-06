import contextlib
import logging
import os
import traceback
import uuid
from datetime import datetime

from flask import Blueprint, current_app, jsonify, request, url_for
from sqlalchemy import case, text
from werkzeug.utils import secure_filename

from app.auth_compat import current_user, login_required
from app.extensions import csrf, db
from app.models import Chat, ChatParticipant, Message, User
from app.services.notification_service import NotificationService
from app.socketio_events import online_users
from app.utils.sanitizer import sanitize_text

chat_bp = Blueprint('chat', __name__)
notification_service = NotificationService()
logger = logging.getLogger(__name__)

# Shared error capture for diagnostics
_last_error = {}


def get_last_error():
    return dict(_last_error)


STAFF_ROLES = ('admin', 'supervisor', 'terapista', 'terapeuta')
PATIENT_ROLES = ('jugador', 'paciente')


def _apply_role_filter(q, role_filter):
    if not role_filter or role_filter == 'todos':
        return q
    if role_filter in PATIENT_ROLES:
        return q.filter(User.role.in_(PATIENT_ROLES))
    return q.filter(User.role == role_filter)


def get_contact_list(role_filter=None):
    if current_user.role in ('admin', 'supervisor'):
        q = User.query.filter(User.id != current_user.id, User.is_active)
        return _apply_role_filter(q, role_filter).order_by(User.role, User.username).all()
    elif current_user.role == 'terapista':
        patient_ids = [p.id for p in current_user.assigned_patients if p.is_active]
        associated_ids = [p.id for p in current_user.associated_patients if p.is_active]
        all_patient_ids = set(patient_ids + associated_ids)
        staff_ids = [
            u.id
            for u in User.query.filter(User.role.in_(STAFF_ROLES), User.id != current_user.id, User.is_active).all()
        ]
        ids = all_patient_ids | set(staff_ids)
        if not ids:
            return []
        q = User.query.filter(User.id.in_(ids), User.is_active)
        return _apply_role_filter(q, role_filter).order_by(User.role, User.username).all()
    else:
        admin_super_ids = [u.id for u in User.query.filter(User.role.in_(STAFF_ROLES[:2]), User.is_active).all()]
        ids = set(admin_super_ids)
        if current_user.assigned_therapist_id:
            ids.add(current_user.assigned_therapist_id)
        ids.discard(current_user.id)
        if not ids:
            return []
        q = User.query.filter(User.id.in_(ids), User.is_active)
        return _apply_role_filter(q, role_filter).order_by(User.role, User.username).all()


@chat_bp.route('/api/contacts')
@login_required
def list_contacts():
    role_filter = request.args.get('role')
    contacts = get_contact_list(role_filter)
    online = set(online_users.keys())
    return jsonify(
        [
            {
                'id': u.id,
                'username': u.username,
                'email': u.email,
                'role': u.role,
                'avatar': u.avatar,
                'is_online': u.id in online,
            }
            for u in contacts
        ]
    )


def migrate_legacy_messages():
    try:
        legacy_pairs = (
            db.session.query(
                case((Message.sender_id == current_user.id, Message.receiver_id), else_=Message.sender_id).label(
                    'other_id'
                )
            )
            .filter(
                (Message.sender_id == current_user.id) | (Message.receiver_id == current_user.id),
                Message.chat_id.is_(None),
            )
            .distinct()
            .all()
        )

        migrated = 0
        for (other_id,) in legacy_pairs:
            if other_id is None:
                continue
            other_id = int(other_id)
            other_user = User.query.get(other_id)
            if not other_user:
                continue
            existing = (
                Chat.query.join(ChatParticipant)
                .filter(
                    ChatParticipant.user_id == current_user.id,
                    Chat.id.in_(db.session.query(ChatParticipant.chat_id).filter(ChatParticipant.user_id == other_id)),
                )
                .first()
            )
            if existing:
                Message.query.filter(
                    ((Message.sender_id == current_user.id) & (Message.receiver_id == other_id))
                    | ((Message.sender_id == other_id) & (Message.receiver_id == current_user.id)),
                    Message.chat_id.is_(None),
                ).update({'chat_id': existing.id}, synchronize_session=False)
                continue

            chat = Chat(created_by_id=current_user.id)
            db.session.add(chat)
            db.session.flush()
            for uid in [current_user.id, other_id]:
                cp = ChatParticipant(chat_id=chat.id, user_id=uid)
                db.session.add(cp)
            Message.query.filter(
                ((Message.sender_id == current_user.id) & (Message.receiver_id == other_id))
                | ((Message.sender_id == other_id) & (Message.receiver_id == current_user.id)),
                Message.chat_id.is_(None),
            ).update({'chat_id': chat.id}, synchronize_session=False)
            migrated += 1

        if migrated:
            db.session.commit()
            logger.info(f'Migrated {migrated} legacy message threads for user {current_user.id}')
    except Exception as e:
        db.session.rollback()
        logger.error(f'Error migrating legacy messages for user {current_user.id}: {str(e)}')


@chat_bp.route('/api/chats', methods=['GET'])
@login_required
def list_chats():
    try:
        online = set(online_users.keys())
        migrate_legacy_messages()

        chat_rows = db.session.execute(
            text("""
                SELECT c.id, c.is_group, c.created_at
                FROM chat c
                JOIN chat_participant cp ON cp.chat_id = c.id
                WHERE cp.user_id = :uid
                ORDER BY c.created_at DESC
            """),
            {'uid': current_user.id},
        ).fetchall()

        chat_list = []
        for cr in chat_rows:
            try:
                other_row = db.session.execute(
                    text('SELECT user_id FROM chat_participant WHERE chat_id = :cid AND user_id != :uid LIMIT 1'),
                    {'cid': cr.id, 'uid': current_user.id},
                ).fetchone()
                other_user_row = None
                if other_row:
                    other_user_row = db.session.execute(
                        text('SELECT id, username, role, avatar FROM `user` WHERE id = :uid'),
                        {'uid': other_row.user_id},
                    ).fetchone()

                last_msg_row = db.session.execute(
                    text(
                        'SELECT id, body, sender_id, created_at, attachment_type FROM message WHERE chat_id = :cid ORDER BY created_at DESC LIMIT 1'
                    ),
                    {'cid': cr.id},
                ).fetchone()

                unread_count = (
                    db.session.execute(
                        text("""
                        SELECT COUNT(*) FROM message
                        WHERE chat_id = :cid AND sender_id != :uid AND status IN ('sent', 'delivered')
                    """),
                        {'cid': cr.id, 'uid': current_user.id},
                    ).scalar()
                    or 0
                )

                chat_list.append(
                    {
                        'id': cr.id,
                        'is_group': cr.is_group,
                        'created_at': cr.created_at.isoformat() if cr.created_at else None,
                        'other_user': {
                            'id': other_user_row.id,
                            'username': other_user_row.username,
                            'role': other_user_row.role,
                            'avatar': other_user_row.avatar,
                            'is_online': other_user_row.id in online,
                        }
                        if other_user_row
                        else None,
                        'unread_count': unread_count,
                        'last_message': {
                            'id': last_msg_row.id,
                            'body': last_msg_row.body,
                            'sender_id': last_msg_row.sender_id,
                            'created_at': last_msg_row.created_at.isoformat() if last_msg_row.created_at else None,
                            'attachment_type': last_msg_row.attachment_type,
                        }
                        if last_msg_row
                        else None,
                    }
                )
            except Exception as e:
                logger.error(f'Error processing chat {cr.id}: {str(e)}')
                continue

        if current_user.role in ('admin', 'supervisor'):
            try:
                contact_row = db.session.execute(
                    text('SELECT id, message, created_at FROM contact_message ORDER BY created_at DESC LIMIT 1')
                ).fetchone()
                unread_contact = (
                    db.session.execute(text("SELECT COUNT(*) FROM contact_message WHERE status = 'unread'")).scalar()
                    or 0
                )

                chat_list.append(
                    {
                        'id': -1,
                        'is_group': False,
                        'created_at': contact_row.created_at.isoformat() if contact_row else None,
                        'other_user': {
                            'id': -1,
                            'username': 'Mensajes de la Web',
                            'role': 'system',
                            'avatar': None,
                            'is_online': False,
                        },
                        'unread_count': unread_contact,
                        'last_message': {
                            'id': 0,
                            'body': contact_row.message[:100] if contact_row else 'Sin mensajes',
                            'sender_id': -1,
                            'created_at': contact_row.created_at.isoformat() if contact_row else None,
                            'attachment_type': None,
                        }
                        if contact_row
                        else None,
                    }
                )
            except Exception as e:
                logger.error(f'Error adding contact messages for admin: {str(e)}')

        return jsonify(chat_list)
    except Exception as e:
        logger.error(f'Error in list_chats for user {current_user.id}: {str(e)}', exc_info=True)
        import traceback

        return jsonify(
            {
                'success': False,
                'message': 'Error al cargar conversaciones',
                'error': str(e)[:500],
                'traceback': traceback.format_exc(),
            }
        ), 500


@chat_bp.route('/api/chats', methods=['POST'])
@csrf.exempt
@login_required
def create_chat():
    try:
        data = request.get_json(silent=True) or {}
        other_user_id = data.get('user_id')
        if not other_user_id:
            return jsonify({'success': False, 'message': 'user_id requerido'}), 400

        other = User.query.get(other_user_id)
        if not other or not other.is_active:
            return jsonify({'success': False, 'message': 'Usuario no encontrado'}), 404

        existing = (
            Chat.query.join(ChatParticipant)
            .filter(ChatParticipant.user_id == current_user.id)
            .filter(
                Chat.id.in_(db.session.query(ChatParticipant.chat_id).filter(ChatParticipant.user_id == other_user_id))
            )
            .first()
        )

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
    except Exception as e:
        db.session.rollback()
        logger.error(f'Error creating chat: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'message': 'Error al crear conversación'}), 500


@chat_bp.route('/api/chats/-1/messages', methods=['GET'])
@login_required
def get_contact_messages():
    try:
        if current_user.role not in ('admin', 'supervisor'):
            return jsonify({'success': False, 'message': 'Acceso denegado'}), 403
        from app.models import ContactMessage

        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 50, type=int)
        limit = min(limit, 100)
        msgs = (
            ContactMessage.query.order_by(ContactMessage.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
            .all()
        )
        msgs.reverse()
        total = ContactMessage.query.count()
        ContactMessage.query.filter_by(status='unread').update({'status': 'read'})
        db.session.commit()
        return jsonify(
            {
                'messages': [
                    {
                        'id': m.id,
                        'sender_id': -1,
                        'receiver_id': current_user.id,
                        'body': f'{m.first_name} {m.last_name} ({m.email}){(" - " + m.phone) if m.phone else ""}:\n{m.message}',
                        'status': 'read',
                        'is_read': m.status != 'unread',
                        'file_url': None,
                        'attachment_type': None,
                        'created_at': m.created_at.isoformat() if m.created_at else None,
                    }
                    for m in msgs
                ],
                'total': total,
                'page': page,
                'has_more': (page * limit) < total,
            }
        )
    except Exception as e:
        logger.error(f'Error getting contact messages: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'message': 'Error al cargar mensajes de la web'}), 500


@chat_bp.route('/api/chats/<int:chat_id>/messages', methods=['GET'])
@login_required
def get_messages(chat_id):
    try:
        if chat_id == -1:
            return get_contact_messages()

        chat_exists = db.session.execute(text('SELECT id FROM chat WHERE id = :cid'), {'cid': chat_id}).fetchone()
        if not chat_exists:
            return jsonify({'success': False, 'message': 'Chat no encontrado'}), 404

        is_participant = db.session.execute(
            text('SELECT user_id FROM chat_participant WHERE chat_id = :cid AND user_id = :uid'),
            {'cid': chat_id, 'uid': current_user.id},
        ).fetchone()
        if not is_participant:
            return jsonify({'success': False, 'message': 'No eres participante de este chat'}), 403

        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 50, type=int)
        limit = min(limit, 100)

        rows = db.session.execute(
            text(
                'SELECT id, sender_id, receiver_id, body, status, is_read, attachment_path, attachment_type FROM message WHERE chat_id = :cid ORDER BY id DESC LIMIT :lim OFFSET :offs'
            ),
            {'cid': chat_id, 'offs': (page - 1) * limit, 'lim': limit},
        ).fetchall()
        rows = list(reversed(list(rows)))

        total = (
            db.session.execute(text('SELECT COUNT(*) FROM message WHERE chat_id = :cid'), {'cid': chat_id}).scalar()
            or 0
        )

        def _msg_dict(r):
            return {
                'id': r.id,
                'sender_id': r.sender_id,
                'receiver_id': r.receiver_id,
                'body': r.body,
                'status': r.status,
                'is_read': r.is_read,
                'file_url': url_for('uploads.protected_file', filename=f'messages/{r.attachment_path}', _external=False)
                if r.attachment_path
                else None,
                'attachment_type': r.attachment_type,
                'created_at': None,
            }

        return jsonify(
            {'messages': [_msg_dict(r) for r in rows], 'total': total, 'page': page, 'has_more': (page * limit) < total}
        )
    except Exception as e:
        logger.error(f'Error getting messages for chat {chat_id}: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'message': 'Error al cargar mensajes'}), 500


@chat_bp.route('/api/chats/<int:chat_id>/messages', methods=['POST'])
@csrf.exempt
@login_required
def send_message(chat_id):
    try:
        chat_exists = db.session.execute(text('SELECT id FROM chat WHERE id = :cid'), {'cid': chat_id}).fetchone()
        if not chat_exists:
            return jsonify({'success': False, 'message': 'Chat no encontrado'}), 404

        is_participant = db.session.execute(
            text('SELECT user_id FROM chat_participant WHERE chat_id = :cid AND user_id = :uid'),
            {'cid': chat_id, 'uid': current_user.id},
        ).fetchone()
        if not is_participant:
            return jsonify({'success': False, 'message': 'No eres participante de este chat'}), 403

        body = ''
        attachment_path = None
        attachment_type = None

        if request.is_json:
            data = request.get_json(silent=True) or {}
            body = sanitize_text(data.get('body', ''))
        else:
            data = request.form.to_dict()
            body = sanitize_text(data.get('body', ''))

            if 'file' in request.files:
                file = request.files['file']
                if file and file.filename:
                    filename = secure_filename(file.filename)
                    unique_filename = f'{uuid.uuid4().hex}_{filename}'
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

        other_participant_rows = db.session.execute(
            text('SELECT user_id FROM chat_participant WHERE chat_id = :cid AND user_id != :uid'),
            {'cid': chat_id, 'uid': current_user.id},
        ).fetchall()
        receiver_id = other_participant_rows[0].user_id if other_participant_rows else current_user.id

        result = db.session.execute(
            Message.__table__.insert().values(
                sender_id=current_user.id,
                receiver_id=receiver_id,
                body=body,
                chat_id=chat_id,
                status='sent',
                attachment_path=attachment_path,
                attachment_type=attachment_type,
            )
        )
        msg_id = result.inserted_primary_key[0]
        db.session.commit()

        msg_row = db.session.execute(
            text(
                'SELECT id, sender_id, receiver_id, body, status, is_read, attachment_path, attachment_type FROM message WHERE id = :mid'
            ),
            {'mid': msg_id},
        ).fetchone()

        try:
            from flask_socketio import emit as sio_emit

            sio_emit(
                'message:new',
                {
                    'chat_id': chat_id,
                    'message': {
                        'id': msg_row.id,
                        'sender_id': msg_row.sender_id,
                        'receiver_id': msg_row.receiver_id,
                        'body': msg_row.body,
                        'status': msg_row.status,
                        'is_read': msg_row.is_read,
                        'file_url': url_for(
                            'uploads.protected_file', filename=f'messages/{msg_row.attachment_path}', _external=False
                        )
                        if msg_row.attachment_path
                        else None,
                        'attachment_type': msg_row.attachment_type,
                        'created_at': None,
                    },
                },
                room=f'chat_{chat_id}',
            )
        except Exception as e:
            logger.warning(f'SocketIO emit failed: {str(e)}')

        for row in other_participant_rows:
            with contextlib.suppress(Exception):
                notification_service.create_notification(
                    user_id=row.user_id,
                    title=f'Nuevo mensaje de {current_user.username}',
                    message=body or 'Ha enviado un archivo adjunto',
                    notif_type='message',
                    link='/messages',
                )

        return jsonify(
            {
                'success': True,
                'message': {
                    'id': msg_row.id,
                    'sender_id': msg_row.sender_id,
                    'body': msg_row.body,
                    'status': msg_row.status,
                    'file_url': url_for(
                        'uploads.protected_file', filename=f'messages/{msg_row.attachment_path}', _external=False
                    )
                    if msg_row.attachment_path
                    else None,
                    'attachment_type': msg_row.attachment_type,
                    'created_at': None,
                },
            }
        )
    except Exception as e:
        db.session.rollback()
        logger.error(f'Error sending message to chat {chat_id}: {str(e)}', exc_info=True)
        _last_error.update(
            {
                'time': str(datetime.now()),
                'endpoint': 'send_message',
                'chat_id': chat_id,
                'error': str(e),
                'traceback': traceback.format_exc(),
                'user_id': current_user.id if hasattr(current_user, 'id') else None,
            }
        )
        return jsonify(
            {
                'success': False,
                'message': 'Error al enviar mensaje',
                'error': str(e),
                'traceback': traceback.format_exc(),
            }
        ), 500


@chat_bp.route('/api/chats/-1/read', methods=['PUT'])
@csrf.exempt
@login_required
def mark_contact_read():
    try:
        if current_user.role in ('admin', 'supervisor'):
            from app.models import ContactMessage

            ContactMessage.query.filter_by(status='unread').update({'status': 'read'})
            db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        logger.error(f'Error marking contact messages read: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'message': 'Error al marcar como leído'}), 500


@chat_bp.route('/api/chats/<int:chat_id>/read', methods=['PUT'])
@csrf.exempt
@login_required
def mark_read(chat_id):
    try:
        if chat_id == -1:
            return mark_contact_read()

        participant = ChatParticipant.query.filter_by(chat_id=chat_id, user_id=current_user.id).first()
        if not participant:
            return jsonify({'success': False, 'message': 'No eres participante'}), 403

        participant.last_read_at = datetime.utcnow()
        Message.query.filter(
            Message.chat_id == chat_id,
            Message.receiver_id == current_user.id,
            Message.status.in_(['sent', 'delivered']),
        ).update({'status': 'read', 'is_read': True}, synchronize_session=False)
        db.session.commit()

        try:
            from flask_socketio import emit as sio_emit

            sio_emit(
                'message:status',
                {'chat_id': chat_id, 'user_id': current_user.id, 'status': 'read'},
                room=f'chat_{chat_id}',
                include_self=False,
            )
        except Exception as e:
            logger.warning(f'SocketIO status emit failed: {str(e)}')

        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        logger.error(f'Error marking read for chat {chat_id}: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'message': 'Error al marcar como leído'}), 500


@chat_bp.route('/api/chats/<int:chat_id>', methods=['DELETE'])
@csrf.exempt
@login_required
def delete_chat(chat_id):
    try:
        participant = ChatParticipant.query.filter_by(chat_id=chat_id, user_id=current_user.id).first()
        if not participant:
            return jsonify({'success': False, 'message': 'No eres participante'}), 403

        db.session.delete(participant)
        remaining = ChatParticipant.query.filter_by(chat_id=chat_id).count()
        if remaining == 0:
            Chat.query.filter_by(id=chat_id).delete()
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        logger.error(f'Error deleting chat {chat_id}: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'message': 'Error al eliminar conversación'}), 500
