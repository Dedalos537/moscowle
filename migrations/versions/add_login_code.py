"""Add login_code to user table and populate existing users.

Revision ID: add_login_code
Revises: None
Create Date: 2026-09-02
"""

import sqlalchemy as sa
from alembic import op

revision = 'add_login_code'
down_revision = None
branch_labels = None
depends_on = None


ROLE_CODE_MAP = {
    'jugador': 'PCJP',
    'terapista': 'TCJP',
    'admin': 'ACJP',
    'supervisor': 'SCJP',
}


def upgrade():
    op.add_column('user', sa.Column('login_code', sa.String(20), nullable=True))
    op.create_index('ix_user_login_code', 'user', ['login_code'], unique=True)

    conn = op.get_bind()
    result = conn.execute(sa.text('SELECT id, role FROM user ORDER BY id ASC'))
    rows = result.fetchall()

    counters = {prefix: 0 for prefix in ROLE_CODE_MAP.values()}
    for row in rows:
        user_id, role = row
        prefix = ROLE_CODE_MAP.get(role, 'UCJP')
        counters[prefix] += 1
        code = f'{prefix}{counters[prefix]}'
        conn.execute(
            sa.text('UPDATE user SET login_code = :code WHERE id = :id'),
            {'code': code, 'id': user_id},
        )


def downgrade():
    op.drop_index('ix_user_login_code', table_name='user')
    op.drop_column('user', 'login_code')
