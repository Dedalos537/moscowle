import pytest

LEGACY_PAGES = ['dashboard', 'patients', 'sessions', 'calendar', 'messages', 'profile', 'analytics', 'reports', 'games']


class TestTherapistRoutes:
    """Las páginas Jinja se quitaron: el frontend es la SPA en /app/therapist/..."""

    @pytest.mark.parametrize('page', LEGACY_PAGES)
    def test_legacy_html_page_is_gone(self, client, page):
        response = client.get(f'/therapist/{page}')
        assert response.status_code == 404
        assert response.is_json

    def test_efficiency_requires_login(self, client):
        response = client.get('/therapist/efficiency')
        assert response.status_code in (302, 401)
        if response.status_code == 302:
            assert response.headers['Location'].endswith('/app/login')


class TestTherapistApiEndpoints:
    def test_api_endpoints_return_auth_error_when_unauthenticated(self, client):
        endpoints = [
            '/therapist/api/dashboard-stats',
            '/therapist/api/conversations',
            '/therapist/api/profile',
            '/therapist/api/analytics',
            '/therapist/api/reports/overview',
            '/therapist/api/reports/detailed',
            '/therapist/api/patient-stats',
        ]
        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code in (401, 403), f'{endpoint} returned {response.status_code}'
