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


@health_bp.route('/health/debug/schema', methods=['GET'])
def debug_schema():
    from sqlalchemy import inspect as sa_inspect
    from flask import request as req
    if req.args.get('key') != 'debug2026':
        return jsonify({'error': 'invalid key'}), 403
    inspector = sa_inspect(db.engine)
    tables = inspector.get_table_names()
    result = {}
    for t in sorted(tables):
        cols = [c['name'] for c in inspector.get_columns(t)]
        result[t] = cols
    return jsonify({'tables': result})


@health_bp.route('/health/debug/query', methods=['GET'])
def debug_query():
    from flask import request as req
    if req.args.get('key') != 'debug2026':
        return jsonify({'error': 'invalid key'}), 403
    test = req.args.get('test', 'basic')

    try:
        if test == 'basic':
            r = db.session.execute(text("SELECT 1 AS ok")).fetchone()
            return jsonify({'ok': r.ok, 'test': 'basic'})

        elif test == 'chat_count':
            r = db.session.execute(text("SELECT COUNT(*) FROM chat")).scalar() or 0
            p = db.session.execute(text("SELECT COUNT(*) FROM chat_participant")).scalar() or 0
            m = db.session.execute(text("SELECT COUNT(*) FROM message")).scalar() or 0
            return jsonify({'chat_count': r, 'participant_count': p, 'message_count': m, 'test': 'chat_count'})

        elif test == 'chat_columns':
            r = db.session.execute(text("SELECT id, is_group, created_at FROM chat LIMIT 5")).fetchall()
            return jsonify({'rows': [dict(z._mapping) for z in r], 'test': 'chat_columns'})

        elif test == 'msg_columns':
            r = db.session.execute(text("SELECT id, sender_id, receiver_id, body, status, is_read, chat_id, attachment_path, attachment_type FROM message LIMIT 5")).fetchall()
            return jsonify({'rows': [dict(z._mapping) for z in r], 'test': 'msg_columns'})

        elif test == 'join_chat':
            r = db.session.execute(
                text("""
                    SELECT c.id, c.is_group, c.created_at
                    FROM chat c
                    JOIN chat_participant cp ON cp.chat_id = c.id
                    LIMIT 20
                """)
            ).fetchall()
            return jsonify({'rows': [dict(z._mapping) for z in r], 'test': 'join_chat'})

        elif test == 'last_msg':
            r = db.session.execute(
                text("SELECT id, body, sender_id, created_at, attachment_type FROM message WHERE chat_id = :cid ORDER BY created_at DESC LIMIT 1"),
                {'cid': int(req.args.get('cid', 1))}
            ).fetchone()
            return jsonify({'row': dict(r._mapping) if r else None, 'test': 'last_msg'})

        elif test == 'simulate_chats':
            uid = int(req.args.get('uid', 1))
            chats = db.session.execute(
                text("""
                    SELECT c.id, c.is_group, c.created_at
                    FROM chat c
                    JOIN chat_participant cp ON cp.chat_id = c.id
                    WHERE cp.user_id = :uid
                    ORDER BY c.created_at DESC
                """),
                {'uid': uid}
            ).fetchall()
            result = []
            for cr in chats:
                other = db.session.execute(
                    text("SELECT user_id FROM chat_participant WHERE chat_id = :cid AND user_id != :uid LIMIT 1"),
                    {'cid': cr.id, 'uid': uid}
                ).fetchone()
                last_msg = db.session.execute(
                    text("SELECT id, body, sender_id, created_at, attachment_type FROM message WHERE chat_id = :cid ORDER BY created_at DESC LIMIT 1"),
                    {'cid': cr.id}
                ).fetchone()
                unread = db.session.execute(
                    text("SELECT COUNT(*) FROM message WHERE chat_id = :cid AND sender_id != :uid AND status IN ('sent', 'delivered')"),
                    {'cid': cr.id, 'uid': uid}
                ).scalar() or 0
                result.append({
                    'chat_id': cr.id,
                    'other_user_id': other.user_id if other else None,
                    'last_msg_id': last_msg.id if last_msg else None,
                    'unread': unread
                })
            return jsonify({'chats': result, 'test': 'simulate_chats'})

        elif test == 'simulate_messages':
            cid = int(req.args.get('cid', 1))
            rows = db.session.execute(
                text("SELECT id, sender_id, receiver_id, body, status, is_read, attachment_path, attachment_type FROM message WHERE chat_id = :cid ORDER BY id DESC LIMIT 10"),
                {'cid': cid}
            ).fetchall()
            return jsonify({'messages': [{'id':r.id,'sender_id':r.sender_id,'body':r.body[:50]} for r in rows], 'test': 'simulate_messages'})

        else:
            return jsonify({'error': 'unknown test', 'available': ['basic', 'chat_count', 'chat_columns', 'msg_columns', 'join_chat', 'last_msg']}), 400

    except Exception as e:
        import traceback
        return jsonify({'error': str(e)[:1000], 'traceback': traceback.format_exc(), 'test': test}), 500



