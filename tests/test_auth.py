from flask import url_for


def _login(client, email, password):
    return client.post(url_for('auth.api_login'), json={'email': email, 'password': password})


def test_login_page_redirects_to_spa(client):
    """El formulario Jinja se quitó: /login lleva a la pantalla de Angular."""
    response = client.get(url_for('auth.login'))
    assert response.status_code == 302
    assert response.headers['Location'].endswith('/app/login')


def test_login_success(client, test_user):
    response = _login(client, 'test@example.com', 'password123')
    assert response.status_code == 200
    body = response.get_json()
    assert body['success'] is True
    assert body['access_token']
    assert body['user']['email'] == 'test@example.com'


def test_login_failed(client):
    response = _login(client, 'wrong@example.com', 'wrongpassword')
    assert response.status_code in (400, 401)
    assert response.get_json()['success'] is False


def test_logout(client, test_user):
    _login(client, 'test@example.com', 'password123')
    response = client.post(url_for('auth.api_logout'))
    assert response.status_code == 200
    assert response.get_json()['success'] is True


def test_protected_route_requires_login(client):
    response = client.get(url_for('main.dashboard'))
    assert response.status_code == 302
    assert '/app/' in response.headers['Location']
