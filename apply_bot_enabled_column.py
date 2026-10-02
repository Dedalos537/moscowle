"""Add bot_config.enabled directly via SQLAlchemy - no Alembic dependency.

The master on/off switch for the bot. Runs the same way as
apply_itil_columns.py: idempotent, skips if the column is already there.

Run: python apply_bot_enabled_column.py
"""

import os
import sys

import sqlalchemy as sa
from dotenv import load_dotenv

# El script se lanza suelto, sin pasar por config.py: carga el .env igual.
_BASEDIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_BASEDIR, '.env'))
load_dotenv(os.path.join(_BASEDIR, '.env.local'), override=True)

# Tabla y columna fijas en el codigo: no se interpola ninguna entrada externa.
COLUMN = 'enabled'
ALTER_SQL = 'ALTER TABLE bot_config ADD COLUMN enabled BOOLEAN NOT NULL DEFAULT TRUE'
CHECK_SQL = (
    'SELECT COUNT(*) FROM information_schema.columns WHERE table_name = :table_name AND column_name = :column_name'
)


def main():
    uri = os.environ.get('SQLALCHEMY_DATABASE_URI', '')
    if not uri:
        print('No SQLALCHEMY_DATABASE_URI - skipping')
        return

    try:
        engine = sa.create_engine(uri)
        with engine.connect() as conn:
            result = conn.execute(sa.text(CHECK_SQL), {'table_name': 'bot_config', 'column_name': COLUMN})
            if result.scalar() > 0:
                print('Column already exists - skipping')
                return

            print(f'Adding {COLUMN} to bot_config...')
            # DEFAULT TRUE para que las filas existentes arranquen activas.
            conn.execute(sa.text(ALTER_SQL))
            conn.commit()
            print('Done!')
    except Exception as e:
        print(f'Error: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()
