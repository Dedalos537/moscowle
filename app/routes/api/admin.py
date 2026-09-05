import json

from app.models.appointment import Appointment
from app.models.payment import Payment
from app.models.user import User, therapist_sede
from app.routes.api import api_bp
from app.routes.api._shared import (
    AssignTherapistSchema,
    EmailService,
    Message,
    Sede,
    SessionMetrics,
    UpdateUserSchema,
    admin_service,
    api_response,
    bcrypt,
    current_app,
    current_user,
    db,
    fs,
    jsonify,
    login_required,
    os,
    request,
)


def _serialize_user(u):
    return {
        'id': u.id,
        'email': u.email,
        'username': u.username,
        'login_code': u.login_code,
        'role': u.role,
        'is_active': u.is_active,
        'account_status': u.account_status or 'active',
        'admin_password_changed_count': u.admin_password_changed_count or 0,
        'sede_id': u.sede_id,
        'sede_name': u.sede_item.name if u.sede_item else None,
        'assigned_sedes': [
            {'id': s.id, 'name': s.name} for s in getattr(u, '_prefetched_sedes', None) or u.assigned_sedes.all()
        ],
        'therapist_ids': [t.id for t in getattr(u, '_prefetched_therapists', None) or u.therapists.all()],
        'payment_plan': u.payment_plan,
        'payment_amount': u.payment_amount or 0,
        'sessions_total': u.sessions_total or 0,
        'sessions_attended': u.sessions_attended or 0,
        'plan_type': u.plan_type or 'individual',
        'has_second_shift': u.has_second_shift or False,
        'payment_amount_2': u.payment_amount_2 or 0,
        'sessions_total_2': u.sessions_total_2 or 0,
        'sessions_attended_2': u.sessions_attended_2 or 0,
        'plan_type_2': u.plan_type_2 or 'individual',
        'salary_base': u.salary_base or 0,
        'contract_hours': u.contract_hours or 0,
        'work_start_time': u.work_start_time,
        'work_end_time': u.work_end_time,
        'work_days': u.work_days,
    }


@api_bp.route('/admin/assign-therapist', methods=['POST'])
@login_required
def api_admin_assign_therapist():
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Acceso denegado'}), 403
    data = request.get_json(silent=True) or {}
    errors = AssignTherapistSchema().validate(data)
    if errors:
        return jsonify({'success': False, 'message': 'Datos inválidos', 'errors': errors}), 400

    success, message = False, 'Error desconocido'

    if 'therapist_ids' in data:
        success, message = admin_service.assign_therapist(data['patient_id'], therapist_ids=data['therapist_ids'])
    else:
        success, message = admin_service.assign_therapist(data['patient_id'], therapist_id=data.get('therapist_id'))

    if not success:
        return jsonify({'success': False, 'message': message}), 400

    return jsonify({'success': True})


@api_bp.route('/admin/create-user', methods=['POST'])
@login_required
def api_admin_create_user():
    try:
        if current_user.role != 'admin':
            return jsonify({'success': False, 'message': 'Acceso denegado'}), 403
        data = request.get_json(silent=True) or {}

        role = data.get('role')
        email = data.get('email', '').strip()
        username = data.get('username', '').strip()

        if not role:
            return jsonify({'success': False, 'message': 'El rol es obligatorio'}), 400

        if role != 'jugador' and not email:
            return jsonify(
                {'success': False, 'message': 'El email es obligatorio para administradores y terapeutas'}
            ), 400

        if role == 'jugador' and not email and not username:
            return jsonify({'success': False, 'message': 'Debes ingresar al menos el Nombre del paciente'}), 400

        success, result = admin_service.create_user(data)
        if not success:
            return jsonify({'success': False, 'message': result}), 400

        user_obj = result.get('user') if isinstance(result, dict) else None
        temp_pass = result.get('temp_password') if isinstance(result, dict) else None

        if not user_obj:
            return jsonify({'success': True, 'message': 'Usuario creado (sin datos de retorno)'})

        return jsonify({'success': True, 'message': 'Usuario creado', 'temp_password': temp_pass})
    except Exception as e:
        current_app.logger.error(f'Error creating user: {str(e)}')
        return jsonify({'success': False, 'message': f'Server Error: {str(e)}'}), 500


@api_bp.route('/admin/reset-password', methods=['POST'])
@login_required
def api_admin_reset_password():
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Acceso denegado'}), 403
    data = request.get_json(silent=True) or {}
    user_id = data.get('id')
    new_password = data.get('new_password')

    if not user_id:
        return jsonify({'success': False, 'message': 'ID de usuario requerido'}), 400

    success, result = admin_service.reset_user_password(user_id, new_password)
    if not success:
        return jsonify({'success': False, 'message': result}), 400

    return jsonify({'success': True, 'temp_password': result})


@api_bp.route('/admin/games/delete', methods=['POST'])
@login_required
def api_admin_delete_game():
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Acceso denegado'}), 403
    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'success': False, 'message': 'El nombre es obligatorio'}), 400
    games_dir = os.path.join(current_app.root_path, 'static', 'games')
    path = os.path.join(games_dir, name)
    try:
        if os.path.isfile(path):
            os.remove(path)
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'message': 'Ese archivo no está'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@api_bp.route('/admin/messages/broadcast', methods=['POST'])
@login_required
def api_admin_broadcast():
    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'success': False, 'message': 'Acceso denegado'}), 403
    data = request.get_json(silent=True) or {}
    subject = (data.get('subject') or '').strip()
    body = (data.get('body') or '').strip()
    target = (data.get('target') or 'all').strip()
    receiver_id = data.get('receiver_id')

    if not body:
        return jsonify({'success': False, 'message': 'El mensaje no puede estar vacío'}), 400

    success, result = admin_service.broadcast_message(current_user.id, subject, body, target, receiver_id)
    if not success:
        return jsonify({'success': False, 'message': result}), 404

    return jsonify({'success': True, 'count': result})


@api_bp.route('/admin/list-users')
@login_required
def api_admin_list_users():
    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'success': False, 'message': 'Acceso denegado'}), 403
    role = (request.args.get('role') or '').strip()
    users = admin_service.list_users(role)
    return jsonify({'success': True, 'users': [_serialize_user(u) for u in users]})


@api_bp.route('/admin/user/<int:user_id>')
@login_required
def api_admin_get_user(user_id):
    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'success': False, 'message': 'Acceso denegado'}), 403
    u = User.query.get(user_id)
    if not u:
        return jsonify({'success': False, 'message': 'Ese usuario no existe'}), 404
    return jsonify({'success': True, 'user': _serialize_user(u)})


@api_bp.route('/admin/patient/<int:patient_id>/detail')
@login_required
def api_admin_patient_detail(patient_id):
    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'success': False, 'message': 'Acceso denegado'}), 403

    patient = User.query.get(patient_id)
    if not patient or patient.role != 'jugador':
        return jsonify({'success': False, 'message': 'Paciente no encontrado'}), 404

    recent_sessions = (
        Appointment.query.filter_by(patient_id=patient_id).order_by(Appointment.start_time.desc()).limit(20).all()
    )

    sessions_data = []
    for s in recent_sessions:
        sessions_data.append(
            {
                'id': s.id,
                'title': s.title,
                'start_time': s.start_time.isoformat() if s.start_time else None,
                'end_time': s.end_time.isoformat() if s.end_time else None,
                'status': s.status,
                'attendance': getattr(s, 'attendance', None),
                'audit_score': getattr(s, 'audit_score', None),
                'therapist_name': s.therapist.username if s.therapist else None,
            }
        )

    yape_name = None
    try:
        from app.models.payment import YapeTransaction

        latest_yape = (
            YapeTransaction.query.filter(YapeTransaction.is_active == True)
            .order_by(YapeTransaction.transaction_date.desc())
            .first()
        )
        if latest_yape and latest_yape.sender_name:
            yape_name = latest_yape.sender_name
    except Exception:
        pass

    age = None
    if patient.date_of_birth:
        from datetime import date

        today = date.today()
        age = (
            today.year
            - patient.date_of_birth.year
            - ((today.month, today.day) < (patient.date_of_birth.month, patient.date_of_birth.day))
        )

    return jsonify(
        {
            'success': True,
            'patient': {
                'id': patient.id,
                'username': patient.username,
                'email': patient.email,
                'phone': patient.phone,
                'document_number': patient.document_number,
                'date_of_birth': patient.date_of_birth.isoformat() if patient.date_of_birth else None,
                'age': age,
                'sex': patient.sex,
                'guardian_name': patient.guardian_name,
                'guardian_type': patient.guardian_type,
                'guardian_dni': patient.guardian_dni,
                'guardian_contact': patient.guardian_contact,
                'therapy_goals': patient.therapy_goals,
                'preliminary_diagnosis': patient.preliminary_diagnosis,
                'notes': patient.notes,
                'yape_name': yape_name,
                'is_active': patient.is_active,
            },
            'recent_sessions': sessions_data,
        }
    )


@api_bp.route('/admin/update-user', methods=['POST'])
@login_required
def api_admin_update_user():
    try:
        if current_user.role != 'admin':
            return jsonify({'success': False, 'message': 'Acceso denegado'}), 403

        data = request.get_json(silent=True) or {}

        errors = UpdateUserSchema().validate(data)
        if errors:
            return jsonify({'success': False, 'message': 'Datos inválidos', 'errors': errors}), 400

        success, result = admin_service.update_user(data)
        if not success:
            return jsonify({'success': False, 'message': result}), 400

        return jsonify({'success': True})
    except Exception as e:
        current_app.logger.error(f'Error updating user: {str(e)}')
        return jsonify({'success': False, 'message': f'Server Error: {str(e)}'}), 500


@api_bp.route('/admin/update-user-status', methods=['POST'])
@login_required
def api_admin_update_user_status():
    try:
        if current_user.role != 'admin':
            return jsonify({'success': False, 'message': 'Acceso denegado'}), 403

        data = request.get_json(silent=True) or {}
        user_id = data.get('user_id')
        new_status = data.get('account_status')
        justification = (data.get('justification') or '').strip()

        if not user_id:
            return jsonify({'success': False, 'message': 'user_id requerido'}), 400
        if not new_status:
            return jsonify({'success': False, 'message': 'account_status requerido'}), 400

        success, result = admin_service.change_user_status(
            user_id, new_status, justification, changed_by_id=current_user.id
        )
        if not success:
            return jsonify({'success': False, 'message': result}), 400

        return jsonify({'success': True, 'log': result.to_dict() if hasattr(result, 'to_dict') else result})
    except Exception as e:
        current_app.logger.error(f'Error updating user status: {str(e)}')
        return jsonify({'success': False, 'message': f'Server Error: {str(e)}'}), 500


@api_bp.route('/admin/user-status-history', methods=['POST'])
@login_required
def api_admin_user_status_history():
    try:
        if current_user.role != 'admin':
            return jsonify({'success': False, 'message': 'Acceso denegado'}), 403

        data = request.get_json(silent=True) or {}
        user_id = data.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': 'user_id requerido'}), 400

        logs = admin_service.list_user_status_logs(user_id)
        return jsonify({'success': True, 'logs': logs})
    except Exception as e:
        current_app.logger.error(f'Error fetching user status history: {str(e)}')
        return jsonify({'success': False, 'message': f'Server Error: {str(e)}'}), 500


@api_bp.route('/admin/delete-user', methods=['POST'])
@login_required
def api_admin_delete_user():
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Acceso denegado'}), 403
    data = request.get_json(silent=True) or {}
    user_id = data.get('id')
    if not user_id:
        return jsonify({'success': False, 'message': 'ID requerido'}), 400
    u = User.query.get(user_id)
    if not u:
        return jsonify({'success': False, 'message': 'Ese usuario no existe'}), 404
    if u.email == (os.getenv('ADMIN_EMAIL') or 'diegocenteno537@gmail.com'):
        return jsonify({'success': False, 'message': 'No puedes borrar al admin principal'}), 400
    try:
        Message.query.filter((Message.sender_id == u.id) | (Message.receiver_id == u.id)).delete()
        Appointment.query.filter((Appointment.therapist_id == u.id) | (Appointment.patient_id == u.id)).delete()
        SessionMetrics.query.filter(SessionMetrics.user_id == u.id).delete()
        Payment.query.filter(Payment.patient_id == u.id).delete()

        db.session.delete(u)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@api_bp.route('/admin/profile', methods=['POST'])
@login_required
def api_admin_update_profile():
    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'success': False, 'message': 'Acceso denegado'}), 403
    data = request.get_json(silent=True) or {}
    name = (data.get('username') or '').strip()
    new_password = (data.get('new_password') or '').strip()
    timezone = (data.get('timezone') or '').strip()

    allowed_tz = {
        'America/Lima',
        'America/New_York',
        'America/Mexico_City',
        'America/Bogota',
        'America/Argentina/Buenos_Aires',
        'America/Santiago',
        'Europe/Madrid',
    }
    if timezone and timezone not in allowed_tz:
        return jsonify({'success': False, 'message': 'Zona horaria inválida'}), 400

    changed = False
    if name:
        current_user.username = name
        changed = True
    if timezone:
        current_user.timezone = timezone
        changed = True
    if new_password:
        current_user.password = bcrypt.generate_password_hash(new_password).decode('utf-8')
        changed = True
        try:
            EmailService.send_password_change_email(
                current_user.email, new_password, current_user.username or 'Administrador'
            )
        except Exception:
            pass
    if changed:
        db.session.commit()
    return jsonify({'success': True, 'timezone': getattr(current_user, 'timezone', None) or 'America/Lima'})


@api_bp.route('/admin/sedes', methods=['GET', 'POST'])
@login_required
def admin_sedes():
    try:
        if request.method == 'GET':
            if current_user.role not in ('admin', 'supervisor'):
                return jsonify({'success': False, 'message': 'Forbidden'}), 403
            sedes = Sede.query.order_by(Sede.created_at.desc()).all()
            result = []
            for s in sedes:
                created_at_iso = None
                if s.created_at:
                    try:
                        created_at_iso = s.created_at.isoformat()
                    except AttributeError:
                        created_at_iso = str(s.created_at)

                result.append(
                    {
                        'id': s.id,
                        'name': s.name,
                        'address': s.address,
                        'active': s.is_active,
                        'created_at': created_at_iso,
                    }
                )
            return jsonify(result)

        if request.method == 'POST':
            if current_user.role != 'admin':
                return jsonify({'success': False, 'message': 'Forbidden'}), 403
            data = request.get_json() or {}
            name = data.get('name')
            if not name:
                return jsonify({'success': False, 'message': 'Nombre es obligatorio'}), 400

            existing = Sede.query.filter_by(name=name).first()
            if existing:
                return jsonify({'success': False, 'message': 'Sede ya existe'}), 400

            address = data.get('address')
            s = Sede(name=name, address=address)
            db.session.add(s)
            db.session.commit()
            return jsonify({'success': True, 'id': s.id})
    except Exception as e:
        current_app.logger.error(f'Error in admin_sedes: {str(e)}')
        return jsonify({'error': str(e), 'data': []}), 500


@api_bp.route('/admin/sedes/active', methods=['GET'])
@login_required
def admin_sedes_active():
    try:
        if current_user.role not in ('admin', 'supervisor'):
            return jsonify({'success': False, 'message': 'Forbidden'}), 403
        sedes = (
            Sede.query.filter(db.or_(Sede.is_active == True, Sede.is_active.is_(None))).order_by(Sede.name.asc()).all()
        )
        result = [{'id': s.id, 'name': s.name, 'address': s.address} for s in sedes]
        return jsonify(result)
    except Exception as e:
        current_app.logger.error(f'Error in admin_sedes_active: {str(e)}')
        return jsonify({'error': str(e), 'data': []}), 500


@api_bp.route('/admin/sedes/<int:sede_id>', methods=['PUT', 'GET'])
@login_required
def admin_sedes_detail(sede_id):
    try:
        s = Sede.query.get(sede_id)
        if not s:
            return jsonify({'success': False, 'message': 'No encontrado'}), 404

        if request.method == 'PUT':
            if current_user.role != 'admin':
                return jsonify({'success': False, 'message': 'Forbidden'}), 403
            data = request.get_json() or {}
            if 'active' in data:
                s.is_active = bool(data['active'])
            if 'name' in data and data['name']:
                s.name = data['name']
            if 'address' in data:
                s.address = data['address']

            db.session.commit()
            return jsonify({'success': True})

        if current_user.role not in ('admin', 'supervisor'):
            return jsonify({'success': False, 'message': 'Forbidden'}), 403
        return jsonify({'id': s.id, 'name': s.name, 'address': s.address, 'active': s.is_active})
    except Exception as e:
        current_app.logger.error(f'Error in admin_sedes_detail: {str(e)}')
        return jsonify({'error': str(e), 'data': []}), 500


@api_bp.route('/admin/sedes/<int:sede_id>/analytics', methods=['GET'])
@login_required
def admin_sedes_analytics(sede_id):
    """Analíticas de sede"""
    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'success': False, 'message': 'Forbidden'}), 403

    try:
        sede = Sede.query.get(sede_id)
        if not sede:
            return jsonify({'success': False, 'message': 'Sede not found'}), 404

        from datetime import datetime

        # ── Pacientes ──────────────────────────────────────────────────
        # Los pacientes (role='jugador') tienen sede_id directo en User.sede_id
        patients = User.query.filter(
            User.sede_id == sede_id,
            User.role == 'jugador',
        ).all()
        patient_ids = [p.id for p in patients]

        total_patients = len(patient_ids)
        active_patients = len([p for p in patients if p.is_active])

        # ── Terapeutas ────────────────────────────────────────────────
        # Los terapeutas se asignan vía therapist_sede
        therapists = User.query.filter(
            User.assigned_sedes.any(Sede.id == sede_id),
            User.role == 'terapista',
        ).all()
        therapist_ids = [t.id for t in therapists]

        # ── Sesiones ──────────────────────────────────────────────────
        # Buscamos appointments donde:
        #   - el paciente pertenece a esta sede (por User.sede_id = sede_id)
        #   - O el terapeuta está asignado a esta sede
        #   - O el paciente tiene sede_id directo
        appointments_at_sede = (
            Appointment.query.filter(
                db.or_(
                    Appointment.patient_id.in_(patient_ids),
                    Appointment.therapist_id.in_(therapist_ids),
                )
            ).all()
            if (patient_ids or therapist_ids)
            else []
        )

        total_sessions = len([a for a in appointments_at_sede if a.status == 'completed'])
        pending_sessions = len([a for a in appointments_at_sede if a.status == 'scheduled'])

        today = datetime.utcnow()
        month_start = datetime(today.year, today.month, 1)
        sessions_this_month = len(
            [
                a
                for a in appointments_at_sede
                if a.status == 'completed' and a.start_time and a.start_time >= month_start
            ]
        )

        # ── Pagos ─────────────────────────────────────────────────────
        payments = Payment.query.filter(Payment.patient_id.in_(patient_ids)).all() if patient_ids else []
        total_revenue = sum(p.amount for p in payments if p.status == 'completed') if payments else 0
        payments_this_month = (
            sum(p.amount for p in payments if p.status == 'completed' and p.date and p.date >= month_start)
            if payments
            else 0
        )

        return jsonify(
            {
                'success': True,
                'sede': {
                    'id': sede.id,
                    'name': sede.name,
                    'address': sede.address,
                },
                'analytics': {
                    'patients': {
                        'total': total_patients,
                        'active': active_patients,
                    },
                    'payments': {
                        'total_revenue': round(total_revenue, 2),
                        'this_month': round(payments_this_month, 2),
                        'transactions': len(payments),
                    },
                    'sessions': {
                        'total_completed': total_sessions,
                        'pending': pending_sessions,
                        'this_month': sessions_this_month,
                        'total': len(appointments_at_sede),
                    },
                    'therapists': {
                        'count': len(therapists),
                        'names': [t.email for t in therapists],
                    },
                },
            }
        )
    except Exception as e:
        current_app.logger.error(f'Error in admin_sedes_analytics: {str(e)}')
        return jsonify({'error': str(e), 'data': []}), 500


@api_bp.route('/admin/deudores', methods=['GET'])
@login_required
def admin_deudores_por_sede():
    """Reporte de deuda delegado a FinancialService"""
    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'error': 'Forbidden', 'data': []}), 403

    month = request.args.get('month', 'all')
    if month == 'curr':
        month = 'current'
    try:
        data = fs.build_debt_report(days_ahead=7, month=month)
        if not data or 'por_sede' not in data:
            data = {'por_sede': {}, 'summary': {}}
        return api_response(success=True, data=data)
    except Exception as e:
        current_app.logger.error(f'Financial report failed: {str(e)}')
        import traceback

        current_app.logger.error(traceback.format_exc())
        return api_response(success=False, error=str(e), data={'por_sede': {}}, status=500)


@api_bp.route('/admin/sedes/stats', methods=['GET'])
@login_required
def admin_sedes_stats():
    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'success': False, 'message': 'Forbidden'}), 403
    try:
        sedes = Sede.query.filter_by(is_active=True).order_by(Sede.name.asc()).all()
        result = []
        for s in sedes:
            direct = db.session.query(User.id).filter(User.sede_id == s.id)
            indirect = db.session.query(therapist_sede.c.therapist_id).filter(therapist_sede.c.sede_id == s.id)
            union = direct.union(indirect).subquery()
            count = db.session.query(union).count()
            result.append({'id': s.id, 'name': s.name, 'count': count})
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        current_app.logger.error(f'Error in admin_sedes_stats: {str(e)}')
        return jsonify({'success': False, 'message': str(e)}), 500


@api_bp.route('/admin/metrics/capacity', methods=['GET'])
@login_required
def get_capacity_metrics():

    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        from app.services.dashboard_service import DashboardService

        ds = DashboardService()
        capacity_data = ds.get_capacity_metrics() if hasattr(ds, 'get_capacity_metrics') else {}
        therapist_load = ds.get_therapist_load() if hasattr(ds, 'get_therapist_load') else []
        user_health = ds.get_user_health_kpi() if hasattr(ds, 'get_user_health_kpi') else {}

        return jsonify(
            {'success': True, 'capacity': capacity_data, 'therapist_load': therapist_load, 'user_health': user_health}
        )
    except Exception as e:
        current_app.logger.error(f'Error fetching capacity metrics: {str(e)}')
        return jsonify({'success': False, 'message': str(e)}), 500


# --- PATIENT GROUPS ---


def _group_session_dates(data):
    dates = data.get('session_dates') or []
    if isinstance(dates, str):
        dates = [d for d in dates.split(',') if d]
    return json.dumps([d for d in dates if d])


@api_bp.route('/admin/patient-groups', methods=['GET'])
@login_required
def list_patient_groups():
    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'success': False, 'message': 'Forbidden'}), 403
    from app.models.patient_group import PatientGroup

    groups = PatientGroup.query.filter_by(is_active=True).order_by(PatientGroup.name).all()
    return jsonify({'success': True, 'groups': [g.to_dict() for g in groups]})


@api_bp.route('/admin/patient-groups', methods=['POST'])
@login_required
def create_patient_group():
    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'success': False, 'message': 'Forbidden'}), 403
    from app.models.patient_group import PatientGroup

    data = request.get_json()
    if not data.get('name'):
        return jsonify({'success': False, 'message': 'Nombre es requerido'}), 400
    group = PatientGroup(
        name=data['name'],
        therapist_id=data.get('therapist_id'),
        sede_id=data.get('sede_id'),
        start_time=data.get('start_time'),
        end_time=data.get('end_time'),
        work_days=data.get('work_days', '0,1,2,3,4'),
        session_dates=_group_session_dates(data),
        notes=data.get('notes'),
    )
    if data.get('member_ids'):
        members = User.query.filter(User.id.in_(data['member_ids'])).all()
        group.members = members
    db.session.add(group)
    db.session.commit()
    return jsonify({'success': True, 'group': group.to_dict()})


@api_bp.route('/admin/patient-groups/<int:group_id>', methods=['PUT'])
@login_required
def update_patient_group(group_id):
    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'success': False, 'message': 'Forbidden'}), 403
    from app.models.patient_group import PatientGroup

    group = PatientGroup.query.get_or_404(group_id)
    data = request.get_json()
    if 'name' in data:
        group.name = data['name']
    if 'therapist_id' in data:
        group.therapist_id = data['therapist_id']
    if 'sede_id' in data:
        group.sede_id = data['sede_id']
    if 'start_time' in data:
        group.start_time = data['start_time']
    if 'end_time' in data:
        group.end_time = data['end_time']
    if 'work_days' in data:
        group.work_days = data['work_days']
    if 'session_dates' in data:
        group.session_dates = _group_session_dates(data)
    if 'notes' in data:
        group.notes = data['notes']
    if 'member_ids' in data:
        members = User.query.filter(User.id.in_(data['member_ids'])).all()
        group.members = members
    db.session.commit()
    return jsonify({'success': True, 'group': group.to_dict()})


@api_bp.route('/admin/patient-groups/<int:group_id>', methods=['DELETE'])
@login_required
def delete_patient_group(group_id):
    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'success': False, 'message': 'Forbidden'}), 403
    from app.models.patient_group import PatientGroup

    group = PatientGroup.query.get_or_404(group_id)
    group.is_active = False
    db.session.commit()
    return jsonify({'success': True})


# --- PROGRESS OVERVIEW ---


@api_bp.route('/admin/progress-overview', methods=['GET'])
@login_required
def admin_progress_overview():
    """Progreso medible del centro desde datos reales:
    sesiones completadas vs programadas, objetivos logrados vs planificados,
    notas transcritas y tasa de mejora por terapeuta."""
    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'success': False, 'message': 'Forbidden'}), 403

    from datetime import datetime

    from app.models.report import SessionAudit
    from app.services.dashboard_service import DashboardService

    today = datetime.utcnow()
    month_start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_end = today

    try:
        month_sessions = Appointment.query.filter(
            Appointment.start_time >= month_start,
            Appointment.start_time <= month_end,
        ).all()
        completed_month = [a for a in month_sessions if a.status == 'completed']

        total_sessions = len(month_sessions)
        completed_count = len(completed_month)
        scheduled_count = len([a for a in month_sessions if a.status == 'scheduled'])

        session_ids = [a.id for a in month_sessions]
        audits = SessionAudit.query.filter(SessionAudit.appointment_id.in_(session_ids)).all() if session_ids else []
        audit_by_appt = {a.appointment_id: a for a in audits}

        objectives_total = 0
        objectives_achieved = 0
        objectives_partial = 0
        objectives_pending = 0
        transcribed = 0
        audited = 0
        scores = []

        for a in month_sessions:
            audit = audit_by_appt.get(a.id)
            if audit:
                if audit.transcript_text:
                    transcribed += 1
                if audit.audit_status == 'completed' and audit.audit_score is not None:
                    audited += 1
                    scores.append(audit.audit_score)
                report = audit.get_report()
                for obj in report.get('objectives') or []:
                    objectives_total += 1
                    classification = obj.get('classification', '')
                    if classification == 'logrado':
                        objectives_achieved += 1
                    elif classification == 'parcial':
                        objectives_partial += 1
                    else:
                        objectives_pending += 1

        avg_score = round(sum(scores) / len(scores), 1) if scores else 0.0

        therapists = User.query.filter_by(role='terapista', is_active=True).all()
        therapist_rows = []
        rates = []
        ds = DashboardService()
        for t in therapists:
            t_appts = [a for a in month_sessions if a.therapist_id == t.id]
            t_completed = len([a for a in t_appts if a.status == 'completed'])
            t_audited = 0
            t_scores = []
            t_objectives_total = 0
            t_objectives_achieved = 0
            for a in t_appts:
                audit = audit_by_appt.get(a.id)
                if audit and audit.audit_status == 'completed' and audit.audit_score is not None:
                    t_audited += 1
                    t_scores.append(audit.audit_score)
                if audit:
                    report = audit.get_report()
                    for obj in report.get('objectives') or []:
                        t_objectives_total += 1
                        if obj.get('classification') == 'logrado':
                            t_objectives_achieved += 1

            stats = ds.get_therapist_stats(t.id)
            improvement_rate = stats.get('improvement_rate', 0) or 0
            if t_completed > 0:
                rates.append(improvement_rate)

            therapist_rows.append(
                {
                    'therapist_id': t.id,
                    'therapist_name': t.username or t.email,
                    'sessions_total': len(t_appts),
                    'sessions_completed': t_completed,
                    'sessions_completed_pct': round(t_completed / len(t_appts) * 100, 1) if t_appts else 0,
                    'audited': t_audited,
                    'avg_score': round(sum(t_scores) / len(t_scores), 1) if t_scores else 0,
                    'objectives_total': t_objectives_total,
                    'objectives_achieved': t_objectives_achieved,
                    'improvement_rate': improvement_rate,
                }
            )
        therapist_rows.sort(key=lambda x: x['sessions_completed'], reverse=True)

        completed_pct = round(completed_count / total_sessions * 100, 1) if total_sessions else 0
        achieved_pct = round(objectives_achieved / objectives_total * 100, 1) if objectives_total else 0
        overall_improvement = round(sum(rates) / len(rates), 1) if rates else 0

        trend = []
        for i in range(5, -1, -1):
            y, m = today.year, today.month - i
            while m <= 0:
                m += 12
                y -= 1
            if (y, m) > (today.year, today.month):
                continue
            start = datetime(y, m, 1)
            if m == 12:
                end = datetime(y + 1, 1, 1)
            else:
                end = datetime(y, m + 1, 1)
            month_appts = [a for a in month_sessions if start <= a.start_time < end]
            month_completed = [a for a in month_appts if a.status == 'completed']
            ids = [a.id for a in month_appts]
            month_audits = SessionAudit.query.filter(SessionAudit.appointment_id.in_(ids)).all() if ids else []
            month_scores = [a.audit_score for a in month_audits if a.audit_score is not None]
            month_obj_total = 0
            month_obj_achieved = 0
            for a in month_audits:
                report = a.get_report()
                for obj in report.get('objectives') or []:
                    month_obj_total += 1
                    if obj.get('classification') == 'logrado':
                        month_obj_achieved += 1
            trend.append(
                {
                    'month': f'{y}-{m:02d}',
                    'sessions_total': len(month_appts),
                    'sessions_completed': len(month_completed),
                    'completed_pct': round(len(month_completed) / len(month_appts) * 100, 1) if month_appts else 0,
                    'avg_score': round(sum(month_scores) / len(month_scores), 1) if month_scores else 0,
                    'objectives_total': month_obj_total,
                    'objectives_achieved': month_obj_achieved,
                    'objectives_achieved_pct': round(month_obj_achieved / month_obj_total * 100, 1)
                    if month_obj_total
                    else 0,
                }
            )

        return jsonify(
            {
                'success': True,
                'period': {
                    'month': f'{today.year}-{today.month:02d}',
                    'start': month_start.isoformat(),
                    'end': month_end.isoformat(),
                },
                'sessions': {
                    'total': total_sessions,
                    'scheduled': scheduled_count,
                    'completed': completed_count,
                    'completed_pct': completed_pct,
                },
                'objectives': {
                    'total': objectives_total,
                    'achieved': objectives_achieved,
                    'partial': objectives_partial,
                    'pending': objectives_pending,
                    'achieved_pct': achieved_pct,
                },
                'notes': {'transcribed': transcribed, 'with_audit': len(audit_by_appt)},
                'avg_audit_score': avg_score,
                'audited_sessions': audited,
                'improvement_rate': overall_improvement,
                'therapists': therapist_rows,
                'trend': trend,
            }
        )
    except Exception as e:
        current_app.logger.error(f'Error in admin_progress_overview: {str(e)}')
        return jsonify({'success': False, 'message': str(e)}), 500


@api_bp.route('/admin/activity-logs', methods=['GET'])
@login_required
def get_activity_logs():
    """Get recent activity logs for the Activity tab."""
    log_type = request.args.get('type', 'all')
    limit = int(request.args.get('limit', 50))

    logs = []

    try:
        if log_type in ('all', 'telegram'):
            from app.models.telegram_user import TelegramUser

            tg_users = (
                TelegramUser.query.filter(TelegramUser.last_interaction_at.isnot(None))
                .order_by(TelegramUser.last_interaction_at.desc())
                .limit(10)
                .all()
            )

            for tu in tg_users:
                logs.append(
                    {
                        'id': f'tg_{tu.id}',
                        'type': 'telegram',
                        'title': f'@{tu.telegram_username or tu.telegram_first_name or "Usuario"}',
                        'message': f'Interacción con el bot (vinculado: {"sí" if tu.is_linked else "no"})',
                        'timestamp': tu.last_interaction_at.isoformat(),
                        'user': tu.telegram_username or tu.telegram_first_name,
                    }
                )

        if log_type in ('all', 'api'):
            recent_payments = Payment.query.order_by(Payment.id.desc()).limit(8).all()
            for p in recent_payments:
                patient = User.query.get(p.patient_id) if p.patient_id else None
                logs.append(
                    {
                        'id': f'pay_{p.id}',
                        'type': 'api',
                        'title': f'Pago S/{getattr(p, "amount", 0)}',
                        'message': f'{getattr(p, "method", "")} — {patient.username if patient else "paciente desconocido"}',
                        'timestamp': (p.date.isoformat() if getattr(p, 'date', None) else ''),
                        'user': patient.username if patient else None,
                    }
                )

            recent_sessions = Appointment.query.order_by(Appointment.id.desc()).limit(8).all()
            for s in recent_sessions:
                logs.append(
                    {
                        'id': f'sess_{s.id}',
                        'type': 'api',
                        'title': f'Sesión #{s.id}',
                        'message': f'{s.title or "Sesión"} — Estado: {getattr(s, "status", "N/A")}',
                        'timestamp': (s.start_time.isoformat() if getattr(s, 'start_time', None) else ''),
                        'user': None,
                    }
                )

        if log_type in ('all', 'errors'):
            from app.models.notification import Notification

            error_notifs = (
                Notification.query.filter_by(
                    type='error',
                )
                .order_by(Notification.id.desc())
                .limit(10)
                .all()
            )

            for n in error_notifs:
                logs.append(
                    {
                        'id': f'err_{n.id}',
                        'type': 'error',
                        'title': n.title or 'Error del sistema',
                        'message': n.message,
                        'timestamp': n.timestamp.isoformat() if getattr(n, 'timestamp', None) else '',
                        'user': None,
                    }
                )

        logs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        logs = logs[:limit]

        return jsonify({'success': True, 'logs': logs})

    except Exception as e:
        current_app.logger.error(f'Error in get_activity_logs: {str(e)}')
        return jsonify({'success': False, 'logs': [], 'error': str(e)}), 500
