"""Métricas de la app en formato de texto de Prometheus (PRP 010), sin dependencias nuevas.

El deploy (`scripts/server_deploy.sh`) no instala paquetes de pip, así que no se usa `prometheus_client`: con un solo
worker de gunicorn (eventlet) basta un registro en memoria. Se exponen en `/api/server-monitor/metrics` con token
(`METRICS_TOKEN`): por el túnel todas las peticiones llegan desde el host, así que filtrar por IP no sirve.
"""

import os
import threading
import time
from collections import defaultdict
from datetime import datetime

from flask import g, request

BUCKETS = (0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0)
_STARTED = time.time()
_lock = threading.Lock()
_requests: dict = defaultdict(int)  # (method, route, code) → total
_hist: dict = defaultdict(lambda: [0] * (len(BUCKETS) + 1))  # route → contadores por cubeta (+Inf al final)
_sum: dict = defaultdict(float)
_count: dict = defaultdict(int)


def _route():
    if request.path.startswith('/app'):
        return 'spa'  # ~60 archivos estáticos por carga: una sola etiqueta para no inflar series
    if request.path.startswith('/socket.io'):
        return 'socket.io'
    rule = getattr(request, 'url_rule', None)
    return rule.rule if rule else 'unmatched'


def init_app(app):
    @app.before_request
    def _metrics_start():
        g._metrics_t0 = time.perf_counter()

    @app.after_request
    def _metrics_observe(response):
        t0 = getattr(g, '_metrics_t0', None)
        if t0 is None or request.path.endswith('/server-monitor/metrics'):
            return response
        took = time.perf_counter() - t0
        route = _route()
        with _lock:
            _requests[(request.method, route, response.status_code)] += 1
            row = _hist[route]
            for i, edge in enumerate(BUCKETS):
                if took <= edge:
                    row[i] += 1
            row[-1] += 1
            _sum[route] += took
            _count[route] += 1
        return response


def _esc(value):
    return str(value).replace('\\', '\\\\').replace('"', '\\"').replace('\n', ' ')


def _rss_bytes():
    try:
        with open(f'/proc/{os.getpid()}/status') as fh:
            for line in fh:
                if line.startswith('VmRSS:'):
                    return int(line.split()[1]) * 1024
    except OSError:
        pass
    return 0


def _business_gauges():
    """Datos de negocio baratos de consultar (se calculan al momento del scrape, cada 30 s)."""
    out = []
    try:
        from app.extensions import db
        from app.models.ai_external_call import AiExternalCall
        from app.models.payment import Payment
        from app.services import opencode_client as oc

        start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        for inst in ('chat', 'dev'):
            out.append(f'moscowle_mimo_configured{{instance_name="{inst}"}} {int(oc.configured(inst))}')
            out.append(f'moscowle_mimo_paused{{instance_name="{inst}"}} {int(oc.blocked(inst))}')
        rows = (
            db.session.query(
                AiExternalCall.route,
                AiExternalCall.ok,
                db.func.count(AiExternalCall.id),
                db.func.coalesce(db.func.sum(AiExternalCall.tokens_in), 0),
            )
            .filter(AiExternalCall.created_at >= start)
            .group_by(AiExternalCall.route, AiExternalCall.ok)
            .all()
        )
        for route, ok, calls, tokens in rows:
            out.append(f'moscowle_mimo_calls_today{{route="{_esc(route)}",ok="{int(bool(ok))}"}} {int(calls)}')
            out.append(f'moscowle_mimo_tokens_in_today{{route="{_esc(route)}",ok="{int(bool(ok))}"}} {int(tokens)}')
        paid = (
            db.session.query(db.func.count(Payment.id), db.func.coalesce(db.func.sum(Payment.amount), 0))
            .filter(Payment.date >= start, Payment.is_active.isnot(False))
            .one()
        )
        out.append(f'moscowle_payments_today_count {int(paid[0])}')
        out.append(f'moscowle_payments_today_amount {float(paid[1]):.2f}')
    except Exception:  # noqa: BLE001 - una consulta que falle no debe tumbar el scrape
        from app.extensions import db

        db.session.rollback()
        out.append('moscowle_business_metrics_error 1')
    return out


def render():
    lines = [
        '# HELP moscowle_http_requests_total Peticiones HTTP por método, ruta y código.',
        '# TYPE moscowle_http_requests_total counter',
    ]
    with _lock:
        reqs = dict(_requests)
        hist = {k: list(v) for k, v in _hist.items()}
        sums, counts = dict(_sum), dict(_count)
    for (method, route, code), n in sorted(reqs.items()):
        lines.append(f'moscowle_http_requests_total{{method="{method}",route="{_esc(route)}",code="{code}"}} {n}')
    lines += [
        '# HELP moscowle_http_request_duration_seconds Duración de las peticiones por ruta.',
        '# TYPE moscowle_http_request_duration_seconds histogram',
    ]
    for route, row in sorted(hist.items()):
        r = _esc(route)
        for edge, n in zip(BUCKETS, row, strict=False):
            lines.append(f'moscowle_http_request_duration_seconds_bucket{{route="{r}",le="{edge}"}} {n}')
        lines.append(f'moscowle_http_request_duration_seconds_bucket{{route="{r}",le="+Inf"}} {row[-1]}')
        lines.append(f'moscowle_http_request_duration_seconds_sum{{route="{r}"}} {sums.get(route, 0.0):.6f}')
        lines.append(f'moscowle_http_request_duration_seconds_count{{route="{r}"}} {counts.get(route, 0)}')
    lines += [
        '# TYPE moscowle_process_resident_memory_bytes gauge',
        f'moscowle_process_resident_memory_bytes {_rss_bytes()}',
        '# TYPE moscowle_process_uptime_seconds gauge',
        f'moscowle_process_uptime_seconds {time.time() - _STARTED:.0f}',
    ]
    lines += _business_gauges()
    return '\n'.join(lines) + '\n'


def authorized(header_value, env='METRICS_TOKEN'):
    import hmac

    token = os.environ.get(env, '')
    got = (header_value or '').removeprefix('Bearer ').strip()
    return bool(token) and hmac.compare_digest(got, token)
