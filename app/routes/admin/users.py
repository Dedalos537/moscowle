import logging
from datetime import date, datetime

from flask import flash, jsonify, redirect, render_template, request, url_for
from app.auth_compat import current_user, login_required

from app.extensions import db
from app.models import Payment, Sede, SessionMetrics, User, db
from app.routes.admin import admin_bp
from app.utils.decorators import admin_required

logger = logging.getLogger(__name__)


@admin_bp.route('/api/patients', methods=['GET'])
@login_required
@admin_required
def list_patients():
    """Return all patients with details for the finanzas tab."""
    try:
        users = User.query.filter_by(role='jugador', is_active=True).order_by(User.username.asc()).all()
        patients = []
        for u in users:
            # Calculate age if date_of_birth is set
            age = None
            if u.date_of_birth:
                today = date.today()
                age = today.year - u.date_of_birth.year - (
                    (today.month, today.day) < (u.date_of_birth.month, u.date_of_birth.day)
                )
            patients.append({
                'id': u.id,
                'username': u.username,
                'email': u.email,
                'is_active': u.is_active,
                'phone': u.phone,
                'document_number': u.document_number,
                'date_of_birth': u.date_of_birth.strftime('%Y-%m-%d') if u.date_of_birth else None,
                'age': age,
                'sex': u.sex,
                'guardian_name': u.guardian_name,
                'guardian_type': u.guardian_type,
                'guardian_dni': u.guardian_dni,
                'guardian_contact': u.guardian_contact,
                'preliminary_diagnosis': u.preliminary_diagnosis,
                'therapy_goals': u.therapy_goals,
                'notes': u.notes,
                'payment_plan': u.payment_plan,
                'payment_amount': u.payment_amount,
                'sede': u.sede.name if u.sede else None,
                'sede_id': u.sede_id,
                'therapist': u.therapist.username if u.therapist else None,
                'therapist_id': u.therapist_id,
                'created_at': u.created_at.strftime('%Y-%m-%d') if u.created_at else None,
            })
        return jsonify({'success': True, 'patients': patients})
    except Exception as e:
        db.session.rollback()
        logger.exception('Error listing patients')
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/users')
@login_required
def users():
    if current_user.role not in ('admin', 'supervisor'):
        flash('Acceso denegado.', 'error')
        return redirect(url_for('main.dashboard'))

    sede_filter = request.args.get('sede_id')
    query = User.query

    if sede_filter and sede_filter.isdigit():
        query = query.filter(User.sede_id == int(sede_filter))

    users = query.order_by(User.created_at.desc()).all()

    patient_therapist_map = {}
    for u in users:
        if u.role == 'jugador':
            patient_therapist_map[u.id] = [t.id for t in u.therapists]

    therapists = User.query.filter_by(role='terapista').order_by(User.username.asc()).all()
    sedes = Sede.query.filter_by(is_active=True).order_by(Sede.name.asc()).all()

    return render_template(
        'admin/users.html',
        users=users,
        therapists=therapists,
        patient_therapist_map=patient_therapist_map,
        sedes=sedes,
        active_page='admin_users',
    )


@admin_bp.route('/users/<int:user_id>')
@login_required
def user_details(user_id):
    if current_user.role not in ('admin', 'supervisor'):
        flash('Acceso denegado.', 'error')
        return redirect(url_for('main.dashboard'))

    user = User.query.get_or_404(user_id)

    stats = {}

    if user.role == 'jugador':
        stats['total_sessions'] = SessionMetrics.query.filter_by(user_id=user.id).count()
        stats['last_session'] = (
            SessionMetrics.query.filter_by(user_id=user.id).order_by(SessionMetrics.date.desc()).first()
        )
        stats['payments_count'] = Payment.query.filter_by(patient_id=user.id).count()
        stats['assigned_therapists'] = user.therapists.all()
        stats['sessions_left'] = user.sessions_total - user.sessions_attended

    elif user.role == 'terapista':
        stats['assigned_sedes'] = user.assigned_sedes.all()
        stats['active_patients_count'] = user.associated_patients.filter_by(is_active=True).count()

    return render_template('admin/user_detail.html', user=user, stats=stats, active_page='admin_users')


@admin_bp.route('/users/<int:user_id>/toggle-status', methods=['POST'])
@login_required
def toggle_user_status(user_id):
    if current_user.role not in ('admin', 'supervisor'):
        flash('Acceso denegado.', 'error')
        return redirect(url_for('main.dashboard'))

    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('No puedes cambiar tu propio estado.', 'error')
        return redirect(url_for('admin.user_details', user_id=user.id))

    status = request.form.get('status') or 'active'

    if status not in ['active', 'inactive', 'retired', 'debtor']:
        flash('Estado inválido', 'error')
        return redirect(url_for('admin.user_details', user_id=user.id))

    user.account_status = status

    user.is_active = status == 'active'

    messages = {
        'active': 'Usuario activado, todo ok',
        'inactive': 'Usuario desactivado',
        'retired': 'Usuario marcado como retirado',
        'debtor': 'Usuario marcado como deudor',
    }

    db.session.commit()
    flash(messages.get(status, 'Estado actualizado'), 'success')
    return redirect(url_for('admin.user_details', user_id=user.id))


@admin_bp.route('/api/users/<int:user_id>/toggle-status', methods=['POST'])
@login_required
def api_toggle_user_status(user_id):
    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json(silent=True) or {}
    status = data.get('status', 'active')

    if status not in ['active', 'inactive', 'retired', 'debtor']:
        return jsonify({'error': 'Estado invalido. Use: active, inactive, retired, debtor'}), 400

    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        return jsonify({'error': 'No puedes cambiar tu propio estado'}), 400

    old_status = user.account_status or ('active' if user.is_active else 'inactive')
    user.account_status = status
    user.is_active = status == 'active'
    db.session.commit()

    messages = {
        'active': 'Usuario activado',
        'inactive': 'Usuario desactivado',
        'retired': 'Usuario marcado como retirado',
        'debtor': 'Usuario marcado como deudor',
    }
    return jsonify({'success': True, 'message': messages.get(status, 'Estado actualizado'), 'old_status': old_status, 'new_status': status})


@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
def delete_user(user_id):
    if current_user.role != 'admin':
        flash('Acceso denegado.', 'error')
        return redirect(url_for('main.dashboard'))

    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('No puedes eliminar tu propia cuenta.', 'error')
        return redirect(url_for('admin.user_details', user_id=user.id))

    try:
        db.session.delete(user)
        db.session.commit()
        flash('Usuario eliminado, listo.', 'success')
        return redirect(url_for('admin.users'))
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar usuario: {str(e)}', 'error')
        return redirect(url_for('admin.user_details', user_id=user.id))


@admin_bp.route('/users/<int:user_id>/reset-password', methods=['POST'])
@login_required
def reset_password(user_id):
    if current_user.role != 'admin':
        flash('Acceso denegado.', 'error')
        return redirect(url_for('main.dashboard'))

    user = User.query.get_or_404(user_id)
    flash(f'Correo de restablecimiento enviado a {user.email} (simulado)', 'success')
    return redirect(url_for('admin.user_details', user_id=user.id))


@admin_bp.route('/api/users/<int:user_id>/patient-details', methods=['PATCH'])
@login_required
@admin_required
def update_patient_details(user_id):
    """Update patient-specific detail fields (DNI, birth date, sex, phone, guardian info, etc.)"""
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'success': False, 'error': 'Usuario no encontrado'}), 404

        data = request.get_json(silent=True) or {}

        allowed_fields = [
            'document_number', 'phone', 'date_of_birth', 'sex',
            'guardian_name', 'guardian_type', 'guardian_dni', 'guardian_contact',
            'preliminary_diagnosis', 'therapy_goals', 'notes',
        ]

        updated = []
        for field in allowed_fields:
            if field in data:
                value = data[field]
                if field == 'date_of_birth' and value:
                    from datetime import datetime
                    try:
                        value = datetime.strptime(value, '%Y-%m-%d').date()
                    except ValueError:
                        return jsonify({'success': False, 'error': f'Formato de fecha invalido para {field}'}), 400
                setattr(user, field, value if value != '' else None)
                updated.append(field)

        if not updated:
            return jsonify({'success': False, 'error': 'No hay campos para actualizar'}), 400

        db.session.commit()
        return jsonify({'success': True, 'message': 'Datos actualizados', 'updated_fields': updated})
    except Exception as e:
        db.session.rollback()
        logger.exception('Error updating patient details')
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/api/users/<int:user_id>/patient-details', methods=['GET'])
@login_required
@admin_required
def get_patient_details(user_id):
    """Get all patient detail fields for editing"""
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'success': False, 'error': 'Usuario no encontrado'}), 404

        return jsonify({
            'success': True,
            'patient': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'phone': user.phone,
                'document_number': user.document_number,
                'date_of_birth': user.date_of_birth.strftime('%Y-%m-%d') if user.date_of_birth else None,
                'sex': user.sex,
                'guardian_name': user.guardian_name,
                'guardian_type': user.guardian_type,
                'guardian_dni': user.guardian_dni,
                'guardian_contact': user.guardian_contact,
                'preliminary_diagnosis': user.preliminary_diagnosis,
                'therapy_goals': user.therapy_goals,
                'notes': user.notes,
                'payment_plan': user.payment_plan,
                'payment_amount': user.payment_amount,
                'sessions_total': user.sessions_total,
                'sessions_attended': user.sessions_attended,
                'plan_type': user.plan_type,
                'sede_id': user.sede_id,
            }
        })
    except Exception as e:
        logger.exception('Error getting patient details')
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/api/patient-stats', methods=['GET'])
@login_required
@admin_required
def patient_stats():
    """Get patient demographic stats for MCP queries"""
    try:
        from datetime import date, timedelta

        patients = User.query.filter_by(role='jugador', is_active=True).all()
        total = len(patients)

        if total == 0:
            return jsonify({'success': True, 'stats': {'total': 0}})

        today = date.today()

        age_ranges = {'0-3': 0, '4-6': 0, '7-9': 0, '10-12': 0, '13-15': 0, '16-18': 0, '19+': 0}
        sex_counts = {'M': 0, 'F': 0, 'Otro': 0, 'No especificado': 0}
        sede_counts = {}
        join_month_counts = {}
        has_guardian = 0
        has_dni = 0
        has_diagnosis = 0
        active_contracts = 0

        for p in patients:
            if p.date_of_birth:
                age = (today - p.date_of_birth).days // 365
                if age <= 3: age_ranges['0-3'] += 1
                elif age <= 6: age_ranges['4-6'] += 1
                elif age <= 9: age_ranges['7-9'] += 1
                elif age <= 12: age_ranges['10-12'] += 1
                elif age <= 15: age_ranges['13-15'] += 1
                elif age <= 18: age_ranges['16-18'] += 1
                else: age_ranges['19+'] += 1

            if p.sex:
                sex_key = p.sex if p.sex in ('M', 'F') else 'Otro'
            else:
                sex_key = 'No especificado'
            sex_counts[sex_key] = sex_counts.get(sex_key, 0) + 1

            sede_name = p.sede_item.name if p.sede_item else 'Sin sede'
            sede_counts[sede_name] = sede_counts.get(sede_name, 0) + 1

            if p.created_at:
                month_key = p.created_at.strftime('%Y-%m')
                join_month_counts[month_key] = join_month_counts.get(month_key, 0) + 1

            if p.guardian_name: has_guardian += 1
            if p.document_number: has_dni += 1
            if p.preliminary_diagnosis: has_diagnosis += 1

        from app.models.contract import Contract
        active_contracts = Contract.query.filter_by(status='active').count()

        return jsonify({
            'success': True,
            'stats': {
                'total': total,
                'age_ranges': age_ranges,
                'sex_distribution': sex_counts,
                'by_sede': sede_counts,
                'by_join_month': dict(sorted(join_month_counts.items(), reverse=True)[:12])),
                'has_guardian': has_guardian,
                'has_dni': has_dni,
                'has_diagnosis': has_diagnosis,
                'active_contracts': active_contracts,
                'without_contract': total - active_contracts,
            }
        })
    except Exception as e:
        logger.exception('Error getting patient stats')
        return jsonify({'success': False, 'error': str(e)}), 500
