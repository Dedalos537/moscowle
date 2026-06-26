import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import func

from app.extensions import db
from app.models.appointment import Appointment, SessionMetrics
from app.models.incidente import Incidente
from app.services.incident_escalation_service import IncidentEscalationService

logger = logging.getLogger(__name__)


class IncidentDetectionService:
    """
    Servicio de detección automática de incidencias.
    Analiza datos del sistema y genera tickets cuando detecta problemas.
    """

    @classmethod
    def run_daily_checks(cls):
        """Ejecuta todas las verificaciones de detección."""
        logger.info('Iniciando verificaciones diarias de incidencias')
        cls._check_low_compliance_sessions()
        cls._check_scheduling_gaps()
        logger.info('Verificaciones diarias de incidencias completadas')

    @classmethod
    def _check_low_compliance_sessions(cls):
        """
        Detecta sesiones con menos del 50% de cumplimiento.
        Umbral: accuracy promedio < 0.5 en las últimas 24h.
        """
        umbral_cumplimiento = 0.5

        sesiones_bajas = (
            db.session.query(
                SessionMetrics.session_id,
                func.avg(SessionMetrics.accurracy).label('avg_accuracy'),
                func.count(SessionMetrics.id).label('total_metrics'),
            )
            .filter(SessionMetrics.date > datetime.now(UTC) - timedelta(hours=24))
            .group_by(SessionMetrics.session_id)
            .having(func.avg(SessionMetrics.accurracy) < umbral_cumplimiento)
            .all()
        )

        for sesion in sesiones_bajas:
            if sesion.session_id is None:
                continue

            appointment = Appointment.query.get(sesion.session_id)
            if not appointment:
                continue

            titulo = f'Sesión #{sesion.session_id} con bajo cumplimiento'
            descripcion = f'Accuracy promedio: {sesion.avg_accuracy:.1%}. Total métricas: {sesion.total_metrics}'

            cls._create_incident(
                titulo=titulo,
                descripcion=descripcion,
                categoria='OPERACIONES',
                subcategoria='session_compliance',
                prioridad=3,
                appointment_id=sesion.session_id,
                user_id=appointment.patient_id,
                evidencia_tipo='EVALUATION',
                evidencia_original=f'Accuracy: {sesion.avg_accuracy:.1%}, Métricas: {sesion.total_metrics}',
            )

    @classmethod
    def _check_scheduling_gaps(cls):
        """
        Detecta ausencia de programación (pacientes sin citas próximas).
        Pacientes activos sin citas en los próximos 7 días.
        """
        from app.models.user import User

        pacientes_sin_citas = (
            User.query.filter(
                User.role == 'jugador',
                User.is_active,
                ~User.id.in_(
                    db.session.query(Appointment.patient_id).filter(
                        Appointment.start_time > datetime.now(UTC),
                        Appointment.start_time < datetime.now(UTC) + timedelta(days=7),
                    )
                ),
            )
            .limit(50)
            .all()
        )

        for paciente in pacientes_sin_citas:
            titulo = f'Paciente {paciente.username} sin programación'
            descripcion = 'Paciente activo sin citas programadas en los próximos 7 días'

            cls._create_incident(
                titulo=titulo,
                descripcion=descripcion,
                categoria='OPERACIONES',
                subcategoria='scheduling',
                prioridad=3,
                user_id=paciente.id,
                evidencia_tipo='SYSTEM_ALERT',
                evidencia_original=f'Paciente ID: {paciente.id}',
            )

    @classmethod
    def _create_incident(cls, **kwargs) -> Incidente:
        """Crea un incidente y calcula su SLA."""
        titulo = kwargs.get('titulo')

        existente = Incidente.query.filter(
            Incidente.titulo == titulo,
            Incidente.estado.in_(['NUEVO', 'EN_CURSO']),
            Incidente.created_at > datetime.now(UTC) - timedelta(hours=24),
        ).first()

        if existente:
            return existente

        fecha_creacion = datetime.now(UTC)
        fecha_limite = IncidentEscalationService.calculate_sla_deadline(
            categoria=kwargs.get('categoria'),
            prioridad=kwargs.get('prioridad', 3),
            fecha_creacion=fecha_creacion,
        )

        incidente = Incidente(
            titulo=titulo,
            descripcion=kwargs.get('descripcion'),
            categoria=kwargs.get('categoria'),
            subcategoria=kwargs.get('subcategoria'),
            prioridad=kwargs.get('prioridad', 3),
            estado='NUEVO',
            user_id=kwargs.get('user_id'),
            appointment_id=kwargs.get('appointment_id'),
            evidencia_tipo=kwargs.get('evidencia_tipo'),
            evidencia_original=kwargs.get('evidencia_original'),
            fecha_creacion=fecha_creacion,
            fecha_limite_sla=fecha_limite,
        )

        db.session.add(incidente)
        db.session.commit()

        logger.info(
            'Incidente #%s creado: %s (SLA: %s)',
            incidente.id_incidente,
            incidente.titulo,
            fecha_limite.isoformat(),
        )

        return incidente
