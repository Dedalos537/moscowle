from flask import Blueprint, jsonify, request
from ..extensions import db
from ..models.user import User
from ..schemas.user_schema import UserSchema
from sqlalchemy import text

users_bp = Blueprint('users_bp', __name__)


@users_bp.route('', methods=['GET'])
def list_users():
    """Return list of users with optional role name resolved.

    Response shape: { users: [ { id, email, role_id, role_name, status, created_at }, ... ] }
    """
    try:
        users = User.query.order_by(User.id).all()
        schema = UserSchema(many=True)
        users_data = schema.dump(users)

        # attach role_name if possible
        for u in users_data:
            role_name = None
            try:
                if u.get('role_id') is not None:
                    row = db.session.execute(text("SELECT name FROM roles WHERE id = :id"), {"id": int(u['role_id'])}).mappings().first()
                    if row:
                        role_name = row['name']
            except Exception:
                role_name = None
            u['role_name'] = role_name

        return jsonify({'users': users_data}), 200
    except Exception as e:
        return jsonify({'users': [], 'error': str(e)}), 500


@users_bp.route('/<int:user_id>', methods=['GET'])
def get_user(user_id: int):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'msg': 'User not found'}), 404
    schema = UserSchema()
    data = schema.dump(user)
    # attach role_name
    try:
        if data.get('role_id') is not None:
            row = db.session.execute(text("SELECT name FROM roles WHERE id = :id"), {"id": int(data['role_id'])}).mappings().first()
            if row:
                data['role_name'] = row['name']
    except Exception:
        data['role_name'] = None

    return jsonify({'user': data})


@users_bp.route('/<int:user_id>', methods=['PUT'])
def update_user(user_id: int):
    payload = request.get_json() or {}
    user = User.query.get(user_id)
    if not user:
        return jsonify({'msg': 'User not found'}), 404

    # Only allow updating a subset of fields that exist in the model
    allowed = ['email', 'status', 'role_id']
    changed = False
    for k in allowed:
        if k in payload:
            setattr(user, k, payload[k])
            changed = True

    if changed:
        try:
            db.session.add(user)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return jsonify({'msg': 'Update failed', 'detail': str(e)}), 500

    schema = UserSchema()
    return jsonify({'user': schema.dump(user)})


@users_bp.route('/<int:user_id>', methods=['DELETE'])
def delete_user(user_id: int):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'msg': 'User not found'}), 404
    try:
        db.session.delete(user)
        db.session.commit()
        return jsonify({'msg': 'deleted'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'msg': 'Delete failed', 'detail': str(e)}), 500
