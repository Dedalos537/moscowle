import logging

from app.extensions import db

logger = logging.getLogger('app')


def create_ia_tables():
    """Crea las tablas de conversación de IA si no existen."""
    try:
        db.create_all()
        logger.info('Tablas de IA creadas correctamente')
        print('Tablas de conversación de IA creadas')
        return True
    except Exception as e:
        logger.error(f'Error creando tablas de IA: {e}')
        print(f'Error: {e}')
        return False


def check_ia_tables():
    """Verifica si las tablas existen."""
    try:
        from sqlalchemy import inspect

        from app.extensions import db

        inspector = inspect(db.engine)
        tables = inspector.get_table_names()

        has_conversation = 'ai_conversation' in tables
        has_messages = 'ai_chat_message' in tables

        print(f'AI Conversation table: {"yes" if has_conversation else "no"}')
        print(f'AI Chat Message table: {"yes" if has_messages else "no"}')

        return has_conversation and has_messages
    except Exception as e:
        logger.error(f'Error checking tables: {e}')
        return False
