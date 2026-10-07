from datetime import datetime, timedelta

from flask import current_app, flash, jsonify, redirect, render_template, request, url_for
from sqlalchemy.orm import joinedload

from app.auth_compat import current_user, login_required
from app.extensions import db
from app.models import Appointment, User
from app.routes.admin import admin_bp
from app.services.holiday_service import is_holiday
from app.utils import (
    get_user_day_utc_range,
    localize_datetime_for_display,
    normalize_datetime_for_storage,
)


@admin_bp.route('/sessions')
@login_required
def sessions_calendar():
    if current_user.role not in ('admin', 'supervisor'):
        flash('Acceso denegado.', 'error')
        return redirect(url_for('main.dashboard'))

    therapists = User.query.filter_by(role='terapista', is_active=True).order_by(User.username.asc()).all()
    patients = User.query.filter_by(role='jugador', is_active=True).order_by(User.username.asc()).all()

    return render_template(
        'admin/sessions.html', therapists=therapists, patients=patients, active_page='admin_sessions'
    )


VALID_STATUSES = ('scheduled', 'in_progress', 'completed', 'cancelled')
MAX_RANGE_DAYS = 100
STATUS_COLORS = {'completed': '#10b981', 'cancelled': '#ef4444', 'scheduled': '#3b82f6'}


def _parse_day(value):
    return datetime.strptime(str(value).split('T')[0], '%Y-%m-%d').date()


@admin_bp.route('/api/sessions')
@login_required
def get_sessions_api():
    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        start_str = request.args.get('start')
        end_str = request.args.get('end')
        therapist_id = request.args.get('therapist_id')
        patient_id = request.args.get('patient_id')

        # Sin rango válido ya no se devuelve TODA la tabla: se exige un rango acotado.
        if bool(start_str) != bool(end_str):
            return jsonify({'error': 'start y end deben enviarse juntos'}), 400
        if start_str and end_str:
            try:
                start_day, end_day = _parse_day(start_str), _parse_day(end_str)
            except ValueError:
                return jsonify({'error': 'start/end deben tener formato YYYY-MM-DD'}), 400
            if end_day < start_day:
                return jsonify({'error': 'end no puede ser anterior a start'}), 400
            if (end_day - start_day).days > MAX_RANGE_DAYS:
                return jsonify({'error': f'El rango máximo es de {MAX_RANGE_DAYS} días'}), 400
        else:
            today = datetime.utcnow().date()
            start_day, end_day = today.replace(day=1), today.replace(day=1) + timedelta(days=62)

        start_dt, _ = get_user_day_utc_range(current_user, start_day.isoformat())
        _, end_dt = get_user_day_utc_range(current_user, end_day.isoformat())

        query = (
            Appointment.query.options(joinedload(Appointment.patient), joinedload(Appointment.therapist))
            .filter(Appointment.start_time >= start_dt, Appointment.start_time < end_dt)
            .order_by(Appointment.start_time.asc())
        )

        for column, raw in ((Appointment.therapist_id, therapist_id), (Appointment.patient_id, patient_id)):
            if raw and raw not in {'all', 'undefined', 'null'}:
                try:
                    query = query.filter(column == int(raw))
                except ValueError:
                    return jsonify({'error': 'Identificador inválido'}), 400

        tz_name = current_user.timezone or 'America/Lima'
        events = []
        for app in query.all():
            try:
                if not app.start_time:
                    continue
                color = STATUS_COLORS.get(app.status, '#3788d8')
                p_name = app.patient.username if getattr(app, 'patient', None) else '???'
                t_name = app.therapist.username if getattr(app, 'therapist', None) else '???'
                local_start = localize_datetime_for_display(app.start_time, tz_name)
                local_end = localize_datetime_for_display(app.end_time, tz_name)
                events.append(
                    {
                        'id': app.id,
                        'title': app.title if app.title else f'{p_name} ({t_name})',
                        'start': local_start.isoformat() if local_start else app.start_time.isoformat(),
                        'end': local_end.isoformat()
                        if local_end
                        else (app.end_time.isoformat() if app.end_time else None),
                        'backgroundColor': color,
                        'borderColor': color,
                        'extendedProps': {
                            'therapist_id': app.therapist_id,
                            'patient_id': app.patient_id,
                            'therapist': t_name,
                            'patient': p_name,
                            'status': app.status,
                            'notes': app.notes,
                            'location': app.location,
                            'session_type': app.session_type,
                            'group_id': app.group_id,
                        },
                    }
                )
            except Exception as e_inner:
                current_app.logger.error(f'Error packing event {app.id}: {e_inner}')
                continue

        return jsonify(events)
    except Exception as e:
        current_app.logger.error(f'API Sessions Error: {e}')
        return jsonify({'error': 'No se pudieron cargar las sesiones'}), 500


def _overlaps(a_start, a_end, b_start, b_end):
    return a_start < b_end and a_end > b_start


def _find_conflict(candidate, existing):
    """Primer choque de `candidate` con `existing` (sesiones ya guardadas + las creadas en este mismo lote).

    - Mismo paciente en el mismo tramo: siempre choca.
    - Mismo terapeuta en el mismo tramo: choca, salvo que sean sesiones de un mismo grupo y el mismo horario.
    """
    for other in existing:
        if other['status'] == 'cancelled' or not _overlaps(
            candidate['start'], candidate['end'], other['start'], other['end']
        ):
            continue
        if other['patient_id'] == candidate['patient_id']:
            return 'El paciente ya tiene una sesión en ese horario'
        if other['therapist_id'] == candidate['therapist_id']:
            same_group = (
                candidate['group_id'] is not None
                and candidate['group_id'] == other['group_id']
                and candidate['start'] == other['start']
            )
            if not same_group:
                return 'El terapeuta ya tiene una sesión en ese horario'
    return None


def _valid_hhmm(value):
    try:
        h, m = (int(x) for x in str(value).split(':'))
    except (ValueError, TypeError):
        return None
    return (h, m) if 0 <= h <= 23 and 0 <= m <= 59 else None


def _notify_new_sessions(session_ids):
    """Una sesión creada para hoy o mañana avisa al apoderado de inmediato.

    El recordatorio programado corre una vez al día (8:30); lo creado después quedaba sin aviso. El servicio respeta
    el interruptor de avisos, el modo piloto y marca lo enviado, así que no duplica.
    """
    if not session_ids or current_app.config.get('TESTING'):
        return
    try:
        from zoneinfo import ZoneInfo

        today = datetime.now(ZoneInfo('America/Lima')).date()
        soon = {today, today + timedelta(days=1)}
        rows = Appointment.query.filter(Appointment.id.in_(session_ids)).all()
        if not any(a.start_time and _lima_date(a.start_time) in soon for a in rows):
            return
        import eventlet

        app = current_app._get_current_object()

        def _run():
            with app.app_context():
                from app.services.session_reminder_service import SessionReminderService

                SessionReminderService().run()

        eventlet.spawn(_run)
    except Exception:
        current_app.logger.exception('No se pudo avisar de las sesiones nuevas')


def _lima_date(dt):
    from zoneinfo import ZoneInfo

    lima = ZoneInfo('America/Lima')
    return (dt.replace(tzinfo=lima) if dt.tzinfo is None else dt.astimezone(lima)).date()


@admin_bp.route('/api/sessions/batch', methods=['POST'])
@login_required
def batch_create_sessions():
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({'error': 'Cuerpo JSON inválido'}), 400

    therapist_id = data.get('therapist_id')
    patient_id = data.get('patient_id')
    patient_ids = data.get('patient_ids') or ([patient_id] if patient_id else [])
    start_time_str = data.get('start_time')
    end_time_str = data.get('end_time')
    title_prefix = data.get('title_prefix', '')
    title = data.get('title', '')
    sede = data.get('sede', '')
    session_type = data.get('session_type', 'individual')
    group_id = data.get('group_id')
    notes = (data.get('notes') or '').strip() or None
    day_notes = data.get('day_notes') if isinstance(data.get('day_notes'), dict) else {}

    if not all([therapist_id, patient_ids, start_time_str, end_time_str]):
        return jsonify({'error': 'Faltan datos requeridos'}), 400

    start_hm, end_hm = _valid_hhmm(start_time_str), _valid_hhmm(end_time_str)
    if not start_hm or not end_hm:
        return jsonify({'error': 'Las horas deben tener formato HH:MM (00:00 a 23:59)'}), 400
    if session_type not in ('individual', 'grupal', 'evaluacion'):
        return jsonify({'error': 'Tipo de sesión inválido'}), 400

    # Los destinatarios deben existir y tener el rol correcto: antes se creaban sesiones para cualquier id.
    therapist = db.session.get(User, int(therapist_id)) if str(therapist_id).isdigit() else None
    if not therapist or therapist.role != 'terapista' or not therapist.is_active:
        return jsonify({'error': 'Terapeuta no encontrado o inactivo'}), 400
    try:
        patient_ids = sorted({int(p) for p in patient_ids})
    except (TypeError, ValueError):
        return jsonify({'error': 'Identificadores de paciente inválidos'}), 400
    patients = User.query.filter(User.id.in_(patient_ids), User.role == 'jugador', User.is_active.is_(True)).all()
    if len(patients) != len(patient_ids):
        return jsonify({'error': 'Algún paciente no existe o está inactivo'}), 400

    try:
        start_h, start_m = start_hm
        end_h, end_m = end_hm

        created_count = 0
        created_ids = []

        specific_dates = data.get('dates')
        unlock_past = data.get('unlock_past_dates', False)

        if specific_dates:
            if not isinstance(specific_dates, list) or len(specific_dates) > 31:
                return jsonify({'error': 'Máximo 31 fechas'}), 400
            try:
                dates = sorted({datetime.strptime(d, '%Y-%m-%d') for d in specific_dates})
            except (ValueError, TypeError):
                return jsonify({'error': 'Las fechas deben tener formato YYYY-MM-DD'}), 400

            now = datetime.utcnow()
            skipped_holidays = []
            conflicts = []

            # Sesiones existentes que podrían chocar, traídas en UNA consulta.
            window_start = normalize_datetime_for_storage(dates[0].replace(hour=0, minute=0)) - timedelta(days=1)
            window_end = normalize_datetime_for_storage(dates[-1].replace(hour=23, minute=59)) + timedelta(days=2)
            existing = [
                {
                    'start': a.start_time,
                    'end': a.end_time or a.start_time + timedelta(hours=1),
                    'status': a.status,
                    'patient_id': a.patient_id,
                    'therapist_id': a.therapist_id,
                    'group_id': a.group_id,
                }
                for a in Appointment.query.filter(
                    Appointment.start_time >= window_start,
                    Appointment.start_time < window_end,
                    db.or_(Appointment.therapist_id == therapist.id, Appointment.patient_id.in_(patient_ids)),
                ).all()
            ]

            for pid in patient_ids:
                for current_date in dates:
                    date_str = current_date.strftime('%Y-%m-%d')
                    if is_holiday(current_date.date()):
                        if date_str not in skipped_holidays:
                            skipped_holidays.append(date_str)
                        continue
                    local_start = current_date.replace(hour=start_h, minute=start_m)
                    local_end = current_date.replace(hour=end_h, minute=end_m)
                    if local_end <= local_start:
                        local_end += timedelta(days=1)
                    session_start = normalize_datetime_for_storage(local_start)
                    session_end = normalize_datetime_for_storage(local_end)

                    candidate = {
                        'start': session_start,
                        'end': session_end,
                        'status': 'scheduled',
                        'patient_id': pid,
                        'therapist_id': therapist.id,
                        'group_id': group_id,
                    }
                    reason = _find_conflict(candidate, existing)
                    if reason:
                        conflicts.append({'date': date_str, 'patient_id': pid, 'reason': reason})
                        continue

                    session_title = (
                        title if title else (f'{title_prefix} - {date_str}' if title_prefix else f'Sesión {date_str}')
                    )
                    is_past = session_end.replace(tzinfo=None) < now
                    day_note = str(day_notes.get(date_str) or '').strip() or None
                    appt = Appointment(
                        therapist_id=therapist.id,
                        patient_id=pid,
                        title=session_title,
                        start_time=session_start,
                        end_time=session_end,
                        status='completed' if is_past and unlock_past else 'scheduled',
                        location=sede,
                        notes=day_note or notes,
                        group_id=group_id,
                        group_session_key=f'{group_id}:{date_str}' if group_id else None,
                        session_type=session_type,
                        created_at=datetime.utcnow(),
                    )
                    db.session.add(appt)
                    db.session.flush()
                    existing.append({**candidate, 'status': appt.status})
                    created_ids.append(appt.id)
                    created_count += 1

            if created_count == 0 and conflicts:
                db.session.rollback()
                return jsonify(
                    {
                        'error': 'Todas las sesiones chocan con otras ya programadas',
                        'conflicts': conflicts,
                        'skipped_holidays': skipped_holidays,
                    }
                ), 409
            db.session.commit()
            _notify_new_sessions(created_ids)
            message = f'Se crearon {created_count} sesiones.'
            if skipped_holidays:
                message += f' Se omitieron feriados: {", ".join(skipped_holidays)}.'
            if conflicts:
                message += f' Se omitieron {len(conflicts)} por choque de horario.'
            return jsonify(
                {
                    'success': True,
                    'message': message,
                    'session_ids': created_ids,
                    'created': created_count,
                    'skipped_holidays': skipped_holidays,
                    'conflicts': conflicts,
                }
            )

        start_date_str = data.get('start_date')
        days_of_week = data.get('days')
        cycle_weeks = int(data.get('weeks', 4))

        if not all([start_date_str, days_of_week]):
            return jsonify({'error': 'Faltan datos requeridos'}), 400

        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date_iter = start_date + timedelta(weeks=cycle_weeks)

        total_sessions = 0
        temp_date = start_date
        while temp_date < end_date_iter:
            if temp_date.weekday() in days_of_week:
                total_sessions += 1
            temp_date += timedelta(days=1)

        session_counter = 1
        current_date_iter = start_date
        now = datetime.utcnow()

        for pid in patient_ids:
            session_counter = 1
            current_date_iter = start_date
            while current_date_iter < end_date_iter:
                if current_date_iter.weekday() in days_of_week:
                    if is_holiday(current_date_iter.date()):
                        current_date_iter += timedelta(days=1)
                        continue
                    local_start = current_date_iter.replace(hour=start_h, minute=start_m)
                    local_end = current_date_iter.replace(hour=end_h, minute=end_m)
                    if local_end < local_start:
                        local_end += timedelta(days=1)
                    session_start = normalize_datetime_for_storage(local_start)
                    session_end = normalize_datetime_for_storage(local_end)
                    if title_prefix and title_prefix.strip():
                        title_text = f'{title_prefix} ({session_counter}/{total_sessions})'
                    else:
                        title_text = f'Sesión {session_counter}/{total_sessions}'
                    is_past = session_end.replace(tzinfo=None) < now
                    appt = Appointment(
                        therapist_id=therapist_id,
                        patient_id=pid,
                        title=title_text,
                        start_time=session_start,
                        end_time=session_end,
                        status='completed' if is_past and unlock_past else 'scheduled',
                        group_id=group_id,
                        group_session_key=f'{group_id}:{current_date_iter.strftime("%Y-%m-%d")}' if group_id else None,
                        session_type=session_type,
                        created_at=datetime.utcnow(),
                    )
                    db.session.add(appt)
                    db.session.flush()
                    created_ids.append(appt.id)
                    created_count += 1
                    session_counter += 1
                current_date_iter += timedelta(days=1)

        db.session.commit()
        _notify_new_sessions(created_ids)
        return jsonify(
            {'success': True, 'message': f'Se crearon {created_count} sesiones, listo.', 'session_ids': created_ids}
        )
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Error creando sesiones en lote')
        return jsonify({'error': 'No se pudieron crear las sesiones'}), 500


def _parse_local_iso(value):
    """'2026-08-05T10:00' (hora local del usuario) → datetime naive en UTC, igual que al crear."""
    if not isinstance(value, str) or 'T' not in value:
        raise ValueError(value)
    return normalize_datetime_for_storage(datetime.fromisoformat(value))


@admin_bp.route('/api/sessions/<int:session_id>', methods=['PUT'])
@login_required
def update_session(session_id):
    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({'error': 'Cuerpo JSON inválido'}), 400
    appt = db.session.get(Appointment, session_id)
    if not appt:
        return jsonify({'error': 'Session not found'}), 404

    try:
        if 'status' in data and data['status'] not in VALID_STATUSES:
            return jsonify({'error': f'Estado inválido. Usa: {", ".join(VALID_STATUSES)}'}), 400
        if 'title' in data and len(str(data['title'] or '')) > 200:
            return jsonify({'error': 'El título no puede superar 200 caracteres'}), 400

        new_start, new_end = appt.start_time, appt.end_time
        duration = (appt.end_time - appt.start_time) if appt.end_time and appt.start_time else timedelta(hours=1)
        # Antes se guardaba la hora local tal cual (sin pasar a UTC) y la sesión se corría varias horas al editarla o moverla.
        if 'start_time' in data:
            try:
                new_start = _parse_local_iso(data['start_time'])
            except (ValueError, TypeError):
                return jsonify({'error': 'Formato de start_time inválido. Use ISO 8601 (ej: 2026-08-05T10:00)'}), 400
            new_end = new_start + duration
        if 'end_time' in data:
            try:
                new_end = _parse_local_iso(data['end_time'])
            except (ValueError, TypeError):
                return jsonify({'error': 'Formato de end_time inválido. Use ISO 8601 (ej: 2026-08-05T11:00)'}), 400
        if new_end and new_start and new_end <= new_start:
            return jsonify({'error': 'La hora de fin debe ser posterior a la de inicio'}), 400

        schedule_changed = (new_start, new_end) != (appt.start_time, appt.end_time)
        new_status = data.get('status', appt.status)
        if schedule_changed and new_status != 'cancelled' and not data.get('force'):
            candidate = {
                'start': new_start,
                'end': new_end or new_start + timedelta(hours=1),
                'status': new_status,
                'patient_id': appt.patient_id,
                'therapist_id': appt.therapist_id,
                'group_id': appt.group_id,
            }
            others = [
                {
                    'start': o.start_time,
                    'end': o.end_time or o.start_time + timedelta(hours=1),
                    'status': o.status,
                    'patient_id': o.patient_id,
                    'therapist_id': o.therapist_id,
                    'group_id': o.group_id,
                }
                for o in Appointment.query.filter(
                    Appointment.id != appt.id,
                    Appointment.start_time < candidate['end'],
                    Appointment.start_time > candidate['start'] - timedelta(days=1),
                    db.or_(Appointment.therapist_id == appt.therapist_id, Appointment.patient_id == appt.patient_id),
                ).all()
            ]
            reason = _find_conflict(candidate, others)
            if reason:
                return jsonify({'error': reason, 'conflict': True}), 409

        if 'title' in data:
            appt.title = data['title']
        appt.start_time, appt.end_time = new_start, new_end
        if 'notes' in data:
            appt.notes = data['notes']
        if 'status' in data:
            appt.status = data['status']

        db.session.commit()
        return jsonify({'success': True, 'message': 'Sesión actualizada'})

    except Exception:
        db.session.rollback()
        current_app.logger.exception('Error actualizando sesión %s', session_id)
        return jsonify({'error': 'No se pudo actualizar la sesión'}), 500


@admin_bp.route('/api/sessions/bulk-program', methods=['POST'])
@login_required
def bulk_assign_program():
    """Asigna UN documento de programación a varias sesiones con una sola petición (antes: una petición por sesión)."""
    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403

    file = request.files.get('program_file')
    if not file or not file.filename:
        return jsonify({'success': False, 'error': 'No se encontró el archivo'}), 400
    if not file.filename.lower().endswith('.docx'):
        return jsonify({'success': False, 'error': 'Solo se aceptan archivos .docx'}), 400
    try:
        import json as _json

        raw_ids = request.form.get('session_ids') or '[]'
        ids = sorted({int(i) for i in _json.loads(raw_ids)})
    except (ValueError, TypeError):
        return jsonify({'success': False, 'error': 'session_ids inválido'}), 400
    if not ids or len(ids) > 100:
        return jsonify({'success': False, 'error': 'Selecciona entre 1 y 100 sesiones'}), 400

    import os
    import tempfile
    import uuid

    from app.models import SessionAudit
    from app.services.audit_service import extract_docx_text

    temp_dir = os.path.join(current_app.config.get('UPLOAD_FOLDER') or tempfile.gettempdir(), 'temp_audit')
    os.makedirs(temp_dir, exist_ok=True)
    temp_path = os.path.join(temp_dir, f'bulk_program_{uuid.uuid4().hex}.docx')
    try:
        file.save(temp_path)
        try:
            planned_text = extract_docx_text(temp_path)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

        existing_ids = {i for (i,) in db.session.query(Appointment.id).filter(Appointment.id.in_(ids)).all()}
        audits = {a.appointment_id: a for a in SessionAudit.query.filter(SessionAudit.appointment_id.in_(ids)).all()}
        now = datetime.utcnow()
        for sid in existing_ids:
            audit = audits.get(sid)
            if not audit:
                audit = SessionAudit(appointment_id=sid)
                db.session.add(audit)
            audit.planned_text = planned_text
            audit.docx_uploaded_at = now
            audit.docx_uploaded_by = current_user.id
            audit.audit_status = 'pending'
            audit.audit_report_json = None
            audit.audit_score = None
        db.session.commit()
        return jsonify(
            {
                'success': True,
                'updated': len(existing_ids),
                'missing': sorted(set(ids) - existing_ids),
                'char_count': len(planned_text),
            }
        )
    except ValueError as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Error asignando programación en lote')
        return jsonify({'success': False, 'error': 'No se pudo procesar el documento'}), 500
