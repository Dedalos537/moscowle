"""
Gherkin-style BDD tests for Login.

Feature: Inicio de sesión
  Como usuario registrado
  Quiero iniciar sesión en el sistema
  Para acceder a mis sesiones y reportes

  Scenario: Login exitoso con credenciales válidas
    Given un usuario registrado con email "test@example.com" y password "password123"
    When envía credenciales correctas a /api/login
    Then recibe status 200 y token CSRF
    And el usuario está autenticado

  Scenario: Login fallido por credenciales incorrectas
    Given un usuario registrado con email "test@example.com" y password "password123"
    When envía credenciales incorrectas a /api/login
    Then recibe status 401

  Scenario: Login fallido por campos vacíos
    Given un formulario de login vacío
    When envía email y password vacíos a /api/login
    Then recibe status 400
"""
import json


class TestBddLoginSuccess:
    """Scenario: Login exitoso con credenciales válidas"""

    def test_given_user_exists(self, test_user):
        assert test_user is not None
        assert test_user.email == 'test@example.com'

    def test_when_send_valid_credentials(self, client, test_user):
        self.response = client.post(
            '/api/login',
            content_type='application/json',
            data=json.dumps({'email': 'test@example.com', 'password': 'password123'}),
        )

    def test_then_receive_200_and_csrf(self, client, test_user):
        resp = client.post(
            '/api/login',
            content_type='application/json',
            data=json.dumps({'email': 'test@example.com', 'password': 'password123'}),
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert 'csrf_token' in data

    def test_and_user_is_authenticated(self, client, test_user):
        client.post(
            '/api/login',
            content_type='application/json',
            data=json.dumps({'email': 'test@example.com', 'password': 'password123'}),
        )
        resp = client.get('/api/auth/me')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['email'] == 'test@example.com'


class TestBddLoginFailure:
    """Scenario: Login fallido por credenciales incorrectas"""

    def test_given_user_exists(self, test_user):
        assert test_user.email == 'test@example.com'

    def test_when_send_wrong_credentials(self, client):
        resp = client.post(
            '/api/login',
            content_type='application/json',
            data=json.dumps({'email': 'test@example.com', 'password': 'wrongpassword'}),
        )
        assert resp.status_code == 401
        data = resp.get_json()
        assert data['success'] is False


class TestBddLoginEmptyFields:
    """Scenario: Login fallido por campos vacíos"""

    def test_when_send_empty_fields(self, client):
        resp = client.post(
            '/api/login',
            content_type='application/json',
            data=json.dumps({'email': '', 'password': ''}),
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert data['success'] is False
