import tempfile

from app.routes.api import api_bp
from app.routes.api._shared import (
    Appointment,
    AvailabilityService,
    SessionImage,
    SessionMetrics,
    User,
    _parse_datetime,
    appointment_service,
    csrf,
    current_app,
    current_user,
    datetime,
    db,
    drive_service,
    json,
    jsonify,
    login_required,
    notification_service,
    os,
    request,
    secure_filename,
    timedelta,
    url_for,
    uuid,
)
from app.utils import get_user_day_utc_range, get_user_timezone, localize_datetime_for_display
from app.utils.objectives import enrich_objectives_from_audit, parse_objectives
from app.utils.sanitizer import sanitize_text


def _is_date_only_param(value):
    if not value:
        return False
    v = value.strip()
    return len(v) <= 10 and 'T' not in v and ' ' not in v


@api_bp.route('/sessions', methods=['GET'])
@login_required
def api_get_sessions():
    if current_user.role not in ('terapista', 'admin', 'supervisor'):
        return jsonify({'error': 'Acceso denegado'}), 403
    start = request.args.get('start')
    end = request.args.get('end')
    try:
        start_dt = _parse_datetime(start)
        end_dt = _parse_datetime(end)
    except Exception:
        start_dt = None
        end_dt = None
    if start_dt and end_dt:
        if _is_date_only_param(start) and _is_date_only_param(end):
            start_dt, _ = get_user_day_utc_range(current_user, start[:10])
            _, end_dt = get_user_day_utc_range(current_user, end[:10])
            q = Appointment.query.filter(
                Appointment.start_time >= start_dt,
                Appointment.start_time < end_dt,
            )
            if current_user.role == 'terapista':
                q = q.filter(Appointment.therapist_id == current_user.id)
            appts = q.order_by(Appointment.start_time.asc()).all()
        else:
            if start_dt.date() == end_dt.date():
                end_dt = end_dt + timedelta(days=1)
            if current_user.role == 'terapista':
                appts = appointment_service.get_therapist_appointments(current_user.id, start_dt, end_dt)
            else:
                appts = appointment_service.get_all_appointments(start_dt, end_dt)
    else:
        q = Appointment.query
        if current_user.role == 'terapista':
            q = q.filter(Appointment.therapist_id == current_user.id)
        appts = q.order_by(Appointment.start_time.desc()).limit(200).all()
    results = []

    def _session_color(status):
        colors = {
            'scheduled': '#3B82F6',
            'in_progress': '#75a83a',
            'completed': '#6B7280',
            'cancelled': '#EF4444',
        }
        return colors.get(status, '#9CA3AF')

    from app.models import SessionAudit

    appt_ids = [a.id for a in appts]
    audit_map = {}
    if appt_ids:
        audits = SessionAudit.query.filter(SessionAudit.appointment_id.in_(appt_ids)).all()
        audit_map = {audit.appointment_id: audit for audit in audits}

    tz_name = get_user_timezone(current_user)

    for a in appts:
        local_start = localize_datetime_for_display(a.start_time, tz_name)
        local_end = localize_datetime_for_display(a.end_time, tz_name)
        start_iso = local_start.isoformat() if local_start else None
        end_iso = local_end.isoformat() if local_end else None
        try:
            games_list = json.loads(a.games) if a.games else []
        except (json.JSONDecodeError, TypeError):
            games_list = []
        audit = audit_map.get(a.id)
        audit_score = audit.audit_score if audit and audit.audit_score is not None else None
        has_transcript = bool(audit and audit.transcript_text)
        has_program = bool(audit and audit.planned_text)
        feedback_notes = (audit.feedback_notes or '').strip() if audit else ''
        results.append(
            {
                'id': a.id,
                'title': a.title or (a.patient.username if a.patient else 'Sesión'),
                'start': start_iso,
                'end': end_iso,
                'backgroundColor': _session_color(a.status),
                'borderColor': _session_color(a.status),
                'extendedProps': {
                    'therapist_id': a.therapist_id,
                    'patient_id': a.patient_id,
                    'therapist': a.therapist.username if a.therapist else '',
                    'patient': a.patient.username if a.patient else '',
                    'status': a.status,
                    'notes': a.notes or '',
                    'audit_score': audit_score,
                    'has_transcript': has_transcript,
                    'has_program': has_program,
                    'feedback_notes': feedback_notes,
                },
                'status': a.status,
                'attendance': a.attendance,
                'patient': {'id': a.patient.id, 'name': a.patient.username} if a.patient else None,
                'location': a.location,
                'notes': a.notes,
                'audit_score': audit_score,
                'has_transcript': has_transcript,
                'has_program': has_program,
                'games': games_list,
                'is_holiday': True if a.notes and 'Scheduled on Holiday' in a.notes else False,
            }
        )
    return jsonify(results)


@api_bp.route('/sessions/upcoming', methods=['GET'])
@login_required
def api_upcoming_sessions():
    if current_user.role != 'terapista':
        return jsonify({'error': 'Acceso denegado'}), 403
    appts = appointment_service.get_upcoming_sessions(current_user.id)
    tz_name = get_user_timezone(current_user)
    results = []
    for a in appts:
        patient = User.query.get(a.patient_id)
        local_start = localize_datetime_for_display(a.start_time, tz_name)
        local_end = localize_datetime_for_display(a.end_time, tz_name)
        start_iso = local_start.isoformat() if local_start else a.start_time.isoformat()
        end_iso = local_end.isoformat() if local_end else (a.end_time.isoformat() if a.end_time else None)
        results.append(
            {
                'id': a.id,
                'patient': patient.username or patient.email,
                'start_time': start_iso,
                'end_time': end_iso,
                'status': a.status,
                'attendance': a.attendance,
                'games': json.loads(a.games) if a.games else [],
            }
        )
    return jsonify(results)


@api_bp.route('/appointments/patient', methods=['GET'])
@login_required
def api_get_patient_appointments():
    if current_user.role != 'jugador':
        return jsonify({'error': 'Acceso denegado'}), 403
    start = request.args.get('start')
    end = request.args.get('end')
    try:
        start_dt = _parse_datetime(start)
        end_dt = _parse_datetime(end)
    except Exception:
        start_dt = None
        end_dt = None
    appts = appointment_service.get_patient_appointments(current_user.id, start_dt, end_dt)
    results = []
    for a in appts:
        start_iso = a.start_time.isoformat() if a.start_time else None
        end_iso = a.end_time.isoformat() if a.end_time else None
        results.append(
            {
                'id': a.id,
                'title': a.title,
                'start': start_iso,
                'end': end_iso,
                'status': a.status,
                'attendance': a.attendance,
                'therapist': {'id': a.therapist.id, 'name': a.therapist.username} if a.therapist else None,
                'location': a.location,
                'notes': a.notes,
                'games': json.loads(a.games) if a.games else [],
            }
        )
    return jsonify(results)


@api_bp.route('/sessions/day', methods=['GET'])
@login_required
def api_get_sessions_day():

    if current_user.role not in ('terapista', 'admin', 'supervisor'):
        return jsonify({'success': False, 'message': 'Acceso denegado'}), 403

    date_str = request.args.get('date')

    if not date_str:
        return jsonify({'success': False, 'message': 'Falta el parámetro date'}), 400
    try:
        if _is_date_only_param(date_str):
            query_start, query_end = get_user_day_utc_range(current_user, date_str[:10])
        else:
            day = _parse_datetime(date_str)
            query_start = day
            query_end = query_start + timedelta(days=1)
    except Exception:
        return jsonify({'success': False, 'message': 'Fecha malita, revisa el formato'}), 400

    base_query = Appointment.query
    if current_user.role == 'terapista':
        base_query = base_query.filter(Appointment.therapist_id == current_user.id)

    query = (
        base_query.filter(Appointment.start_time >= query_start, Appointment.start_time < query_end)
        .order_by(Appointment.start_time.asc())
        .all()
    )

    tz_name = get_user_timezone(current_user)

    results = []
    for a in query:
        local_start = localize_datetime_for_display(a.start_time, tz_name)
        local_end = localize_datetime_for_display(a.end_time, tz_name)
        start_iso = local_start.isoformat() if local_start else None
        end_iso = local_end.isoformat() if local_end else None

        results.append(
            {
                'id': a.id,
                'title': a.title or (a.patient.username if a.patient else 'Sesión'),
                'start': start_iso,
                'end': end_iso,
                'status': a.status,
                'attendance': a.attendance,
                'patient': {'id': a.patient.id, 'name': a.patient.username} if a.patient else None,
                'notes': a.notes,
                'location': a.location,
            }
        )

    return jsonify({'date': date_str, 'sessions': results})


@api_bp.route('/sessions', methods=['POST'])
@login_required
def api_create_session():
    """Crear sesión (terapista)"""
    if current_user.role != 'terapista':
        return jsonify({'success': False, 'message': 'Acceso denegado'}), 403

    data = request.json or {}
    for field in ('title', 'notes', 'location'):
        if isinstance(data.get(field), str):
            data[field] = sanitize_text(data[field], 1000)

    for field in ('start_time', 'end_time'):
        if isinstance(data.get(field), str):
            data[field] = _parse_datetime(data[field])

    if not data.get('patient_id') or not data.get('start_time'):
        return jsonify({'success': False, 'message': 'patient_id and start_time are required'}), 400

    if not data.get('end_time'):
        data['end_time'] = data['start_time'] + timedelta(hours=1)
    therapist_id = current_user.id
    if current_user.role in ('admin', 'supervisor'):
        if 'therapist_ids' in data:
            therapist_id = data['therapist_ids'][0]
        elif 'therapist_id' in data:
            therapist_id = data['therapist_id']
    if therapist_id:
        is_available, error_msg = AvailabilityService.check_availability(
            therapist_id=therapist_id, start_time=data['start_time'], end_time=data['end_time']
        )
        if not is_available:
            return jsonify({'success': False, 'message': error_msg}), 409
    patient_ids = data.get('patient_id')
    if not isinstance(patient_ids, list):
        patient_ids = [patient_ids]
    if len(patient_ids) > 5:
        return jsonify({'success': False, 'message': 'Máximo 5 pacientes por sesión nomá'}), 400
    created_sessions = []
    all_validation_errors = []
    ignore_therapist_conflict = len(patient_ids) > 1
    for pid in patient_ids:
        validation_errors = appointment_service.validate_session_times(
            start_time=data['start_time'],
            end_time=data['end_time'],
            patient_id=pid,
            therapist_id=current_user.id,
            session_id=None,
            ignore_therapist_conflict=ignore_therapist_conflict,
        )
        if validation_errors:
            p_user = User.query.get(pid)
            p_name = p_user.username if p_user else f'ID {pid}'
            for err in validation_errors:
                all_validation_errors.append(f'{p_name}: {err}')
    if all_validation_errors:
        return jsonify({'success': False, 'message': 'Algunos datos no cuadran', 'errors': all_validation_errors}), 400
    try:
        results = []
        for pid in patient_ids:
            session_data = data.copy()
            session_data['patient_id'] = pid
            appt = appointment_service.create_session(current_user.id, session_data, current_user.username)
            created_sessions.append(appt)
            created = {
                'id': appt.id,
                'title': appt.title,
                'start_time': appt.start_time.isoformat() if appt.start_time else None,
                'end_time': appt.end_time.isoformat() if appt.end_time else None,
                'status': appt.status,
                'patient': {'id': appt.patient.id, 'name': appt.patient.username} if appt.patient else None,
                'location': appt.location,
                'notes': appt.notes,
            }
            try:
                created['games'] = json.loads(appt.games) if appt.games else []
            except Exception:
                created['games'] = []
            results.append(created)
        return jsonify(
            {
                'success': True,
                'message': 'Sesión registrada, todo ok',
                'session': results[0] if results else {},
                'sessions': results,
            }
        ), 201
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@api_bp.route('/sessions/<int:session_id>', methods=['GET'])
@login_required
def api_get_session(session_id):
    if current_user.role not in ('terapista', 'admin', 'supervisor'):
        return jsonify({'error': 'Acceso denegado'}), 403
    appt = Appointment.query.get_or_404(session_id)
    if current_user.role == 'terapista':
        is_assigned = False
        if appt.patient:
            is_assigned = current_user in appt.patient.therapists
        if appt.therapist_id != current_user.id and not is_assigned:
            return jsonify({'error': 'No tienes permiso para ver esta sesión'}), 403
    images = []
    for img in appt.session_images or []:
        images.append(
            {
                'id': img.id,
                'url': url_for('static', filename=img.image_path),
                'type': img.image_type,
                'notes': img.notes,
                'uploaded_at': img.uploaded_at.isoformat() if img.uploaded_at else None,
                'uploaded_by': img.uploaded_by.username if img.uploaded_by else None,
            }
        )
    tz_name = get_user_timezone(current_user)
    local_start = localize_datetime_for_display(appt.start_time, tz_name)
    local_end = localize_datetime_for_display(appt.end_time, tz_name)
    start_iso = local_start.isoformat() if local_start else None
    end_iso = local_end.isoformat() if local_end else None
    return jsonify(
        {
            'id': appt.id,
            'title': appt.title or 'Sesión de Terapia',
            'start_time': start_iso,
            'end_time': end_iso,
            'status': appt.status,
            'attendance': appt.attendance,
            'patient': {'id': appt.patient.id, 'name': appt.patient.username} if appt.patient else None,
            'therapist_id': appt.therapist_id,
            'location': appt.location,
            'notes': appt.notes,
            'games': appt.games_list,
            'images': images,
        }
    )


@api_bp.route('/sessions/<int:session_id>', methods=['PUT'])
@login_required
def api_update_session(session_id):
    if current_user.role not in ('terapista', 'admin', 'supervisor'):
        return jsonify({'success': False, 'message': 'Acceso denegado'}), 403

    data = request.json or {}
    for field in ('title', 'notes', 'location'):
        if isinstance(data.get(field), str):
            data[field] = sanitize_text(data[field], 1000)

    for field in ('start_time', 'end_time'):
        if isinstance(data.get(field), str):
            data[field] = _parse_datetime(data[field])

    existing_appt = Appointment.query.get(session_id)
    if not existing_appt:
        return jsonify({'success': False, 'message': 'Esa sesión no existe'}), 404
    if 'start_time' in data or 'end_time' in data:
        start_time = data.get('start_time', existing_appt.start_time)
        end_time = data.get('end_time', existing_appt.end_time or (existing_appt.start_time + timedelta(hours=1)))

        validation_errors = appointment_service.validate_session_times(
            start_time=start_time,
            end_time=end_time,
            patient_id=existing_appt.patient_id,
            therapist_id=current_user.id,
            session_id=session_id,
        )

        if validation_errors:
            return jsonify({'success': False, 'message': 'Hay observaciones', 'errors': validation_errors}), 400

    appt = appointment_service.update_session(session_id, data)
    if not appt:
        return jsonify({'success': False, 'message': 'Esa sesión no existe'}), 404
    updated = {
        'id': appt.id,
        'title': appt.title,
        'start_time': appt.start_time.isoformat() if appt.start_time else None,
        'end_time': appt.end_time.isoformat() if appt.end_time else None,
        'status': appt.status,
        'patient': {'id': appt.patient.id, 'name': appt.patient.username} if appt.patient else None,
        'location': appt.location,
        'attendance': appt.attendance,
        'notes': appt.notes,
    }

    return jsonify(updated)


@api_bp.route('/sessions/<int:session_id>', methods=['DELETE'])
@login_required
@csrf.exempt
def api_delete_session(session_id):
    if current_user.role not in ('terapista', 'admin', 'supervisor'):
        return jsonify({'success': False, 'message': 'Acceso denegado'}), 403

    try:
        success = appointment_service.delete_session(session_id, current_user.id)
        if not success:
            return jsonify({'success': False, 'message': 'Esa sesión no existe'}), 404
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error eliminando sesión {session_id}: {e}')
        return jsonify({'success': False, 'message': 'No se pudo eliminar la sesión'}), 400


@api_bp.route('/sessions/<int:session_id>/cancel', methods=['POST'])
@login_required
def api_cancel_session(session_id):

    if current_user.role not in ['terapista', 'admin']:
        return jsonify({'success': False, 'message': 'Acceso denegado'}), 403

    data = request.get_json(silent=True) or {}
    reason = sanitize_text(data.get('reason', ''), 500)

    try:
        appt = appointment_service.transition_status(
            session_id=session_id, new_status='cancelled', changed_by_user_id=current_user.id, notify=True
        )

        if reason:
            if appt.notes:
                appt.notes += f'\n\n[Cancelada] {reason}'
            else:
                appt.notes = f'[Cancelada] {reason}'
            db.session.commit()

        return jsonify(
            {
                'success': True,
                'message': 'Sesión cancelada, listo',
                'session': {
                    'id': appt.id,
                    'status': appt.status,
                    'status_changed_at': appt.status_changed_at.isoformat() if appt.status_changed_at else None,
                },
            }
        )
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        current_app.logger.error(f'Error cancelling session {session_id}: {str(e)}')
        return jsonify({'success': False, 'message': 'No se pudo cancelar la sesión'}), 500


@api_bp.route('/sessions/assign-games', methods=['POST'])
@login_required
def assign_games_to_session():
    """Asignar juegos vía AppointmentGame"""
    if current_user.role not in ('terapista', 'admin', 'supervisor'):
        return jsonify({'error': 'Acceso denegado'}), 403

    data = request.get_json() or {}
    session_id = data.get('session_id')
    games = data.get('games') or []

    if not session_id:
        return jsonify({'error': 'session_id requerido'}), 400

    game_filenames = []
    for game in games:
        if isinstance(game, dict):
            game_filenames.append(game.get('name', ''))
        else:
            game_filenames.append(game)

    game_filenames = [g for g in game_filenames if g]

    try:
        validated_games = appointment_service.set_session_games(session_id, game_filenames)
        return jsonify({'status': 'ok', 'assigned': [{'name': g.filename, 'title': g.title} for g in validated_games]})
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        return jsonify({'error': f'Error asignando juegos: {str(e)}'}), 500


@api_bp.route('/sessions/<int:session_id>/games', methods=['GET'])
@login_required
def session_games(session_id):
    appt = Appointment.query.get(session_id)
    if not appt:
        return jsonify({'error': 'Sesión no encontrada'}), 404
    now = datetime.utcnow()
    end_time = appt.end_time or (appt.start_time + timedelta(hours=2))
    enabled = appt.status == 'scheduled' and appt.start_time <= now <= end_time
    games = []
    try:
        games = json.loads(appt.games) if appt.games else []
    except Exception:
        games = []
    return jsonify({'enabled': enabled, 'games': games})


@api_bp.route('/sessions/<int:session_id>/complete', methods=['POST'])
@login_required
def complete_session(session_id):
    appt = Appointment.query.get(session_id)
    if not appt:
        return jsonify({'error': 'Sesión no encontrada'}), 404
    if current_user.id != appt.therapist_id:
        return jsonify({'error': 'Acceso denegado'}), 403

    if appt.status != 'completed':
        appt.status = 'completed'
        appt.end_time = datetime.utcnow()
        db.session.add(appt)

    try:
        import threading

        from app.models import SessionAudit
        from app.services.audit_service import run_audit

        audit = SessionAudit.query.filter_by(appointment_id=session_id).first()
        if audit and audit.planned_text and audit.transcript_text and audit.audit_status == 'pending':
            app_obj = current_app._get_current_object()

            def _run_bg_audit(sid):
                with app_obj.app_context():
                    try:
                        run_audit(sid)
                    except Exception as exc:
                        app_obj.logger.error('auto audit failed for %s: %s', sid, exc)

            threading.Thread(target=_run_bg_audit, args=(session_id,), daemon=True).start()
    except Exception as exc:
        current_app.logger.debug('auto audit trigger failed: %s', exc)

    metrics = SessionMetrics.query.filter_by(user_id=appt.patient_id, session_id=session_id).all()
    if not metrics:
        db.session.commit()
        return jsonify({'status': 'ok', 'message': 'Sin métricas para agregar'})

    avg_acc = float(sum(m.accurracy for m in metrics) / len(metrics))
    avg_time_ms = float(sum(m.avg_time for m in metrics) / len(metrics) * 1000)
    plays = len(metrics)
    last_games = [
        {
            'game_name': m.game_name,
            'accuracy': float(m.accurracy),
            'avg_time_ms': float(m.avg_time * 1000),
            'prediction': int(m.prediction),
            'date': m.date.isoformat(),
        }
        for m in metrics
    ]

    patient = User.query.get(appt.patient_id)
    try:
        existing = json.loads(patient.game_profile) if patient.game_profile else {}
    except Exception:
        existing = {}
    existing.setdefault('history', []).extend(last_games)
    existing['kpis'] = {'avg_accuracy': avg_acc, 'avg_time_ms': avg_time_ms, 'plays': plays}

    patient.game_profile = json.dumps(existing, ensure_ascii=False)
    db.session.commit()

    try:
        notification_service.create_notification(
            appt.therapist_id,
            f'Sesión #{appt.id} completada. {plays} juegos registrados.',
            link=url_for('therapist.reports'),
        )
        notification_service.create_notification(
            appt.patient_id, 'Sesión completada. ¡Buen trabajo!', link=url_for('patient.progress')
        )
    except Exception as exc:
        current_app.logger.debug('completion notifications failed: %s', exc)

    return jsonify({'status': 'ok', 'updated_profile': existing})


@api_bp.route('/resources/<int:resource_id>')
@login_required
def get_resource(resource_id):
    try:
        if resource_id == 1:
            metrics = (
                SessionMetrics.query.filter_by(user_id=current_user.id)
                .order_by(SessionMetrics.date.desc())
                .limit(20)
                .all()
            )
            if metrics:
                avg_acc = sum((m.accurracy or 0) for m in metrics) / len(metrics)
                avg_time = sum((m.avg_time or 0) for m in metrics) / len(metrics)
                perf_summary = f'Tu precisión promedio en las últimas sesiones es {avg_acc:.0f}%. Tiempo medio por ejercicio {avg_time:.1f}s.'
            else:
                perf_summary = 'No hay datos de sesiones suficientes para personalizar esta guía.'

            content = f'<h3>Guía de Ejercicios Personalizada</h3><p>{perf_summary}</p>'
            content += '<ol><li>Ejercicio respiratorio: 5 minutos.</li><li>Ejercicios de atención: 3 bloques de 4 minutos.</li><li>Revisión de estrategias aprendidas en la sesión.</li></ol>'
            return jsonify({'id': resource_id, 'title': 'Guía de Ejercicios', 'content': content})

        if resource_id == 2:
            content = '<h3>Video Tutorial: Técnicas básicas</h3><p>Este video explica las técnicas recomendadas y cuándo aplicarlas. Duración: 15:30.</p>'
            content += '<p>Puntos clave: respiración, pausas activas, seguimiento de progreso.</p>'
            return jsonify({'id': resource_id, 'title': 'Video Tutorial', 'content': content})

        if resource_id == 3:
            content = (
                '<h3>Hoja de Práctica</h3><p>Plantilla descargable para llevar un registro de ejercicios diarios.</p>'
            )
            content += (
                '<ul><li>Día 1: Ejercicio A - 10 repeticiones</li><li>Día 2: Ejercicio B - 8 repeticiones</li></ul>'
            )
            return jsonify({'id': resource_id, 'title': 'Hoja de Práctica', 'content': content})

        return jsonify({'error': 'Recurso no encontrado'}), 404
    except Exception as e:
        return jsonify({'error': 'Error generando recurso', 'detail': str(e)}), 500


@api_bp.route('/appointments/<int:appointment_id>/upload_image', methods=['POST'])
@login_required
@csrf.exempt
def upload_session_image(appointment_id):

    if current_user.role not in ('terapista', 'admin', 'supervisor'):
        return jsonify({'error': 'Acceso denegado'}), 403

    appointment = Appointment.query.get_or_404(appointment_id)

    if current_user.role == 'terapista' and appointment.therapist_id != current_user.id:
        return jsonify({'error': 'No tienes permiso para editar esta sesión'}), 403

    if 'image' not in request.files:
        return jsonify({'error': 'No se encontró el archivo de imagen'}), 400

    file = request.files['image']
    image_type = request.form.get('image_type', 'session_photo')
    notes = sanitize_text(request.form.get('notes', ''), 1000)

    if file.filename == '':
        return jsonify({'error': 'Nombre de archivo vacío'}), 400

    if file:
        allowed_extensions = {'png', 'jpg', 'jpeg', 'webp', 'doc', 'docx'}
        if '.' not in file.filename or file.filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
            return jsonify({'error': 'Tipo de archivo no permitido (solo imágenes y Word)'}), 400

        original_filename = secure_filename(file.filename)
        extension = original_filename.rsplit('.', 1)[1].lower()
        unique_filename = f'{uuid.uuid4().hex}.{extension}'

        now = datetime.utcnow()
        relative_path = os.path.join('uploads', 'session_images', str(now.year), f'{now.month:02d}')
        upload_folder = os.path.join(current_app.root_path, 'static', relative_path)

        os.makedirs(upload_folder, exist_ok=True)

        file_path = os.path.join(upload_folder, unique_filename)
        file.save(file_path)

        try:
            patient_name = appointment.patient.username if appointment.patient else 'Paciente_Desconocido'
            session_date = appointment.start_time.strftime('%Y-%m-%d')

            print(f'Subiendo a Drive: {patient_name} / {session_date} / {unique_filename}')
            drive_service.upload_file(
                file_path,
                unique_filename,
                file.mimetype,
                patient_name,
                session_date,
            )
        except Exception as e:
            print(f'Error subiendo a Google Drive: {str(e)}')

        db_relative_path = os.path.join(relative_path, unique_filename)

        session_image = SessionImage(
            appointment_id=appointment.id,
            image_path=db_relative_path,
            image_type=image_type,
            uploaded_by_id=current_user.id,
            notes=notes,
        )

        db.session.add(session_image)
        db.session.commit()

        return jsonify(
            {
                'success': True,
                'image': {
                    'id': session_image.id,
                    'url': url_for('static', filename=db_relative_path),
                    'type': session_image.image_type,
                    'notes': session_image.notes,
                },
            }
        )

    return jsonify({'error': 'Error al subir archivo'}), 500


@api_bp.route('/appointments/<int:appointment_id>/images/<int:image_id>', methods=['DELETE'])
@login_required
def delete_session_image(appointment_id, image_id):

    if current_user.role not in ('terapista', 'admin', 'supervisor'):
        return jsonify({'error': 'Acceso denegado'}), 403

    image = SessionImage.query.get_or_404(image_id)

    if image.appointment_id != appointment_id:
        return jsonify({'error': 'Imagen no corresponde a la sesión'}), 400

    if current_user.role == 'terapista':
        appointment = Appointment.query.get(appointment_id)
        if appointment.therapist_id != current_user.id:
            return jsonify({'error': 'No tienes permiso para editar esta sesión'}), 403

    try:
        full_path = os.path.join(current_app.root_path, 'static', image.image_path)
        if os.path.exists(full_path):
            os.remove(full_path)

        db.session.delete(image)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': f'Error al eliminar imagen: {str(e)}'}), 500


@api_bp.route('/sessions/<int:appointment_id>/program', methods=['POST'])
@login_required
@csrf.exempt
def upload_session_program(appointment_id):
    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'success': False, 'error': 'Solo administración puede subir la programación'}), 403

    appointment = Appointment.query.get_or_404(appointment_id)

    if 'program_file' not in request.files:
        return jsonify({'success': False, 'error': 'No se encontró el archivo'}), 400

    file = request.files['program_file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'Nombre de archivo vacío'}), 400

    if not file.filename.lower().endswith('.docx'):
        return jsonify({'success': False, 'error': 'Solo se aceptan archivos .docx'}), 400

    try:
        from app.models import SessionAudit
        from app.services.audit_service import extract_docx_text

        temp_filename = f'temp_program_{uuid.uuid4().hex}.docx'
        upload_root = current_app.config.get('UPLOAD_FOLDER') or tempfile.gettempdir()
        temp_dir = os.path.join(upload_root, 'temp_audit')
        os.makedirs(temp_dir, exist_ok=True)
        temp_path = os.path.join(temp_dir, temp_filename)
        file.save(temp_path)

        try:
            planned_text = extract_docx_text(temp_path)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

        audit = SessionAudit.query.filter_by(appointment_id=appointment_id).first()
        if not audit:
            audit = SessionAudit(appointment_id=appointment_id)
            db.session.add(audit)

        audit.planned_text = planned_text
        audit.docx_uploaded_at = datetime.utcnow()
        audit.docx_uploaded_by = current_user.id
        audit.audit_status = 'pending'
        audit.audit_report_json = None
        audit.audit_score = None

        db.session.commit()

        return jsonify(
            {
                'success': True,
                'message': 'Programación subida correctamente',
                'planned_text_preview': planned_text[:500] + ('...' if len(planned_text) > 500 else ''),
                'char_count': len(planned_text),
            }
        )

    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        current_app.logger.error(f'Error subiendo programación: {str(e)}')
        return jsonify({'success': False, 'error': f'Error interno: {str(e)}'}), 500


@api_bp.route('/sessions/auto-complete-expired', methods=['POST'])
@login_required
@csrf.exempt
def completar_sesiones_vencidas():
    cutoff = datetime.utcnow() - timedelta(minutes=5)
    expired = Appointment.query.filter(Appointment.status == 'in_progress', Appointment.end_time < cutoff).all()
    count = 0
    for appt in expired:
        appt.status = 'completed'
        count += 1
    db.session.commit()
    return jsonify({'success': True, 'completed': count})


@api_bp.route('/sessions/<int:appointment_id>/audio', methods=['POST'])
@login_required
@csrf.exempt
def upload_session_audio(appointment_id):
    """Subir audio para transcripción Whisper (se elimina tras transcribir)"""
    if current_user.role not in ('terapista', 'admin', 'supervisor'):
        return jsonify({'success': False, 'error': 'Acceso denegado'}), 403

    appointment = Appointment.query.get_or_404(appointment_id)

    if current_user.role == 'terapista' and appointment.therapist_id != current_user.id:
        return jsonify({'success': False, 'error': 'No tienes permiso para esta sesión'}), 403

    if 'audio_file' not in request.files:
        return jsonify({'success': False, 'error': 'No se encontró el archivo de audio'}), 400

    file = request.files['audio_file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'Nombre de archivo vacío'}), 400

    allowed_audio = {'webm', 'wav', 'mp3', 'ogg', 'm4a', 'mp4'}
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if ext not in allowed_audio:
        return jsonify({'success': False, 'error': f'Formato no soportado. Usa: {", ".join(allowed_audio)}'}), 400

    try:
        from app.models import SessionAudit
        from app.services.audit_service import transcribe_audio

        temp_filename = f'session_audio_{appointment_id}_{uuid.uuid4().hex}.{ext}'
        upload_root = current_app.config.get('UPLOAD_FOLDER') or tempfile.gettempdir()
        temp_dir = os.path.join(upload_root, 'temp_audio')
        os.makedirs(temp_dir, exist_ok=True)
        temp_path = os.path.join(temp_dir, temp_filename)
        file.save(temp_path)

        result = transcribe_audio(temp_path)

        audit = SessionAudit.query.filter_by(appointment_id=appointment_id).first()
        if not audit:
            audit = SessionAudit(appointment_id=appointment_id)
            db.session.add(audit)

        existing = audit.transcript_text or ''
        separator = ' ' if existing else ''
        audit.transcript_text = existing + separator + result['text']
        audit.audio_transcribed_at = datetime.utcnow()
        audit.audio_duration_seconds = (audit.audio_duration_seconds or 0) + result.get('duration', 0)
        if audit.audit_status == 'completed':
            audit.audit_status = 'pending'
            audit.audit_report_json = None
            audit.audit_score = None

        db.session.commit()

        return jsonify(
            {
                'success': True,
                'message': 'Audio transcrito correctamente. Archivo eliminado del servidor.',
                'transcript_text': result['text'],
                'transcript_preview': result['text'][:500] + ('...' if len(result['text']) > 500 else ''),
                'duration_seconds': result.get('duration', 0),
                'char_count': len(result['text']),
            }
        )

    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        current_app.logger.error(f'Error transcribiendo audio: {str(e)}')
        try:
            if 'temp_path' in locals() and os.path.exists(temp_path):
                os.remove(temp_path)
                current_app.logger.info(f' Audio eliminado tras error: {temp_path}')
        except OSError as exc:
            current_app.logger.debug('temp audio cleanup failed: %s', exc)
        return jsonify({'success': False, 'error': f'Error al transcribir: {str(e)}'}), 500


@api_bp.route('/sessions/<int:appointment_id>/audit', methods=['POST'])
@login_required
def trigger_session_audit(appointment_id):
    """Disparar auditoría IA: programación vs transcripción"""
    if current_user.role not in ('terapista', 'admin', 'supervisor'):
        return jsonify({'success': False, 'error': 'Acceso denegado'}), 403

    try:
        from app.models import User
        from app.services.audit_service import run_audit

        report = run_audit(appointment_id)
        appt = Appointment.query.get(appointment_id)
        score = None
        if report:
            score = (
                report.get('score') or (report.get('report') or {}).get('audit_score')
                if isinstance(report, dict)
                else None
            )
        therapist_name = appt.therapist.username if appt and appt.therapist else 'Desconocido'
        patient_name = appt.patient.username if appt and appt.patient else 'Desconocido'
        score_str = f' — Puntuación: {score}/100' if score is not None else ''

        try:
            from app.services.notification_service import NotificationService

            ns = NotificationService()
            msg_admin = f'Auditoría completada: {therapist_name} / {patient_name}{score_str}'[:255]
            admins = User.query.filter_by(role='admin').all()
            for admin in admins:
                ns.create_notification(admin.id, msg_admin)
            msg_therapist = f'Auditoría completada para {patient_name}{score_str}'[:255]
            if appt and appt.therapist_id:
                ns.create_notification(appt.therapist_id, msg_therapist)
        except Exception as notif_err:
            current_app.logger.warning('Notificaciones post-auditoría omitidas: %s', notif_err)

        if appt and score is not None:
            try:
                from app.services.report_service import ReportService

                rs = ReportService()
                session_date = appt.start_time.date() if appt.start_time else datetime.utcnow().date()
                rs.generate_daily_report(appt.patient_id, appt.therapist_id, session_date.isoformat())
            except Exception as daily_err:
                current_app.logger.error(f'Error generando reporte diario post-auditoría: {daily_err}')

        return jsonify({'success': True, 'message': 'Auditoría completada', 'report': report})
    except ValueError as e:
        err_msg = str(e)
        current_app.logger.warning(f'Audit ValueError for session {appointment_id}: {err_msg}')
        return jsonify({'success': False, 'error': err_msg, 'reason': 'validation'}), 400
    except Exception as e:
        current_app.logger.error(f'Error en auditoría IA: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'error': f'Error en auditoría: {str(e)}', 'reason': 'server'}), 500


@api_bp.route('/sessions/<int:appointment_id>/audit', methods=['GET'])
@login_required
def get_session_audit(appointment_id):
    """Estado y reporte de auditoría de sesión"""
    if current_user.role not in ('terapista', 'admin', 'supervisor'):
        return jsonify({'success': False, 'error': 'Acceso denegado'}), 403

    try:
        from app.models import SessionAudit

        audit = SessionAudit.query.filter_by(appointment_id=appointment_id).first()
        if not audit:
            return jsonify(
                {'success': True, 'exists': False, 'message': 'No hay registro de auditoría para esta sesión'}
            )

        return jsonify(
            {
                'success': True,
                'exists': True,
                'audit': {
                    'id': audit.id,
                    'has_program': bool(audit.planned_text),
                    'has_transcript': bool(audit.transcript_text),
                    'planned_text_preview': (audit.planned_text[:300] + '...')
                    if audit.planned_text and len(audit.planned_text) > 300
                    else audit.planned_text,
                    'transcript_preview': (audit.transcript_text[:300] + '...')
                    if audit.transcript_text and len(audit.transcript_text) > 300
                    else audit.transcript_text,
                    'planned_text': audit.planned_text,
                    'transcript_text': audit.transcript_text,
                    'audio_duration_seconds': audit.audio_duration_seconds,
                    'audit_status': audit.audit_status,
                    'audit_score': audit.audit_score,
                    'report': audit.get_report() if audit.audit_status == 'completed' else None,
                    'docx_uploaded_at': audit.docx_uploaded_at.isoformat() if audit.docx_uploaded_at else None,
                    'audio_transcribed_at': audit.audio_transcribed_at.isoformat()
                    if audit.audio_transcribed_at
                    else None,
                    'audited_at': audit.audited_at.isoformat() if audit.audited_at else None,
                    'feedback_engagement': audit.feedback_engagement,
                    'feedback_progress': audit.feedback_progress,
                    'feedback_notes': audit.feedback_notes,
                    'feedback_submitted_at': audit.feedback_submitted_at.isoformat()
                    if audit.feedback_submitted_at
                    else None,
                },
            }
        )
    except Exception as e:
        current_app.logger.error('Error obteniendo auditoría %s: %s', appointment_id, e, exc_info=True)
        return jsonify({'success': False, 'error': 'No se pudo cargar la auditoría'}), 500


@api_bp.route('/sessions/<int:appointment_id>/compare-live', methods=['GET'])
@login_required
def compare_session_live(appointment_id):
    if current_user.role not in ('terapista', 'admin', 'supervisor'):
        return jsonify({'success': False, 'error': 'Acceso denegado'}), 403

    from app.models import SessionAudit
    from app.services.audit_service import compute_similarity_vectorial

    audit = SessionAudit.query.filter_by(appointment_id=appointment_id).first()
    if not audit:
        return jsonify({'success': False, 'error': 'No hay auditoría'}), 404

    vectorial = compute_similarity_vectorial(audit.planned_text or '', audit.transcript_text or '')

    duracion = audit.audio_duration_seconds or 0
    ratio = min(1.0, duracion / 2700)
    factor = min(1.0, ratio / 0.1)

    return jsonify(
        {
            'success': True,
            'score_vectorial': vectorial['score_vectorial'],
            'objetivos_cubiertos': vectorial['objetivos_cubiertos'],
            'n_objectives': vectorial['n_objectives'],
            'ratio_duracion': round(ratio, 3),
            'factor_penalizacion': round(factor, 3),
            'duracion_segundos': duracion,
            'char_count': len(audit.transcript_text or ''),
        }
    )


@api_bp.route('/sessions/<int:appointment_id>/program', methods=['DELETE'])
@login_required
@csrf.exempt
def delete_session_program(appointment_id):
    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'success': False, 'error': 'Solo administración puede eliminar la programación'}), 403

    from app.models import SessionAudit

    audit = SessionAudit.query.filter_by(appointment_id=appointment_id).first()
    if not audit or not audit.planned_text:
        return jsonify({'success': False, 'error': 'No hay programación para esta sesión'}), 404

    audit.planned_text = None
    audit.docx_uploaded_at = None
    audit.docx_uploaded_by = None
    if audit.audit_status == 'completed':
        audit.audit_status = 'pending'
        audit.audit_report_json = None
        audit.audit_score = None
        audit.audited_at = None

    if not audit.transcript_text:
        db.session.delete(audit)

    db.session.commit()
    return jsonify({'success': True, 'message': 'Programación eliminada'})


@api_bp.route('/sessions/<int:appointment_id>/program', methods=['GET'])
@login_required
def get_session_program(appointment_id):
    """Texto de programación para terapista"""
    if current_user.role not in ('terapista', 'admin', 'supervisor'):
        return jsonify({'success': False, 'error': 'Acceso denegado'}), 403

    from app.models import SessionAudit

    audit = SessionAudit.query.filter_by(appointment_id=appointment_id).first()
    if not audit or not audit.planned_text:
        return jsonify({'success': False, 'exists': False})

    return jsonify(
        {
            'success': True,
            'exists': True,
            'planned_text': audit.planned_text,
            'uploaded_at': audit.docx_uploaded_at.isoformat() if audit.docx_uploaded_at else None,
        }
    )


@api_bp.route('/sessions/<int:appointment_id>/objectives', methods=['GET'])
@login_required
def get_session_objectives(appointment_id):
    if current_user.role not in ('terapista', 'admin', 'supervisor'):
        return jsonify({'success': False, 'error': 'Acceso denegado'}), 403

    from app.models import SessionAudit

    audit = SessionAudit.query.filter_by(appointment_id=appointment_id).first()
    if not audit or not audit.planned_text:
        return jsonify({'success': True, 'objectives': []})

    objectives = parse_objectives(audit.planned_text)
    if audit.audit_status == 'completed':
        enrich_objectives_from_audit(objectives, audit.audit_report_json)

    from app.utils.objectives import objective_status_to_ui

    items = []
    for obj in objectives:
        code, label = objective_status_to_ui(obj.get('status', 'pendiente'))
        items.append({'name': obj['name'], 'status': code, 'status_label': label, 'evidence': obj.get('evidence', '')})

    return jsonify({'success': True, 'objectives': items})


@api_bp.route('/sessions/<int:session_id>/start-recording', methods=['POST'])
@login_required
def start_session_recording(session_id):
    """Marcar sesión como en_progreso para grabación"""
    if current_user.role not in ('terapista', 'admin', 'supervisor'):
        return jsonify({'success': False, 'error': 'Acceso denegado'}), 403

    appt = Appointment.query.get_or_404(session_id)
    if current_user.role == 'terapista' and appt.therapist_id != current_user.id:
        return jsonify({'success': False, 'error': 'No tienes permiso para esta sesión'}), 403

    if appt.status not in ('scheduled', 'in_progress', 'completed'):
        return jsonify({'success': False, 'error': f'Estado de sesión inválido: {appt.status}'}), 400

    if appt.status != 'in_progress':
        appt.status = 'in_progress'
        appt.status_changed_at = datetime.utcnow()
        appt.status_changed_by = current_user.id
        db.session.commit()

    return jsonify({'success': True, 'message': 'Grabación iniciada', 'session_id': session_id})


@api_bp.route('/sessions/<int:session_id>/analyze-attendance', methods=['POST'])
@login_required
def analyze_session_attendance(session_id):
    """Detectar inasistencia vía transcripción vs plan"""
    if current_user.role not in ('terapista', 'admin', 'supervisor'):
        return jsonify({'success': False, 'error': 'Acceso denegado'}), 403

    appt = Appointment.query.get_or_404(session_id)
    if current_user.role == 'terapista' and appt.therapist_id != current_user.id:
        return jsonify({'success': False, 'error': 'No tienes permiso para esta sesión'}), 403

    from app.models import SessionAudit

    audit = SessionAudit.query.filter_by(appointment_id=session_id).first()

    transcript = audit.transcript_text if audit and audit.transcript_text else ''
    planned = audit.planned_text if audit and audit.planned_text else ''

    if not transcript or len(transcript.strip()) < 50:
        return jsonify(
            {
                'success': True,
                'suggested_attendance': 'absent',
                'confidence': 0.95,
                'reason': 'Sin transcripción o muy corta',
                'coverage_pct': 0,
            }
        )

    if not planned:
        return jsonify(
            {
                'success': True,
                'suggested_attendance': 'present',
                'confidence': 0.5,
                'reason': 'Sin programación para comparar',
                'coverage_pct': 50,
            }
        )

    try:
        from app.services.audit_service import analyze_attendance

        result = analyze_attendance(planned, transcript)
        return jsonify(
            {
                'success': True,
                'suggested_attendance': result['suggested_attendance'],
                'confidence': result['confidence'],
                'reason': result.get('reason', ''),
                'coverage_pct': result.get('coverage_pct', 0),
            }
        )
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        current_app.logger.error(f'Error analyzing attendance: {str(e)}')
        return jsonify({'success': False, 'error': f'Error: {str(e)}'}), 500


@api_bp.route('/sessions/<int:session_id>/mark-absent', methods=['POST'])
@login_required
def mark_session_absent(session_id):
    """Marcar sesión como ausente"""
    if current_user.role not in ('terapista', 'admin', 'supervisor'):
        return jsonify({'success': False, 'error': 'Acceso denegado'}), 403

    appt = Appointment.query.get_or_404(session_id)
    if current_user.role == 'terapista' and appt.therapist_id != current_user.id:
        return jsonify({'success': False, 'error': 'No tienes permiso para esta sesión'}), 403

    appt.attendance = 'absent'
    appt.status = 'completed'
    appt.status_changed_at = datetime.utcnow()
    appt.status_changed_by = current_user.id
    db.session.commit()

    return jsonify({'success': True, 'message': 'Sesión marcada como ausente', 'session_id': session_id})


@api_bp.route('/sessions/<int:session_id>/feedback', methods=['POST'])
@login_required
def submit_session_feedback(session_id):
    """Feedback del terapeuta sobre la sesión"""
    if current_user.role not in ('terapista', 'admin', 'supervisor'):
        return jsonify({'success': False, 'error': 'Acceso denegado'}), 403

    appt = Appointment.query.get_or_404(session_id)
    if current_user.role == 'terapista' and appt.therapist_id != current_user.id:
        return jsonify({'success': False, 'error': 'No tienes permiso para esta sesión'}), 403

    data = request.get_json(silent=True) or {}
    engagement = data.get('engagement')
    progress = data.get('progress')
    notes = data.get('notes', '')

    from app.models import SessionAudit

    audit = SessionAudit.query.filter_by(appointment_id=session_id).first()
    if not audit:
        audit = SessionAudit(appointment_id=session_id)
        db.session.add(audit)

    audit.feedback_engagement = engagement
    audit.feedback_progress = progress
    audit.feedback_notes = notes
    audit.feedback_submitted_at = datetime.utcnow()

    propagated = 0
    if appt.group_session_key and appt.group_id:
        siblings = Appointment.query.filter(
            Appointment.group_session_key == appt.group_session_key,
            Appointment.group_id == appt.group_id,
            Appointment.id != appt.id,
            Appointment.therapist_id == appt.therapist_id,
        ).all()
        for sibling in siblings:
            s_audit = SessionAudit.query.filter_by(appointment_id=sibling.id).first()
            if not s_audit:
                s_audit = SessionAudit(appointment_id=sibling.id)
                db.session.add(s_audit)
            s_audit.feedback_engagement = engagement
            s_audit.feedback_progress = progress
            s_audit.feedback_notes = notes
            s_audit.feedback_submitted_at = datetime.utcnow()
            propagated += 1

    db.session.commit()

    return jsonify(
        {
            'success': True,
            'message': 'Feedback guardado',
            'propagated_sessions': propagated,
        }
    )


@api_bp.route('/sessions/<int:session_id>/briefing', methods=['GET'])
@login_required
def api_session_briefing(session_id):
    """Briefing for therapist: program text, recording status, transcription status, audit score"""
    if current_user.role not in ('terapista', 'admin', 'supervisor'):
        return jsonify({'success': False, 'error': 'Acceso denegado'}), 403

    appt = Appointment.query.get_or_404(session_id)
    if current_user.role == 'terapista' and appt.therapist_id != current_user.id:
        return jsonify({'success': False, 'error': 'No tienes permiso'}), 403

    from app.models import SessionAudit

    audit = SessionAudit.query.filter_by(appointment_id=session_id).first()

    objectives = []
    if audit and audit.planned_text:
        objectives = parse_objectives(audit.planned_text)
        if audit.audit_status == 'completed':
            enrich_objectives_from_audit(objectives, audit.audit_report_json)

    return jsonify(
        {
            'success': True,
            'session': {
                'id': appt.id,
                'title': appt.title or 'Sesión',
                'status': appt.status,
                'start_time': appt.start_time.isoformat() + 'Z' if appt.start_time else None,
                'end_time': appt.end_time.isoformat() + 'Z' if appt.end_time else None,
                'patient': {'id': appt.patient.id, 'name': appt.patient.username} if appt.patient else None,
                'location': appt.location,
            },
            'program': {
                'has_program': bool(audit and audit.planned_text),
                'planned_text': (audit.planned_text[:2000] + '...')
                if audit and audit.planned_text and len(audit.planned_text) > 2000
                else (audit.planned_text if audit else None),
                'uploaded_at': audit.docx_uploaded_at.isoformat() if audit and audit.docx_uploaded_at else None,
                'objectives': objectives,
            }
            if audit
            else {'has_program': False, 'objectives': []},
            'recording': {
                'has_transcript': bool(audit and audit.transcript_text),
                'transcript_preview': (audit.transcript_text[:500] + '...')
                if audit and audit.transcript_text and len(audit.transcript_text) > 500
                else (audit.transcript_text if audit else None),
                'audit_score': audit.audit_score if audit else None,
                'audit_status': audit.audit_status if audit else 'none',
            }
            if audit
            else {'has_transcript': False, 'audit_score': None, 'audit_status': 'none'},
        }
    )


@api_bp.route('/sessions/current', methods=['GET'])
@login_required
def api_current_session():
    if current_user.role not in ('terapista', 'admin', 'supervisor'):
        return jsonify({'success': False, 'error': 'Acceso denegado'}), 403
    now = datetime.utcnow()
    from sqlalchemy import or_

    appt = (
        Appointment.query.filter(
            Appointment.therapist_id == current_user.id,
            Appointment.start_time <= now,
            or_(Appointment.end_time >= now, Appointment.end_time.is_(None)),
            Appointment.status.in_(['scheduled', 'in_progress']),
        )
        .order_by(Appointment.start_time)
        .first()
    )
    if not appt:
        current_app.logger.info(
            'api_current_session: no active session',
            extra={
                'user_id': current_user.id,
                'role': current_user.role,
                'now': now.isoformat(),
            },
        )
        return jsonify({'success': False, 'has_active': False})

    delay_minutes = int((now - appt.start_time).total_seconds() / 60)
    delay_minutes = max(delay_minutes, 0)

    current_app.logger.info(
        'api_current_session: active session found',
        extra={
            'user_id': current_user.id,
            'session_id': appt.id,
            'start': appt.start_time.isoformat() if appt.start_time else None,
            'end': appt.end_time.isoformat() if appt.end_time else None,
            'status': appt.status,
            'delay_minutes': delay_minutes,
        },
    )

    return jsonify(
        {
            'success': True,
            'has_active': True,
            'delay_minutes': delay_minutes,
            'session': {
                'id': appt.id,
                'title': appt.title or 'Sesión',
                'start': appt.start_time.isoformat() + 'Z' if appt.start_time else None,
                'end': appt.end_time.isoformat() + 'Z' if appt.end_time else None,
                'status': appt.status,
                'patient': {'id': appt.patient.id, 'name': appt.patient.username} if appt.patient else None,
                'location': appt.location,
            },
        }
    )
