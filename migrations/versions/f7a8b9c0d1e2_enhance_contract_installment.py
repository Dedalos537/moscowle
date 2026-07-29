"""Enhance contract and installment models with billing, cancellation, payment fields

Revision ID: f7a8b9c0d1e2
Revises: e5f6a7b8c9d0
Create Date: 2026-07-28
"""

import sqlalchemy as sa
from alembic import op

revision = 'f7a8b9c0d1e2'
down_revision = 'e5f6a7b8c9d0'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('contract', sa.Column('billing_type', sa.String(20), server_default='Mensual'))
    op.add_column('contract', sa.Column('currency', sa.String(5), server_default='PEN'))
    op.add_column('contract', sa.Column('bonus_months', sa.Integer, server_default='0'))
    op.add_column('contract', sa.Column('sign_date', sa.Date(), nullable=True))
    op.add_column('contract', sa.Column('service_start_date', sa.Date(), nullable=True))
    op.add_column('contract', sa.Column('billing_rule', sa.String(20), server_default='standard'))
    op.add_column('contract', sa.Column('implementation_cost', sa.Float, server_default='0'))
    op.add_column('contract', sa.Column('cancelled_at', sa.DateTime(), nullable=True))
    op.add_column('contract', sa.Column('cancellation_reason', sa.String(200), nullable=True))
    op.add_column('contract', sa.Column('cancellation_comment', sa.Text(), nullable=True))
    op.add_column('contract', sa.Column('refund_status', sa.String(20), nullable=True))
    op.add_column('contract', sa.Column('total_refunded', sa.Float, server_default='0'))

    op.add_column('installment', sa.Column('real_amount', sa.Float, nullable=True))
    op.add_column('installment', sa.Column('payment_method', sa.String(50), nullable=True))
    op.add_column('installment', sa.Column('payment_currency', sa.String(5), nullable=True))
    op.add_column('installment', sa.Column('payment_notes', sa.Text(), nullable=True))
    op.add_column('installment', sa.Column('is_free_month', sa.Boolean, server_default='0'))
    op.add_column('installment', sa.Column('refunded_amount', sa.Float, server_default='0'))
    op.add_column('installment', sa.Column('refunded_at', sa.DateTime(), nullable=True))
    op.add_column('installment', sa.Column('description', sa.String(200), nullable=True))
    op.add_column('installment', sa.Column('is_implementation', sa.Boolean, server_default='0'))


def downgrade():
    op.drop_column('installment', 'is_implementation')
    op.drop_column('installment', 'description')
    op.drop_column('installment', 'refunded_at')
    op.drop_column('installment', 'refunded_amount')
    op.drop_column('installment', 'is_free_month')
    op.drop_column('installment', 'payment_notes')
    op.drop_column('installment', 'payment_currency')
    op.drop_column('installment', 'payment_method')
    op.drop_column('installment', 'real_amount')

    op.drop_column('contract', 'total_refunded')
    op.drop_column('contract', 'refund_status')
    op.drop_column('contract', 'cancellation_comment')
    op.drop_column('contract', 'cancellation_reason')
    op.drop_column('contract', 'cancelled_at')
    op.drop_column('contract', 'implementation_cost')
    op.drop_column('contract', 'billing_rule')
    op.drop_column('contract', 'service_start_date')
    op.drop_column('contract', 'sign_date')
    op.drop_column('contract', 'bonus_months')
    op.drop_column('contract', 'currency')
    op.drop_column('contract', 'billing_type')
