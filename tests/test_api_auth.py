import json


class TestApiLogin:
    def test_api_login_success(self, client, test_user):
        response = client.post(
            '/api/login',
            content_type='application/json',
            data=json.dumps({'email': 'test@example.com', 'password': 'password123'}),
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'csrf_token' in data
        assert data['user']['email'] == 'test@example.com'
        assert data['user']['role'] == 'admin'

    def test_api_login_missing_credentials(self, client):
        response = client.post(
            '/api/login', content_type='application/json', data=json.dumps({'email': '', 'password': ''})
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False

    def test_api_login_wrong_password(self, client):
        response = client.post(
            '/api/login',
            content_type='application/json',
            data=json.dumps({'email': 'test@example.com', 'password': 'wrongpassword'}),
        )
        assert response.status_code == 401
        data = response.get_json()
        assert data['success'] is False

    def test_api_login_no_json(self, client):
        response = client.post('/api/login', data='not json', content_type='text/plain')
        assert response.status_code == 400


class TestApiLogout:
    def test_api_logout_without_login(self, client):
        response = client.post('/api/logout', content_type='application/json')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_api_logout_after_login(self, client, test_user):
        client.post(
            '/api/login',
            content_type='application/json',
            data=json.dumps({'email': 'test@example.com', 'password': 'password123'}),
        )
        response = client.post('/api/logout', content_type='application/json')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True


class TestApiAuthMe:
    def test_auth_me_unauthenticated(self, client):
        response = client.get('/api/auth/me')
        assert response.status_code == 401

    def test_auth_me_authenticated(self, client, test_user):
        client.post(
            '/api/login',
            content_type='application/json',
            data=json.dumps({'email': 'test@example.com', 'password': 'password123'}),
        )
        response = client.get('/api/auth/me')
        assert response.status_code == 200
        data = response.get_json()
        assert data['id'] == test_user.id
        assert data['email'] == 'test@example.com'
        assert data['username'] == 'testuser'
        assert data['role'] == 'admin'


class TestApiAuthValidate:
    def test_validate_valid_credentials(self, client, test_user):
        response = client.post(
            '/api/auth/validate',
            content_type='application/json',
            data=json.dumps({'email': 'test@example.com', 'password': 'password123'}),
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['valid'] is True

    def test_validate_invalid_credentials(self, client):
        response = client.post(
            '/api/auth/validate',
            content_type='application/json',
            data=json.dumps({'email': 'wrong@example.com', 'password': 'wrong'}),
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['valid'] is False

    def test_validate_missing_fields(self, client):
        response = client.post('/api/auth/validate', content_type='application/json', data=json.dumps({}))
        assert response.status_code == 200
        data = response.get_json()
        assert data['valid'] is False
