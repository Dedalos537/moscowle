"""
Endpoints API para el servidor MCP.
Autenticación por API key (no requiere login de usuario).
"""

import hmac
import os

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
