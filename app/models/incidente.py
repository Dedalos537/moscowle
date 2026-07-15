from datetime import UTC, datetime

from app.extensions import db
from app.models.base import AuditMixin, SoftDeleteMixin


def _utcnow():
    """Return naive UTC now for SQLite compatibility, aware for MySQL."""
    return datetime.now(UTC).replace(tzinfo=None)


class Incidente(db.Model, AuditMixin, SoftDeleteMixin):
    """Modelo principal de incidencias del sistema.

    ITIL Priority Matrix (Impact x Urgency):
    ==========================================
    Impact\\Urgency  | 1 (Baja) | 2 (Media) | 3 (Alta)
    -------------------------------------------------
    1 (Bajo)         |    1     |     2     |    3
    2 (Medio)        |    2     |     4     |    6
    3 (Alto)         |    3     |     6     |    9

    Priority Levels:
      1-2 = P4 (Baja)  — Resolucion en 72h
      3-4 = P3 (Media) — Resolucion en 24h
      6   = P2 (Alta)  — Resolucion en 8h
      9   = P1 (Critica) — Resolucion en 4h

    State Machine (ITIL-aligned):
      NUEVO -> EN_CURSO | PENDIENTE_PROVEEDOR | RESUELTO
      EN_CURSO -> PENDIENTE_PROVEEDOR | RESUELTO
      PENDIENTE_PROVEEDOR -> EN_CURSO | RESUELTO
      RESUELTO -> CERRADO
    """

    __tablename__ = 'incidente'

    id_incidente = db.Column(db.Integer, primary_key=True)

    # Información básica
    titulo = db.Column(db.String(200), nullable=False)
    descripcion = db.Column(db.Text, nullable=False)

    # Relaciones con entidades existentes
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointment.id'), nullable=True, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    reports_to_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, index=True)

    # Clasificación ITIL (Impacto x Urgencia = Prioridad)
    categoria = db.Column(db.String(50), nullable=False, index=True)
    subcategoria = db.Column(db.String(100), nullable=True)
    impacto = db.Column(db.Integer, default=2, nullable=False)  # 1=Bajo, 2=Medio, 3=Alto
    urgencia = db.Column(db.Integer, default=2, nullable=False)  # 1=Baja, 2=Media, 3=Alta
    prioridad = db.Column(db.Integer, default=4, nullable=False, index=True)  # impacto * urgencia (1-9)

    # Post-mortem
    post_mortem = db.Column(db.Text, nullable=True)
    causa_raiz = db.Column(db.Text, nullable=True)
    lecciones_aprendidas = db.Column(db.Text, nullable=True)

    # Estado y flujo de vida
    estado = db.Column(db.String(50), default='NUEVO', nullable=False, index=True)
    responsable_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, index=True)

    # Evidencia y trazabilidad
    evidencia_original = db.Column(db.Text, nullable=False)
    evidencia_tipo = db.Column(db.String(50), nullable=False)
    evidencia_metadata = db.Column(db.Text, nullable=True)  # JSON como Text

    # SLA y escalamiento
    fecha_creacion = db.Column(db.DateTime, default=_utcnow, nullable=False)
    fecha_limite_sla = db.Column(db.DateTime, nullable=True, index=True)
    fecha_resolucion = db.Column(db.DateTime, nullable=True)
    escalamiento_nivel = db.Column(db.Integer, default=0)
    horas_invertidas = db.Column(db.Float, default=0.0)

    # Auditoría adicional
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    # Relaciones
    appointment = db.relationship('Appointment', backref=db.backref('incidentes', lazy=True))
    user = db.relationship('User', foreign_keys=[user_id], backref=db.backref('incidentes_creados', lazy=True))
    responsable = db.relationship(
        'User', foreign_keys=[responsable_id], backref=db.backref('incidentes_asignados', lazy=True)
    )
    reports_to = db.relationship(
        'User', foreign_keys=[reports_to_id], backref=db.backref('incidentes_reportados', lazy=True)
    )

    def __repr__(self):
        return f'<Incidente #{self.id_incidente}: {self.titulo}>'

    @property
    def horas_restantes_sla(self):
        """Calcula las horas restantes antes de vencer el SLA."""
        if not self.fecha_limite_sla:
            return None
        ahora = datetime.now(UTC).replace(tzinfo=None)
        delta = self.fecha_limite_sla - ahora
        return delta.total_seconds() / 3600

    @property
    def esta_vencido(self):
        """Verifica si el incidente ha superado su SLA."""
        if not self.fecha_limite_sla:
            return False
        return datetime.now(UTC).replace(tzinfo=None) > self.fecha_limite_sla


class IncidenteHistorial(db.Model):
    """Historial de transiciones de estado de incidentes."""

    __tablename__ = 'incidente_historial'

    id_historial = db.Column(db.Integer, primary_key=True)
    incidente_id = db.Column(
        db.Integer, db.ForeignKey('incidente.id_incidente', ondelete='CASCADE'), nullable=False, index=True
    )

    estado_anterior = db.Column(db.String(50), nullable=True)
    estado_nuevo = db.Column(db.String(50), nullable=False)
    comentario = db.Column(db.Text, nullable=True)

    changed_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    changed_at = db.Column(db.DateTime, default=_utcnow, nullable=False, index=True)

    # Datos de escalamiento
    escalamiento_nivel = db.Column(db.Integer, nullable=True)
    responsable_anterior_id = db.Column(db.Integer, nullable=True)
    responsable_nuevo_id = db.Column(db.Integer, nullable=True)

    # Relaciones
    incidente = db.relationship('Incidente', backref=db.backref('historial', lazy=True, cascade='all, delete-orphan'))
    changed_by = db.relationship(
        'User', foreign_keys=[changed_by_id], backref=db.backref('incidentes_cambios', lazy=True)
    )


class IncidenteComentario(db.Model):
    """Comentarios en incidencias."""

    __tablename__ = 'incidente_comentario'

    id_comentario = db.Column(db.Integer, primary_key=True)
    incidente_id = db.Column(
        db.Integer, db.ForeignKey('incidente.id_incidente', ondelete='CASCADE'), nullable=False, index=True
    )
    autor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    contenido = db.Column(db.Text, nullable=False)
    es_interno = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), nullable=False)
    is_active = db.Column(db.Boolean, default=True)

    # Relaciones
    incidente = db.relationship('Incidente', backref=db.backref('comentarios', lazy=True, cascade='all, delete-orphan'))
    autor = db.relationship('User', foreign_keys=[autor_id], backref=db.backref('incidentes_comentarios', lazy=True))
