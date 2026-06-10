from flask import Blueprint, jsonify, current_app
from app.extensions import db
from app.services.crisis_monitor import crisis_monitor
from sqlalchemy import text
import os
import logging

logger = logging.getLogger(__name__)

health_bp = Blueprint('health', __name__, url_prefix='/api')


@health_bp.route('/health', methods=['GET'])
def health_check():
    """Health check: DB, Groq, Gemini, Ollama, crisis alerts"""
    checks = {}
    overall = 'healthy'

    db_ok = False
    try:
        with db.engine.connect() as conn:
            conn.execute(text('SELECT 1'))
            conn.commit()
        db_ok = True
    except Exception as e:
        logger.warning(f"Health check: DB failed: {e}")
    checks['database'] = {'status': 'ok' if db_ok else 'error'}
    if not db_ok:
        overall = 'degraded'

    groq_key = os.environ.get('GROQ_API_KEY') or current_app.config.get('GROQ_API_KEY')
    groq_ok = bool(groq_key)
    checks['groq'] = {'status': 'ok' if groq_ok else 'missing_key'}
    if not groq_ok and overall == 'healthy':
        overall = 'degraded'

    gemini_key = os.environ.get('GEMINI_API_KEY') or current_app.config.get('GEMINI_API_KEY')
    gemini_ok = bool(gemini_key)
    checks['gemini'] = {'status': 'ok' if gemini_ok else 'missing_key'}
    if not gemini_ok and overall == 'healthy':
        overall = 'degraded'

    ollama_ok = False
    try:
        import ollama
        from ollama import Client
        cli = Client(host=os.environ.get('OLLAMA_HOST', 'http://127.0.0.1:11434'))
        cli.list()
        ollama_ok = True
    except Exception:
        pass
    checks['ollama'] = {'status': 'ok' if ollama_ok else 'unreachable'}

    checks['alerts'] = crisis_monitor.get_metrics() or {}

    return jsonify({
        'status': overall,
        'checks': checks,
        'version': '2.0-remediation',
        'timestamp': __import__('datetime').datetime.utcnow().isoformat()
    }), 200 if overall != 'error' else 503



