from flask import Blueprint, jsonify
from sqlalchemy import text

from ..extensions import db

roles_bp = Blueprint('roles_bp', __name__)


@roles_bp.route('', methods=['GET'])
def list_roles():
    """Return a list of roles from the `roles` table.

    Response shape: { roles: [ { id, name }, ... ] }
    """
    try:
        sql = text("SELECT id, name FROM roles ORDER BY id")
        res = db.session.execute(sql).fetchall()
        roles = [{'id': int(r[0]), 'name': r[1]} for r in res]
        return jsonify({'roles': roles}), 200
    except Exception as e:
        # Minimal error handling — centralized error handlers will wrap if present
        return jsonify({'roles': [], 'error': str(e)}), 500
