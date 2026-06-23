"""add_audit_fields_and_indexes

Revision ID: bba7eaa6929c
Revises: bba7eaa6929b
Create Date: 2026-06-10 18:00:00.000000

"""

revision = 'bba7eaa6929c'
down_revision = 'bba7eaa6929b'
branch_labels = None
depends_on = None

import sqlalchemy as sa
from alembic import op

TABLES = [
    'user', 'sede', 'smart_action', 'csp_report', 'admin_api_token',
    'ai_conversation', 'ai_chat_message',
    'session_metrics', 'appointment_game', 'session_image', 'appointment',
    'chat', 'chat_participant', 'message', 'contact_message',
    'game',
    'notification',
    'payment', 'expense', 'yape_transaction',
    'session_audit', 'weekly_report', 'daily_report', 'monthly_report', 'quarterly_report',
]

TABLES_WITH_UPDATED_AT = {'ai_conversation', 'appointment', 'yape_transaction', 'session_audit'}
TABLES_WITH_CREATED_BY_ID = {'chat'}


def upgrade():
    for table in TABLES:
        if table not in TABLES_WITH_CREATED_BY_ID:
            op.add_column(table, sa.Column('created_by_id', sa.Integer(), nullable=True))
            op.create_foreign_key(
                f'fk_{table}_created_by_id_user',
                table, 'user',
                ['created_by_id'], ['id'],
            )
        if table not in TABLES_WITH_UPDATED_AT:
            op.add_column(table, sa.Column('updated_at', sa.DateTime(), nullable=True))

    op.create_index('idx_user_email', 'user', ['email'])
    op.create_index('idx_user_role', 'user', ['role'])
    op.create_index('idx_user_is_active', 'user', ['is_active'])

    op.create_index('idx_sede_active', 'sede', ['active'])

    op.create_index('idx_smart_action_status', 'smart_action', ['status'])
    op.create_index('idx_smart_action_module', 'smart_action', ['module'])

    op.create_index('idx_ai_conversation_user', 'ai_conversation', ['user_id'])
    op.create_index('idx_ai_conversation_session', 'ai_conversation', ['session_id'])
    op.create_index('idx_ai_chat_message_conversation', 'ai_chat_message', ['conversation_id'])

    op.create_index('idx_session_metrics_user', 'session_metrics', ['user_id'])
    op.create_index('idx_session_metrics_session', 'session_metrics', ['session_id'])

    op.create_index('idx_appointment_therapist', 'appointment', ['therapist_id'])
    op.create_index('idx_appointment_patient', 'appointment', ['patient_id'])
    op.create_index('idx_appointment_status', 'appointment', ['status'])
    op.create_index('idx_appointment_start', 'appointment', ['start_time'])

    op.create_index('idx_session_image_appointment', 'session_image', ['appointment_id'])

    op.create_index('idx_message_sender', 'message', ['sender_id'])
    op.create_index('idx_message_receiver', 'message', ['receiver_id'])
    op.create_index('idx_message_chat', 'message', ['chat_id'])
    op.create_index('idx_message_status', 'message', ['status'])

    op.create_index('idx_contact_message_status', 'contact_message', ['status'])
    op.create_index('idx_contact_message_urgency', 'contact_message', ['urgency'])

    op.create_index('idx_game_is_active', 'game', ['is_active'])

    op.create_index('idx_notification_user', 'notification', ['user_id'])
    op.create_index('idx_notification_is_read', 'notification', ['is_read'])

    op.create_index('idx_payment_patient', 'payment', ['patient_id'])
    op.create_index('idx_payment_status', 'payment', ['status'])

    op.create_index('idx_yape_operation', 'yape_transaction', ['operation_number'])
    op.create_index('idx_yape_category', 'yape_transaction', ['category'])

    op.create_index('idx_weekly_report_patient', 'weekly_report', ['patient_id'])
    op.create_index('idx_daily_report_patient', 'daily_report', ['patient_id'])
    op.create_index('idx_monthly_report_patient', 'monthly_report', ['patient_id'])
    op.create_index('idx_quarterly_report_patient', 'quarterly_report', ['patient_id'])

    op.create_index('idx_session_audit_appointment', 'session_audit', ['appointment_id'])
    op.create_index('idx_session_audit_status', 'session_audit', ['audit_status'])

    op.create_index('idx_admin_api_token_active', 'admin_api_token', ['is_active'])


def downgrade():
    op.drop_index('idx_admin_api_token_active', table_name='admin_api_token')
    op.drop_index('idx_session_audit_status', table_name='session_audit')
    op.drop_index('idx_session_audit_appointment', table_name='session_audit')
    op.drop_index('idx_quarterly_report_patient', table_name='quarterly_report')
    op.drop_index('idx_monthly_report_patient', table_name='monthly_report')
    op.drop_index('idx_daily_report_patient', table_name='daily_report')
    op.drop_index('idx_weekly_report_patient', table_name='weekly_report')
    op.drop_index('idx_yape_category', table_name='yape_transaction')
    op.drop_index('idx_yape_operation', table_name='yape_transaction')
    op.drop_index('idx_payment_status', table_name='payment')
    op.drop_index('idx_payment_patient', table_name='payment')
    op.drop_index('idx_notification_is_read', table_name='notification')
    op.drop_index('idx_notification_user', table_name='notification')
    op.drop_index('idx_game_is_active', table_name='game')
    op.drop_index('idx_contact_message_urgency', table_name='contact_message')
    op.drop_index('idx_contact_message_status', table_name='contact_message')
    op.drop_index('idx_message_status', table_name='message')
    op.drop_index('idx_message_chat', table_name='message')
    op.drop_index('idx_message_receiver', table_name='message')
    op.drop_index('idx_message_sender', table_name='message')
    op.drop_index('idx_session_image_appointment', table_name='session_image')
    op.drop_index('idx_appointment_start', table_name='appointment')
    op.drop_index('idx_appointment_status', table_name='appointment')
    op.drop_index('idx_appointment_patient', table_name='appointment')
    op.drop_index('idx_appointment_therapist', table_name='appointment')
    op.drop_index('idx_session_metrics_session', table_name='session_metrics')
    op.drop_index('idx_session_metrics_user', table_name='session_metrics')
    op.drop_index('idx_ai_chat_message_conversation', table_name='ai_chat_message')
    op.drop_index('idx_ai_conversation_session', table_name='ai_conversation')
    op.drop_index('idx_ai_conversation_user', table_name='ai_conversation')
    op.drop_index('idx_smart_action_module', table_name='smart_action')
    op.drop_index('idx_smart_action_status', table_name='smart_action')
    op.drop_index('idx_sede_active', table_name='sede')
    op.drop_index('idx_user_is_active', table_name='user')
    op.drop_index('idx_user_role', table_name='user')
    op.drop_index('idx_user_email', table_name='user')

    for table in reversed(TABLES):
        if table not in TABLES_WITH_UPDATED_AT:
            op.drop_column(table, 'updated_at')
        if table not in TABLES_WITH_CREATED_BY_ID:
            op.drop_constraint(f'fk_{table}_created_by_id_user', table, type_='foreignkey')
            op.drop_column(table, 'created_by_id')
