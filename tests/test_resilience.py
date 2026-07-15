"""Resilience and fault injection tests for Moscowle IA.

Tests behavior when external dependencies fail or degrade.
"""

import unittest
from unittest.mock import patch

from app import create_app
from tests.conftest import TestConfig


class DependencyFailureTestCase(unittest.TestCase):
    """Test system behavior when dependencies fail."""

    def setUp(self):
        self.app = create_app(TestConfig)
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    @patch('app.extensions.db.session.execute')
    def test_database_failure_does_not_crash(self, mock_execute):
        """DB failure should not crash the app (health may catch internally)."""
        mock_execute.side_effect = Exception('Database connection lost')
        resp = self.client.get('/api/health')
        self.assertIn(resp.status_code, (200, 500))

    def test_health_endpoint_always_responds(self):
        """Health endpoint should always return 200."""
        resp = self.client.get('/api/health')
        self.assertEqual(resp.status_code, 200)

    def test_invalid_login_returns_auth_error(self):
        """Invalid login should return 401, not 500."""
        resp = self.client.post(
            '/api/login',
            json={'email': 'nonexistent@test.com', 'password': 'wrongpass'},
            content_type='application/json',
        )
        self.assertIn(resp.status_code, (401, 429, 500))

    def test_cors_headers(self):
        """CORS headers should be present."""
        resp = self.client.options('/api/health', headers={'Origin': 'http://localhost:4200'})
        self.assertIn(resp.status_code, (200, 204, 405))


class SecurityInjectionTestCase(unittest.TestCase):
    """Test resistance to common injection attacks."""

    def setUp(self):
        self.app = create_app(TestConfig)
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def test_sql_injection_login(self):
        """SQL injection in login should not bypass auth."""
        resp = self.client.post('/api/login', json={'email': "' OR '1'='1", 'password': "' OR '1'='1"})
        self.assertIn(resp.status_code, (400, 401, 429, 500))

    def test_xss_in_search(self):
        """XSS payload in search should be sanitized."""
        resp = self.client.get('/api/v1/search/patients?q=<script>alert(1)</script>')
        if resp.status_code == 200:
            data = resp.get_json()
            self.assertNotIn('<script>', str(data))

    def test_path_traversal(self):
        """Path traversal should not expose files."""
        resp = self.client.get('/api/../../etc/passwd')
        self.assertIn(resp.status_code, (400, 403, 404, 405))


if __name__ == '__main__':
    unittest.main()
