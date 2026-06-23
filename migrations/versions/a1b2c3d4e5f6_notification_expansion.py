"""notification: add category/priority/icon/metadata_json, create user_notification_preference

Revision ID: a1b2c3d4e5f6
Revises: abcd1234remediation
Create Date: 2026-06-23 11:25:00.000000

"""

import contextlib

import sqlalchemy as sa
from alembic import op

revision = 'a1b2c3d4e5f6'
down_revision = 'abcd1234remediation'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()

    # --- notification: new columns ---
    for _col in ['category', 'priority', 'icon', 'metadata_json']:
        if not conn.dialect.has_table(conn, 'notification'):
            break
    with contextlib.suppress(Exception):
        op.add_column('notification', sa.Column('category', sa.String(50), nullable=False, server_default='system'))
    with contextlib.suppress(Exception):
        op.add_column('notification', sa.Column('priority', sa.String(20), nullable=False, server_default='normal'))
    with contextlib.suppress(Exception):
        op.add_column('notification', sa.Column('icon', sa.String(50), nullable=True))
    with contextlib.suppress(Exception):
        op.add_column('notification', sa.Column('metadata_json', sa.JSON(), nullable=True))

    # --- create user_notification_preference table ---
    if not conn.dialect.has_table(conn, 'user_notification_preference'):
        op.create_table(
            'user_notification_preference',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('user.id'), nullable=False, unique=True),
            sa.Column('debt_enabled', sa.Boolean(), nullable=False, server_default='1'),
            sa.Column('activity_enabled', sa.Boolean(), nullable=False, server_default='1'),
            sa.Column('system_enabled', sa.Boolean(), nullable=False, server_default='1'),
            sa.Column('alert_enabled', sa.Boolean(), nullable=False, server_default='1'),
            sa.Column('payment_enabled', sa.Boolean(), nullable=False, server_default='1'),
            sa.Column('sound_enabled', sa.Boolean(), nullable=False, server_default='1'),
            sa.Column('browser_notifications', sa.Boolean(), nullable=False, server_default='0'),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('ix_user_notif_pref_user_id', 'user_notification_preference', ['user_id'])


def downgrade():
    for action in [
        lambda: op.drop_column('notification', 'metadata_json'),
        lambda: op.drop_column('notification', 'icon'),
        lambda: op.drop_column('notification', 'priority'),
        lambda: op.drop_column('notification', 'category'),
        lambda: op.drop_index('ix_user_notif_pref_user_id', table_name='user_notification_preference'),
        lambda: op.drop_table('user_notification_preference'),
    ]:
        with contextlib.suppress(Exception):
            action()
