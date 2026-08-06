"""Add password reset approval fields

Revision ID: a1b2c3d4e5f6
Revises: f7a8b9c0d1e2
Create Date: 2026-08-04
"""

import sqlalchemy as sa
from alembic import op

revision = 'a1b2c3d4e5f6'
down_revision = 'f7a8b9c0d1e2'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('password_resets', sa.Column('temp_password_plain', sa.String(64), nullable=True))
    op.add_column('password_resets', sa.Column('admin_id', sa.Integer, nullable=True))
    op.add_column('password_resets', sa.Column('admin_decision', sa.String(20), nullable=True))
    op.add_column('password_resets', sa.Column('decision_at', sa.DateTime(), nullable=True))
    op.add_column('password_resets', sa.Column('requester_ip', sa.String(64), nullable=True))
    op.add_column('password_resets', sa.Column('requester_user_agent', sa.String(255), nullable=True))
    op.alter_column('password_resets', 'code', existing_type=sa.String(6), nullable=True)
    op.alter_column(
        'password_resets', 'status', existing_type=sa.String(20), nullable=True, server_default='awaiting_approval'
    )
    op.create_index('ix_password_resets_status', 'password_resets', ['status'])
    op.create_index('ix_password_resets_expires_at', 'password_resets', ['expires_at'])
    op.create_foreign_key('fk_password_resets_admin_id', 'password_resets', 'user', ['admin_id'], ['id'])


def downgrade():
    op.drop_constraint('fk_password_resets_admin_id', 'password_resets', type_='foreignkey')
    op.drop_index('ix_password_resets_expires_at', table_name='password_resets')
    op.drop_index('ix_password_resets_status', table_name='password_resets')
    op.alter_column('password_resets', 'status', existing_type=sa.String(20), nullable=True, server_default='pending')
    op.alter_column('password_resets', 'code', existing_type=sa.String(6), nullable=False)
    op.drop_column('password_resets', 'requester_user_agent')
    op.drop_column('password_resets', 'requester_ip')
    op.drop_column('password_resets', 'decision_at')
    op.drop_column('password_resets', 'admin_decision')
    op.drop_column('password_resets', 'admin_id')
    op.drop_column('password_resets', 'temp_password_plain')
