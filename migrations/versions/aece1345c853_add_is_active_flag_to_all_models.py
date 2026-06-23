"""add is_active flag to all models

Revision ID: aece1345c853
Revises: bba7eaa6929c
Create Date: 2026-06-10 11:52:26.657844

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'aece1345c853'
down_revision = 'bba7eaa6929c'
branch_labels = None
depends_on = None

TABLES = [
    'ai_chat_message',
    'ai_conversation',
    'appointment',
    'appointment_game',
    'chat',
    'chat_participant',
    'contact_message',
    'daily_report',
    'expense',
    'message',
    'monthly_report',
    'notification',
    'payment',
    'quarterly_report',
    'session_audit',
    'session_image',
    'session_metrics',
    'weekly_report',
    'yape_transaction',
]


def upgrade():
    for table in TABLES:
        op.add_column(table, sa.Column('is_active', sa.Boolean(), nullable=True))


def downgrade():
    for table in reversed(TABLES):
        op.drop_column(table, 'is_active')
