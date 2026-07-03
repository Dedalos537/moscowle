from flask import flash, redirect, render_template, request, url_for
from app.auth_compat import current_user, login_required

from app.extensions import db
from app.models import Payment, Sede, SessionMetrics, User, db
from app.routes.admin import admin_bp


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
