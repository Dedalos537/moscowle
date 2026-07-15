from datetime import UTC, datetime, timedelta

from flask import jsonify, request

from app.auth_compat import current_user, login_required
from app.extensions import db
from app.models.incidente import Incidente, IncidenteComentario, IncidenteHistorial
from app.routes.api import api_bp
from app.schemas.incident_schema import (
    validate_incident_assign,
    validate_incident_comment,
    validate_incident_create,
    validate_incident_status,
)
from app.services.incident_escalation_service import IncidentEscalationService
from app.services.incident_notification_service import IncidentNotificationService


def _utcnow():
    """Return naive UTC now for SQLite compatibility."""
    return datetime.now(UTC).replace(tzinfo=None)


def _serialize_incident(incidente, detail=False):
    data = {
        'id': incidente.id_incidente,
        'titulo': incidente.titulo,
        'descripcion': incidente.descripcion,
        'categoria': incidente.categoria,
        'subcategoria': incidente.subcategoria,
        'prioridad': incidente.prioridad,
        'estado': incidente.estado,
        'responsable_id': incidente.responsable_id,
        'responsable_name': incidente.responsable.username if incidente.responsable else None,
        'user_id': incidente.user_id,
        'user_name': incidente.user.username if incidente.user else None,
        'appointment_id': incidente.appointment_id,
        'evidencia_tipo': incidente.evidencia_tipo,
        'fecha_creacion': incidente.fecha_creacion.isoformat() if incidente.fecha_creacion else None,
        'fecha_limite_sla': incidente.fecha_limite_sla.isoformat() if incidente.fecha_limite_sla else None,
        'fecha_resolucion': incidente.fecha_resolucion.isoformat() if incidente.fecha_resolucion else None,
        'escalamiento_nivel': incidente.escalamiento_nivel,
        'horas_invertidas': incidente.horas_invertidas,
        'esta_vencido': incidente.esta_vencido,
        'horas_restantes_sla': round(incidente.horas_restantes_sla, 1)
        if incidente.horas_restantes_sla is not None
        else None,
    }

    if detail:
        data['evidencia_original'] = incidente.evidencia_original
        data['evidencia_metadata'] = incidente.evidencia_metadata
        data['historial'] = [
            {
                'id': h.id_historial,
                'estado_anterior': h.estado_anterior,
                'estado_nuevo': h.estado_nuevo,
                'comentario': h.comentario,
                'changed_by': h.changed_by.username if h.changed_by else None,
                'changed_at': h.changed_at.isoformat() if h.changed_at else None,
                'escalamiento_nivel': h.escalamiento_nivel,
            }
            for h in sorted(
                incidente.historial, key=lambda x: x.changed_at or datetime.min.replace(tzinfo=UTC), reverse=True
            )
        ]
        data['comentarios'] = [
            {
                'id': c.id_comentario,
                'contenido': c.contenido,
                'es_interno': c.es_interno,
                'autor': c.autor.username if c.autor else None,
                'created_at': c.created_at.isoformat() if c.created_at else None,
            }
            for c in sorted(
                incidente.comentarios, key=lambda x: x.created_at or datetime.min.replace(tzinfo=UTC), reverse=True
            )
        ]

    return data


@api_bp.route('/incidents/dashboard', methods=['GET'])
@login_required
def incidents_dashboard():
    """KPIs en tiempo real del sistema de incidencias."""
    try:
        now = _utcnow()

        total_abiertos = Incidente.query.filter(
            Incidente.estado.in_(['NUEVO', 'EN_CURSO', 'PENDIENTE_PROVEEDOR']),
            Incidente.is_active,
        ).count()

        vencidos = Incidente.query.filter(
            Incidente.estado.in_(['NUEVO', 'EN_CURSO', 'PENDIENTE_PROVEEDOR']),
            Incidente.fecha_limite_sla < now,
            Incidente.is_active,
        ).count()

        por_estado = dict(
            db.session.query(Incidente.estado, db.func.count(Incidente.id_incidente))
            .filter(Incidente.is_active)
            .group_by(Incidente.estado)
            .all()
        )

        por_categoria = dict(
            db.session.query(Incidente.categoria, db.func.count(Incidente.id_incidente))
            .filter(
                Incidente.is_active,
                Incidente.estado.in_(['NUEVO', 'EN_CURSO', 'PENDIENTE_PROVEEDOR']),
            )
            .group_by(Incidente.categoria)
            .all()
        )

        por_prioridad = dict(
            db.session.query(Incidente.prioridad, db.func.count(Incidente.id_incidente))
            .filter(
                Incidente.is_active,
                Incidente.estado.in_(['NUEVO', 'EN_CURSO', 'PENDIENTE_PROVEEDOR']),
            )
            .group_by(Incidente.prioridad)
            .all()
        )

        resueltos_hoy = Incidente.query.filter(
            Incidente.estado.in_(['RESUELTO', 'CERRADO']),
            Incidente.fecha_resolucion >= now.replace(hour=0, minute=0, second=0, microsecond=0),
            Incidente.is_active,
        ).count()

        total_7d = Incidente.query.filter(
            Incidente.created_at >= now - timedelta(days=7),
            Incidente.is_active,
        ).count()

        resueltos_7d = Incidente.query.filter(
            Incidente.estado.in_(['RESUELTO', 'CERRADO']),
            Incidente.fecha_resolucion >= now - timedelta(days=7),
            Incidente.is_active,
        ).count()

        sla_compliance = round((resueltos_7d / total_7d * 100), 1) if total_7d > 0 else 100.0

        return jsonify(
            {
                'total_abiertos': total_abiertos,
                'vencidos': vencidos,
                'resueltos_hoy': resueltos_hoy,
                'sla_compliance_7d': sla_compliance,
                'por_estado': por_estado,
                'por_categoria': por_categoria,
                'por_prioridad': por_prioridad,
            }
        )

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/incidents', methods=['GET'])
@login_required
def list_incidents():
    """Listar incidencias con filtros y permisos por rol."""
    try:
        estado = request.args.get('estado')
        prioridad = request.args.get('prioridad', type=int)
        categoria = request.args.get('categoria')
        responsable_id = request.args.get('responsable_id', type=int)
        desde = request.args.get('desde')
        hasta = request.args.get('hasta')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)

        query = Incidente.query.filter(Incidente.is_active)

        # Role-based filtering
        if current_user.role not in ('admin', 'supervisor'):
            if current_user.role == 'terapista':
                query = query.filter(
                    db.or_(
                        Incidente.user_id == current_user.id,
                        Incidente.responsable_id == current_user.id,
                    )
                )
            elif current_user.role == 'jugador':
                query = query.filter(Incidente.user_id == current_user.id)

        if estado:
            query = query.filter(Incidente.estado == estado)
        if prioridad:
            query = query.filter(Incidente.prioridad == prioridad)
        if categoria:
            query = query.filter(Incidente.categoria == categoria)
        if responsable_id:
            query = query.filter(Incidente.responsable_id == responsable_id)
        if desde:
            try:
                desde_dt = datetime.fromisoformat(desde)
                query = query.filter(Incidente.created_at >= desde_dt)
            except ValueError:
                pass
        if hasta:
            try:
                hasta_dt = datetime.fromisoformat(hasta)
                query = query.filter(Incidente.created_at <= hasta_dt)
            except ValueError:
                pass

        query = query.order_by(Incidente.created_at.desc())
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

        return jsonify(
            {
                'incidentes': [_serialize_incident(i) for i in pagination.items],
                'total': pagination.total,
                'page': pagination.page,
                'per_page': pagination.per_page,
                'pages': pagination.pages,
            }
        )

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/incidents/<int:incident_id>', methods=['GET'])
@login_required
def get_incident(incident_id):
    """Detalle completo de un incidente con verificación de permisos."""
    try:
        incidente = Incidente.query.filter_by(id_incidente=incident_id, is_active=True).first()

        if not incidente:
            return jsonify({'error': 'Incidente no encontrado'}), 404

        # Role-based visibility
        if current_user.role not in ('admin', 'supervisor'):
            if current_user.role == 'terapista':
                if current_user.id not in {incidente.user_id, incidente.responsable_id}:
                    return jsonify({'error': 'Acceso denegado'}), 403
            elif current_user.role == 'jugador':
                if incidente.user_id != current_user.id:
                    return jsonify({'error': 'Acceso denegado'}), 403

        return jsonify(_serialize_incident(incidente, detail=True))

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/incidents', methods=['POST'])
@login_required
def create_incident():
    """Crear un incidente manualmente."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Datos requeridos'}), 400

        validated, errors = validate_incident_create(data)
        if errors:
            return jsonify({'error': 'Validación fallida', 'details': errors}), 400

        # ITIL: Auto-compute priority from impact x urgency
        impacto = validated.get('impacto')
        urgencia = validated.get('urgencia')
        if impacto is not None and urgencia is not None:
            prioridad = impacto * urgencia  # 1-9 scale
        else:
            prioridad = validated.get('prioridad', 3)

        fecha_creacion = _utcnow()
        fecha_limite = IncidentEscalationService.calculate_sla_deadline(
            categoria=validated['categoria'],
            prioridad=prioridad,
            fecha_creacion=fecha_creacion,
        )

        incidente = Incidente(
            titulo=validated['titulo'],
            descripcion=validated['descripcion'],
            categoria=validated['categoria'],
            subcategoria=validated.get('subcategoria'),
            impacto=impacto,
            urgencia=urgencia,
            prioridad=prioridad,
            estado='NUEVO',
            user_id=current_user.id,
            appointment_id=validated.get('appointment_id'),
            evidencia_tipo=validated.get('evidencia_tipo', 'MANUAL'),
            evidencia_original=validated.get('evidencia_original', ''),
            fecha_creacion=fecha_creacion,
            fecha_limite_sla=fecha_limite,
            responsable_id=current_user.id,
        )

        db.session.add(incidente)
        db.session.flush()

        historial = IncidenteHistorial(
            incidente_id=incidente.id_incidente,
            estado_anterior=None,
            estado_nuevo='NUEVO',
            comentario='Incidente creado manualmente',
            changed_by_id=current_user.id,
        )
        db.session.add(historial)
        db.session.commit()

        IncidentNotificationService.notify_new_incident(incidente)

        return jsonify(_serialize_incident(incidente, detail=True)), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@api_bp.route('/incidents/<int:incident_id>/status', methods=['PUT'])
@login_required
def update_incident_status(incident_id):
    """Cambiar estado de un incidente."""
    try:
        incidente = Incidente.query.filter_by(id_incidente=incident_id, is_active=True).first()

        if not incidente:
            return jsonify({'error': 'Incidente no encontrado'}), 404

        data = request.get_json()
        if not data:
            return jsonify({'error': 'Datos requeridos'}), 400

        validated, errors = validate_incident_status(data)
        if errors:
            return jsonify({'error': 'Validación fallida', 'details': errors}), 400

        nuevo_estado = validated['estado']
        estado_anterior = incidente.estado

        valid_transitions = {
            'NUEVO': {'EN_CURSO', 'PENDIENTE_PROVEEDOR', 'RESUELTO'},
            'EN_CURSO': {'PENDIENTE_PROVEEDOR', 'RESUELTO'},
            'PENDIENTE_PROVEEDOR': {'EN_CURSO', 'RESUELTO'},
            'RESUELTO': {'CERRADO'},
        }

        if nuevo_estado not in valid_transitions.get(estado_anterior, set()):
            return jsonify(
                {
                    'error': f'Transición inválida: {estado_anterior} -> {nuevo_estado}',
                    'transiciones_permitidas': list(valid_transitions.get(estado_anterior, set())),
                }
            ), 400

        incidente.estado = nuevo_estado
        incidente.updated_at = _utcnow()

        if nuevo_estado in ('RESUELTO', 'CERRADO'):
            incidente.fecha_resolucion = _utcnow()
            # Auto-generate post-mortem summary
            horas_total = (_utcnow() - incidente.fecha_creacion).total_seconds() / 3600
            if not incidente.post_mortem:
                incidente.post_mortem = (
                    f'Resuelto por {current_user.username} en {round(horas_total, 1)}h. '
                    f'Estado: {estado_anterior} -> {nuevo_estado}. '
                    f'Nivel de escalamiento alcanzado: {incidente.escalamiento_nivel}.'
                )

        horas = (_utcnow() - incidente.fecha_creacion).total_seconds() / 3600
        incidente.horas_invertidas = round(horas, 2)

        historial = IncidenteHistorial(
            incidente_id=incidente.id_incidente,
            estado_anterior=estado_anterior,
            estado_nuevo=nuevo_estado,
            comentario=data.get('comentario', ''),
            changed_by_id=current_user.id,
        )
        db.session.add(historial)
        db.session.commit()

        if nuevo_estado in ('RESUELTO', 'CERRADO'):
            IncidentNotificationService.notify_resolution(incidente)

        return jsonify(_serialize_incident(incidente, detail=True))

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@api_bp.route('/incidents/<int:incident_id>/comments', methods=['POST'])
@login_required
def add_incident_comment(incident_id):
    """Agregar comentario a un incidente."""
    try:
        incidente = Incidente.query.filter_by(id_incidente=incident_id, is_active=True).first()

        if not incidente:
            return jsonify({'error': 'Incidente no encontrado'}), 404

        data = request.get_json()
        if not data:
            return jsonify({'error': 'Datos requeridos'}), 400

        validated, errors = validate_incident_comment(data)
        if errors:
            return jsonify({'error': 'Validación fallida', 'details': errors}), 400

        comentario = IncidenteComentario(
            incidente_id=incidente.id_incidente,
            autor_id=current_user.id,
            contenido=validated['contenido'],
            es_interno=validated.get('es_interno', False),
        )

        db.session.add(comentario)
        db.session.commit()

        return jsonify(
            {
                'id': comentario.id_comentario,
                'contenido': comentario.contenido,
                'es_interno': comentario.es_interno,
                'autor': current_user.username,
                'created_at': comentario.created_at.isoformat() if comentario.created_at else None,
            }
        ), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@api_bp.route('/incidents/<int:incident_id>/assign', methods=['PUT'])
@login_required
def assign_incident(incident_id):
    """Reasignar responsable de un incidente."""
    try:
        if current_user.role not in ('admin', 'supervisor'):
            return jsonify({'error': 'Acceso denegado'}), 403

        incidente = Incidente.query.filter_by(id_incidente=incident_id, is_active=True).first()

        if not incidente:
            return jsonify({'error': 'Incidente no encontrado'}), 404

        data = request.get_json()
        if not data:
            return jsonify({'error': 'Datos requeridos'}), 400

        validated, errors = validate_incident_assign(data)
        if errors:
            return jsonify({'error': 'Validación fallida', 'details': errors}), 400

        from app.models.user import User

        nuevo_responsable = User.query.get(validated['responsable_id'])
        if not nuevo_responsable or not nuevo_responsable.is_active:
            return jsonify({'error': 'Responsable no encontrado o inactivo'}), 404

        responsable_anterior_id = incidente.responsable_id
        incidente.responsable_id = nuevo_responsable.id
        incidente.updated_at = _utcnow()

        historial = IncidenteHistorial(
            incidente_id=incidente.id_incidente,
            estado_anterior=incidente.estado,
            estado_nuevo=incidente.estado,
            comentario=f'Reasignado a {nuevo_responsable.username}',
            changed_by_id=current_user.id,
            responsable_anterior_id=responsable_anterior_id,
            responsable_nuevo_id=nuevo_responsable.id,
        )
        db.session.add(historial)
        db.session.commit()

        return jsonify(_serialize_incident(incidente))

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@api_bp.route('/incidents/my', methods=['GET'])
@login_required
def my_incidents():
    """Incidencias del usuario actual (con roles: terapista ve propias + asignadas, jugador ve propias)."""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)

        query = Incidente.query.filter(Incidente.is_active)

        if current_user.role == 'jugador':
            query = query.filter(Incidente.user_id == current_user.id)
        elif current_user.role == 'terapista':
            query = query.filter(
                db.or_(
                    Incidente.user_id == current_user.id,
                    Incidente.responsable_id == current_user.id,
                )
            )
        else:
            query = query.filter(
                db.or_(
                    Incidente.user_id == current_user.id,
                    Incidente.responsable_id == current_user.id,
                )
            )

        query = query.order_by(Incidente.created_at.desc())
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

        return jsonify(
            {
                'incidentes': [_serialize_incident(i) for i in pagination.items],
                'total': pagination.total,
                'page': pagination.page,
                'per_page': pagination.per_page,
                'pages': pagination.pages,
            }
        )

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/incidents/metrics', methods=['GET'])
@login_required
def incident_metrics():
    """Métricas de incidencias: tiempo promedio resolución, SLA compliance, por categoría."""
    try:
        if current_user.role not in ('admin', 'supervisor'):
            return jsonify({'error': 'Acceso denegado'}), 403

        now = _utcnow()
        thirty_days_ago = now - timedelta(days=30)

        # Average resolution time (hours)
        resueltos = Incidente.query.filter(
            Incidente.fecha_resolucion.isnot(None),
            Incidente.fecha_resolucion >= thirty_days_ago,
            Incidente.is_active,
        ).all()

        avg_resolution_hours = 0
        if resueltos:
            total_hours = sum(i.horas_invertidas or 0 for i in resueltos)
            avg_resolution_hours = round(total_hours / len(resueltos), 1)

        # SLA compliance
        total_30d = Incidente.query.filter(
            Incidente.created_at >= thirty_days_ago,
            Incidente.is_active,
        ).count()

        resueltos_en_sla = Incidente.query.filter(
            Incidente.estado.in_(['RESUELTO', 'CERRADO']),
            Incidente.fecha_resolucion.isnot(None),
            Incidente.fecha_limite_sla.isnot(None),
            Incidente.fecha_resolucion <= Incidente.fecha_limite_sla,
            Incidente.created_at >= thirty_days_ago,
            Incidente.is_active,
        ).count()

        sla_compliance = round((resueltos_en_sla / total_30d * 100), 1) if total_30d > 0 else 100.0

        # By category
        por_categoria = dict(
            db.session.query(Incidente.categoria, db.func.count(Incidente.id_incidente))
            .filter(Incidente.created_at >= thirty_days_ago, Incidente.is_active)
            .group_by(Incidente.categoria)
            .all()
        )

        # By priority
        por_prioridad = dict(
            db.session.query(Incidente.prioridad, db.func.count(Incidente.id_incidente))
            .filter(Incidente.created_at >= thirty_days_ago, Incidente.is_active)
            .group_by(Incidente.prioridad)
            .all()
        )

        # Open incidents
        abiertos = Incidente.query.filter(
            Incidente.estado.in_(['NUEVO', 'EN_CURSO', 'PENDIENTE_PROVEEDOR']),
            Incidente.is_active,
        ).count()

        return jsonify(
            {
                'avg_resolution_hours': avg_resolution_hours,
                'sla_compliance_30d': sla_compliance,
                'total_30d': total_30d,
                'abiertos': abiertos,
                'por_categoria': por_categoria,
                'por_prioridad': por_prioridad,
            }
        )

    except Exception as e:
        return jsonify({'error': str(e)}), 500
