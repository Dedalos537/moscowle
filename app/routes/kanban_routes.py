import base64
import contextlib
import logging
from datetime import UTC, datetime

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.extensions import db
from app.models import KanbanAttachment, KanbanTask, User

kanban_bp = Blueprint('kanban', __name__, url_prefix='/api/kanban')

logger = logging.getLogger('app.kanban')

ALLOWED_COLUMNS = ('todo', 'in-progress', 'review', 'done')
ALLOWED_PRIORITIES = (1, 2, 3)
MAX_ATTACHMENT_BYTES = 20 * 1024 * 1024  # 20 MB
PRIORITY_FILTER_MAP = {
    'urgent': 1,
    'high': 1,
    'media': 2,
    'medium': 2,
    'low': 3,
    'baja': 3,
}


def _now():
    return datetime.now(UTC).replace(tzinfo=None)


def _safe_ts(dt):
    return dt.isoformat() if dt else None


def _user_name(user_id):
    if not user_id:
        return None
    user = db.session.get(User, user_id)
    return user.username if user else None


def _task_dict(task):
    now = _now()
    expired = False
    if task.timer_start and task.max_minutes and task.max_minutes > 0:
        elapsed_s = (now - task.timer_start).total_seconds()
        expired = elapsed_s > task.max_minutes * 60
    return {
        'id': task.id,
        'title': task.title,
        'description': task.description,
        'therapy_type': task.therapy_type,
        'session_id': task.session_id,
        'max_minutes': task.max_minutes,
        'column': task.column,
        'position': task.position,
        'timer_start': _safe_ts(task.timer_start),
        'is_expired': bool(task.is_expired) or expired,
        'priority': task.priority,
        'assigned_to_id': task.assigned_to_id,
        'assigned_to_name': _user_name(task.assigned_to_id),
        'created_by_id': task.created_by_id,
        'created_by_name': _user_name(task.created_by_id),
        'sede_id': task.sede_id,
        'sede_name': task.sede_item.name if task.sede_item else None,
        'is_active': task.is_active,
        'attachment_count': task.attachment_count,
        'created_at': _safe_ts(task.created_at),
        'updated_at': _safe_ts(task.updated_at),
    }


def _attachment_dict(att, include_data=False):
    d = {
        'id': att.id,
        'filename': att.filename,
        'mimetype': att.mimetype,
        'size': att.size,
        'task_id': att.task_id,
        'created_at': _safe_ts(att.created_at),
    }
    if include_data:
        if att.data_b64:
            d['data'] = att.data_b64
        elif att.data:
            d['data'] = 'data:{};base64,{}'.format(
                att.mimetype or 'application/octet-stream', base64.b64encode(att.data).decode('ascii')
            )
    return d


def _require_staff():
    identity = get_jwt_identity()
    user = db.session.get(User, int(identity)) if identity else None
    if not user or not user.is_active:
        return None, (jsonify({'success': False, 'message': 'Usuario no encontrado'}), 401)
    if user.role not in ('admin', 'supervisor', 'terapista', 'terapeuta'):
        return None, (jsonify({'success': False, 'message': 'Acceso denegado'}), 403)
    return user, None


def _get_task_or_404(task_id):
    task = db.session.get(KanbanTask, task_id)
    if not task:
        return None, (jsonify({'success': False, 'message': 'Tarea no encontrada'}), 404)
    return task, None


@kanban_bp.route('/tasks', methods=['GET'])
@jwt_required()
def list_tasks():
    try:
        filters = {}
        q = KanbanTask.query.filter_by(is_active=True)
        therapy_type = request.args.get('therapy_type')
        if therapy_type:
            q = q.filter_by(therapy_type=therapy_type)
        prio_raw = request.args.get('priority')
        if prio_raw:
            try:
                filters['priority'] = int(prio_raw)
            except (TypeError, ValueError):
                filters['priority'] = PRIORITY_FILTER_MAP.get(prio_raw)
            if filters['priority']:
                q = q.filter_by(priority=filters['priority'])
        assigned_to = request.args.get('assigned_to')
        if assigned_to and str(assigned_to).isdigit():
            q = q.filter_by(assigned_to_id=int(assigned_to))
        tasks = q.order_by(KanbanTask.column.asc(), KanbanTask.position.asc()).all()
        return jsonify([_task_dict(t) for t in tasks])
    except Exception as e:
        logger.error(f'Error listing kanban tasks: {e}', exc_info=True)
        return jsonify({'success': False, 'message': 'Error al cargar tareas', 'error': str(e)}), 500


@kanban_bp.route('/tasks', methods=['POST'])
@jwt_required()
def create_task():
    user, err = _require_staff()
    if err:
        return err
    try:
        data = request.get_json(silent=True) or {}
        title = (data.get('title') or '').strip()
        if not title:
            return jsonify({'success': False, 'message': 'El título es obligatorio'}), 400
        column = data.get('column') or 'todo'
        if column not in ALLOWED_COLUMNS:
            column = 'todo'
        priority = data.get('priority', 3)
        try:
            priority = int(priority)
        except (TypeError, ValueError):
            priority = 3
        if priority not in ALLOWED_PRIORITIES:
            priority = 3
        max_minutes = data.get('max_minutes', 0) or 0
        try:
            max_minutes = max(0, int(max_minutes))
        except (TypeError, ValueError):
            max_minutes = 0
        last_pos = (
            db.session.query(db.func.max(KanbanTask.position))
            .filter(KanbanTask.column == column, KanbanTask.is_active == True)  # noqa: E712
            .scalar()
        )
        position = (last_pos or 0) + 1
        sede_id = data.get('sede_id')
        try:
            sede_id = int(sede_id) if sede_id not in (None, '') else None
        except (TypeError, ValueError):
            sede_id = None
        assigned_to_id = data.get('assigned_to_id')
        try:
            assigned_to_id = int(assigned_to_id) if assigned_to_id not in (None, '') else None
        except (TypeError, ValueError):
            assigned_to_id = None
        session_id = data.get('session_id')
        try:
            session_id = int(session_id) if session_id not in (None, '') else None
        except (TypeError, ValueError):
            session_id = None
        task = KanbanTask(
            title=title,
            description=data.get('description') or None,
            therapy_type=data.get('therapy_type') or None,
            session_id=session_id,
            max_minutes=max_minutes,
            column=column,
            position=position,
            priority=priority,
            assigned_to_id=assigned_to_id,
            sede_id=sede_id,
            created_by_id=user.id,
            timer_start=None,
            is_expired=False,
            created_at=_now(),
            updated_at=_now(),
        )
        db.session.add(task)
        db.session.commit()
        return jsonify(_task_dict(task)), 201
    except Exception as e:
        db.session.rollback()
        logger.error(f'Error creating kanban task: {e}', exc_info=True)
        return jsonify({'success': False, 'message': 'Error al crear la tarea', 'error': str(e)}), 500


@kanban_bp.route('/tasks/<int:task_id>', methods=['PATCH'])
@jwt_required()
def update_task(task_id):
    user, err = _require_staff()
    if err:
        return err
    task, err = _get_task_or_404(task_id)
    if err:
        return err
    try:
        data = request.get_json(silent=True) or {}
        editable = {
            'title': lambda v: (v or '').strip() or None,
            'therapy_type': lambda v: v or None,
            'max_minutes': lambda v: max(0, int(v)) if str(v).isdigit() else task.max_minutes,
            'priority': lambda v: int(v) if int(v) in ALLOWED_PRIORITIES else task.priority,
            'position': lambda v: max(0, int(v)) if str(v).lstrip('-').isdigit() else task.position,
            'session_id': lambda v: int(v) if str(v).isdigit() else None,
            'assigned_to_id': lambda v: int(v) if str(v).isdigit() else None,
            'sede_id': lambda v: int(v) if str(v).isdigit() else None,
            'is_active': bool,
        }
        for key, coerce in editable.items():
            if key in data:
                with contextlib.suppress(TypeError, ValueError):
                    setattr(task, key, coerce(data[key]))
        if 'description' in data:
            task.description = data['description']
        if 'title' in data and (data['title'] or '').strip():
            task.title = (data['title'] or '').strip()
        if 'column' in data and data['column'] in ALLOWED_COLUMNS:
            task.column = data['column']
        if task.column == 'in-progress' and not task.timer_start:
            task.timer_start = _now()
            task.is_expired = False
        if task.column == 'done':
            task.is_expired = False
        task.updated_at = _now()
        db.session.commit()
        return jsonify(_task_dict(task))
    except Exception as e:
        db.session.rollback()
        logger.error(f'Error updating kanban task {task_id}: {e}', exc_info=True)
        return jsonify({'success': False, 'message': 'Error al actualizar la tarea', 'error': str(e)}), 500


@kanban_bp.route('/tasks/<int:task_id>', methods=['DELETE'])
@jwt_required()
def delete_task(task_id):
    user, err = _require_staff()
    if err:
        return err
    task, err = _get_task_or_404(task_id)
    if err:
        return err
    try:
        db.session.delete(task)
        db.session.commit()
        return jsonify({'success': True, 'deleted_id': task_id})
    except Exception as e:
        db.session.rollback()
        logger.error(f'Error deleting kanban task {task_id}: {e}', exc_info=True)
        return jsonify({'success': False, 'message': 'Error al eliminar la tarea', 'error': str(e)}), 500


@kanban_bp.route('/tasks/<int:task_id>/extend', methods=['PATCH'])
@jwt_required()
def extend_timer(task_id):
    user, err = _require_staff()
    if err:
        return err
    task, err = _get_task_or_404(task_id)
    if err:
        return err
    try:
        data = request.get_json(silent=True) or {}
        minutes = int(data.get('minutes', 0))
        if minutes <= 0:
            return jsonify({'success': False, 'message': 'minutes debe ser mayor a 0'}), 400
        if not task.timer_start:
            task.timer_start = _now()
        task.max_minutes = (task.max_minutes or 0) + minutes
        task.is_expired = False
        task.updated_at = _now()
        db.session.commit()
        return jsonify(_task_dict(task))
    except Exception as e:
        db.session.rollback()
        logger.error(f'Error extending kanban timer {task_id}: {e}', exc_info=True)
        return jsonify({'success': False, 'message': 'Error al extender el tiempo', 'error': str(e)}), 500


@kanban_bp.route('/tasks/<int:task_id>/attachments', methods=['GET'])
@jwt_required()
def list_attachments(task_id):
    task, err = _get_task_or_404(task_id)
    if err:
        return err
    return jsonify([_attachment_dict(a) for a in task.attachments])


@kanban_bp.route('/tasks/<int:task_id>/attachments', methods=['POST'])
@jwt_required()
def upload_attachment(task_id):
    user, err = _require_staff()
    if err:
        return err
    task, err = _get_task_or_404(task_id)
    if err:
        return err
    try:
        data = request.get_json(silent=True) or {}
        filename = (data.get('filename') or '').strip()
        if not filename:
            return jsonify({'success': False, 'message': 'filename requerido'}), 400
        raw = data.get('data')
        if not raw:
            return jsonify({'success': False, 'message': 'data requerido'}), 400
        if isinstance(raw, str) and ',' in raw and raw.strip().lower().startswith('data:'):
            header, _, b64body = raw.partition(',')
            payload = b64body
            mime = header[5:].split(';')[0].strip().lower() or data.get('mimetype')
        else:
            payload = raw
            mime = data.get('mimetype') or 'application/octet-stream'
        try:
            payload_bytes = base64.b64decode(payload, validate=False)
        except Exception:
            return jsonify({'success': False, 'message': 'data base64 inválido'}), 400
        if len(payload_bytes) > MAX_ATTACHMENT_BYTES:
            return jsonify({'success': False, 'message': 'Archivo demasiado grande (máx. 20MB)'}), 413
        att = KanbanAttachment(
            task_id=task.id,
            filename=filename[:255],
            mimetype=(mime or 'application/octet-stream')[:120],
            size=len(payload_bytes),
            data=payload_bytes,
            data_b64='data:{};base64,{}'.format(mime or 'application/octet-stream', payload),
            created_at=_now(),
        )
        db.session.add(att)
        db.session.commit()
        return jsonify(_attachment_dict(att, include_data=False)), 201
    except Exception as e:
        db.session.rollback()
        logger.error(f'Error uploading kanban attachment for task {task_id}: {e}', exc_info=True)
        return jsonify({'success': False, 'message': 'Error al subir el archivo', 'error': str(e)}), 500


@kanban_bp.route('/tasks/<int:task_id>/attachments', methods=['DELETE'])
@jwt_required()
def delete_attachment(task_id):
    user, err = _require_staff()
    if err:
        return err
    task, err = _get_task_or_404(task_id)
    if err:
        return err
    try:
        attachment_id = request.args.get('attachmentId')
        if not attachment_id:
            return jsonify({'success': False, 'message': 'attachmentId requerido'}), 400
        att = db.session.get(KanbanAttachment, int(attachment_id))
        if not att or att.task_id != task.id:
            return jsonify({'success': False, 'message': 'Adjunto no encontrado'}), 404
        db.session.delete(att)
        db.session.commit()
        return jsonify({'success': True, 'deleted_id': int(attachment_id)})
    except Exception as e:
        db.session.rollback()
        logger.error(f'Error deleting kanban attachment {task_id}: {e}', exc_info=True)
        return jsonify({'success': False, 'message': 'Error al eliminar el archivo', 'error': str(e)}), 500


@kanban_bp.route('/attachments/<int:att_id>', methods=['GET'])
@jwt_required()
def get_attachment(att_id):
    att = db.session.get(KanbanAttachment, att_id)
    if not att:
        return jsonify({'success': False, 'message': 'Adjunto no encontrado'}), 404
    return jsonify(_attachment_dict(att, include_data=True))


@kanban_bp.route('/stats', methods=['GET'])
@jwt_required()
def get_stats():
    try:
        tasks = KanbanTask.query.filter_by(is_active=True).all()
        by_column = {'todo': 0, 'in-progress': 0, 'review': 0, 'done': 0}
        expired = 0
        unassigned = 0
        for t in tasks:
            by_column[t.column] = by_column.get(t.column, 0) + 1
            if t.is_expired or (
                t.timer_start and t.max_minutes and (_now() - t.timer_start).total_seconds() > t.max_minutes * 60
            ):
                expired += 1
            if not t.assigned_to_id:
                unassigned += 1
        return jsonify({'total': len(tasks), 'by_column': by_column, 'expired': expired, 'unassigned': unassigned})
    except Exception as e:
        logger.error(f'Error computing kanban stats: {e}', exc_info=True)
        return jsonify({'success': False, 'message': 'Error al calcular estadísticas', 'error': str(e)}), 500
