import threading
import time
from collections import defaultdict

from flask import g, request


class MetricsCollector:
    """Thread-safe metrics collector for request latency, status codes, and counters."""

    def __init__(self):
        self._lock = threading.Lock()
        self._request_count = defaultdict(int)
        self._request_latency = defaultdict(list)
        self._status_codes = defaultdict(int)
        self._error_count = defaultdict(int)
        self._db_query_count = 0
        self._db_query_total_ms = 0.0
        self._active_requests = 0
        self._started_at = time.time()

    def record_request(self, method, path, status_code, duration_ms):
        with self._lock:
            key = f'{method} {path}'
            self._request_count[key] += 1
            self._request_latency[key].append(duration_ms)
            self._status_codes[status_code] += 1
            if status_code >= 500:
                self._error_count[key] += 1

    def record_db_query(self, duration_ms):
        with self._lock:
            self._db_query_count += 1
            self._db_query_total_ms += duration_ms

    def increment_active(self):
        with self._lock:
            self._active_requests += 1

    def decrement_active(self):
        with self._lock:
            self._active_requests = max(0, self._active_requests - 1)

    def get_snapshot(self):
        with self._lock:
            snapshot = {
                'request_count': dict(self._request_count),
                'status_codes': dict(self._status_codes),
                'error_count': dict(self._error_count),
                'db_query_count': self._db_query_count,
                'db_query_total_ms': round(self._db_query_total_ms, 2),
                'active_requests': self._active_requests,
                'uptime_seconds': round(time.time() - self._started_at, 0),
            }

            latency_summary = {}
            for key, values in self._request_latency.items():
                if values:
                    sorted_vals = sorted(values)
                    n = len(sorted_vals)
                    latency_summary[key] = {
                        'count': n,
                        'avg_ms': round(sum(values) / n, 2),
                        'p50_ms': round(sorted_vals[n // 2], 2),
                        'p95_ms': round(sorted_vals[int(n * 0.95)] if n >= 20 else sorted_vals[-1], 2),
                        'p99_ms': round(sorted_vals[int(n * 0.99)] if n >= 100 else sorted_vals[-1], 2),
                        'max_ms': round(sorted_vals[-1], 2),
                    }
            snapshot['latency'] = latency_summary

            return snapshot

    def reset(self):
        with self._lock:
            self._request_count.clear()
            self._request_latency.clear()
            self._status_codes.clear()
            self._error_count.clear()
            self._db_query_count = 0
            self._db_query_total_ms = 0.0
            self._started_at = time.time()


collector = MetricsCollector()


def init_metrics_middleware(app):
    """Register before/after request hooks for metrics collection."""

    @app.before_request
    def metrics_before_request():
        g._metrics_start = time.time()
        collector.increment_active()

    @app.after_request
    def metrics_after_request(response):
        collector.decrement_active()

        start = getattr(g, '_metrics_start', None)
        if start is None:
            return response

        duration_ms = (time.time() - start) * 1000
        path = request.path

        skip_paths = ('/metrics', '/health', '/static/', '/uploads/')
        if not any(path.startswith(p) for p in skip_paths):
            collector.record_request(
                method=request.method,
                path=path,
                status_code=response.status_code,
                duration_ms=round(duration_ms, 2),
            )

        response.headers['X-Request-Duration-Ms'] = str(round(duration_ms, 2))
        return response
