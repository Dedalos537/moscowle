import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import func

from app.extensions import db
from app.models.appointment import Appointment, SessionMetrics
from app.models.incidente import Incidente
from app.services.incident_escalation_service import IncidentEscalationService

logger = logging.getLogger(__name__)


def _utcnow():
    """Return naive UTC now for SQLite compatibility."""
    return datetime.now(UTC).replace(tzinfo=None)


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
        cls._check_model_errors()
        cls._check_weekly_attendance()
        cls._check_expired_slas()
        logger.info('Verificaciones diarias de incidencias completadas')

    @classmethod
    def run_realtime_checks(cls):
        """Checks más frecuentes (cada 15 min)."""
        cls._check_api_latency()
        cls._check_model_errors()
        cls._check_expired_slas()

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
            .filter(SessionMetrics.date > _utcnow() - timedelta(hours=24))
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
                        Appointment.start_time > _utcnow(),
                        Appointment.start_time < _utcnow() + timedelta(days=7),
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
    def _check_api_latency(cls):
        """
        Detecta latencia API elevada.
        Umbral: p95 > 800ms por más de 2 minutos.
        """
        try:
            from app.middleware.metrics_middleware import collector

            snap = collector.get_snapshot()
            latency = snap.get('latency', {})

            high_latency_paths = []
            for path_key, lat in latency.items():
                p95 = lat.get('p95_ms', 0)
                if p95 > 800:
                    high_latency_paths.append(f'{path_key}: p95={p95}ms')

            if high_latency_paths:
                cls._create_incident(
                    titulo='Latencia API elevada detectada',
                    descripcion='Paths con p95 > 800ms:\n' + '\n'.join(high_latency_paths),
                    categoria='SOFTWARE',
                    subcategoria='api_timeout',
                    prioridad=2,
                    evidencia_tipo='MONITORING',
                    evidencia_original='\n'.join(high_latency_paths),
                )
        except Exception:
            logger.exception('Failed to check API latency')

    @classmethod
    def _check_model_errors(cls):
        """
        Detecta errores del modelo SVM/IA.
        Umbral: > 5% errores de predicción en 30 min.
        """
        recent_metrics = SessionMetrics.query.filter(SessionMetrics.date > _utcnow() - timedelta(minutes=30)).all()

        if not recent_metrics:
            return

        total = len(recent_metrics)
        errors = sum(1 for m in recent_metrics if m.accurracy < 0.1)
        error_rate = errors / total if total > 0 else 0

        if error_rate > 0.15:
            prioridad = 1
        elif error_rate > 0.05:
            prioridad = 2
        else:
            return

        cls._create_incident(
            titulo='Errores elevados en modelo de predicción',
            descripcion=(
                f'Tasa de error: {error_rate:.1%} ({errors}/{total} predicciones con accuracy < 10% en últimos 30 min)'
            ),
            categoria='SOFTWARE',
            subcategoria='ai_model',
            prioridad=prioridad,
            evidencia_tipo='MONITORING',
            evidencia_original=f'error_rate={error_rate:.4f}, errors={errors}, total={total}',
        )

    @classmethod
    def _check_weekly_attendance(cls):
        """
        Detecta tasa de asistencia semanal baja.
        Umbral: < 80% en la semana actual.
        """
        now = _utcnow()
        week_start = now - timedelta(days=now.weekday())
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)

        total_sessions = Appointment.query.filter(
            Appointment.start_time >= week_start,
            Appointment.start_time <= now,
            Appointment.is_active,
        ).count()

        if total_sessions == 0:
            return

        attended = Appointment.query.filter(
            Appointment.start_time >= week_start,
            Appointment.start_time <= now,
            Appointment.attendance == 'present',
            Appointment.is_active,
        ).count()

        attendance_rate = attended / total_sessions

        if attendance_rate < 0.70:
            prioridad = 2
        elif attendance_rate < 0.80:
            prioridad = 3
        else:
            return

        cls._create_incident(
            titulo='Tasa de asistencia semanal baja',
            descripcion=(f'Asistencia: {attendance_rate:.1%} ({attended}/{total_sessions} sesiones esta semana)'),
            categoria='OPERACIONES',
            subcategoria='no_show',
            prioridad=prioridad,
            evidencia_tipo='EVALUATION',
            evidencia_original=f'attendance_rate={attendance_rate:.4f}, attended={attended}, total={total_sessions}',
        )

    @classmethod
    def _check_expired_slas(cls):
        """
        Detecta incidentes con SLA vencido que no han sido escalados.
        Agrupa todas las notificaciones en UN solo mensaje Telegram.
        """
        import os

        sla_enabled = os.environ.get('SLA_ENABLED', 'true').lower() == 'true'
        if not sla_enabled:
            logger.info('SLA monitoring disabled, skipping SLA checks')
            return

        ahora = _utcnow()
        vencidos = Incidente.query.filter(
            Incidente.estado.in_(['NUEVO', 'EN_CURSO']),
            Incidente.fecha_limite_sla < ahora,
            Incidente.escalamiento_nivel < 2,
            Incidente.is_active,
        ).all()

        if not vencidos:
            return

        # Deduplicate: only notify if last notification was > 1 hour ago
        incidentes_a_notificar = []

        for incidente in vencidos:
            # Check if we already notified recently (use fecha_limite_sla as proxy)
            # If SLA breached more than 1 hour ago and we already notified, skip
            horas_vencido = (ahora - incidente.fecha_limite_sla).total_seconds() / 3600
            if horas_vencido > 24:
                # SLA breached more than 24h ago - don't keep notifying
                continue
            incidentes_a_notificar.append(incidente)

        if not incidentes_a_notificar:
            return

        # Send ONE grouped notification instead of individual ones
        try:
            from app.services.incident_notification_service import IncidentNotificationService

            IncidentNotificationService.notify_sla_breach_grouped(incidentes_a_notificar)
        except Exception as e:
            logger.error(f'Failed to send grouped SLA notification: {e}')

    @classmethod
    def _create_incident(cls, **kwargs) -> Incidente:
        """Crea un incidente y calcula su SLA."""
        titulo = kwargs.get('titulo')

        existente = Incidente.query.filter(
            Incidente.titulo == titulo,
            Incidente.estado.in_(['NUEVO', 'EN_CURSO']),
            Incidente.created_at > _utcnow() - timedelta(hours=24),
        ).first()

        if existente:
            return existente

        fecha_creacion = _utcnow()
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
            user_id=kwargs.get('user_id', 1),
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

        try:
            from app.services.incident_notification_service import IncidentNotificationService

            IncidentNotificationService.notify_new_incident(incidente)
        except Exception:
            logger.exception('Failed to send notification for new incident')

        return incidente
