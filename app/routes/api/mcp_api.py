"""
Endpoints API para el servidor MCP.
Autenticación por API key (no requiere login de usuario).
"""

import hmac
import os
from datetime import datetime, timedelta

from app.routes.api import api_bp
from app.routes.api._shared import (
    User,
    db,
    json,
    jsonify,
    request,
)

# API Key para MCP (generar con: python -c "import secrets; print(secrets.token_hex(32))")
MCP_API_KEY = os.getenv(
    'MCP_API_KEY',
    'moscowle_mcp_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0',
)


def verify_api_key():
    """Verificar API key del request."""
    auth_header = request.headers.get('Authorization', '')
    api_key = request.headers.get('X-API-Key', '')

    # Accept either "Bearer <key>" or direct X-API-Key header
    if auth_header.startswith('Bearer '):
        api_key = auth_header[7:]

    if not api_key:
        return False

    return hmac.compare_digest(api_key, MCP_API_KEY)


def require_api_key(f):
    """Decorador para verificar API key."""

    def decorated(*args, **kwargs):
        if not verify_api_key():
            return jsonify({'error': 'API key inválida'}), 401
        return f(*args, **kwargs)

    decorated.__name__ = f.__name__
    return decorated


# ============================================================
# MCP API Endpoints
# ============================================================


@api_bp.route('/mcp/pacientes', methods=['GET'])
@require_api_key
def mcp_listar_pacientes():
    """Listar pacientes activos."""
    therapist_id = request.args.get('therapist_id', type=int)

    query = User.query.filter_by(role='jugador', is_active=True)

    if therapist_id:
        query = query.filter_by(assigned_therapist_id=therapist_id)

    pacientes = query.order_by(User.username.asc()).all()

    return jsonify(
        [
            {
                'id': p.id,
                'username': p.username,
                'email': p.email,
                'payment_plan': p.payment_plan,
                'sessions_total': p.sessions_total,
                'sessions_attended': p.sessions_attended,
                'sessions_remaining': p.sessions_remaining,
                'assigned_therapist_id': p.assigned_therapist_id,
                'date_of_birth': p.date_of_birth.isoformat() if p.date_of_birth else None,
                'guardian_name': p.guardian_name,
                'therapy_goals': p.therapy_goals,
            }
            for p in pacientes
        ]
    )


@api_bp.route('/mcp/paciente/<int:patient_id>', methods=['GET'])
@require_api_key
def mcp_obtener_paciente(patient_id):
    """Obtener detalle completo de un paciente."""
    paciente = User.query.get(patient_id)
    if not paciente or paciente.role != 'jugador':
        return jsonify({'error': 'Paciente no encontrado'}), 404

    # Parsear game_profile
    game_profile = None
    if paciente.game_profile:
        import contextlib

        with contextlib.suppress(json.JSONDecodeError, TypeError):
            game_profile = json.loads(paciente.game_profile)

    # Métricas recientes
    from app.models.appointment import SessionMetrics

    metricas = SessionMetrics.query.filter_by(user_id=patient_id).order_by(SessionMetrics.date.desc()).limit(20).all()

    return jsonify(
        {
            'id': paciente.id,
            'username': paciente.username,
            'email': paciente.email,
            'phone': paciente.phone,
            'date_of_birth': paciente.date_of_birth.isoformat() if paciente.date_of_birth else None,
            'guardian_name': paciente.guardian_name,
            'guardian_contact': paciente.guardian_contact,
            'therapy_goals': paciente.therapy_goals,
            'notes': paciente.notes,
            'game_profile': game_profile,
            'payment_plan': paciente.payment_plan,
            'payment_due_date': paciente.payment_due_date.isoformat() if paciente.payment_due_date else None,
            'payment_amount': paciente.payment_amount,
            'sessions_total': paciente.sessions_total,
            'sessions_attended': paciente.sessions_attended,
            'sessions_remaining': paciente.sessions_remaining,
            'assigned_therapist_id': paciente.assigned_therapist_id,
            'therapist_name': paciente.assigned_therapist.username if paciente.assigned_therapist else None,
            'metricas_recientes': [
                {
                    'game_name': m.game_name,
                    'accurracy': m.accurracy,
                    'avg_time': m.avg_time,
                    'prediction': m.prediction,
                    'date': m.date.isoformat() if m.date else None,
                }
                for m in metricas
            ],
        }
    )


@api_bp.route('/mcp/sesiones', methods=['GET'])
@require_api_key
def mcp_listar_sesiones():
    """Listar sesiones con filtros."""
    from app.models.appointment import Appointment

    patient_id = request.args.get('patient_id', type=int)
    therapist_id = request.args.get('therapist_id', type=int)
    estado = request.args.get('estado')
    dias = request.args.get('dias', 30, type=int)

    from datetime import datetime, timedelta

    cutoff = datetime.utcnow() - timedelta(days=dias)

    query = Appointment.query.filter(Appointment.start_time >= cutoff)

    if patient_id:
        query = query.filter_by(patient_id=patient_id)
    if therapist_id:
        query = query.filter_by(therapist_id=therapist_id)
    if estado:
        query = query.filter_by(status=estado)

    sesiones = query.order_by(Appointment.start_time.desc()).limit(100).all()

    return jsonify(
        [
            {
                'id': s.id,
                'title': s.title,
                'start_time': s.start_time.isoformat() if s.start_time else None,
                'end_time': s.end_time.isoformat() if s.end_time else None,
                'status': s.status,
                'attendance': s.attendance,
                'patient_id': s.patient_id,
                'patient_name': s.patient.username if s.patient else None,
                'therapist_id': s.therapist_id,
                'therapist_name': s.therapist.username if s.therapist else None,
                'location': s.location,
                'notes': s.notes,
            }
            for s in sesiones
        ]
    )


@api_bp.route('/mcp/metricas/<int:patient_id>', methods=['GET'])
@require_api_key
def mcp_obtener_metricas(patient_id):
    """Obtener métricas de un paciente."""
    from app.models.appointment import SessionMetrics

    juego = request.args.get('juego')

    query = SessionMetrics.query.filter_by(user_id=patient_id)

    if juego:
        query = query.filter_by(game_name=juego)

    metricas = query.order_by(SessionMetrics.date.desc()).limit(100).all()

    if metricas:
        avg_acc = sum(m.accurracy for m in metricas) / len(metricas)
        avg_time = sum(m.avg_time for m in metricas) / len(metricas)
        resumen = {
            'total_registros': len(metricas),
            'precision_promedio': round(avg_acc, 2),
            'tiempo_promedio_seg': round(avg_time, 2),
            'juegos_disponibles': list(set(m.game_name for m in metricas)),
        }
    else:
        resumen = {'total_registros': 0}

    return jsonify(
        {
            'resumen': resumen,
            'metricas': [
                {
                    'game_name': m.game_name,
                    'accurracy': m.accurracy,
                    'avg_time': m.avg_time,
                    'prediction': m.prediction,
                    'date': m.date.isoformat() if m.date else None,
                }
                for m in metricas
            ],
        }
    )


@api_bp.route('/mcp/estadisticas', methods=['GET'])
@require_api_key
def mcp_estadisticas():
    """Estadísticas generales del sistema."""
    from app.models.appointment import Appointment, SessionMetrics
    from app.models.game import Game

    usuarios = db.session.query(User.role, db.func.count(User.id)).filter_by(is_active=True).group_by(User.role).all()

    sesiones_estado = (
        db.session.query(Appointment.status, db.func.count(Appointment.id))
        .filter_by(is_active=True)
        .group_by(Appointment.status)
        .all()
    )

    total_metricas = SessionMetrics.query.count()
    total_juegos = Game.query.filter_by(is_active=True).count()

    return jsonify(
        {
            'usuarios_por_rol': {role: count for role, count in usuarios},
            'sesiones_por_estado': {status: count for status, count in sesiones_estado},
            'total_metricas': total_metricas,
            'juegos_activos': total_juegos,
        }
    )


@api_bp.route('/mcp/juegos', methods=['GET'])
@require_api_key
def mcp_listar_juegos():
    """Listar juegos terapéuticos."""
    from app.models.game import Game

    juegos = Game.query.filter_by(is_active=True).order_by(Game.title).all()

    return jsonify(
        [
            {
                'id': j.id,
                'title': j.title,
                'filename': j.filename,
                'description': j.description,
            }
            for j in juegos
        ]
    )


# ============================================================
# MCP API - Incidencias
# ============================================================


@api_bp.route('/mcp/incidencias', methods=['GET'])
@require_api_key
def mcp_listar_incidencias():
    """Listar incidencias con filtros (MCP)."""
    from app.models.incidente import Incidente

    estado = request.args.get('estado')
    prioridad = request.args.get('prioridad', type=int)
    categoria = request.args.get('categoria')
    limite = request.args.get('limite', 20, type=int)

    query = Incidente.query.filter(Incidente.is_active)

    if estado:
        query = query.filter(Incidente.estado == estado)
    if prioridad:
        query = query.filter(Incidente.prioridad == prioridad)
    if categoria:
        query = query.filter(Incidente.categoria == categoria)

    incidentes = query.order_by(Incidente.created_at.desc()).limit(limite).all()

    return jsonify(
        [
            {
                'id': i.id_incidente,
                'titulo': i.titulo,
                'categoria': i.categoria,
                'subcategoria': i.subcategoria,
                'prioridad': i.prioridad,
                'estado': i.estado,
                'responsable': i.responsable.username if i.responsable else None,
                'fecha_creacion': i.fecha_creacion.isoformat() if i.fecha_creacion else None,
                'fecha_limite_sla': i.fecha_limite_sla.isoformat() if i.fecha_limite_sla else None,
                'escalamiento_nivel': i.escalamiento_nivel,
                'esta_vencido': i.esta_vencido,
            }
            for i in incidentes
        ]
    )


@api_bp.route('/mcp/incidente/<int:incident_id>', methods=['GET'])
@require_api_key
def mcp_obtener_incidencia(incident_id):
    """Obtener detalle de una incidencia (MCP)."""
    from app.models.incidente import Incidente

    incidente = Incidente.query.filter_by(id_incidente=incident_id, is_active=True).first()

    if not incidente:
        return jsonify({'error': 'Incidente no encontrado'}), 404

    return jsonify(
        {
            'id': incidente.id_incidente,
            'titulo': incidente.titulo,
            'descripcion': incidente.descripcion,
            'categoria': incidente.categoria,
            'subcategoria': incidente.subcategoria,
            'prioridad': incidente.prioridad,
            'estado': incidente.estado,
            'responsable': incidente.responsable.username if incidente.responsable else None,
            'creado_por': incidente.user.username if incidente.user else None,
            'fecha_creacion': incidente.fecha_creacion.isoformat() if incidente.fecha_creacion else None,
            'fecha_limite_sla': incidente.fecha_limite_sla.isoformat() if incidente.fecha_limite_sla else None,
            'fecha_resolucion': incidente.fecha_resolucion.isoformat() if incidente.fecha_resolucion else None,
            'escalamiento_nivel': incidente.escalamiento_nivel,
            'horas_invertidas': incidente.horas_invertidas,
            'esta_vencido': incidente.esta_vencido,
            'historial': [
                {
                    'estado_anterior': h.estado_anterior,
                    'estado_nuevo': h.estado_nuevo,
                    'comentario': h.comentario,
                    'changed_by': h.changed_by.username if h.changed_by else None,
                    'changed_at': h.changed_at.isoformat() if h.changed_at else None,
                }
                for h in sorted(incidente.historial, key=lambda x: x.changed_at or '', reverse=True)
            ],
        }
    )


@api_bp.route('/mcp/incidencias/estadisticas', methods=['GET'])
@require_api_key
def mcp_estadisticas_incidencias():
    """KPIs del sistema de incidencias (MCP)."""
    from app.models.incidente import Incidente

    ahora = datetime.utcnow()

    total_abiertos = Incidente.query.filter(
        Incidente.estado.in_(['NUEVO', 'EN_CURSO', 'PENDIENTE_PROVEEDOR']),
        Incidente.is_active,
    ).count()

    vencidos = Incidente.query.filter(
        Incidente.estado.in_(['NUEVO', 'EN_CURSO', 'PENDIENTE_PROVEEDOR']),
        Incidente.fecha_limite_sla < ahora,
        Incidente.is_active,
    ).count()

    por_categoria = dict(
        db.session.query(Incidente.categoria, db.func.count(Incidente.id_incidente))
        .filter(
            Incidente.is_active,
            Incidente.estado.in_(['NUEVO', 'EN_CURSO', 'PENDIENTE_PROVEEDOR']),
        )
        .group_by(Incidente.categoria)
        .all()
    )

    total_7d = Incidente.query.filter(
        Incidente.created_at >= ahora - timedelta(days=7),
        Incidente.is_active,
    ).count()
    resueltos_7d = Incidente.query.filter(
        Incidente.estado.in_(['RESUELTO', 'CERRADO']),
        Incidente.fecha_resolucion >= ahora - timedelta(days=7),
        Incidente.is_active,
    ).count()

    sla_compliance = round(resueltos_7d / total_7d * 100, 1) if total_7d > 0 else 100.0

    return jsonify(
        {
            'total_abiertos': total_abiertos,
            'vencidos': vencidos,
            'sla_compliance_7d': sla_compliance,
            'por_categoria': por_categoria,
        }
    )


@api_bp.route('/mcp/incidencias/tendencia', methods=['GET'])
@require_api_key
def mcp_tendencia_incidencias():
    """Análisis de tendencia de incidencias (MCP)."""
    from app.models.incidente import Incidente

    dias = request.args.get('dias', 30, type=int)
    desde = datetime.utcnow() - timedelta(days=dias)

    por_dia = (
        db.session.query(
            db.func.date(Incidente.created_at).label('dia'),
            db.func.count(Incidente.id_incidente).label('total'),
        )
        .filter(Incidente.created_at >= desde, Incidente.is_active)
        .group_by(db.func.date(Incidente.created_at))
        .order_by(db.func.date(Incidente.created_at))
        .all()
    )

    por_categoria = dict(
        db.session.query(Incidente.categoria, db.func.count(Incidente.id_incidente))
        .filter(Incidente.created_at >= desde, Incidente.is_active)
        .group_by(Incidente.categoria)
        .all()
    )

    repetidos = (
        db.session.query(Incidente.titulo, db.func.count(Incidente.id_incidente).label('cnt'))
        .filter(Incidente.created_at >= desde, Incidente.is_active)
        .group_by(Incidente.titulo)
        .having(db.func.count(Incidente.id_incidente) > 1)
        .order_by(db.desc('cnt'))
        .limit(10)
        .all()
    )

    return jsonify(
        {
            'periodo_dias': dias,
            'por_dia': [{'dia': str(p.dia), 'total': p.total} for p in por_dia],
            'por_categoria': por_categoria,
            'patrones_recurrentes': [{'titulo': r.titulo, 'veces': r.cnt} for r in repetidos],
        }
    )
