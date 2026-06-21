"""Add contract, installment tables + guardian_dni + installment_id

Revision ID: d1234567890
Revises: abcd1234remediation
Create Date: 2026-06-21 18:00:00.000000

"""

revision = 'd1234567890'
down_revision = 'abcd1234remediation'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    # Create contract table
    op.create_table('contract',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('patient_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('total_amount', sa.Float(), nullable=False),
        sa.Column('installment_count', sa.Integer(), nullable=False),
        sa.Column('installment_amount', sa.Float(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['patient_id'], ['user.id'], ),
        sa.ForeignKeyConstraint(['created_by_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_contract_patient', 'contract', ['patient_id'])
    op.create_index('idx_contract_status', 'contract', ['status'])

    # Create installment table
    op.create_table('installment',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('contract_id', sa.Integer(), nullable=False),
        sa.Column('number', sa.Integer(), nullable=False),
        sa.Column('due_date', sa.Date(), nullable=False),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('paid_amount', sa.Float(), nullable=False, server_default='0'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='pending'),
        sa.Column('payment_id', sa.Integer(), nullable=True),
        sa.Column('reminder_sent', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('reminded_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['contract_id'], ['contract.id'], ),
        sa.ForeignKeyConstraint(['payment_id'], ['payment.id'], ),
        sa.ForeignKeyConstraint(['created_by_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_installment_contract', 'installment', ['contract_id'])
    op.create_index('idx_installment_status', 'installment', ['status'])
    op.create_index('idx_installment_due_date', 'installment', ['due_date'])
    op.create_index('idx_installment_payment', 'installment', ['payment_id'])

    # Add guardian_dni to user table
    op.add_column('user', sa.Column('guardian_dni', sa.String(length=20), nullable=True))
    op.create_index('idx_user_guardian_dni', 'user', ['guardian_dni'])

    # Add installment_id to payment table
    op.add_column('payment', sa.Column('installment_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_payment_installment_id_installment', 'payment', 'installment', ['installment_id'], ['id'])
    op.create_index('idx_payment_installment', 'payment', ['installment_id'])


def downgrade():
    op.drop_index('idx_payment_installment', table_name='payment')
    op.drop_constraint('fk_payment_installment_id_installment', 'payment', type_='foreignkey')
    op.drop_column('payment', 'installment_id')

    op.drop_index('idx_user_guardian_dni', table_name='user')
    op.drop_column('user', 'guardian_dni')

    op.drop_index('idx_installment_payment', table_name='installment')
    op.drop_index('idx_installment_due_date', table_name='installment')
    op.drop_index('idx_installment_status', table_name='installment')
    op.drop_index('idx_installment_contract', table_name='installment')
    op.drop_table('installment')

    op.drop_index('idx_contract_status', table_name='contract')
    op.drop_index('idx_contract_patient', table_name='contract')
    op.drop_table('contract')
