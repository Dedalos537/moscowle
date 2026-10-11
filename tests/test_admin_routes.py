import pytest

from app.models import Sede, User
from app.models.user import patient_therapist, therapist_sede
from app.routes.api.admin import _serialize_user
from app.services.admin_service import AdminService

LEGACY_PAGES = [
    'dashboard',
    'users',
    'reports',
    'sessions',
    'games',
    'csp-reports',
    'payments',
    'expenses',
    'messages',
    'sedes',
    'profile',
]


class TestAdminRoutes:
    """Las páginas Jinja se quitaron: el frontend es la SPA en /app/admin/..."""

    @pytest.mark.parametrize('page', LEGACY_PAGES)
    def test_legacy_html_page_is_gone(self, client, page):
        response = client.get(f'/admin/{page}')
        assert response.status_code == 404
        assert response.is_json


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
