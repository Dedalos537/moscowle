"""Apply ITIL columns directly via SQLAlchemy - no Alembic dependency.

Run: python apply_itil_columns.py
"""

import os
import sys

import sqlalchemy as sa


def main():
    uri = os.environ.get('SQLALCHEMY_DATABASE_URI', '')
    if not uri:
        print('No SQLALCHEMY_DATABASE_URI - skipping')
        return

    try:
        engine = sa.create_engine(uri)
        with engine.connect() as conn:
            result = conn.execute(
                sa.text(
                    'SELECT COUNT(*) FROM information_schema.columns '
                    "WHERE table_name = 'incidente' AND column_name = 'impacto'"
                )
            )
            if result.scalar() > 0:
                print('Columns already exist - skipping')
                return

            print('Adding ITIL columns to incidente table...')
            columns = [
                ('impacto', 'INTEGER NOT NULL DEFAULT 2'),
                ('urgencia', 'INTEGER NOT NULL DEFAULT 2'),
                ('post_mortem', 'TEXT NULL'),
                ('causa_raiz', 'TEXT NULL'),
                ('lecciones_aprendidas', 'TEXT NULL'),
            ]
            for col, typ in columns:
                try:
                    conn.execute(sa.text(f'ALTER TABLE incidente ADD COLUMN {col} {typ}'))
                    print(f'  + {col}')
                except Exception as e:
                    if 'Duplicate column' in str(e):
                        print(f'  ~ {col} (already exists)')
                    else:
                        print(f'  ! {col}: {e}')

            conn.commit()
            print('Done!')
    except Exception as e:
        print(f'Error: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()
