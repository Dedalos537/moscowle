"""Admin endpoints for password-reset approval flow."""

from datetime import datetime

from flask import current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity

from app.auth_compat import login_required
from app.extensions import bcrypt, db
from app.models.password_reset import PasswordReset
from app.models.user import User
from app.routes.admin import admin_bp
from app.services.notification_service import NotificationService
from app.utils.decorators import admin_required


def _current_admin_id():
    try:
        ident = get_jwt_identity()
        return int(ident) if ident is not None else None
    except Exception:
        return None


@admin_bp.route('/api/admin/reset-actions', methods=['GET'])
@login_required
@admin_required
def list_password_resets():
    try:
        status = request.args.get('status', 'awaiting_approval')
        q = PasswordReset.query
        if status and status != 'all':
            q = q.filter(PasswordReset.status == status)
        rows = q.order_by(PasswordReset.created_at.desc()).limit(100).all()

        user_ids = {r.user_id for r in rows if r.user_id}
        users = {u.id: u for u in User.query.filter(User.id.in_(user_ids)).all()} if user_ids else {}

        items = []
        for r in rows:
            d = r.to_dict(include_temp_password=(r.status == 'awaiting_approval'))
            u = users.get(r.user_id)
            if u:
                d['target_username'] = u.username
                d['target_role'] = u.role
            items.append(d)
        return jsonify({'success': True, 'items': items})
    except Exception as e:
        current_app.logger.error(f'list_password_resets: {e}')
        return jsonify({'success': False, 'error': 'Error interno'}), 500


@admin_bp.route('/api/admin/reset-actions/<int:reset_id>', methods=['POST'])
@login_required
@admin_required
def process_password_reset(reset_id):
    try:
        admin_id = _current_admin_id()
        data = request.get_json(silent=True) or {}
        action = (data.get('action') or '').strip().lower()
        reason = (data.get('reason') or '').strip()[:500]

        record = PasswordReset.query.get(reset_id)
        if not record:
            return jsonify({'success': False, 'error': 'Solicitud no encontrada'}), 404
        if record.status != 'awaiting_approval':
            return jsonify({'success': False, 'error': f'La solicitud ya está en estado {record.status}'}), 400
        if record.expires_at <= datetime.utcnow():
            record.mark_expired()
            return jsonify({'success': False, 'error': 'La solicitud ha expirado'}), 400

        if action == 'approve':
            user = User.query.get(record.user_id) if record.user_id else None
            if not user:
                return jsonify({'success': False, 'error': 'Usuario objetivo no encontrado'}), 404

            new_password = record.temp_password_plain
            if not new_password:
                return jsonify({'success': False, 'error': 'La solicitud no tiene contraseña temporal'}), 400

            user.password = bcrypt.generate_password_hash(new_password).decode('utf-8')
            record.approve(admin_id)
            db.session.commit()

            try:
                notif = NotificationService()
                notif.create_notification(
                    user_id=user.id,
                    title='Tu contraseña fue reseteada',
                    message=(
                        f'Un administrador aprobó tu solicitud de reseteo. '
                        f'Tu nueva contraseña temporal es: {new_password}. '
                        f'Inicia sesión y cámbiala de inmediato.'
                    ),
                    notif_type='warning',
                    link='/auth/login',
                    category='security',
                    priority='high',
                    icon='key',
                    metadata_json={'reset_request_id': record.id, 'must_change_password': True},
                )
            except Exception as ne:
                current_app.logger.error(f'Notif user failed: {ne}')

            return jsonify(
                {
                    'success': True,
                    'message': 'Solicitud aprobada',
                    'temp_password': new_password,
                    'target_user': {'id': user.id, 'email': user.email, 'username': user.username, 'role': user.role},
                }
            )

        elif action == 'reject':
            record.reject(admin_id)
            db.session.commit()
            if record.user_id:
                try:
                    notif = NotificationService()
                    notif.create_notification(
                        user_id=record.user_id,
                        title='Solicitud de reseteo rechazada',
                        message=(
                            'Un administrador rechazó tu solicitud de reseteo de contraseña.'
                            + (f' Motivo: {reason}' if reason else '')
                            + ' Si necesitas ayuda contacta al administrador.'
                        ),
                        notif_type='error',
                        link=None,
                        category='security',
                        priority='normal',
                        icon='ban',
                        metadata_json={'reset_request_id': record.id},
                    )
                except Exception as ne:
                    current_app.logger.error(f'Notif reject failed: {ne}')
            return jsonify({'success': True, 'message': 'Solicitud rechazada'})

        else:
            return jsonify({'success': False, 'error': 'Acción inválida. Use "approve" o "reject"'}), 400

    except Exception as e:
        current_app.logger.error(f'process_password_reset: {e}')
        db.session.rollback()
        return jsonify({'success': False, 'error': 'Error interno'}), 500
