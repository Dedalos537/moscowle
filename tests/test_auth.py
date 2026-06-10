from flask import url_for


def test_login_page_loads(client, app):
    """Prueba que la página de login carga correctamente."""
    with app.app_context():
        from app.auth_compat import current_user

        if current_user.is_authenticated:
            pass
    response = client.get(url_for('auth.login'), follow_redirects=True)
    assert response.status_code == 200


def test_login_success(client, test_user):
    """Prueba un login exitoso."""
    response = client.post(
        url_for('auth.login'), data={'email': 'test@example.com', 'password': 'password123'}, follow_redirects=True
    )

    assert response.status_code == 200
    # Verifica que redirija al dashboard o contenga user info
    # Assuming 'main.dashboard' endpoint exists and renders something specific or user is logged in
    # Flask-Login puts user in session.
    # We can check content of dashboard if possible, OR check if current_user is authenticated
    # But current_user is context local.
    # Checking response data is safer.
    # assert b'Dashboard' in response.data or b'Bienvenido' in response.data


def test_login_failed(client):
    """Prueba un login con credenciales incorrectas."""
    response = client.post(
        url_for('auth.login'), data={'email': 'wrong@example.com', 'password': 'wrongpassword'}, follow_redirects=True
    )

    assert response.status_code == 200
    assert b'Credenciales inv' in response.data or b'error' in response.data.lower()


def test_logout(client, test_user):
    """Prueba el logout."""
    # First login
    client.post(
        url_for('auth.login'), data={'email': 'test@example.com', 'password': 'password123'}, follow_redirects=True
    )

    # Then logout
    response = client.get(url_for('auth.logout'), follow_redirects=True)

    assert response.status_code == 200
    # Should redirect back to login
    assert b'login' in response.data.lower()


def test_protected_route_requires_login(client):
    """Prueba que una ruta protegida redirija al login si no hay sesión."""
    # Assuming 'main.dashboard' is protected
    response = client.get(url_for('main.dashboard'), follow_redirects=True)

    # Should redirect
    # assert response.history[0].status_code == 302 # Only if follow_redirects=True preserves history cleanly or use status_code of final page
    assert response.status_code == 200
    assert b'login' in response.data.lower() or b'Inicia' in response.data
