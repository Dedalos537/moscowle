import contextlib

from app.routes.api import api_bp
from app.routes.api._shared import (
    Appointment,
    Game,
    SessionMetrics,
    User,
    current_app,
    current_user,
    datetime,
    db,
    func,
    game_service,
    json,
    jsonify,
    limiter,
    login_required,
    notification_service,
    or_,
    os,
    predict_level,
    request,
    requests,
    start_async_training,
    url_for,
)


@api_bp.route('/games', methods=['GET'])
@login_required
def api_list_games():
    files = game_service.list_games()
    return jsonify({'games': files})


@api_bp.route('/save_game', methods=['POST'])
@login_required
@limiter.limit('20 per minute')
def save_game():
    try:
        data = request.get_json() or {}
        game_name = data.get('game_name') or 'Juego'
        accuracy = float(data.get('accuracy') or 0)
        avg_time = float(data.get('avg_time') or 0)
        session_id = data.get('session_id')

        appt = None
        if session_id:
            appt = Appointment.query.get(int(session_id))
            if not appt:
                return jsonify({'error': 'Esa sesión no existe'}), 404

            if current_user.role == 'jugador' and appt.patient_id != current_user.id:
                return jsonify({'error': 'No autorizado para esta sesión'}), 403

            if appt.status == 'completed':
                return jsonify({'error': 'Esta sesión ya se completó'}), 400

            assigned_normalized = [g.lower().replace('.html', '').replace('_', ' ') for g in appt.games_list]
            current_normalized = game_name.lower().replace('.html', '').replace('_', ' ')

            if appt.games_list and current_normalized not in assigned_normalized:
                current_app.logger.warning(f'Game mismatch: {game_name} not in {appt.games_list}')

        pred_code, label = predict_level(accuracy, avg_time * 1000)

        m = SessionMetrics(
            user_id=current_user.id,
            session_id=int(session_id) if session_id else None,
            game_name=game_name,
            accurracy=accuracy,
            avg_time=avg_time,
            prediction=pred_code,
        )

        game_obj = Game.query.filter(or_(Game.filename == game_name, Game.title == game_name)).first()
        if game_obj:
            m.game_id = game_obj.id

        db.session.add(m)

        if appt:
            db.session.flush()

            played_count = SessionMetrics.query.filter_by(session_id=appt.id).count()

            total_assigned = len(appt.games_list)

            if played_count >= total_assigned > 0:
                appt.status = 'completed'
                appt.end_time = datetime.utcnow()
                db.session.add(appt)
                with contextlib.suppress(Exception):
                    notification_service.create_notification(
                        appt.therapist_id,
                        f'Sesión #{appt.id} completada por {current_user.username}',
                        link=url_for('therapist.patients', _external=False),
                    )

        db.session.commit()

        try:
            total_metrics = SessionMetrics.query.count()
            if total_metrics > 0 and total_metrics % 5 == 0:
                all_metrics = SessionMetrics.query.all()
                training_data = [[m.accurracy, m.avg_time * 1000] for m in all_metrics]
                current_app.logger.info(f'Triggering AI async retraining with {len(training_data)} samples...')
                start_async_training(training_data)
        except Exception as e:
            current_app.logger.error(f'AI Retraining trigger failed: {e}')

        return jsonify({'status': 'ok', 'prediction': pred_code, 'recommendation': label})
    except Exception as e:
        return jsonify({'error': 'no_se_pudo_guardar', 'detail': str(e)}), 400


@api_bp.route('/games/upload', methods=['POST'])
@limiter.limit('5 per hour')
@login_required
def upload_game():
    if current_user.role != 'terapista':
        return jsonify({'error': 'Acceso denegado'}), 403
    file = request.files.get('file')
    name = request.form.get('name')
    if not file or not name:
        return jsonify({'error': 'Falta el archivo o el nombre'}), 400
    if not name.lower().endswith('.html'):
        name = f'{name}.html'
    dest_dir = os.path.join(current_app.root_path, 'static', 'games')
    os.makedirs(dest_dir, exist_ok=True)
    path = os.path.join(dest_dir, name)
    file.save(path)
    return jsonify({'status': 'ok', 'file': name, 'url': url_for('static', filename=f'games/{name}')})


@api_bp.route('/ai/generate_game', methods=['POST'])
@login_required
def generate_game():
    if current_user.role not in ('terapista', 'admin', 'supervisor'):
        return jsonify({'error': 'Acceso denegado'}), 403
    api_key = current_app.config.get('GEMINI_API_KEY')
    payload = request.get_json() or {}
    prompt = payload.get('prompt') or 'Genera un juego terapéutico en HTML.'
    target_user_id = payload.get('user_id')
    game_name = (payload.get('name') or 'ai_game').strip().replace(' ', '_')
    if not target_user_id:
        return jsonify({'error': 'Falta user_id'}), 400
    user = User.query.get(target_user_id)
    if not user:
        return jsonify({'error': 'Usuario no encontrado'}), 404

    kpi = {}
    kpi['total_sessions'] = SessionMetrics.query.filter_by(user_id=user.id).count()
    kpi['avg_accuracy'] = float(
        db.session.query(func.avg(SessionMetrics.accurracy)).filter_by(user_id=user.id).scalar() or 0
    )
    kpi['avg_time_ms'] = float(
        (db.session.query(func.avg(SessionMetrics.avg_time)).filter_by(user_id=user.id).scalar() or 0) * 1000
    )
    kpi['last_games'] = [
        {
            'game_name': m.game_name,
            'accuracy': float(m.accurracy),
            'avg_time_ms': float(m.avg_time * 1000),
            'prediction': int(m.prediction),
            'date': m.date.isoformat(),
        }
        for m in SessionMetrics.query.filter_by(user_id=user.id).order_by(SessionMetrics.date.desc()).limit(10)
    ]

    full_prompt = (
        f'{prompt}\n\n'
        'Genera dos bloques: 1) HTML completo para un juego sencillo de reflejos/cognitivo con UI moderna, tailwindcdn y FontAwesome (no frameworks).\n'
        '2) JSON de configuración KPI con claves: kpis(avg_accuracy, avg_time_ms, total_sessions), goals, difficulty, and tracking schema for events.\n'
        f'KPIs del paciente: {json.dumps(kpi, ensure_ascii=False)}\n'
        'Devuelve primero el JSON (entre marcadores ---JSON---) y luego el HTML (entre ---HTML---).'
    )

    if not api_key:
        config = {
            'kpis': {
                'avg_accuracy': kpi['avg_accuracy'],
                'avg_time_ms': kpi['avg_time_ms'],
                'total_sessions': kpi['total_sessions'],
            },
            'goals': ['Mejorar reflejos', 'Reducir tiempo de reacción'],
            'difficulty': 'medium',
            'tracking': {'events': ['click', 'hit', 'miss'], 'schema_version': 1},
        }
        html = (
            '<!DOCTYPE html><html><head><meta charset="utf-8"><script src="https://cdn.tailwindcss.com"></script></head><body class="p-6">\n'
            '<h2 class="text-2xl font-bold">Juego IA (fallback)</h2>\n'
            '<p class="text-gray-600">Config basado en KPIs.</p>\n'
            '</body></html>'
        )
    else:
        try:
            url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={api_key}'
            body = {'contents': [{'parts': [{'text': full_prompt}]}]}
            resp = requests.post(url, json=body, timeout=15)
            resp.raise_for_status()
            j = resp.json()
            text = j.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text') or ''
            json_start = text.find('---JSON---')
            html_start = text.find('---HTML---')
            if json_start != -1 and html_start != -1:
                json_block = text[json_start + len('---JSON---') : html_start].strip()
                html_block = text[html_start + len('---HTML---') :].strip()
                try:
                    config = json.loads(json_block)
                except Exception:
                    config = {'raw': json_block}
                html = html_block
            else:
                config = {'raw': text}
                html = '<!DOCTYPE html><html><body><pre>Salida IA sin marcadores</pre></body></html>'
        except Exception as e:
            config = {'error': str(e), 'kpis': kpi}
            html = '<!DOCTYPE html><html><body><pre>Error generando juego IA</pre></body></html>'

    dest_dir = os.path.join(current_app.root_path, 'static', 'games')
    os.makedirs(dest_dir, exist_ok=True)
    filename = f'{game_name}.html'
    path = os.path.join(dest_dir, filename)
    try:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(html)
    except Exception as e:
        return jsonify({'error': 'write_failed', 'detail': str(e)}), 500

    try:
        user.game_profile = json.dumps(config, ensure_ascii=False)
        db.session.commit()
    except Exception as e:
        return jsonify({'error': 'persist_failed', 'detail': str(e)}), 500

    return jsonify(
        {'status': 'ok', 'file': filename, 'url': url_for('static', filename=f'games/{filename}'), 'config': config}
    )
