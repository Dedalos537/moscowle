from app.middleware.metrics_middleware import MetricsCollector


class TestMetricsCollector:
    def test_record_request(self):
        c = MetricsCollector()
        c.record_request('GET', '/api/test', 200, 50.5)
        snap = c.get_snapshot()
        assert snap['request_count']['GET /api/test'] == 1
        assert snap['status_codes'][200] == 1

    def test_record_multiple_requests(self):
        c = MetricsCollector()
        c.record_request('GET', '/api/a', 200, 10)
        c.record_request('GET', '/api/a', 200, 20)
        c.record_request('POST', '/api/b', 201, 30)
        c.record_request('GET', '/api/a', 500, 100)

        snap = c.get_snapshot()
        assert snap['request_count']['GET /api/a'] == 3
        assert snap['request_count']['POST /api/b'] == 1
        assert snap['status_codes'][200] == 2
        assert snap['status_codes'][201] == 1
        assert snap['status_codes'][500] == 1
        assert snap['error_count']['GET /api/a'] == 1

    def test_latency_percentiles(self):
        c = MetricsCollector()
        for i in range(100):
            c.record_request('GET', '/api/slow', 200, float(i))

        snap = c.get_snapshot()
        lat = snap['latency']['GET /api/slow']
        assert lat['count'] == 100
        assert lat['avg_ms'] == 49.5
        assert lat['p50_ms'] == 50.0
        assert lat['max_ms'] == 99.0

    def test_active_requests(self):
        c = MetricsCollector()
        assert c.get_snapshot()['active_requests'] == 0
        c.increment_active()
        c.increment_active()
        assert c.get_snapshot()['active_requests'] == 2
        c.decrement_active()
        assert c.get_snapshot()['active_requests'] == 1

    def test_db_query_metrics(self):
        c = MetricsCollector()
        c.record_db_query(15.5)
        c.record_db_query(25.0)
        snap = c.get_snapshot()
        assert snap['db_query_count'] == 2
        assert snap['db_query_total_ms'] == 40.5

    def test_reset(self):
        c = MetricsCollector()
        c.record_request('GET', '/api/test', 200, 50)
        c.record_db_query(10)
        c.reset()
        snap = c.get_snapshot()
        assert snap['request_count'] == {}
        assert snap['db_query_count'] == 0


class TestMetricsEndpoint:
    def test_metrics_returns_prometheus_format(self, client):
        resp = client.get('/metrics')
        assert resp.status_code == 200
        text = resp.data.decode('utf-8')
        assert 'flask_app_info' in text
        assert 'http_requests_total' in text
        assert 'process_uptime_seconds' in text
        assert '# HELP' in text
        assert '# TYPE' in text

    def test_metrics_includes_clinical(self, client):
        resp = client.get('/metrics')
        text = resp.data.decode('utf-8')
        assert 'session_accuracy_avg' in text
        assert 'session_attendance_rate' in text

    def test_metrics_includes_incidents(self, client):
        resp = client.get('/metrics')
        text = resp.data.decode('utf-8')
        assert 'incidents_open' in text
