"""Post-Mortem Service — generates structured incident reports after resolution.

Called when an incident transitions to RESUELTO or CERRADO.
"""

import logging

from app.extensions import db
from app.models.incidente import IncidenteHistorial

logger = logging.getLogger(__name__)


class PostMortemService:
    """Generates post-mortem reports for resolved incidents."""

    @staticmethod
    def generate_post_mortem(incidente):
        """Generate a structured post-mortem for a resolved incident.

        Returns the post-mortem text.
        """
        if not incidente.fecha_resolucion or not incidente.fecha_creacion:
            return None

        duration_hours = (incidente.fecha_resolucion - incidente.fecha_creacion).total_seconds() / 3600

        # Count state transitions
        transitions = (
            IncidenteHistorial.query.filter_by(incidente_id=incidente.id_incidente)
            .order_by(IncidenteHistorial.changed_at)
            .all()
        )

        transition_count = len(transitions)
        escalations = sum(1 for t in transitions if t.escalamiento_nivel and t.escalamiento_nivel > 0)

        # Build post-mortem
        lines = [
            f'=== POST-MORTEM: Incidente #{incidente.id_incidente} ===',
            f'Titulo: {incidente.titulo}',
            f' Categoria: {incidente.categoria}',
            f' Prioridad: {incidente.prioridad} (Impacto: {incidente.impacto} x Urgencia: {incidente.urgencia})',
            '',
            '--- TIMELINE ---',
            f'Creacion: {incidente.fecha_creacion.isoformat() if incidente.fecha_creacion else "N/A"}',
            f'Resolucion: {incidente.fecha_resolucion.isoformat() if incidente.fecha_resolucion else "N/A"}',
            f'Duracion total: {round(duration_hours, 1)}h',
            f'Transiciones de estado: {transition_count}',
            f'Escalamientos: {escalations}',
            '',
            '--- RESUMEN ---',
        ]

        if incidente.post_mortem:
            lines.append(f'Post-mortem: {incidente.post_mortem}')

        if incidente.causa_raiz:
            lines.append(f'Causa raiz: {incidente.causa_raiz}')

        if incidente.lecciones_aprendidas:
            lines.append(f'Lecciones aprendidas: {incidente.lecciones_aprendidas}')

        if incidente.esta_vencido:
            lines.append('NOTA: Este incidente supero su SLA.')

        lines.append('')
        lines.append('--- HISTORIAL ---')
        for t in transitions:
            changed_by = t.changed_by.username if t.changed_by else 'Sistema'
            lines.append(
                f'  [{t.changed_at.strftime("%Y-%m-%d %H:%M") if t.changed_at else "N/A"}] '
                f'{t.estado_anterior or "?"} -> {t.estado_nuevo} '
                f'(por {changed_by})' + (f' | {t.comentario}' if t.comentario else '')
            )

        return '\n'.join(lines)

    @staticmethod
    def auto_generate_on_close(incidente):
        """Auto-generate post-mortem when incident is closed."""
        if incidente.post_mortem:
            return  # Already has post-mortem

        post_mortem = PostMortemService.generate_post_mortem(incidente)
        if post_mortem:
            incidente.post_mortem = post_mortem
            db.session.commit()
            logger.info(f'Auto-generated post-mortem for incident #{incidente.id_incidente}')

        return post_mortem


post_mortem_service = PostMortemService()
