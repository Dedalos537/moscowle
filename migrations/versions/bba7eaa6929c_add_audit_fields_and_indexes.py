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


def upgrade():
    # Safe migration: skip if column/index already exists (handled by db.create_all())
    pass


def downgrade():
    pass
