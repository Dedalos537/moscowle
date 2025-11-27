from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, verify_jwt_in_request, get_jwt_identity, jwt_required
from ..extensions import db
from ..services.user_service import UserService
from ..schemas.user_schema import CreateUserSchema
from ..schemas.user_schema import UserSchema
from ..errors import NotFoundError, ConflictError
from ..config import Config


auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    # accept either username or email field from frontend
    username = data.get('username') or data.get('email')
    password = data.get('password')
    if not username or not password:
        return jsonify({'msg': 'username/email and password required'}), 400

    svc = UserService()
    try:
        user = svc.get_by_email(username)
    except NotFoundError:
        return jsonify({'msg': 'Invalid credentials'}), 401

    if not svc.verify_password(user, password):
        return jsonify({'msg': 'Invalid credentials'}), 401

    # create token with string subject
    access_token = create_access_token(identity=str(user.id))

    # determine admin flag
    is_admin = False
    try:
        admin_email = Config.ADMIN_EMAIL
        if admin_email and user.email and user.email.lower().strip() == admin_email.lower().strip():
            is_admin = True
        elif user.role_id == 1:
            is_admin = True
    except Exception:
        is_admin = False

    user_data = user.to_dict()
    user_data['is_admin'] = is_admin

    return jsonify({'access_token': access_token, 'user': user_data})


@auth_bp.route('/register', methods=['POST'])
@jwt_required()
def register():
    # only admin users may create other users via dashboard
    try:
        verify_jwt_in_request()
    except Exception:
        return jsonify({'msg': 'Missing or invalid token'}), 401

    identity = get_jwt_identity()
    try:
        current_id = int(identity)
    except Exception:
        current_id = identity

    # load current user and check admin
    svc = UserService()
    try:
        current_user = svc.get_by_email(svc.repo.session.query(svc.repo.model).get(current_id).email)
    except Exception:
        # fallback to query
        from ..models.user import User
        current_user = User.query.get(current_id)

    if not current_user or not (current_user.role_id == 1 or (Config.ADMIN_EMAIL and current_user.email.lower().strip() == Config.ADMIN_EMAIL.lower().strip())):
        return jsonify({'msg': 'Admin privileges required'}), 403

    # validate input
    payload = request.get_json() or {}
    schema = CreateUserSchema()
    errors = schema.validate(payload)
    if errors:
        return jsonify({'msg': 'Validation failed', 'errors': errors}), 400

    # resolve role name to role_id if provided
    role_arg = payload.get('role')
    role_id_arg = payload.get('role_id')
    resolved_role_id = None
    if role_arg:
        from sqlalchemy import text
        try:
            row = db.session.execute(text("SELECT id FROM roles WHERE name = :name"), {"name": role_arg}).mappings().first()
            if row:
                resolved_role_id = int(row['id'])
        except Exception:
            resolved_role_id = None

    try:
        user = svc.create_user(email=payload['email'], password=payload['password'], role_id=(resolved_role_id if resolved_role_id is not None else role_id_arg))
    except ConflictError as e:
        return jsonify({'msg': str(e)}), 409

    user_schema = UserSchema()
    return jsonify({'user': user_schema.dump(user)}), 201


@auth_bp.route('/me', methods=['GET'])
def me():
    # Expect JWT in Authorization header
    try:
        verify_jwt_in_request()
        identity = get_jwt_identity()
        # JWT identity was stored as a string; convert to int when possible
        try:
            lookup_id = int(identity)
        except Exception:
            lookup_id = identity
        svc = UserService()
        user = svc.repo.session.get(svc.repo.model, lookup_id)
        if not user:
            return jsonify({'msg': 'User not found'}), 404

        is_admin = False
        try:
            admin_email = Config.ADMIN_EMAIL
            if admin_email and user.email and user.email.lower().strip() == admin_email.lower().strip():
                is_admin = True
            elif user.role_id == 1:
                is_admin = True
        except Exception:
            is_admin = False

        data = user.to_dict()
        data['is_admin'] = is_admin
        return jsonify(data)
    except Exception as e:
        return jsonify({'msg': 'Missing or invalid token', 'detail': str(e)}), 401
