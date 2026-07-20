"""Add sex, preliminary_diagnosis, guardian_type to User

Revision ID: a1b2c3d4e5f6
Revises: bba7eaa6929c
Create Date: 2026-07-20
"""

from alembic import op
import sqlalchemy as sa


revision = 'a1b2c3d4e5f6'
down_revision = 'bba7eaa6929c'
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
