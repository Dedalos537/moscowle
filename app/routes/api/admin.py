import contextlib

from app.routes.api import api_bp
from app.routes.api._shared import (
    Appointment,
    AssignTherapistSchema,
    EmailService,
    Message,
    Payment,
    Sede,
    SessionMetrics,
    UpdateUserSchema,
    User,
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
        'role': u.role,
        'is_active': u.is_active,
        'account_status': u.account_status or 'active',
        'admin_password_changed_count': u.admin_password_changed_count or 0,
        'sede_id': u.sede_id,
        'sede_name': u.sede_item.name if u.sede_item else None,
        'assigned_sedes': [{'id': s.id, 'name': s.name} for s in u.assigned_sedes.all()],
        'therapist_ids': [t.id for t in u.therapists.all()],
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
    changed = False
    if name:
        current_user.username = name
        changed = True
    if new_password:
        current_user.password = bcrypt.generate_password_hash(new_password).decode('utf-8')
        changed = True
        with contextlib.suppress(Exception):
            EmailService.send_password_change_email(
                current_user.email, new_password, current_user.username or 'Administrador'
            )
    if changed:
        db.session.commit()
    return jsonify({'success': True})


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

        therapists = User.query.filter(User.assigned_sedes.any(Sede.id == sede_id), User.role == 'terapista').all()
        therapist_ids = [t.id for t in therapists]

        appointments_at_sede = (
            Appointment.query.filter(Appointment.therapist_id.in_(therapist_ids)).all() if therapist_ids else []
        )

        patient_ids = list(set([a.patient_id for a in appointments_at_sede if a.patient_id]))

        payments = Payment.query.filter(Payment.patient_id.in_(patient_ids)).all() if patient_ids else []

        total_patients = len(patient_ids)
        active_patients = len([pid for pid in patient_ids if User.query.get(pid) and User.query.get(pid).is_active])

        total_revenue = sum([p.amount for p in payments if p.status == 'completed']) if payments else 0
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
        payments_this_month = (
            sum([p.amount for p in payments if p.status == 'completed' and p.date and p.date >= month_start])
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
