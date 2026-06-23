"""remediation phase 1&2 — refresh_tokens, mfa_lockout, indexes

Revision ID: abcd1234remediation
Revises: 7cf46fd2e754
Create Date: 2026-06-10 14:00:00.000000

"""
import contextlib

import sqlalchemy as sa
from alembic import op

revision = 'abcd1234remediation'
down_revision = '7cf46fd2e754'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()

    # --- refresh_token table (IF NOT EXISTS for db.create_all() compatibility) ---
    if not conn.dialect.has_table(conn, 'refresh_token'):
        op.create_table(
            'refresh_token',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('user.id'), nullable=False, index=True),
            sa.Column('token_hash', sa.String(128), nullable=False, unique=True, index=True),
            sa.Column('expires_at', sa.DateTime(), nullable=False),
            sa.Column('revoked_at', sa.DateTime(), nullable=True),
            sa.Column('device_info', sa.String(255), nullable=True),
            sa.Column('ip_address', sa.String(45), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
        )

    # --- User: MFA lockout fields (try/except for idempotency) ---
    with contextlib.suppress(Exception):
        op.add_column('user', sa.Column('mfa_failed_attempts', sa.Integer(), server_default='0', nullable=True))
    with contextlib.suppress(Exception):
        op.add_column('user', sa.Column('mfa_locked_until', sa.DateTime(), nullable=True))

    # --- Composite indexes ---
    with contextlib.suppress(Exception):
        op.create_index('ix_appointment_therapist_start', 'appointment', ['therapist_id', 'start_time'])
    with contextlib.suppress(Exception):
        op.create_index('ix_payment_patient_status', 'payment', ['patient_id', 'status'])


def downgrade():
    for action in [
        lambda: op.drop_index('ix_payment_patient_status', table_name='payment'),
        lambda: op.drop_index('ix_appointment_therapist_start', table_name='appointment'),
        lambda: op.drop_column('user', 'mfa_locked_until'),
        lambda: op.drop_column('user', 'mfa_failed_attempts'),
        lambda: op.drop_table('refresh_token'),
    ]:
        with contextlib.suppress(Exception):
            action()
