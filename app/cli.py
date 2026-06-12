import click
from flask import Flask


def register_cli_commands(app: Flask) -> None:
    @app.cli.command('migrate-messages')
    def migrate_messages_command():
        from app.extensions import db
        from app.models import Chat, ChatParticipant, Message

        pairs = (
            db.session.query(Message.sender_id, Message.receiver_id).filter(Message.chat_id.is_(None)).distinct().all()
        )
        count = 0
        for sender_id, receiver_id in pairs:
            existing = (
                Chat.query.join(ChatParticipant, ChatParticipant.chat_id == Chat.id)
                .filter(ChatParticipant.user_id == sender_id)
                .filter(
                    Chat.id.in_(
                        db.session.query(ChatParticipant.chat_id).filter(ChatParticipant.user_id == receiver_id)
                    )
                )
                .first()
            )
            if existing:
                chat_id = existing.id
            else:
                chat = Chat(created_by_id=sender_id)
                db.session.add(chat)
                db.session.flush()
                for uid in [sender_id, receiver_id]:
                    db.session.add(ChatParticipant(chat_id=chat.id, user_id=uid))
                chat_id = chat.id
            updated = Message.query.filter(
                Message.sender_id == sender_id, Message.receiver_id == receiver_id, Message.chat_id.is_(None)
            ).update({'chat_id': chat_id}, synchronize_session=False)
            count += updated
            for op_id in [sender_id, receiver_id]:
                ChatParticipant.query.filter_by(chat_id=chat_id, user_id=op_id).update(
                    {'last_read_at': db.func.now()}, synchronize_session=False
                )
        db.session.commit()
        click.echo(f'Migrated {count} messages into {len(pairs)} chat(s).')
