"""add incidente tables

Revision ID: f1e2d3c4b5a6
Revises: aece1345c853
Create Date: 2026-06-24 10:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'f1e2d3c4b5a6'
down_revision = 'aece1345c853'
branch_labels = None
depends_on = None


def upgrade():
    # Tabla principal de incidentes
    op.create_table(
        'incidente',
        sa.Column('id_incidente', sa.Integer(), primary_key=True),
        sa.Column('titulo', sa.String(200), nullable=False),
        sa.Column('descripcion', sa.Text(), nullable=False),
        sa.Column('appointment_id', sa.Integer(), sa.ForeignKey('appointment.id'), nullable=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('user.id'), nullable=False),
        sa.Column('reports_to_id', sa.Integer(), sa.ForeignKey('user.id'), nullable=True),
        sa.Column('categoria', sa.String(50), nullable=False),
        sa.Column('subcategoria', sa.String(100), nullable=True),
        sa.Column('prioridad', sa.Integer(), default=3, nullable=False),
        sa.Column('estado', sa.String(50), default='NUEVO', nullable=False),
        sa.Column('responsable_id', sa.Integer(), sa.ForeignKey('user.id'), nullable=True),
        sa.Column('evidencia_original', sa.Text(), nullable=False),
        sa.Column('evidencia_tipo', sa.String(50), nullable=False),
        sa.Column('evidencia_metadata', sa.Text(), nullable=True),
        sa.Column('fecha_creacion', sa.DateTime(), nullable=False),
        sa.Column('fecha_limite_sla', sa.DateTime(), nullable=True),
        sa.Column('fecha_resolucion', sa.DateTime(), nullable=True),
        sa.Column('escalamiento_nivel', sa.Integer(), default=0),
        sa.Column('horas_invertidas', sa.Float(), default=0.0),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('created_by_id', sa.Integer(), sa.ForeignKey('user.id'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
    )

    # Índices para incidente
    op.create_index('idx_incidente_estado', 'incidente', ['estado'])
    op.create_index('idx_incidente_categoria', 'incidente', ['categoria'])
    op.create_index('idx_incidente_prioridad', 'incidente', ['prioridad'])
    op.create_index('idx_incidente_sla', 'incidente', ['fecha_limite_sla'])
    op.create_index('idx_incidente_responsable', 'incidente', ['responsable_id'])
    op.create_index('idx_incidente_user', 'incidente', ['user_id'])
    op.create_index('idx_incidente_appointment', 'incidente', ['appointment_id'])
    op.create_index('idx_incidente_created', 'incidente', ['created_at'])

    # Tabla de historial de incidentes
    op.create_table(
        'incidente_historial',
        sa.Column('id_historial', sa.Integer(), primary_key=True),
        sa.Column(
            'incidente_id',
            sa.Integer(),
            sa.ForeignKey('incidente.id_incidente', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column('estado_anterior', sa.String(50), nullable=True),
        sa.Column('estado_nuevo', sa.String(50), nullable=False),
        sa.Column('comentario', sa.Text(), nullable=True),
        sa.Column('changed_by_id', sa.Integer(), sa.ForeignKey('user.id'), nullable=False),
        sa.Column('changed_at', sa.DateTime(), nullable=False),
        sa.Column('escalamiento_nivel', sa.Integer(), nullable=True),
        sa.Column('responsable_anterior_id', sa.Integer(), nullable=True),
        sa.Column('responsable_nuevo_id', sa.Integer(), nullable=True),
    )

    op.create_index('idx_historial_incidente', 'incidente_historial', ['incidente_id'])
    op.create_index('idx_historial_changed', 'incidente_historial', ['changed_at'])

    # Tabla de comentarios de incidentes
    op.create_table(
        'incidente_comentario',
        sa.Column('id_comentario', sa.Integer(), primary_key=True),
        sa.Column(
            'incidente_id',
            sa.Integer(),
            sa.ForeignKey('incidente.id_incidente', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column('autor_id', sa.Integer(), sa.ForeignKey('user.id'), nullable=False),
        sa.Column('contenido', sa.Text(), nullable=False),
        sa.Column('es_interno', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True),
    )

    op.create_index('idx_comentario_incidente', 'incidente_comentario', ['incidente_id'])


def downgrade():
    op.drop_table('incidente_comentario')
    op.drop_table('incidente_historial')
    op.drop_table('incidente')
