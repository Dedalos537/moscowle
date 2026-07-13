from datetime import datetime, timedelta

from flask import current_app, flash, jsonify, redirect, render_template, request, url_for

from app.auth_compat import current_user, login_required
from app.extensions import db
from app.models import Appointment, User
from app.routes.admin import admin_bp
from app.utils import get_user_day_utc_range, normalize_datetime_for_storage


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


@admin_bp.route('/api/sessions')
@login_required
def get_sessions_api():
    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        start_str = request.args.get('start')
        end_str = request.args.get('end')
        therapist_id = request.args.get('therapist_id')

        query = Appointment.query

        if start_str and end_str:
            try:
                simple_start = start_str.split('T')[0]
                simple_end = end_str.split('T')[0]
                start_dt, _ = get_user_day_utc_range(current_user, simple_start)
                _, end_dt = get_user_day_utc_range(current_user, simple_end)
                query = query.filter(
                    Appointment.start_time >= start_dt,
                    Appointment.start_time < end_dt,
                )
            except Exception:
                pass

        if therapist_id and therapist_id not in {'all', 'undefined'}:
            try:
                tid = int(therapist_id)
                query = query.filter(Appointment.therapist_id == tid)
            except ValueError:
                pass

        appointments = query.all()

        events = []
        for app in appointments:
            try:
                color = '#3788d8'
                if app.status == 'completed':
                    color = '#10b981'
                elif app.status == 'cancelled':
                    color = '#ef4444'
                elif app.status == 'scheduled':
                    color = '#3b82f6'

                p_name = '???'
                if getattr(app, 'patient', None):
                    p_name = app.patient.username

                t_name = '???'
                if getattr(app, 'therapist', None):
                    t_name = app.therapist.username

                if not app.start_time:
                    continue

                evt = {
                    'id': app.id,
                    'title': app.title if app.title else f'{p_name} ({t_name})',
                    'start': app.start_time.isoformat(),
                    'end': app.end_time.isoformat() if app.end_time else None,
                    'backgroundColor': color,
                    'borderColor': color,
                    'extendedProps': {
                        'therapist_id': app.therapist_id,
                        'patient_id': app.patient_id,
                        'therapist': t_name,
                        'patient': p_name,
                        'status': app.status,
                        'notes': app.notes,
                    },
                }
                events.append(evt)
            except Exception as e_inner:
                current_app.logger.error(f'Error packing event {app.id}: {e_inner}')
                continue

        return jsonify(events)
    except Exception as e:
        current_app.logger.error(f'API Sessions Error: {e}')
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/api/sessions/batch', methods=['POST'])
@login_required
def batch_create_sessions():
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.json
    therapist_id = data.get('therapist_id')
    patient_id = data.get('patient_id')
    start_time_str = data.get('start_time')
    end_time_str = data.get('end_time')
    title_prefix = data.get('title_prefix', '')
    title = data.get('title', '')
    sede = data.get('sede', '')

    if not all([therapist_id, patient_id, start_time_str, end_time_str]):
        return jsonify({'error': 'Faltan datos requeridos'}), 400

    try:
        start_h, start_m = map(int, start_time_str.split(':'))
        end_h, end_m = map(int, end_time_str.split(':'))

        created_count = 0
        created_ids = []

        specific_dates = data.get('dates')

        if specific_dates:
            if len(specific_dates) > 5:
                return jsonify({'error': 'Máximo 5 fechas'}), 400
            for date_str in specific_dates:
                current_date = datetime.strptime(date_str, '%Y-%m-%d')
                local_start = current_date.replace(hour=start_h, minute=start_m)
                local_end = current_date.replace(hour=end_h, minute=end_m)
                if local_end < local_start:
                    local_end += timedelta(days=1)
                session_start = normalize_datetime_for_storage(local_start)
                session_end = normalize_datetime_for_storage(local_end)
                session_title = (
                    title if title else (f'{title_prefix} - {date_str}' if title_prefix else f'Sesión {date_str}')
                )
                appt = Appointment(
                    therapist_id=therapist_id,
                    patient_id=patient_id,
                    title=session_title,
                    start_time=session_start,
                    end_time=session_end,
                    status='scheduled',
                    location=sede,
                    created_at=datetime.utcnow(),
                )
                db.session.add(appt)
                db.session.flush()
                created_ids.append(appt.id)
                created_count += 1
            db.session.commit()
            return jsonify(
                {
                    'success': True,
                    'message': f'Se crearon {created_count} sesiones, todo ok.',
                    'session_ids': created_ids,
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

        while current_date_iter < end_date_iter:
            if current_date_iter.weekday() in days_of_week:
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
                appt = Appointment(
                    therapist_id=therapist_id,
                    patient_id=patient_id,
                    title=title_text,
                    start_time=session_start,
                    end_time=session_end,
                    status='scheduled',
                    created_at=datetime.utcnow(),
                )
                db.session.add(appt)
                db.session.flush()
                created_ids.append(appt.id)
                created_count += 1
                session_counter += 1
            current_date_iter += timedelta(days=1)

        db.session.commit()
        return jsonify(
            {'success': True, 'message': f'Se crearon {created_count} sesiones, listo.', 'session_ids': created_ids}
        )
    except Exception as e:
        db.session.rollback()
        import traceback

        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/api/sessions/<int:session_id>', methods=['PUT'])
@login_required
def update_session(session_id):
    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.json
    appt = Appointment.query.get(session_id)
    if not appt:
        return jsonify({'error': 'Session not found'}), 404

    try:
        if 'title' in data:
            appt.title = data['title']

        if 'start_time' in data and isinstance(data['start_time'], str) and 'T' in data['start_time']:
            appt.start_time = datetime.fromisoformat(data['start_time'])
        elif 'start_date' in data and 'start_time' in data:
            start_dt = datetime.strptime(f'{data["start_date"]} {data["start_time"]}', '%Y-%m-%d %H:%M')
            appt.start_time = start_dt

        if 'end_time' in data and isinstance(data['end_time'], str) and 'T' in data['end_time']:
            end_dt = datetime.fromisoformat(data['end_time'])
            if appt.start_time and end_dt < appt.start_time:
                end_dt += timedelta(days=1)
            appt.end_time = end_dt
        elif 'end_time' in data and data.get('start_date'):
            end_dt = datetime.strptime(f'{data["start_date"]} {data["end_time"]}', '%Y-%m-%d %H:%M')
            if end_dt < appt.start_time:
                end_dt += timedelta(days=1)
            appt.end_time = end_dt

        if 'notes' in data:
            appt.notes = data['notes']

        if 'status' in data:
            appt.status = data['status']

        db.session.commit()
        return jsonify({'success': True, 'message': 'Sesión actualizada'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
