class TestTherapistRoutes:
    def test_dashboard_requires_login(self, client):
        response = client.get('/therapist/dashboard', follow_redirects=True)
        assert response.status_code == 200
        assert b'login' in response.data.lower()

    def test_patients_requires_login(self, client):
        response = client.get('/therapist/patients', follow_redirects=True)
        assert response.status_code == 200
        assert b'login' in response.data.lower()

    def test_sessions_requires_login(self, client):
        response = client.get('/therapist/sessions', follow_redirects=True)
        assert response.status_code == 200
        assert b'login' in response.data.lower()

    def test_calendar_requires_login(self, client):
        response = client.get('/therapist/calendar', follow_redirects=True)
        assert response.status_code == 200
        assert b'login' in response.data.lower()

    def test_messages_requires_login(self, client):
        response = client.get('/therapist/messages', follow_redirects=True)
        assert response.status_code == 200
        assert b'login' in response.data.lower()

    def test_profile_requires_login(self, client):
        response = client.get('/therapist/profile', follow_redirects=True)
        assert response.status_code == 200
        assert b'login' in response.data.lower()

    def test_analytics_requires_login(self, client):
        response = client.get('/therapist/analytics', follow_redirects=True)
        assert response.status_code == 200
        assert b'login' in response.data.lower()

    def test_reports_requires_login(self, client):
        response = client.get('/therapist/reports', follow_redirects=True)
        assert response.status_code == 200
        assert b'login' in response.data.lower()

    def test_games_requires_login(self, client):
        response = client.get('/therapist/games', follow_redirects=True)
        assert response.status_code == 200
        assert b'login' in response.data.lower()

    def test_efficiency_requires_login(self, client):
        response = client.get('/therapist/efficiency', follow_redirects=True)
        assert response.status_code == 200
        assert b'login' in response.data.lower()


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
