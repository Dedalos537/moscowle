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

from app.models import Sede, User
from app.models.user import patient_therapist, therapist_sede
from app.routes.api.admin import _serialize_user
from app.services.admin_service import AdminService


class TestListUsersPrefetch:
    def test_list_users_prefetches_m2m(self, session, db):
        sede = Sede(name='Sede Test')
        session.add(sede)
        session.flush()

        paciente = User(username='paciente', email='paciente@test.local', role='jugador', password='x')
        terapeuta = User(username='terapeuta', email='terapeuta@test.local', role='terapista', password='x')
        session.add(paciente)
        session.add(terapeuta)
        session.flush()

        session.execute(patient_therapist.insert().values(patient_id=paciente.id, therapist_id=terapeuta.id))
        session.execute(therapist_sede.insert().values(therapist_id=terapeuta.id, sede_id=sede.id))
        session.commit()

        users = AdminService().list_users()
        by_username = {u.username: u for u in users}
        assert 'paciente' in by_username
        assert 'terapeuta' in by_username

        serialized = {s['username']: s for s in [_serialize_user(u) for u in users]}
        assert serialized['paciente']['therapist_ids'] == [terapeuta.id]
        assert serialized['terapeuta']['assigned_sedes'] == [{'id': sede.id, 'name': 'Sede Test'}]
        assert serialized['terapeuta']['therapist_ids'] == []
        assert serialized['paciente']['sede_name'] is None
