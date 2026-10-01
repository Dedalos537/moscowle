"""messaging crm campaigns

Revision ID: a1b2c3d4e5f7
Revises: a1b2c3d4e5f6_notification_expansion
Create Date: 2025-10-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f7'
down_revision = 'a1b2c3d4e5f6_notification_expansion'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'message_template',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('key', sa.String(length=60), nullable=False),
        sa.Column('channel', sa.String(length=20), nullable=False),
        sa.Column('label', sa.String(length=120), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('placeholders', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('updated_by_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['updated_by_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_message_template_key'), 'message_template', ['key'], unique=True)

    op.create_table(
        'message_log',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('patient_id', sa.Integer(), nullable=True),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('channel', sa.String(length=20), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('template_key', sa.String(length=60), nullable=True),
        sa.Column('campaign_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('failed_reason', sa.String(length=255), nullable=True),
        sa.Column('provider_message_id', sa.String(length=120), nullable=True),
        sa.Column('sent_by_id', sa.Integer(), nullable=True),
        sa.Column('trigger', sa.String(length=30), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['patient_id'], ['user.id']),
        sa.ForeignKeyConstraint(['sent_by_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_msglog_patient_channel', 'message_log', ['patient_id', 'channel'], unique=False)
    op.create_index('ix_msglog_created_at', 'message_log', ['created_at'], unique=False)
    op.create_index(op.f('ix_message_log_status'), 'message_log', ['status'], unique=False)

    op.create_table(
        'campaign',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('channel', sa.String(length=20), nullable=False),
        sa.Column('template_key', sa.String(length=60), nullable=True),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('segment', sa.String(length=60), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('total_recipients', sa.Integer(), nullable=True),
        sa.Column('sent_count', sa.Integer(), nullable=True),
        sa.Column('failed_count', sa.Integer(), nullable=True),
        sa.Column('skipped_count', sa.Integer(), nullable=True),
        sa.Column('scheduled_at', sa.DateTime(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['created_by_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_campaign_status'), 'campaign', ['status'], unique=False)

    op.create_table(
        'campaign_send',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('campaign_id', sa.Integer(), nullable=False),
        sa.Column('patient_id', sa.Integer(), nullable=False),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('skip_reason', sa.String(length=255), nullable=True),
        sa.Column('failed_reason', sa.String(length=255), nullable=True),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['campaign_id'], ['campaign.id']),
        sa.ForeignKeyConstraint(['patient_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('campaign_id', 'patient_id', name='uq_campaign_patient'),
    )
    op.create_index(op.f('ix_campsend_status'), 'campaign_send', ['status'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_campsend_status'), table_name='campaign_send')
    op.drop_table('campaign_send')
    op.drop_index(op.f('ix_campaign_status'), table_name='campaign')
    op.drop_table('campaign')
    op.drop_index(op.f('ix_message_log_status'), table_name='message_log')
    op.drop_index('ix_msglog_created_at', table_name='message_log')
    op.drop_index('ix_msglog_patient_channel', table_name='message_log')
    op.drop_table('message_log')
    op.drop_index(op.f('ix_message_template_key'), table_name='message_template')
    op.drop_table('message_template')
