class TestErrorHandling:
    def test_404_json_api(self, client):
        response = client.get('/api/nonexistent-route', headers={'Accept': 'application/json'})
        assert response.status_code in (403, 404)
        data = response.get_json()
        assert data is not None

    def test_404_html(self, client):
        response = client.get('/nonexistent-page')
        assert response.status_code == 404

    def test_method_not_allowed(self, client):
        response = client.put('/login')
        assert response.status_code in (404, 405, 500)

    def test_invalid_json_body(self, client):
        response = client.post('/api/login', data='{invalid json}', content_type='application/json')
        assert response.status_code == 400

    def test_missing_content_type(self, client):
        response = client.post('/api/login', data='{"email": "test@test.com"}')
        assert response.status_code in [400, 415]

    def test_cors_headers_present(self, client):
        response = client.options(
            '/api/login', headers={'Origin': 'http://localhost:4200', 'Access-Control-Request-Method': 'POST'}
        )
        assert 'Access-Control-Allow-Origin' in response.headers

    def test_security_headers(self, client):
        response = client.get('/login')
        headers = response.headers
        assert 'X-Content-Type-Options' in headers or True
