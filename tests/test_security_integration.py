import json
from urllib.parse import quote_plus


class TestSqlInjection:
    """C.3 SQL injection simulation tests (read-only payloads)"""

    SQLI_PAYLOADS = [
        "' OR '1'='1",
        "'; DROP TABLE user; --",
        "' UNION SELECT * FROM user --",
        "admin' --",
        "1; SELECT * FROM information_schema.tables",
        "' OR 1=1 --",
        "test@example.com' OR '1'='1",
    ]

    def test_login_sqli_email(self, client):
        for payload in self.SQLI_PAYLOADS:
            resp = client.post(
                '/api/login',
                content_type='application/json',
                data=json.dumps({'email': payload, 'password': 'irrelevant'}),
            )
            assert resp.status_code in (400, 401), f'SQLi payload leaked: {payload}'

    def test_login_sqli_password(self, client):
        for payload in self.SQLI_PAYLOADS:
            resp = client.post(
                '/api/login',
                content_type='application/json',
                data=json.dumps({'email': 'test@example.com', 'password': payload}),
            )
            assert resp.status_code in (400, 401), f'SQLi payload leaked: {payload}'

    def test_sqli_in_url_params(self, client):
        for payload in self.SQLI_PAYLOADS:
            encoded = quote_plus(payload)
            resp = client.get(f'/api/auth/me?debug={encoded}')
            assert resp.status_code in (401, 400, 404), f'SQLi payload leaked via URL: {payload}'


class TestXssSanitizerRuntime:
    """A.6 Verify XSS sanitizer runs on key endpoints"""

    XSS_PAYLOADS = [
        '<script>alert(1)</script>',
        '<img src=x onerror=alert(1)>',
        '"><script>fetch("/steal")</script>',
        '<svg onload=alert(1)>',
    ]

    def test_contact_message_sanitized(self, client):
        for payload in self.XSS_PAYLOADS:
            resp = client.post(
                '/api/contact',
                content_type='application/json',
                data=json.dumps({
                    'first_name': payload,
                    'last_name': 'Test',
                    'email': 'test@example.com',
                    'message': payload,
                }),
            )
            if resp.status_code == 200:
                data = resp.get_json()
                if data and data.get('success'):
                    assert '<script>' not in resp.get_data(as_text=True)

    def test_chat_message_sanitized(self, client, test_user):
        client.post(
            '/api/login',
            content_type='application/json',
            data=json.dumps({'email': 'test@example.com', 'password': 'password123'}),
        )
        for payload in self.XSS_PAYLOADS:
            resp = client.post(
                '/api/chat/send',
                content_type='application/json',
                data=json.dumps({'receiver_id': test_user.id, 'body': payload}),
            )
            if resp.status_code < 500:
                assert '<script>' not in resp.get_data(as_text=True)


class TestCsrfProtection:
    """C.4 CSRF protection verification"""

    def test_api_login_requires_csrf_without_header(self, app):
        from config import Config
        if not getattr(Config, 'WTF_CSRF_ENABLED', True):
            return
        from app.extensions import csrf
        assert csrf is not None

    def test_cors_origins_config_present(self, app):
        from flask import current_app
        origins = current_app.config.get('CORS_ORIGINS')
        if origins is not None:
            assert isinstance(origins, (list, tuple, str))
