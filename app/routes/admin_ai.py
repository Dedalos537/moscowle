from threading import Thread

from flask import Blueprint, current_app, jsonify, request
from app.auth_compat import login_required

from app.services.ai_service import _train_lock, _train_thread, train_model

bp = Blueprint('admin_ai', __name__, url_prefix='/admin/ai')


@bp.route('/status', methods=['GET'])
@login_required
def status():
    """Return whether training is in progress and model existence."""
    model_exists = False
    try:
        import os

        from app.services.ai_service import MODEL_PATH

        model_exists = os.path.exists(MODEL_PATH)
    except Exception:
        model_exists = False

    in_progress = False
    try:
        global _train_thread
        with _train_lock:
            in_progress = _train_thread is not None and _train_thread.is_alive()
    except Exception:
        in_progress = False

    return jsonify({'model_exists': model_exists, 'training_in_progress': in_progress}), 200


@bp.route('/train', methods=['POST'])
@login_required
def trigger_train():
    """Trigger background training. Returns immediately."""
    payload = request.get_json(silent=True) or {}
    real_data = payload.get('real_data')

    started = False
    try:
        global _train_thread
        with _train_lock:
            if _train_thread is None or not _train_thread.is_alive():
                t = Thread(target=lambda: train_model(real_data), daemon=True)
                t.start()
                _train_thread = t
                started = True
    except Exception as e:
        current_app.logger.exception('Failed to start training thread')
        return jsonify({'started': False, 'error': str(e)}), 500

    return jsonify({'started': started}), 202
