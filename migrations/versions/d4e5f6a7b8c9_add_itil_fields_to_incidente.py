"""add ITIL fields to incidente

Revision ID: d4e5f6a7b8c9
Revises: c1d2e3f4a5b6
Create Date: 2026-07-15
"""

import sqlalchemy as sa
from alembic import op

revision = 'd4e5f6a7b8c9'
down_revision = 'c1d2e3f4a5b6'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('incidente', sa.Column('impacto', sa.Integer(), nullable=False, server_default='2'))
    op.add_column('incidente', sa.Column('urgencia', sa.Integer(), nullable=False, server_default='2'))
    op.add_column('incidente', sa.Column('post_mortem', sa.Text(), nullable=True))
    op.add_column('incidente', sa.Column('causa_raiz', sa.Text(), nullable=True))
    op.add_column('incidente', sa.Column('lecciones_aprendidas', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('incidente', 'lecciones_aprendidas')
    op.drop_column('incidente', 'causa_raiz')
    op.drop_column('incidente', 'post_mortem')
    op.drop_column('incidente', 'urgencia')
    op.drop_column('incidente', 'impacto')
