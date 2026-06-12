"""add mfa fields to user

Revision ID: 7cf46fd2e754
Revises: aece1345c853
Create Date: 2026-06-10 12:17:45.598093

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '7cf46fd2e754'
down_revision = 'aece1345c853'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('user', sa.Column('mfa_enabled', sa.Boolean(), nullable=True, server_default=sa.text('0')))
    op.add_column('user', sa.Column('otp_secret', sa.String(length=32), nullable=True))


def downgrade():
    op.drop_column('user', 'otp_secret')
    op.drop_column('user', 'mfa_enabled')
