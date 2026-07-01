"""merge heads: add composite indexes for incident queries

Revision ID: c1d2e3f4a5b6
Revises: a1b2c3d4e5f6, f1e2d3c4b5a6
Create Date: 2026-07-01 10:00:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = 'c1d2e3f4a5b6'
down_revision = ('a1b2c3d4e5f6', 'f1e2d3c4b5a6')
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        'idx_incidente_estado_prioridad',
        'incidente',
        ['estado', 'prioridad'],
    )
    op.create_index(
        'idx_incidente_responsable_estado',
        'incidente',
        ['responsable_id', 'estado'],
    )
    op.create_index(
        'idx_incidente_sla_escalamiento',
        'incidente',
        ['fecha_limite_sla', 'escalamiento_nivel'],
    )
    op.create_index(
        'idx_incidente_categoria_estado',
        'incidente',
        ['categoria', 'estado'],
    )
    op.create_index(
        'idx_incidente_created_estado',
        'incidente',
        ['created_at', 'estado'],
    )


def downgrade():
    op.drop_index('idx_incidente_created_estado', 'incidente')
    op.drop_index('idx_incidente_categoria_estado', 'incidente')
    op.drop_index('idx_incidente_sla_escalamiento', 'incidente')
    op.drop_index('idx_incidente_responsable_estado', 'incidente')
    op.drop_index('idx_incidente_estado_prioridad', 'incidente')
