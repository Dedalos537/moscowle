from flask import url_for

def test_homepage_redirect(client):
    """Prueba que el root '/' redirija o cargue."""
    response = client.get('/')
    assert response.status_code in [200, 302]

def test_404_page(client):
    """Prueba que una ruta inexistente devuelva 404."""
    response = client.get('/ruta-que-no-existe-12345')
    assert response.status_code == 404
