import logging
import os
import time
from datetime import UTC, datetime

from flask import Blueprint, Response, current_app, jsonify
from sqlalchemy import text

from app.middleware.metrics_middleware import collector

logger = logging.getLogger(__name__)

metrics_bp = Blueprint('metrics', __name__, url_prefix='')


@metrics_bp.route('/health')
def health():
    return jsonify(
        {
            'status': 'ok',
            'timestamp': datetime.now(UTC).isoformat(),
            'app': current_app.name,
        }
    )


@metrics_bp.route('/metrics')
def metrics():
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
        f'python_info{{version="{os.sys.version_info.major}.{os.sys.version_info.minor}'
        f'.{os.sys.version_info.micro}"}} 1',
        '',
    ]

    # --- Technical: Request Metrics ---
    snap = collector.get_snapshot()
    total_requests = sum(snap['request_count'].values())
    total_errors = sum(snap['error_count'].values())

    lines.extend(
        [
            '# HELP http_requests_total Total number of HTTP requests',
            '# TYPE http_requests_total counter',
            f'http_requests_total {total_requests}',
            '',
            '# HELP http_request_errors_total Total number of 5xx HTTP requests',
            '# TYPE http_request_errors_total counter',
            f'http_request_errors_total {total_errors}',
            '',
            '# HELP http_active_requests Currently active requests',
            '# TYPE http_active_requests gauge',
            f'http_active_requests {snap["active_requests"]}',
            '',
        ]
    )

    # Per-status code counters
    lines.append('# HELP http_status_codes_total Requests by status code')
    lines.append('# TYPE http_status_codes_total counter')
    for code, count in sorted(snap['status_codes'].items()):
        lines.append(f'http_status_codes_total{{code="{code}"}} {count}')
    lines.append('')

    # Latency percentiles
    lines.append('# HELP http_request_duration_ms Request latency in milliseconds')
    lines.append('# TYPE http_request_duration_ms summary')
    for path_key, lat in snap.get('latency', {}).items():
        lines.append(f'http_request_duration_ms{{path="{path_key}",quantile="avg"}} {lat["avg_ms"]}')
        lines.append(f'http_request_duration_ms{{path="{path_key}",quantile="p50"}} {lat["p50_ms"]}')
        lines.append(f'http_request_duration_ms{{path="{path_key}",quantile="p95"}} {lat["p95_ms"]}')
        lines.append(f'http_request_duration_ms{{path="{path_key}",quantile="p99"}} {lat["p99_ms"]}')
        lines.append(f'http_request_duration_ms{{path="{path_key}",quantile="max"}} {lat["max_ms"]}')
    lines.append('')

    # DB metrics
    lines.extend(
        [
            '# HELP db_queries_total Total database queries executed',
            '# TYPE db_queries_total counter',
            f'db_queries_total {snap["db_query_count"]}',
            '',
            '# HELP db_query_duration_ms_total Total DB query time in ms',
            '# TYPE db_query_duration_ms_total counter',
            f'db_query_duration_ms_total {snap["db_query_total_ms"]}',
            '',
        ]
    )

    # --- Technical: Database counts ---
    try:
        from app.extensions import db

        engine = db.get_engine()
        with engine.connect() as conn:
            result = conn.execute(text('SELECT COUNT(*) FROM user'))
            user_count = result.scalar()
            lines.extend(
                [
                    '# HELP db_user_count Total users in database',
                    '# TYPE db_user_count gauge',
                    f'db_user_count {user_count}',
                    '',
                ]
            )
    except Exception:
        lines.extend(
            [
                '# HELP db_user_count Total users in database',
                '# TYPE db_user_count gauge',
                'db_user_count -1',
                '',
            ]
        )

    # --- Clinical: Session Metrics ---
    try:
        from app.extensions import db as _db
        from app.models.appointment import Appointment, SessionMetrics

        now_dt = datetime.now(UTC)

        # Average accuracy last 24h
        recent_metrics = (
            _db.session.query(SessionMetrics.accurracy)
            .filter(SessionMetrics.date > now_dt - __import__('datetime').timedelta(hours=24))
            .all()
        )
        avg_accuracy = round(sum(m[0] for m in recent_metrics) / len(recent_metrics), 4) if recent_metrics else 0
        lines.extend(
            [
                '# HELP session_accuracy_avg Average session accuracy in last 24h',
                '# TYPE session_accuracy_avg gauge',
                f'session_accuracy_avg {avg_accuracy}',
                '',
            ]
        )

        # Attendance rate last 7 days
        week_ago = now_dt - __import__('datetime').timedelta(days=7)
        total_sessions = Appointment.query.filter(Appointment.start_time >= week_ago, Appointment.is_active).count()
        attended_sessions = Appointment.query.filter(
            Appointment.start_time >= week_ago,
            Appointment.attendance == 'present',
            Appointment.is_active,
        ).count()
        attendance_rate = round(attended_sessions / total_sessions, 4) if total_sessions > 0 else 1.0
        lines.extend(
            [
                '# HELP session_attendance_rate Session attendance rate last 7 days',
                '# TYPE session_attendance_rate gauge',
                f'session_attendance_rate {attendance_rate}',
                '',
                '# HELP session_total_7d Total sessions in last 7 days',
                '# TYPE session_total_7d gauge',
                f'session_total_7d {total_sessions}',
                '',
            ]
        )

        # Model prediction errors
        total_predictions = SessionMetrics.query.filter(
            SessionMetrics.date > now_dt - __import__('datetime').timedelta(hours=24)
        ).count()
        error_predictions = SessionMetrics.query.filter(
            SessionMetrics.date > now_dt - __import__('datetime').timedelta(hours=24),
            SessionMetrics.accurracy < 0.1,
        ).count()
        lines.extend(
            [
                '# HELP model_predictions_total Total model predictions in 24h',
                '# TYPE model_predictions_total gauge',
                f'model_predictions_total {total_predictions}',
                '',
                '# HELP model_prediction_errors_total Predictions with accuracy < 10%',
                '# TYPE model_prediction_errors_total gauge',
                f'model_prediction_errors_total {error_predictions}',
                '',
            ]
        )

    except Exception:
        lines.extend(
            [
                '# HELP session_accuracy_avg Average session accuracy in last 24h',
                '# TYPE session_accuracy_avg gauge',
                'session_accuracy_avg 0',
                '',
                '# HELP session_attendance_rate Session attendance rate last 7 days',
                '# TYPE session_attendance_rate gauge',
                'session_attendance_rate 0',
                '',
            ]
        )

    # --- Clinical: Incident Metrics ---
    try:
        from app.models.incidente import Incidente

        open_incidents = Incidente.query.filter(
            Incidente.estado.in_(['NUEVO', 'EN_CURSO', 'PENDIENTE_PROVEEDOR']),
            Incidente.is_active,
        ).count()

        breached_incidents = Incidente.query.filter(
            Incidente.estado.in_(['NUEVO', 'EN_CURSO', 'PENDIENTE_PROVEEDOR']),
            Incidente.fecha_limite_sla < now_dt,
            Incidente.is_active,
        ).count()

        total_incidents_7d = Incidente.query.filter(
            Incidente.created_at >= now_dt - __import__('datetime').timedelta(days=7),
            Incidente.is_active,
        ).count()
        resolved_7d = Incidente.query.filter(
            Incidente.estado.in_(['RESUELTO', 'CERRADO']),
            Incidente.fecha_resolucion >= now_dt - __import__('datetime').timedelta(days=7),
            Incidente.is_active,
        ).count()
        sla_compliance = round(resolved_7d / total_incidents_7d, 4) if total_incidents_7d > 0 else 1.0

        lines.extend(
            [
                '# HELP incidents_open Total open incidents',
                '# TYPE incidents_open gauge',
                f'incidents_open {open_incidents}',
                '',
                '# HELP incidents_sla_breaches Total incidents with breached SLA',
                '# TYPE incidents_sla_breaches gauge',
                f'incidents_sla_breaches {breached_incidents}',
                '',
                '# HELP incidents_sla_compliance SLA compliance ratio last 7 days',
                '# TYPE incidents_sla_compliance gauge',
                f'incidents_sla_compliance {sla_compliance}',
                '',
            ]
        )

    except Exception:
        lines.extend(
            [
                '# HELP incidents_open Total open incidents',
                '# TYPE incidents_open gauge',
                'incidents_open 0',
                '',
            ]
        )

    # --- Railway Metrics (if configured) ---
    try:
        from app.services.railway_service import get_railway_metrics

        railway = get_railway_metrics()
        if railway.get('success'):
            rd = railway['data']
            lines.extend(
                [
                    '# HELP railway_cpu_percentage CPU usage percentage',
                    '# TYPE railway_cpu_percentage gauge',
                    f'railway_cpu_percentage {rd["cpu"]["percentage"]}',
                    '',
                    '# HELP railway_memory_percentage Memory usage percentage',
                    '# TYPE railway_memory_percentage gauge',
                    f'railway_memory_percentage {rd["memory"]["percentage"]}',
                    '',
                ]
            )
    except Exception as e:
        logger.debug('Railway metrics unavailable: %s', e)

    # --- Crisis Monitor ---
    try:
        from app.services.crisis_monitor import crisis_monitor

        crisis_metrics = crisis_monitor.get_metrics()
        if crisis_metrics:
            for metric_type, data in crisis_metrics.items():
                severity = data.get('severity', 'unknown')
                value = data.get('value', 0)
                lines.extend(
                    [
                        f'# HELP crisis_{metric_type} Crisis monitor alert for {metric_type}',
                        f'# TYPE crisis_{metric_type} gauge',
                        f'crisis_{metric_type}{{severity="{severity}"}} {value}',
                        '',
                    ]
                )
    except Exception as e:
        logger.debug('Crisis monitor metrics unavailable: %s', e)

    return Response('\n'.join(lines), mimetype='text/plain; charset=utf-8')
