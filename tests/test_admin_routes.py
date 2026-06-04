class TestAdminRoutes:
    def test_admin_dashboard_requires_login(self, client):
        response = client.get('/admin/dashboard', follow_redirects=True)
        assert response.status_code == 200
        assert b'login' in response.data.lower()

    def test_admin_users_requires_login(self, client):
        response = client.get('/admin/users', follow_redirects=True)
        assert response.status_code == 200
        assert b'login' in response.data.lower()

    def test_admin_reports_requires_login(self, client):
        response = client.get('/admin/reports', follow_redirects=True)
        assert response.status_code == 200
        assert b'login' in response.data.lower()

    def test_admin_sessions_requires_login(self, client):
        response = client.get('/admin/sessions', follow_redirects=True)
        assert response.status_code == 200
        assert b'login' in response.data.lower()

    def test_admin_games_requires_login(self, client):
        response = client.get('/admin/games', follow_redirects=True)
        assert response.status_code == 200
        assert b'login' in response.data.lower()

    def test_admin_csp_reports_requires_login(self, client):
        response = client.get('/admin/csp-reports', follow_redirects=True)
        assert response.status_code == 200
        assert b'login' in response.data.lower()

    def test_admin_payments_requires_login(self, client):
        response = client.get('/admin/payments', follow_redirects=True)
        assert response.status_code == 200
        assert b'login' in response.data.lower()

    def test_admin_expenses_requires_login(self, client):
        response = client.get('/admin/expenses', follow_redirects=True)
        assert response.status_code == 200
        assert b'login' in response.data.lower()

    def test_admin_messages_requires_login(self, client):
        response = client.get('/admin/messages', follow_redirects=True)
        assert response.status_code == 200
        assert b'login' in response.data.lower()

    def test_admin_sedes_requires_login(self, client):
        response = client.get('/admin/sedes', follow_redirects=True)
        assert response.status_code == 200
        assert b'login' in response.data.lower()

    def test_admin_profile_requires_login(self, client):
        response = client.get('/admin/profile', follow_redirects=True)
        assert response.status_code == 200
        assert b'login' in response.data.lower()
