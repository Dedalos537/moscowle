import logging
import os
from datetime import UTC

from flask import Blueprint, current_app, jsonify
from sqlalchemy import text

from app.extensions import csrf, db
from app.services.crisis_monitor import crisis_monitor

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
        logger.warning(f'Health check: DB failed: {e}')
    checks['database'] = {'status': 'ok' if db_ok else 'error'}
    if not db_ok:
        overall = 'degraded'

    glm_key = os.environ.get('GLM_API_KEY') or current_app.config.get('GLM_API_KEY')
    glm_ok = bool(glm_key)
    checks['glm'] = {'status': 'ok' if glm_ok else 'missing_key', 'model': 'z-ai/glm-5.2'}
    if not glm_ok and overall == 'healthy':
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
        from ollama import Client

        cli = Client(host=os.environ.get('OLLAMA_HOST', 'http://127.0.0.1:11434'))
        cli.list()
        ollama_ok = True
    except Exception:
        pass
    checks['ollama'] = {'status': 'ok' if ollama_ok else 'unreachable'}

    checks['alerts'] = crisis_monitor.get_metrics() or {}

    git_sha = os.environ.get('RAILWAY_GIT_COMMIT_SHA') or ''
    git_msg = os.environ.get('RAILWAY_GIT_COMMIT_MESSAGE') or ''
    return jsonify(
        {
            'status': overall,
            'checks': checks,
            'version': '2.0-remediation',
            'git_commit_sha': git_sha[:12] if git_sha else '',
            'git_commit_message': git_msg[:100] if git_msg else '',
            'timestamp': __import__('datetime').datetime.utcnow().isoformat(),
        }
    ), 200 if overall != 'error' else 503


@health_bp.route('/health/routes', methods=['GET'])
def list_routes():
    """List all registered routes for debugging."""
    from flask import request as req

    if req.args.get('key') != 'debug2026':
        return jsonify({'error': 'invalid key'}), 403
    rules = []
    for rule in current_app.url_map.iter_rules():
        rules.append({
            'endpoint': rule.endpoint,
            'methods': sorted(rule.methods - {'OPTIONS', 'HEAD'}),
            'rule': str(rule),
        })
    return jsonify({'routes': sorted(rules, key=lambda r: r['rule'])})


@health_bp.route('/health/debug/schema', methods=['GET'])
def debug_schema():
    from flask import request as req
    from sqlalchemy import inspect as sa_inspect

    if req.args.get('key') != 'debug2026':
        return jsonify({'error': 'invalid key'}), 403
    inspector = sa_inspect(db.engine)
    tables = inspector.get_table_names()
    result = {}
    for t in sorted(tables):
        cols = [c['name'] for c in inspector.get_columns(t)]
        result[t] = cols
    return jsonify({'tables': result})


@health_bp.route('/health/debug/send-test', methods=['GET'])
@csrf.exempt
def debug_send_test():
    """Diagnostic: replicates send_message flow with verbose output.
    User must be logged in (JWT cookie). Visit in browser after logging into the app.
    """
    from flask import request as req

    if req.args.get('key') != 'debug2026':
        return jsonify({'error': 'invalid key'}), 403

    from app.auth_compat import get_jwt_identity, verify_jwt_in_request

    try:
        verify_jwt_in_request(locations=['cookies'])
        uid = get_jwt_identity()
    except Exception as e:
        return jsonify({'error': 'not authenticated', 'detail': str(e)}), 401

    from app.models import User

    user = User.query.get(int(uid))
    if not user:
        return jsonify({'error': 'user not found'}), 404

    cid = int(req.args.get('cid', 1))
    steps = {}
    errors = []

    # Step 1: chat exists
    try:
        chat = db.session.execute(text('SELECT id FROM chat WHERE id = :cid'), {'cid': cid}).fetchone()
        steps['chat_exists'] = bool(chat)
    except Exception as e:
        steps['chat_exists'] = f'ERROR: {e}'

    # Step 2: is participant
    try:
        part = db.session.execute(
            text('SELECT user_id FROM chat_participant WHERE chat_id = :cid AND user_id = :uid'),
            {'cid': cid, 'uid': user.id},
        ).fetchone()
        steps['is_participant'] = bool(part)
    except Exception as e:
        steps['is_participant'] = f'ERROR: {e}'

    # Step 3: other participants
    try:
        others = db.session.execute(
            text('SELECT user_id FROM chat_participant WHERE chat_id = :cid AND user_id != :uid'),
            {'cid': cid, 'uid': user.id},
        ).fetchall()
        steps['other_count'] = len(others)
        receiver = others[0].user_id if others else None
        steps['receiver'] = receiver
    except Exception as e:
        steps['other_participants'] = f'ERROR: {e}'

    # Step 4: test INSERT with user as sender
    try:
        from datetime import datetime

        from app.models.chat import Message

        ts = str(datetime.now(UTC).timestamp())
        insert_stmt = Message.__table__.insert().values(
            sender_id=user.id,
            receiver_id=receiver or user.id,
            body='DIAGNOSTIC TEST MSG ' + ts,
            chat_id=cid,
            status='sent',
            attachment_path=None,
            attachment_type=None,
        )
        compiled = str(insert_stmt.compile(compile_kwargs={'literal_binds': True}))
        result = db.session.execute(insert_stmt)
        msg_id = result.inserted_primary_key[0]
        db.session.commit()
        # Verify
        verify = db.session.execute(
            text('SELECT id, body, is_read, is_active, created_at FROM message WHERE id = :mid'), {'mid': msg_id}
        ).fetchone()
        verify_dict = dict(verify._mapping) if verify else None
        # Clean up
        db.session.execute(text('DELETE FROM message WHERE id = :mid'), {'mid': msg_id})
        db.session.commit()
        steps['insert'] = {'msg_id': msg_id, 'compiled_sql': compiled[:500], 'verified': verify_dict}
    except Exception as e:
        import traceback

        errors.append({'step': 'insert', 'error': str(e), 'traceback': traceback.format_exc()})

    return jsonify({'user_id': user.id, 'username': user.username, 'chat_id': cid, 'steps': steps, 'errors': errors})


@health_bp.route('/health/debug/last-error', methods=['GET'])
def debug_last_error():
    from flask import request as req

    if req.args.get('key') != 'debug2026':
        return jsonify({'error': 'invalid key'}), 403
    from app.routes.chat_routes import get_last_error

    return jsonify(get_last_error())


@health_bp.route('/health/debug/query', methods=['GET'])
def debug_query():
    from flask import request as req

    if req.args.get('key') != 'debug2026':
        return jsonify({'error': 'invalid key'}), 403
    test = req.args.get('test', 'basic')

    try:
        if test == 'basic':
            r = db.session.execute(text('SELECT 1 AS ok')).fetchone()
            return jsonify({'ok': r.ok, 'test': 'basic'})

        elif test == 'chat_count':
            r = db.session.execute(text('SELECT COUNT(*) FROM chat')).scalar() or 0
            p = db.session.execute(text('SELECT COUNT(*) FROM chat_participant')).scalar() or 0
            m = db.session.execute(text('SELECT COUNT(*) FROM message')).scalar() or 0
            return jsonify({'chat_count': r, 'participant_count': p, 'message_count': m, 'test': 'chat_count'})

        elif test == 'chat_columns':
            r = db.session.execute(text('SELECT id, is_group, created_at FROM chat LIMIT 5')).fetchall()
            return jsonify({'rows': [dict(z._mapping) for z in r], 'test': 'chat_columns'})

        elif test == 'msg_columns':
            r = db.session.execute(
                text(
                    'SELECT id, sender_id, receiver_id, body, status, is_read, chat_id, attachment_path, attachment_type FROM message LIMIT 5'
                )
            ).fetchall()
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
                text(
                    'SELECT id, body, sender_id, created_at, attachment_type FROM message WHERE chat_id = :cid ORDER BY created_at DESC LIMIT 1'
                ),
                {'cid': int(req.args.get('cid', 1))},
            ).fetchone()
            return jsonify({'row': dict(r._mapping) if r else None, 'test': 'last_msg'})

        elif test == 'users':
            r = db.session.execute(
                text('SELECT id, email, username, role, is_active FROM `user` ORDER BY id LIMIT 20')
            ).fetchall()
            users = []
            for u in r:
                try:
                    users.append({'id': u.id, 'email': u.email, 'username': u.username, 'role': u.role})
                except Exception:
                    users.append({'id': u[0], 'email': u[1], 'username': u[2], 'role': u[3]})
            return jsonify({'users': users, 'test': 'users'})

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
                {'uid': uid},
            ).fetchall()
            result = []
            for cr in chats:
                other = db.session.execute(
                    text('SELECT user_id FROM chat_participant WHERE chat_id = :cid AND user_id != :uid LIMIT 1'),
                    {'cid': cr.id, 'uid': uid},
                ).fetchone()
                last_msg = db.session.execute(
                    text(
                        'SELECT id, body, sender_id, created_at, attachment_type FROM message WHERE chat_id = :cid ORDER BY created_at DESC LIMIT 1'
                    ),
                    {'cid': cr.id},
                ).fetchone()
                unread = (
                    db.session.execute(
                        text(
                            "SELECT COUNT(*) FROM message WHERE chat_id = :cid AND sender_id != :uid AND status IN ('sent', 'delivered')"
                        ),
                        {'cid': cr.id, 'uid': uid},
                    ).scalar()
                    or 0
                )
                result.append(
                    {
                        'chat_id': cr.id,
                        'other_user_id': other.user_id if other else None,
                        'last_msg_id': last_msg.id if last_msg else None,
                        'unread': unread,
                    }
                )
            return jsonify({'chats': result, 'test': 'simulate_chats'})

        elif test == 'simulate_messages':
            cid = int(req.args.get('cid', 1))
            rows = db.session.execute(
                text(
                    'SELECT id, sender_id, receiver_id, body, status, is_read, attachment_path, attachment_type FROM message WHERE chat_id = :cid ORDER BY id DESC LIMIT :lim OFFSET :offs'
                ),
                {'cid': cid, 'lim': 10, 'offs': 0},
            ).fetchall()
            return jsonify(
                {
                    'messages': [{'id': r.id, 'sender_id': r.sender_id, 'body': r.body[:50]} for r in rows],
                    'test': 'simulate_messages',
                }
            )

        elif test == 'test_insert':
            from datetime import datetime

            chat_id = int(req.args.get('cid', 1))
            result = db.session.execute(text('SELECT 1 FROM chat WHERE id = :cid'), {'cid': chat_id}).fetchone()
            if not result:
                return jsonify({'error': 'chat not found', 'test': 'test_insert'}), 404

            from app.models.chat import Message

            ts = str(datetime.now(UTC).timestamp())
            insert_stmt = Message.__table__.insert().values(
                sender_id=1,
                receiver_id=5,
                body='debug test msg ' + ts,
                chat_id=chat_id,
                status='sent',
                attachment_path=None,
                attachment_type=None,
            )
            compiled = str(insert_stmt.compile(compile_kwargs={'literal_binds': True}))
            result = db.session.execute(insert_stmt)
            msg_id = result.inserted_primary_key[0]
            db.session.commit()
            # Verify and then delete
            verify = db.session.execute(
                text('SELECT id, body, is_read, is_active, created_at FROM message WHERE id = :mid'), {'mid': msg_id}
            ).fetchone()
            verify_dict = dict(verify._mapping) if verify else None
            db.session.execute(text('DELETE FROM message WHERE id = :mid'), {'mid': msg_id})
            db.session.commit()
            return jsonify(
                {
                    'test': 'test_insert',
                    'msg_id': msg_id,
                    'compiled_sql': compiled[:500],
                    'inserted': verify_dict,
                    'success': True,
                }
            )

        else:
            return jsonify(
                {
                    'error': 'unknown test',
                    'available': [
                        'basic',
                        'chat_count',
                        'chat_columns',
                        'msg_columns',
                        'join_chat',
                        'last_msg',
                        'users',
                        'simulate_chats',
                        'simulate_messages',
                        'test_insert',
                    ],
                }
            ), 400

    except Exception as e:
        import traceback

        return jsonify({'error': str(e)[:1000], 'traceback': traceback.format_exc(), 'test': test}), 500


@health_bp.route('/health/debug/sync-schema', methods=['GET', 'POST'])
def debug_sync_schema():
    from flask import request as req

    if req.args.get('key') != 'debug2026':
        return jsonify({'error': 'invalid key'}), 403

    created = []
    errors = []

    from app.models.password_reset import PasswordReset

    try:
        PasswordReset.__table__.create(db.engine, checkfirst=True)
        created.append('password_resets')
    except Exception as e:
        errors.append(f'password_resets: {e}')

    from sqlalchemy import inspect as sa_inspect

    tables = sa_inspect(db.engine).get_table_names()

    return jsonify({'created': created, 'errors': errors, 'tables': sorted(tables)})


@health_bp.route('/health/llm', methods=['GET'])
def health_llm():
    """Test each LLM provider and return detailed results."""
    import time
    results = {}
    test_messages = [{'role': 'user', 'content': 'Responde solo: hola'}]

    # GLM-5.2
    try:
        from app.services.llm_client import get_glm_client, GLM_MODEL
        import os
        key = os.environ.get('GLM_API_KEY', '')
        results['glm'] = {'key_set': bool(key), 'key_len': len(key), 'model': GLM_MODEL}
        client = get_glm_client()
        if client:
            t0 = time.time()
            r = client.chat.completions.create(model=GLM_MODEL, messages=test_messages, max_tokens=20, temperature=0.1)
            results['glm']['status'] = 'ok'
            results['glm']['response'] = r.choices[0].message.content
            results['glm']['latency_ms'] = int((time.time() - t0) * 1000)
        else:
            results['glm']['status'] = 'client_null'
            results['glm']['error'] = 'get_glm_client() returned None'
    except Exception as e:
        results['glm'] = {'status': 'error', 'error': str(e)[:300]}

    # Groq
    try:
        from app.services.llm_client import get_groq_client, GROQ_MODELS
        import os
        key = os.environ.get('GROQ_API_KEY', '')
        results['groq'] = {'key_set': bool(key), 'key_len': len(key)}
        client = get_groq_client()
        if client:
            t0 = time.time()
            r = client.chat.completions.create(model=GROQ_MODELS[0], messages=test_messages, max_tokens=20, temperature=0.1)
            results['groq']['status'] = 'ok'
            results['groq']['response'] = r.choices[0].message.content
            results['groq']['latency_ms'] = int((time.time() - t0) * 1000)
        else:
            results['groq']['status'] = 'client_null'
    except Exception as e:
        results['groq'] = {'status': 'error', 'error': str(e)[:300]}

    # Gemini
    try:
        from app.services.llm_client import get_gemini_model
        import os
        key = os.environ.get('GEMINI_API_KEY', '')
        results['gemini'] = {'key_set': bool(key), 'key_len': len(key)}
        model = get_gemini_model()
        if model:
            t0 = time.time()
            r = model.generate_content('Responde solo: hola')
            results['gemini']['status'] = 'ok'
            results['gemini']['response'] = r.text[:100]
            results['gemini']['latency_ms'] = int((time.time() - t0) * 1000)
        else:
            results['gemini']['status'] = 'client_null'
    except Exception as e:
        results['gemini'] = {'status': 'error', 'error': str(e)[:300]}

    # Full chain test (what MCP actually uses)
    try:
        from app.services.llm_client import llm_chat
        t0 = time.time()
        content, provider = llm_chat(test_messages, temperature=0.1, max_tokens=20)
        results['chain'] = {'status': 'ok', 'provider': provider, 'response': content, 'latency_ms': int((time.time() - t0) * 1000)}
    except Exception as e:
        results['chain'] = {'status': 'error', 'error': str(e)[:500]}

    return jsonify({'providers': results})


@health_bp.route('/health/llm/config', methods=['GET'])
@csrf.exempt
def health_llm_config():
    """Get current LLM configuration (API keys masked)."""
    import os

    def mask_key(k):
        if not k:
            return ''
        if len(k) <= 8:
            return '****'
        return k[:4] + '****' + k[-4:]

    return jsonify({
        'glm': {
            'key': mask_key(os.environ.get('GLM_API_KEY', '')),
            'model': 'z-ai/glm-5.2',
            'base_url': 'https://integrate.api.nvidia.com/v1',
        },
        'groq': {
            'key': mask_key(os.environ.get('GROQ_API_KEY', '')),
            'models': ['llama-3.3-70b-versatile', 'llama-3.1-8b-instant'],
        },
        'gemini': {
            'key': mask_key(os.environ.get('GEMINI_API_KEY', '')),
            'model': 'gemini-2.0-flash',
        },
    })


@health_bp.route('/health/llm/config', methods=['POST'])
@csrf.exempt
def health_llm_config_update():
    """Update LLM API keys at runtime. Admin only."""
    from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
    from app.models import User

    try:
        verify_jwt_in_request(locations=['cookies', 'headers'])
        uid = get_jwt_identity()
        user = User.query.get(int(uid))
        if not user or user.role not in ('admin', 'supervisor'):
            return jsonify({'error': 'No autorizado'}), 403
    except Exception:
        return jsonify({'error': 'No autenticado'}), 401

    data = request.get_json(silent=True) or {}
    updated = []
    errors = []

    for key_name in ['GLM_API_KEY', 'GROQ_API_KEY', 'GEMINI_API_KEY']:
        if key_name in data:
            new_val = data[key_name]
            if new_val and new_val != '****':
                os.environ[key_name] = new_val
                current_app.config[key_name] = new_val
                updated.append(key_name)

    if updated:
        from app.services.llm_client import reset_clients
        reset_clients()

    return jsonify({'updated': updated, 'errors': errors})


@health_bp.route('/health/debug/routes', methods=['GET'])
def debug_routes():
    rules = []
    for rule in sorted(current_app.url_map.iter_rules(), key=lambda r: r.rule):
        methods = ','.join(sorted(rule.methods - {'HEAD', 'OPTIONS'}))
        rules.append(
            {
                'rule': rule.rule,
                'endpoint': rule.endpoint,
                'methods': methods,
                'blueprint': rule.endpoint.split('.')[0] if '.' in rule.endpoint else '',
            }
        )
    return jsonify({'routes': rules, 'count': len(rules)})


@health_bp.route('/health/debug/request-info', methods=['GET', 'POST', 'OPTIONS', 'PUT', 'DELETE'])
def debug_request_info():
    """Returns full request info: headers, cookies, args, body. Helps diagnose 404/CORS issues."""
    from flask import request as req

    data = {
        'method': req.method,
        'path': req.path,
        'full_path': req.full_path,
        'url': req.url,
        'origin': req.headers.get('Origin', ''),
        'referer': req.headers.get('Referer', ''),
        'is_secure': req.is_secure,
        'scheme': req.scheme,
        'remote_addr': req.remote_addr,
        'content_type': req.content_type,
        'content_length': req.content_length,
        'headers': dict(req.headers),
        'cookies': dict(req.cookies),
        'args': dict(req.args),
        'json': req.get_json(silent=True),
        'blueprint': req.blueprint,
        'endpoint': req.endpoint,
        'user_agent': req.user_agent.string if req.user_agent else '',
        'is_json': req.is_json,
        'accept_mimetypes': str(req.accept_mimetypes),
    }
    return jsonify(data)


@health_bp.route('/health/debug/run-sql', methods=['GET', 'POST'])
def debug_run_sql():
    from flask import request as req

    if req.args.get('key') != 'debug2026':
        return jsonify({'error': 'invalid key'}), 403

    sql = req.args.get('sql', '') or (req.get_json(silent=True) or {}).get('sql', '')
    if not sql:
        return jsonify({'error': 'missing sql param'}), 400

    try:
        from sqlalchemy import text

        result = db.session.execute(text(sql))
        db.session.commit()

        if result.returns_rows:
            rows = [dict(r._mapping) for r in result.fetchmany(50)]
            return jsonify({'rows': rows, 'rowcount': result.rowcount})
        else:
            return jsonify({'rowcount': result.rowcount})

    except Exception as e:
        import traceback

        db.session.rollback()
        return jsonify({'error': str(e)[:1000], 'traceback': traceback.format_exc()}), 500
