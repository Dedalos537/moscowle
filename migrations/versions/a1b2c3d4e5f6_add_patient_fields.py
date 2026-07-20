"""Add sex, preliminary_diagnosis, guardian_type to User

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-07-20
"""

import sqlalchemy as sa
from alembic import op

revision = 'e5f6a7b8c9d0'
down_revision = 'd4e5f6a7b8c9'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('user', sa.Column('sex', sa.String(20), nullable=True))
    op.add_column('user', sa.Column('preliminary_diagnosis', sa.Text(), nullable=True))
    op.add_column('user', sa.Column('guardian_type', sa.String(50), nullable=True))


def downgrade():
    op.drop_column('user', 'guardian_type')
    op.drop_column('user', 'preliminary_diagnosis')
    op.drop_column('user', 'sex')
