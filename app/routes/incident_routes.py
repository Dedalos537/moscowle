from datetime import UTC, datetime, timedelta

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from app.extensions import db
from app.models.incidente import (
    Incidente,
    IncidenteComentario,
    IncidenteHistorial,
)
from app.services.incident_escalation_service import IncidentEscalationService

incident_bp = Blueprint('incident_bp', __name__, url_prefix='/api/incidents')

# Categorías y prioridades válidas
CATEGORIAS_VALIDAS = {'HARDWARE', 'SOFTWARE', 'RED', 'ACCESOS', 'OPERACIONES'}
ESTADOS_VALIDOS = {'NUEVO', 'EN_CURSO', 'PENDIENTE_PROVEEDOR', 'RESUELTO', 'CERRADO'}
EVIDENCIAS_VALIDAS = {'CHAT', 'SESSION_LOG', 'EVALUATION', 'MANUAL', 'SYSTEM_ALERT'}


@incident_bp.route('/dashboard', methods=['GET'])
@login_required
def get_dashboard():
    """KPIs del dashboard de incidencias."""
    ahora = datetime.now(UTC)

    nuevos_hoy = Incidente.query.filter(
        Incidente.estado == 'NUEVO',
        Incidente.created_at > ahora.replace(hour=0, minute=0, second=0),
        Incidente.is_active,
    ).count()

    vencidos = Incidente.query.filter(
        Incidente.estado.notin_(['CERRADO', 'RESUELTO']),
        Incidente.fecha_limite_sla < ahora,
        Incidente.is_active,
    ).count()

    resueltos_semana = Incidente.query.filter(
        Incidente.estado == 'RESUELTO',
        Incidente.fecha_resolucion > ahora - timedelta(days=7),
        Incidente.is_active,
    ).count()

    # % SLA cumplido
    total_resueltos = Incidente.query.filter(
        Incidente.estado.in_(['RESUELTO', 'CERRADO']),
        Incidente.fecha_resolucion.isnot(None),
        Incidente.is_active,
    ).count()

    dentro_sla = Incidente.query.filter(
        Incidente.estado.in_(['RESUELTO', 'CERRADO']),
        Incidente.fecha_resolucion.isnot(None),
        Incidente.fecha_resolucion <= Incidente.fecha_limite_sla,
        Incidente.is_active,
    ).count()

    sla_cumplido_pct = (dentro_sla / total_resueltos * 100) if total_resueltos > 0 else 0

    # Distribución por categoría
    distribucion = (
        db.session.query(
            Incidente.categoria,
            db.func.count(Incidente.id_incidente).label('total'),
        )
        .filter(Incidente.is_active)
        .group_by(Incidente.categoria)
        .all()
    )

    return jsonify(
        {
            'timestamp': ahora.isoformat(),
            'kpis': {
                'nuevos_hoy': nuevos_hoy,
                'vencidos': vencidos,
                'resueltos_semana': resueltos_semana,
                'sla_cumplido_pct': round(sla_cumplido_pct, 2),
            },
            'distribucion_categoria': {cat: total for cat, total in distribucion},
        }
    )


@incident_bp.route('', methods=['GET'])
@login_required
def list_incidents():
    """Lista incidentes con filtros."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    estado = request.args.get('estado')
    categoria = request.args.get('categoria')
    prioridad = request.args.get('prioridad', type=int)

    query = Incidente.query.filter(Incidente.is_active)

    if estado:
        query = query.filter(Incidente.estado == estado)
    if categoria:
        query = query.filter(Incidente.categoria == categoria)
    if prioridad:
        query = query.filter(Incidente.prioridad == prioridad)

    query = query.order_by(Incidente.created_at.desc())
    paginacion = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify(
        {
            'incidentes': [
                {
                    'id_incidente': inc.id_incidente,
                    'titulo': inc.titulo,
                    'categoria': inc.categoria,
                    'prioridad': inc.prioridad,
                    'estado': inc.estado,
                    'fecha_creacion': inc.fecha_creacion.isoformat(),
                    'fecha_limite_sla': (inc.fecha_limite_sla.isoformat() if inc.fecha_limite_sla else None),
                    'responsable_id': inc.responsable_id,
                    'escalamiento_nivel': inc.escalamiento_nivel,
                }
                for inc in paginacion.items
            ],
            'total': paginacion.total,
            'pages': paginacion.pages,
            'current_page': page,
        }
    )


@incident_bp.route('/<int:id_incidente>', methods=['GET'])
@login_required
def get_incident(id_incidente):
    """Obtiene un incidente por ID."""
    incidente = Incidente.query.get_or_404(id_incidente)

    historial = [
        {
            'id': h.id_historial,
            'estado_anterior': h.estado_anterior,
            'estado_nuevo': h.estado_nuevo,
            'comentario': h.comentario,
            'changed_at': h.changed_at.isoformat(),
        }
        for h in IncidenteHistorial.query.filter_by(incidente_id=id_incidente)
        .order_by(IncidenteHistorial.changed_at.desc())
        .all()
    ]

    comentarios = [
        {
            'id': c.id_comentario,
            'contenido': c.contenido,
            'autor_id': c.autor_id,
            'es_interno': c.es_interno,
            'created_at': c.created_at.isoformat(),
        }
        for c in IncidenteComentario.query.filter_by(incidente_id=id_incidente, is_active=True)
        .order_by(IncidenteComentario.created_at.desc())
        .all()
    ]

    return jsonify(
        {
            'id_incidente': incidente.id_incidente,
            'titulo': incidente.titulo,
            'descripcion': incidente.descripcion,
            'categoria': incidente.categoria,
            'subcategoria': incidente.subcategoria,
            'prioridad': incidente.prioridad,
            'estado': incidente.estado,
            'user_id': incidente.user_id,
            'appointment_id': incidente.appointment_id,
            'responsable_id': incidente.responsable_id,
            'evidencia_tipo': incidente.evidencia_tipo,
            'evidencia_original': incidente.evidencia_original,
            'fecha_creacion': incidente.fecha_creacion.isoformat(),
            'fecha_limite_sla': (incidente.fecha_limite_sla.isoformat() if incidente.fecha_limite_sla else None),
            'fecha_resolucion': (incidente.fecha_resolucion.isoformat() if incidente.fecha_resolucion else None),
            'escalamiento_nivel': incidente.escalamiento_nivel,
            'historial': historial,
            'comentarios': comentarios,
        }
    )


@incident_bp.route('', methods=['POST'])
@login_required
def create_incident():
    """Crea un incidente manualmente."""
    data = request.get_json()

    if not data.get('titulo') or not data.get('descripcion'):
        return jsonify({'error': 'título y descripción son requeridos'}), 400

    categoria = data.get('categoria', 'OPERACIONES')
    if categoria not in CATEGORIAS_VALIDAS:
        return jsonify({'error': f'Categoría inválida. Válidas: {CATEGORIAS_VALIDAS}'}), 400

    prioridad = data.get('prioridad', 3)
    if prioridad not in (1, 2, 3, 4):
        return jsonify({'error': 'Prioridad debe ser 1, 2, 3 o 4'}), 400

    ahora = datetime.now(UTC)
    fecha_limite = IncidentEscalationService.calculate_sla_deadline(
        categoria=categoria, prioridad=prioridad, fecha_creacion=ahora
    )

    incidente = Incidente(
        titulo=data['titulo'],
        descripcion=data['descripcion'],
        categoria=categoria,
        subcategoria=data.get('subcategoria'),
        prioridad=prioridad,
        estado='NUEVO',
        user_id=current_user.id,
        appointment_id=data.get('appointment_id'),
        evidencia_tipo=data.get('evidencia_tipo', 'MANUAL'),
        evidencia_original=data.get('evidencia_original', data['descripcion']),
        fecha_creacion=ahora,
        fecha_limite_sla=fecha_limite,
        created_by_id=current_user.id,
    )

    db.session.add(incidente)
    db.session.commit()

    return jsonify(
        {
            'id_incidente': incidente.id_incidente,
            'titulo': incidente.titulo,
            'estado': incidente.estado,
            'fecha_limite_sla': fecha_limite.isoformat(),
        }
    ), 201


@incident_bp.route('/<int:id_incidente>/status', methods=['PUT'])
@login_required
def update_status(id_incidente):
    """Cambia el estado de un incidente."""
    incidente = Incidente.query.get_or_404(id_incidente)
    data = request.get_json()

    nuevo_estado = data.get('estado')
    if nuevo_estado not in ESTADOS_VALIDOS:
        return jsonify({'error': f'Estado inválido. Válidos: {ESTADOS_VALIDOS}'}), 400

    estado_anterior = incidente.estado

    incidente.estado = nuevo_estado
    incidente.updated_at = datetime.now(UTC)

    if nuevo_estado == 'RESUELTO':
        incidente.fecha_resolucion = datetime.now(UTC)

    historial = IncidenteHistorial(
        incidente_id=id_incidente,
        estado_anterior=estado_anterior,
        estado_nuevo=nuevo_estado,
        comentario=data.get('comentario'),
        changed_by_id=current_user.id,
    )
    db.session.add(historial)
    db.session.commit()

    return jsonify(
        {
            'id_incidente': incidente.id_incidente,
            'estado_anterior': estado_anterior,
            'estado_nuevo': nuevo_estado,
        }
    )


@incident_bp.route('/<int:id_incidente>/assign', methods=['PUT'])
@login_required
def assign_incident(id_incidente):
    """Reasigna un incidente a otro responsable."""
    incidente = Incidente.query.get_or_404(id_incidente)
    data = request.get_json()

    responsable_anterior = incidente.responsable_id
    incidente.responsable_id = data.get('responsable_id')
    incidente.updated_at = datetime.now(UTC)

    historial = IncidenteHistorial(
        incidente_id=id_incidente,
        estado_anterior=incidente.estado,
        estado_nuevo=incidente.estado,
        comentario=data.get('comentario', 'Reasignación manual'),
        changed_by_id=current_user.id,
        responsable_anterior_id=responsable_anterior,
        responsable_nuevo_id=data.get('responsable_id'),
    )
    db.session.add(historial)
    db.session.commit()

    return jsonify(
        {
            'id_incidente': incidente.id_incidente,
            'responsable_anterior': responsable_anterior,
            'responsable_nuevo': incidente.responsable_id,
        }
    )


@incident_bp.route('/<int:id_incidente>/comments', methods=['POST'])
@login_required
def add_comment(id_incidente):
    """Agrega un comentario a un incidente."""
    Incidente.query.get_or_404(id_incidente)
    data = request.get_json()

    if not data.get('contenido'):
        return jsonify({'error': 'contenido es requerido'}), 400

    comentario = IncidenteComentario(
        incidente_id=id_incidente,
        autor_id=current_user.id,
        contenido=data['contenido'],
        es_interno=data.get('es_interno', False),
    )

    db.session.add(comentario)
    db.session.commit()

    return jsonify(
        {
            'id_comentario': comentario.id_comentario,
            'contenido': comentario.contenido,
            'created_at': comentario.created_at.isoformat(),
        }
    ), 201


@incident_bp.route('/check-escalations', methods=['POST'])
@login_required
def check_escalations():
    """Ejecuta verificación de escalamientos (manual o via cron)."""
    if current_user.role != 'admin':
        return jsonify({'error': 'Solo administradores pueden ejecutar escalamientos'}), 403

    resultados = IncidentEscalationService.check_escalations()

    return jsonify(
        {
            'escalados': len(resultados),
            'detalles': resultados,
        }
    )
