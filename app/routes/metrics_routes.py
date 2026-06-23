from datetime import UTC, datetime

from flask import Blueprint, Response, current_app, jsonify

metrics_bp = Blueprint('metrics', __name__, url_prefix='')


@metrics_bp.route('/health')
def health():
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now(UTC).isoformat(),
        'app': current_app.name,
    })


@metrics_bp.route('/metrics')
def metrics():
    import os
    import time

    os.getpid()
    now = time.time()
    uptime = current_app.config.get('START_TIME', now)

    lines = [
        '# HELP flask_app_info Application metadata',
        '# TYPE flask_app_info gauge',
        f'flask_app_info{{env="{current_app.config.get("ENV", "unknown")}",name="{current_app.import_name}"}} 1',
        '',
        '# HELP process_start_time_seconds Start time of the process',
        '# TYPE process_start_time_seconds gauge',
        f'process_start_time_seconds {uptime}',
        '',
        '# HELP process_uptime_seconds Seconds since process started',
        '# TYPE process_uptime_seconds gauge',
        f'process_uptime_seconds {now - uptime}',
        '',
        '# HELP python_info Python runtime info',
        '# TYPE python_info gauge',
        f'python_info{{version="{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}"}} 1',
        '',
    ]

    try:
        import sqlalchemy

        from app.extensions import db
        engine = db.get_engine()
        with engine.connect() as conn:
            result = conn.execute(sqlalchemy.text('SELECT COUNT(*) FROM user'))
            user_count = result.scalar()
            lines.append('# HELP db_user_count Total users in database')
            lines.append('# TYPE db_user_count gauge')
            lines.append(f'db_user_count {user_count}')
            lines.append('')
    except Exception:
        lines.append('# HELP db_user_count Total users in database')
        lines.append('# TYPE db_user_count gauge')
        lines.append('db_user_count -1')
        lines.append('')

    return Response('\n'.join(lines), mimetype='text/plain; charset=utf-8')
