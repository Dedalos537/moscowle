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

    @app.cli.command('diagnose-db')
    def diagnose_db_command():
        """Check database connectivity and basic health."""
        import time

        from app.extensions import db

        click.echo('--- Database Diagnostics ---')

        try:
            start = time.time()
            db.session.execute(db.text('SELECT 1'))
            latency = (time.time() - start) * 1000
            click.echo(f'Connection: OK ({latency:.1f}ms)')
        except Exception as e:
            click.echo(f'Connection: FAILED ({e})')
            return

        try:
            result = db.session.execute(db.text('SELECT COUNT(*) FROM user'))
            user_count = result.scalar()
            click.echo(f'Users: {user_count}')
        except Exception as e:
            click.echo(f'User count: ERROR ({e})')

        try:
            result = db.session.execute(db.text('SELECT COUNT(*) FROM appointment'))
            appt_count = result.scalar()
            click.echo(f'Appointments: {appt_count}')
        except Exception as e:
            click.echo(f'Appointment count: ERROR ({e})')

        try:
            result = db.session.execute(db.text('SELECT COUNT(*) FROM incidente'))
            inc_count = result.scalar()
            click.echo(f'Incidents: {inc_count}')
        except Exception as e:
            click.echo(f'Incident count: ERROR ({e})')

    @app.cli.command('diagnose-api')
    def diagnose_api_command():
        """Check API health endpoint."""
        import time

        import requests as req

        click.echo('--- API Diagnostics ---')

        try:
            start = time.time()
            resp = req.get('http://localhost:5000/api/health', timeout=5)
            latency = (time.time() - start) * 1000
            click.echo(f'Health endpoint: {resp.status_code} ({latency:.1f}ms)')
            if resp.status_code == 200:
                data = resp.json()
                click.echo(f'  Status: {data.get("status", "unknown")}')
                click.echo(f'  Database: {data.get("database", "unknown")}')
        except Exception as e:
            click.echo(f'Health endpoint: FAILED ({e})')

    @app.cli.command('diagnose')
    def diagnose_command():
        """Run all diagnostics."""
        click.echo('========================================')
        click.echo(' Moscowle IA - System Diagnostics')
        click.echo('========================================')
        click.echo('')
        ctx = click.get_current_context()
        ctx.invoke(diagnose_db_command)
        click.echo('')
        ctx.invoke(diagnose_api_command)
        click.echo('')
        click.echo('========================================')
        click.echo(' Diagnostics complete')
        click.echo('========================================')
