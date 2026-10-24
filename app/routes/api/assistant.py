"""Visibilidad del asistente (botón flotante del chatbot) por tipo de usuario.

- `GET /api/assistant/visibility`: el ajuste del centro y si el usuario actual lo ve.
- `PUT /api/assistant/visibility`: solo admin. `{admin, terapista, jugador}` (el supervisor sigue al admin).

Apagado para un rol, el botón no aparece y `/mcp/chat` responde 403 para ese rol.
"""

from flask import jsonify, request

from app.auth_compat import current_user, login_required
from app.extensions import db
from app.models.system_setting import SystemSetting
from app.routes.api import api_bp

ROLES = ('admin', 'terapista', 'jugador')
# Hoy el asistente es solo del admin (PRP 009): terapeutas y pacientes se encienden desde Configuración.
DEFAULTS = {'admin': True, 'terapista': False, 'jugador': False}


def _key(role):
    return f'assistant.visible.{role}'


def visibility():
    out = {}
    for role in ROLES:
        row = db.session.get(SystemSetting, _key(role))
        out[role] = DEFAULTS[role] if row is None or row.value is None else row.value == '1'
    return out


def visible_for(role) -> bool:
    group = 'admin' if role in ('admin', 'supervisor') else role
    return bool(visibility().get(group, False))


@api_bp.route('/assistant/visibility', methods=['GET', 'PUT'])
@login_required
def assistant_visibility():
    if request.method == 'PUT':
        if current_user.role != 'admin':
            return jsonify({'success': False, 'message': 'Solo un administrador puede cambiarlo'}), 403
        data = request.get_json(silent=True) or {}
        for role in ROLES:
            if role in data:
                row = db.session.get(SystemSetting, _key(role)) or SystemSetting(key=_key(role))
                row.value = '1' if data[role] else '0'
                row.updated_by_id = current_user.id
                db.session.add(row)
        db.session.commit()
    return jsonify({'success': True, **visibility(), 'visible': visible_for(current_user.role)})


# ── Pantalla del asistente (PRP 015): admin y supervisor (este, limitado a su sede) ──────────────
def _staff_only():
    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'success': False, 'message': 'El asistente del centro es solo para administración'}), 403
    return None


def _call(fn, *args, status=200):
    from app.services.assistant_service import AssistantError

    denied = _staff_only()
    if denied:
        return denied
    try:
        return jsonify(fn(*args)), status
    except AssistantError as exc:
        return jsonify({'success': False, 'message': str(exc)}), exc.status


@api_bp.route('/assistant/home', methods=['GET'])
@login_required
def assistant_home():
    from app.services import assistant_analytics

    return _call(lambda: {'suggestions': assistant_analytics.suggestions(current_user)})


@api_bp.route('/assistant/threads', methods=['GET'])
@login_required
def assistant_threads():
    from app.services import assistant_service as svc

    return _call(lambda: {'threads': svc.list_threads(current_user, request.args.get('q'))})


@api_bp.route('/assistant/threads/<int:thread_id>', methods=['GET', 'PATCH', 'DELETE'])
@login_required
def assistant_thread(thread_id):
    from app.services import assistant_service as svc

    if request.method == 'DELETE':
        return _call(lambda: (svc.delete_thread(current_user, thread_id), {'success': True})[1])
    if request.method == 'PATCH':
        data = request.get_json(silent=True) or {}
        return _call(lambda: svc.thread_dict(svc.update_thread(current_user, thread_id, data), current_user))
    return _call(lambda: svc.thread_dict(svc.get_thread(thread_id, current_user), current_user, with_messages=True))


@api_bp.route('/assistant/ask', methods=['POST'])
@login_required
def assistant_ask():
    from app.services import assistant_service as svc

    data = request.get_json(silent=True) or {}

    def run():
        thread, answer = svc.ask(current_user, data.get('question'), data.get('thread_id'))
        return {'thread': svc.thread_dict(thread, current_user), 'message': svc.message_dict(answer)}

    return _call(run)


@api_bp.route('/assistant/ask/stream', methods=['POST'])
@login_required
def assistant_ask_stream():
    """Igual que `/assistant/ask`, pero en vivo (SSE): pasos de MiMo y herramientas MCP mientras trabaja, y al final
    la conversación y la respuesta guardadas. Un latido cada pocos segundos evita que Cloudflare corte a los 100 s
    (antes la espera larga llegaba al navegador como un error de CORS)."""
    import json
    import queue
    import threading

    from flask import Response, current_app, stream_with_context

    from app.models import User
    from app.services import assistant_service as svc

    denied = _staff_only()
    if denied:
        return denied
    data = request.get_json(silent=True) or {}
    app, user_id = current_app._get_current_object(), current_user.id
    events: queue.Queue = queue.Queue()

    def work():
        with app.app_context():
            try:
                user = db.session.get(User, user_id)
                attachment = data.get('attachment') if isinstance(data.get('attachment'), dict) else None
                thread, answer = svc.ask(
                    user,
                    data.get('question'),
                    data.get('thread_id'),
                    step=lambda text, tool=None: events.put({'type': 'step', 'text': text, 'tool': tool}),
                    model=(str(data.get('model') or '').strip() or None),
                    attachment=attachment,
                )
                events.put(
                    {'type': 'done', 'thread': svc.thread_dict(thread, user), 'message': svc.message_dict(answer, user)}
                )
            except svc.AssistantError as exc:
                events.put({'type': 'error', 'message': str(exc), 'status': exc.status})
            except Exception:  # noqa: BLE001
                app.logger.exception('assistant stream falló')
                events.put({'type': 'error', 'message': 'No pude responder ahora. Inténtalo de nuevo.'})
            finally:
                db.session.remove()

    threading.Thread(target=work, daemon=True).start()

    def generate():
        yield ': inicio\n\n'
        while True:
            try:
                ev = events.get(timeout=8)
            except queue.Empty:
                yield ': latido\n\n'
                continue
            yield f'data: {json.dumps(ev, ensure_ascii=False, default=str)}\n\n'
            if ev['type'] in ('done', 'error'):
                return

    headers = {'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'}
    return Response(stream_with_context(generate()), mimetype='text/event-stream', headers=headers)


@api_bp.route('/assistant/models', methods=['GET'])
@login_required
def assistant_models():
    """Estado de MiMo (cuota) y los modelos que se pueden elegir para responder (barra de modelo del chat)."""
    from app.services import assistant_service as svc

    return _call(lambda: svc.models_status(current_user))


@api_bp.route('/assistant/upload', methods=['POST'])
@login_required
def assistant_upload():
    """Sube una foto o documento al chat; después se manda con `ask/stream` ({attachment: {token, name}})."""
    from app.services import assistant_files

    denied = _staff_only()
    if denied:
        return denied
    file = request.files.get('file')
    if not file:
        return jsonify({'success': False, 'message': 'Falta el archivo'}), 400
    try:
        return jsonify(assistant_files.save_upload(file, current_user)), 201
    except assistant_files.FileError as exc:
        return jsonify({'success': False, 'message': str(exc)}), 400


@api_bp.route('/assistant/files', methods=['GET'])
@login_required
def assistant_file_download():
    """Descarga un archivo del Drive que generó el asistente (informes). El supervisor solo ve los informes."""
    from flask import send_file

    from app.services import drive_service as drive

    denied = _staff_only()
    if denied:
        return denied
    rel = request.args.get('path', '')
    if current_user.role != 'admin' and not rel.startswith('Informes/'):
        return jsonify({'success': False, 'message': 'Solo puedes descargar informes'}), 403
    try:
        path = drive.resolve(rel)
    except drive.DriveError as exc:
        return jsonify({'success': False, 'message': str(exc)}), exc.status
    if path.is_dir():
        return jsonify({'success': False, 'message': 'Es una carpeta'}), 400
    return send_file(path, as_attachment=True, download_name=path.name, max_age=0)


@api_bp.route('/assistant/messages/<int:message_id>/refresh', methods=['POST'])
@login_required
def assistant_refresh(message_id):
    from app.services import assistant_service as svc

    return _call(lambda: svc.message_dict(svc.refresh(current_user, message_id)))


@api_bp.route('/assistant/messages/<int:message_id>/feedback', methods=['POST'])
@login_required
def assistant_feedback(message_id):
    from app.services import assistant_service as svc

    value = int((request.get_json(silent=True) or {}).get('value') or 0)
    return _call(lambda: svc.message_dict(svc.set_feedback(current_user, message_id, value)))


@api_bp.route('/assistant/schedules', methods=['GET', 'POST'])
@login_required
def assistant_schedules():
    from app.models.assistant_thread import AssistantSchedule
    from app.services import assistant_service as svc

    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        return _call(lambda: svc.schedule_dict(svc.create_schedule(current_user, data)), status=201)
    return _call(
        lambda: {
            'schedules': [
                svc.schedule_dict(s) for s in AssistantSchedule.query.filter_by(user_id=current_user.id).all()
            ]
        }
    )


@api_bp.route('/assistant/schedules/<int:schedule_id>', methods=['DELETE'])
@login_required
def assistant_schedule_delete(schedule_id):
    from app.services import assistant_service as svc

    return _call(lambda: (svc.delete_schedule(current_user, schedule_id), {'success': True})[1])


@api_bp.route('/assistant/messages/<int:message_id>/action', methods=['POST'])
@login_required
def assistant_run_action(message_id):
    """Confirmar la acción propuesta (con los datos completados en el formulario)."""
    from app.services import assistant_service as svc

    body = request.get_json(silent=True) or {}
    args = body.get('args') or {}
    block = body.get('block') if isinstance(body.get('block'), int) else None

    def run():
        updated, reply = svc.run_action(current_user, message_id, args, block)
        return {'message': svc.message_dict(updated), 'reply': svc.message_dict(reply)}

    return _call(run)
