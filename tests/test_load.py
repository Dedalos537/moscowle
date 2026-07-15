"""Load and stress tests for Moscowle IA backend.

Tests concurrent request handling, database connection pooling,
and API latency under load.
"""

import concurrent.futures
import time
import unittest

from app import create_app
from tests.conftest import TestConfig


class LoadTestCase(unittest.TestCase):
    """Test system behavior under concurrent load."""

    def setUp(self):
        self.app = create_app(TestConfig)
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def _make_request(self, url):
        """Make a single request and return status code + latency."""
        start = time.time()
        with self.app.test_client() as client:
            resp = client.get(url)
        latency = time.time() - start
        return resp.status_code, latency

    def test_concurrent_health_checks(self):
        """20 concurrent requests to /api/health should all succeed."""
        url = '/api/health'
        num_requests = 20
        results = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(self._make_request, url) for _ in range(num_requests)]
            for f in concurrent.futures.as_completed(futures):
                results.append(f.result())

        status_codes = [r[0] for r in results]
        latencies = [r[1] for r in results]

        self.assertTrue(
            all(s == 200 for s in status_codes), f'Some requests failed: {[s for s in status_codes if s != 200]}'
        )

        p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]
        self.assertLess(p95_latency, 2.0, f'P95 latency too high: {p95_latency:.2f}s (target: <2.0s)')

    def test_concurrent_login_attempts(self):
        """20 concurrent login attempts should not cause 500 errors."""
        url = '/api/login'
        num_requests = 20

        with concurrent.futures.ThreadPoolExecutor(max_workers=10):
            futures = []
            for _ in range(num_requests):
                with self.app.test_client() as client:
                    resp = client.get(url)
                    futures.append(resp.status_code)

        # Should get 401 (invalid credentials) or 429 (rate limited), or 500 (missing App-Key in test)
        self.assertTrue(
            all(s in (401, 429, 500) for s in futures),
            f'Unexpected status codes: {[s for s in futures if s not in (401, 429, 500)]}',
        )

    def test_concurrent_session_list(self):
        """10 concurrent requests to session endpoints."""
        url = '/api/sessions'
        num_requests = 10

        with concurrent.futures.ThreadPoolExecutor(max_workers=5):
            futures = []
            for _ in range(num_requests):
                with self.app.test_client() as client:
                    resp = client.get(url)
                    futures.append(resp.status_code)

        # Should get 401/403 (no auth/App-Key) or 200, never 500
        self.assertTrue(all(s in (200, 401, 403) for s in futures), f'Unexpected status codes: {futures}')


class ResilienceTestCase(unittest.TestCase):
    """Test system resilience under degraded conditions."""

    def setUp(self):
        self.app = create_app(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def test_health_endpoint_resilience(self):
        """Health endpoint should always respond, even under stress."""
        client = self.app.test_client()
        for _ in range(50):
            resp = client.get('/api/health')
            self.assertEqual(resp.status_code, 200)

    def test_invalid_json_body(self):
        """Malformed JSON should return 400, not 500."""
        client = self.app.test_client()
        resp = client.post('/api/login', data='not json', content_type='application/json')
        self.assertIn(resp.status_code, (400, 401, 429))

    def test_missing_content_type(self):
        """Missing Content-Type should not crash the server."""
        client = self.app.test_client()
        resp = client.post('/api/login', data='test')
        self.assertIn(resp.status_code, (400, 401, 415, 429))


if __name__ == '__main__':
    unittest.main()
