import logging
from datetime import UTC, datetime, timedelta

from app.extensions import db
from app.models.incidente import Incidente, IncidenteHistorial

logger = logging.getLogger(__name__)


def _utcnow():
    """Return naive UTC now for SQLite compatibility."""
    return datetime.now(UTC).replace(tzinfo=None)


class IncidentEscalationService:
    """
    Servicio de escalamiento automático de incidencias.
    Evalúa periódicamente si los tickets han superado su SLA.
    """

    # Configuración de SLA por categoría y prioridad (en horas)
    SLA_HOURS = {
        'HARDWARE': {1: 4, 2: 8, 3: 24, 4: 72},
        'SOFTWARE': {1: 2, 2: 4, 3: 12, 4: 48},
        'RED': {1: 1, 2: 4, 3: 8, 4: 24},
        'ACCESOS': {1: 2, 2: 8, 3: 24, 4: 72},
        'OPERACIONES': {1: 4, 2: 12, 3: 48, 4: 96},
    }

    MAX_ESCALAMIENTO = 2

    @classmethod
    def calculate_sla_deadline(cls, categoria: str, prioridad: int, fecha_creacion: datetime) -> datetime:
        """Calcula la fecha límite del SLA."""
        horas = cls.SLA_HOURS.get(categoria, {}).get(prioridad, 48)
        return fecha_creacion + timedelta(hours=horas)

    @classmethod
    def check_escalations(cls) -> list[dict]:
        """
        Evalúa todos los incidentes activos y ejecuta escalamientos necesarios.
        Debe ejecutarse cada 15 minutos via cron/worker.
        """
        ahora = _utcnow()
        incidentes_escalados = []

        incidentes_criticos = Incidente.query.filter(
            Incidente.estado.in_(['NUEVO', 'EN_CURSO']),
            Incidente.prioridad <= 2,
            Incidente.fecha_limite_sla < ahora,
            Incidente.escalamiento_nivel < cls.MAX_ESCALAMIENTO,
            Incidente.is_active,
        ).all()

        for incidente in incidentes_criticos:
            resultado = cls._escalate_incident(incidente)
            if resultado:
                incidentes_escalados.append(resultado)

        return incidentes_escalados

    @classmethod
    def _escalate_incident(cls, incidente: Incidente) -> dict | None:
        """Escala un incidente específico."""
        ahora = _utcnow()
        horas_transcurridas = (ahora - incidente.fecha_creacion).total_seconds() / 3600

        horas_sla = cls.SLA_HOURS.get(incidente.categoria, {}).get(incidente.prioridad, 48)

        if horas_transcurridas <= horas_sla:
            return None

        nuevo_responsable = cls._get_escalation_target(incidente)

        estado_anterior = incidente.estado
        responsable_anterior = incidente.responsable_id

        incidente.estado = 'PENDIENTE_PROVEEDOR'
        incidente.responsable_id = nuevo_responsable.id if nuevo_responsable else None
        incidente.escalamiento_nivel += 1
        incidente.updated_at = ahora

        cls._log_escalation(
            incidente=incidente,
            estado_anterior=estado_anterior,
            responsable_anterior_id=responsable_anterior,
            horas_transcurridas=horas_transcurridas,
        )

        db.session.commit()

        logger.info(
            'Incidente #%s escalado a nivel %s (%.1fh > SLA %sh)',
            incidente.id_incidente,
            incidente.escalamiento_nivel,
            horas_transcurridas,
            horas_sla,
        )

        return {
            'id_incidente': incidente.id_incidente,
            'titulo': incidente.titulo,
            'categoria': incidente.categoria,
            'prioridad': incidente.prioridad,
            'escalamiento_nivel': incidente.escalamiento_nivel,
            'horas_transcurridas': round(horas_transcurridas, 1),
            'nuevo_responsable': (nuevo_responsable.email if nuevo_responsable else None),
        }

    @classmethod
    def _get_escalation_target(cls, incidente: Incidente):
        """Determina el responsable según la categoría y nivel de escalamiento."""
        from app.models.user import User

        escalation_map = {
            'HARDWARE': ['admin'],
            'SOFTWARE': ['admin'],
            'RED': ['admin'],
            'ACCESOS': ['admin'],
            'OPERACIONES': ['terapeuta', 'admin'],
        }

        target_roles = escalation_map.get(incidente.categoria, ['admin'])

        for role in target_roles:
            user = User.query.filter(User.role == role, User.is_active).first()
            if user:
                return user

        return None

    @classmethod
    def _log_escalation(
        cls,
        incidente: Incidente,
        estado_anterior: str,
        responsable_anterior_id: int | None,
        horas_transcurridas: float,
    ):
        """Registra el escalamiento en el historial."""
        historial = IncidenteHistorial(
            incidente_id=incidente.id_incidente,
            estado_anterior=estado_anterior,
            estado_nuevo=incidente.estado,
            comentario=f'Escalamiento automático: {round(horas_transcurridas, 1)}h > SLA',
            changed_by_id=None,
            escalamiento_nivel=incidente.escalamiento_nivel,
            responsable_anterior_id=responsable_anterior_id,
            responsable_nuevo_id=incidente.responsable_id,
        )
        db.session.add(historial)
