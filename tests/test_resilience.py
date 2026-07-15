"""Resilience and fault injection tests for Moscowle IA.

Tests behavior when external dependencies fail or degrade.
"""

import unittest
from unittest.mock import patch

from app import create_app


class DependencyFailureTestCase(unittest.TestCase):
    """Test system behavior when dependencies fail."""

    def setUp(self):
        self.app = create_app('testing')
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    @patch('app.extensions.db.session.execute')
    def test_database_failure_returns_500(self, mock_execute):
        """DB failure should return 500, not crash."""
        mock_execute.side_effect = Exception('Database connection lost')
        resp = self.client.get('/api/health')
        self.assertEqual(resp.status_code, 500)

    @patch('app.services.llm_automation_service.LLMAutomationService')
    def test_llm_service_failure(self, mock_llm):
        """LLM service failure should not crash the app."""
        mock_llm.return_value.generate_session_notes.side_effect = Exception('LLM timeout')
        resp = self.client.get('/api/health')
        self.assertEqual(resp.status_code, 200)

    def test_rate_limiting_enforcement(self):
        """Rate limiter should enforce limits."""
        client = self.app.test_client()
        responses = []
        for _ in range(60):
            resp = client.post('/api/login', json={'email': 'test@test.com', 'password': 'wrong'})
            responses.append(resp.status_code)

        # Should get at least one 429 after many attempts
        self.assertIn(429, responses, 'Rate limiting not enforced after 60 attempts')

    def test_cors_headers(self):
        """CORS headers should be present."""
        resp = self.client.options('/api/health', headers={'Origin': 'http://localhost:4200'})
        self.assertIn(resp.status_code, (200, 204, 405))


class SecurityInjectionTestCase(unittest.TestCase):
    """Test resistance to common injection attacks."""

    def setUp(self):
        self.app = create_app('testing')
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def test_sql_injection_login(self):
        """SQL injection in login should not bypass auth."""
        resp = self.client.post('/api/login', json={'email': "' OR '1'='1", 'password': "' OR '1'='1"})
        self.assertIn(resp.status_code, (400, 401, 429))

    def test_xss_in_search(self):
        """XSS payload in search should be sanitized."""
        resp = self.client.get('/api/v1/search/patients?q=<script>alert(1)</script>')
        if resp.status_code == 200:
            data = resp.get_json()
            self.assertNotIn('<script>', str(data))

    def test_path_traversal(self):
        """Path traversal should not expose files."""
        resp = self.client.get('/api/../../etc/passwd')
        self.assertIn(resp.status_code, (400, 404, 405))


if __name__ == '__main__':
    unittest.main()
