from flask import Blueprint, request, jsonify
from ..extensions import db, jwt
from ..models.user import User
from flask_jwt_extended import create_access_token

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    # accept either username or email field from frontend
    username = data.get('username') or data.get('email')
    password = data.get('password')
    if not username or not password:
        return jsonify({'msg': 'username/email and password required'}), 400

    # login is by email in the current DB schema
    user = User.query.filter_by(email=username).first()
    if not user or not user.check_password(password):
        return jsonify({'msg': 'Invalid credentials'}), 401

    # ensure the JWT "sub" (subject) is a string to satisfy newer JWT libraries
    access_token = create_access_token(identity=str(user.id))

    # mark admin according to config ADMIN_EMAIL (no schema change)
    from ..config import Config
    is_admin = False
    try:
        admin_email = Config.ADMIN_EMAIL
        if admin_email and user.email and user.email.lower().strip() == admin_email.lower().strip():
            is_admin = True
    except Exception:
        is_admin = False

    user_data = user.to_dict()
    user_data['is_admin'] = is_admin

    return jsonify({ 'access_token': access_token, 'user': user_data })


@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    if not username or not email or not password:
        return jsonify({'msg': 'username, email and password required'}), 400

    if User.query.filter((User.username == username) | (User.email == email)).first():
        return jsonify({'msg': 'User already exists'}), 409

    user = User(username=username, email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    return jsonify({'user': user.to_dict()}), 201


@auth_bp.route('/me', methods=['GET'])
def me():
    # Expect JWT in Authorization header
    from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
    try:
        verify_jwt_in_request()
        identity = get_jwt_identity()
        # JWT identity was stored as a string; convert to int when possible
        try:
            lookup_id = int(identity)
        except Exception:
            lookup_id = identity
        user = User.query.get(lookup_id)
        if not user:
            return jsonify({'msg': 'User not found'}), 404

        from ..config import Config
        is_admin = False
        try:
            admin_email = Config.ADMIN_EMAIL
            if admin_email and user.email and user.email.lower().strip() == admin_email.lower().strip():
                is_admin = True
        except Exception:
            is_admin = False

        data = user.to_dict()
        data['is_admin'] = is_admin
        return jsonify(data)
    except Exception as e:
        return jsonify({'msg': 'Missing or invalid token', 'detail': str(e)}), 401
