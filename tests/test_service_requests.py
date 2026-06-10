import json
import pytest


class TestServiceRequestApi:
    """ServiceRequest CRUD API tests"""

    def _login_as(self, client, email, password):
        resp = client.post(
            '/api/login',
            content_type='application/json',
            data=json.dumps({'email': email, 'password': password}),
        )
        assert resp.status_code == 200

    def test_create_request_as_user(self, client, test_user, session):
        self._login_as(client, 'test@example.com', 'password123')
        resp = client.post(
            '/api/service-requests',
            content_type='application/json',
            data=json.dumps({
                'category': 'technical',
                'title': 'Need new laptop',
                'description': 'Current laptop is slow',
                'priority': 'high',
            }),
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data['success'] is True
        assert data['data']['category'] == 'technical'
        assert data['data']['title'] == 'Need new laptop'
        assert data['data']['status'] == 'pending'

    def test_create_request_missing_required_field(self, client, test_user):
        self._login_as(client, 'test@example.com', 'password123')
        resp = client.post(
            '/api/service-requests',
            content_type='application/json',
            data=json.dumps({'category': 'technical'}),
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert data['success'] is False

    def test_create_request_unauthorized(self, client):
        resp = client.post(
            '/api/service-requests',
            content_type='application/json',
            data=json.dumps({'category': 'test', 'title': 'test'}),
        )
        assert resp.status_code == 401

    def test_list_own_requests(self, client, test_user, session):
        self._login_as(client, 'test@example.com', 'password123')
        client.post(
            '/api/service-requests',
            content_type='application/json',
            data=json.dumps({'category': 'admin', 'title': 'Request A'}),
        )
        client.post(
            '/api/service-requests',
            content_type='application/json',
            data=json.dumps({'category': 'admin', 'title': 'Request B'}),
        )
        resp = client.get('/api/service-requests')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert len(data['data']) >= 2

    def test_get_single_request(self, client, test_user, session):
        self._login_as(client, 'test@example.com', 'password123')
        create_resp = client.post(
            '/api/service-requests',
            content_type='application/json',
            data=json.dumps({'category': 'billing', 'title': 'Invoice question'}),
        )
        req_id = create_resp.get_json()['data']['id']
        resp = client.get(f'/api/service-requests/{req_id}')
        assert resp.status_code == 200
        assert resp.get_json()['data']['title'] == 'Invoice question'

    def test_get_request_not_found(self, client, test_user):
        self._login_as(client, 'test@example.com', 'password123')
        resp = client.get('/api/service-requests/99999')
        assert resp.status_code == 404

    def test_approve_request_as_admin(self, client, test_user, session):
        self._login_as(client, 'test@example.com', 'password123')
        create_resp = client.post(
            '/api/service-requests',
            content_type='application/json',
            data=json.dumps({'category': 'it', 'title': 'Approve me'}),
        )
        req_id = create_resp.get_json()['data']['id']
        resp = client.post(
            f'/api/service-requests/{req_id}/approve',
            content_type='application/json',
            data=json.dumps({'notes': 'Approved by admin'}),
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['data']['status'] == 'approved'

    def test_reject_request_as_admin(self, client, test_user, session):
        self._login_as(client, 'test@example.com', 'password123')
        create_resp = client.post(
            '/api/service-requests',
            content_type='application/json',
            data=json.dumps({'category': 'it', 'title': 'Reject me'}),
        )
        req_id = create_resp.get_json()['data']['id']
        resp = client.post(
            f'/api/service-requests/{req_id}/reject',
            content_type='application/json',
            data=json.dumps({'notes': 'Not needed'}),
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['data']['status'] == 'rejected'

    def test_non_admin_cannot_approve(self, client, test_user, session):
        test_user.role = 'therapist'
        session.commit()
        self._login_as(client, 'test@example.com', 'password123')
        create_resp = client.post(
            '/api/service-requests',
            content_type='application/json',
            data=json.dumps({'category': 'it', 'title': 'Cannot approve'}),
        )
        req_id = create_resp.get_json()['data']['id']
        resp = client.post(f'/api/service-requests/{req_id}/approve')
        assert resp.status_code == 403

    def test_forbidden_access_other_user_request(self, client, test_user, session, db):
        test_user.role = 'therapist'
        session.commit()
        self._login_as(client, 'test@example.com', 'password123')
        create_resp = client.post(
            '/api/service-requests',
            content_type='application/json',
            data=json.dumps({'category': 'hr', 'title': 'Private'}),
        )
        req_id = create_resp.get_json()['data']['id']

        from app.models import User
        from app.extensions import bcrypt
        other = User(
            email='other@example.com',
            password=bcrypt.generate_password_hash('otherpass').decode('utf-8'),
            role='therapist',
            username='other',
        )
        db.session.add(other)
        db.session.commit()

        resp = client.post(
            '/api/login',
            content_type='application/json',
            data=json.dumps({'email': 'other@example.com', 'password': 'otherpass'}),
        )
        assert resp.status_code == 200
        resp = client.get(f'/api/service-requests/{req_id}')
        assert resp.status_code == 403


class TestHealthEndpoint:
    """Health endpoint tests"""

    def test_health_returns_200(self, client):
        resp = client.get('/api/health')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['status'] in ('healthy', 'degraded')
        assert 'database' in data['checks']
        assert 'version' in data
        assert data['version'] == '2.0-remediation'

    def test_health_contains_checks(self, client):
        resp = client.get('/api/health')
        data = resp.get_json()
        assert 'groq' in data['checks']
        assert 'gemini' in data['checks']
        assert 'ollama' in data['checks']
        assert 'alerts' in data['checks']

    def test_health_db_check(self, client):
        resp = client.get('/api/health')
        data = resp.get_json()
        assert data['checks']['database']['status'] == 'ok'

    def test_health_timestamp_format(self, client):
        resp = client.get('/api/health')
        data = resp.get_json()
        assert 'timestamp' in data
        assert 'T' in data['timestamp'] or ' ' in data['timestamp']
