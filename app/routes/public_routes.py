import hashlib
import time

from flask import Blueprint, current_app, jsonify

public_bp = Blueprint('public', __name__, url_prefix='/api/public')


@public_bp.route('/app-key', methods=['GET'])
def generate_app_key():
    secret = current_app.config.get('APP_SECRET_KEY', 'dev-app-key-change-in-production')
    client_timestamp = int(time.time() / 300)
    message = f'{secret}:{client_timestamp}'
    expected_hash = hashlib.sha256(message.encode('utf-8')).hexdigest()
    app_key = f'{client_timestamp}.{expected_hash}'
    return jsonify({'app_key': app_key, 'expires_in': 300})
