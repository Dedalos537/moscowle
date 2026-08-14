"""Migración ligera: agrega columnas nuevas a tablas existentes (idempotente).

En hosting compartido el backend corre con db.create_all(), que NO agrega
columnas a tablas que ya existen. Este helper ejecuta ALTER TABLE ... ADD
COLUMN IF NOT EXISTS para las columnas nuevas introducidas en cada deploy.
"""

import logging

from sqlalchemy import text

logger = logging.getLogger('app.migrate')

_COLUMNS = [
    (
        'telegram_users',
        [
            ('pending_confirmation', 'JSON'),
            ('pending_confirmation_expires_at', 'DATETIME'),
            ('awaiting_patient_name', 'JSON'),
        ],
    ),
]


def ensure_columns():
    """Agrega columnas faltantes a tablas existentes. No-op si no hay DB."""
    try:
        from app.extensions import db  # noqa: PLC0415  (lazy: no importar si no hay DB)

        db.engine.dispose()
        for table, columns in _COLUMNS:
            for col, ctype in columns:
                try:
                    db.session.execute(text(f'ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {ctype}'))
                except Exception:
                    db.session.rollback()
                    try:
                        db.session.execute(text(f'ALTER TABLE {table} ADD COLUMN {col} {ctype}'))
                    except Exception:
                        db.session.rollback()
                        logger.info(f'Column {table}.{col} already exists or not supported')
                    else:
                        db.session.commit()
                        logger.info(f'Added column {table}.{col} ({ctype})')
                else:
                    db.session.commit()
                    logger.info(f'Ensured column {table}.{col} ({ctype})')
        logger.info('ensure_columns done')
    except Exception as e:
        logger.warning(f'ensure_columns skipped (non-fatal): {e}')
