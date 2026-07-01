import json

from app.extensions import bcrypt
from app.models.user import User


class TestIncidentsAPI:
    def _create_admin(self, session):
        existing = User.query.filter_by(email='incadmin@test.com').first()
        if existing:
            return existing
        user = User(
            username='incadmin',
            email='incadmin@test.com',
            role='admin',
            password=bcrypt.generate_password_hash('test123').decode('utf-8'),
        )
        session.add(user)
        session.commit()
        return user

    def _login(self, client, user):
        client.post(
            '/api/login',
            json={'email': user.email, 'password': 'test123'},
            content_type='application/json',
        )

    def test_list_incidents_empty(self, client, session):
        self._create_admin(session)
        user = User.query.filter_by(email='incadmin@test.com').first()
        self._login(client, user)

        resp = client.get('/api/incidents')
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert 'incidentes' in data
        assert data['total'] >= 0

    def test_create_incident(self, client, session):
        self._create_admin(session)
        user = User.query.filter_by(email='incadmin@test.com').first()
        self._login(client, user)

        resp = client.post(
            '/api/incidents',
            json={
                'titulo': 'Incidente de prueba API',
                'descripcion': 'Descripción detallada del incidente de prueba',
                'categoria': 'SOFTWARE',
                'prioridad': 2,
                'evidencia_tipo': 'MANUAL',
            },
            content_type='application/json',
        )
        assert resp.status_code == 201
        data = json.loads(resp.data)
        assert data['titulo'] == 'Incidente de prueba API'
        assert data['categoria'] == 'SOFTWARE'
        assert data['prioridad'] == 2
        assert data['estado'] == 'NUEVO'

    def test_create_incident_validation(self, client, session):
        self._create_admin(session)
        user = User.query.filter_by(email='incadmin@test.com').first()
        self._login(client, user)

        resp = client.post(
            '/api/incidents',
            json={'titulo': 'X'},
            content_type='application/json',
        )
        assert resp.status_code == 400

    def test_get_incident_detail(self, client, session):
        self._create_admin(session)
        user = User.query.filter_by(email='incadmin@test.com').first()
        self._login(client, user)

        # Create first
        create_resp = client.post(
            '/api/incidents',
            json={
                'titulo': 'Detail test incident',
                'descripcion': 'Testing detail endpoint',
                'categoria': 'HARDWARE',
            },
            content_type='application/json',
        )
        inc_id = json.loads(create_resp.data)['id']

        resp = client.get(f'/api/incidents/{inc_id}')
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['titulo'] == 'Detail test incident'
        assert 'historial' in data
        assert 'comentarios' in data

    def test_get_incident_not_found(self, client, session):
        self._create_admin(session)
        user = User.query.filter_by(email='incadmin@test.com').first()
        self._login(client, user)

        resp = client.get('/api/incidents/99999')
        assert resp.status_code == 404

    def test_update_status(self, client, session):
        self._create_admin(session)
        user = User.query.filter_by(email='incadmin@test.com').first()
        self._login(client, user)

        create_resp = client.post(
            '/api/incidents',
            json={
                'titulo': 'Status test',
                'descripcion': 'Testing status update',
                'categoria': 'SOFTWARE',
            },
            content_type='application/json',
        )
        inc_id = json.loads(create_resp.data)['id']

        resp = client.put(
            f'/api/incidents/{inc_id}/status',
            json={'estado': 'EN_CURSO'},
            content_type='application/json',
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['estado'] == 'EN_CURSO'

    def test_invalid_status_transition(self, client, session):
        self._create_admin(session)
        user = User.query.filter_by(email='incadmin@test.com').first()
        self._login(client, user)

        create_resp = client.post(
            '/api/incidents',
            json={
                'titulo': 'Invalid transition',
                'descripcion': 'Testing invalid transition',
                'categoria': 'SOFTWARE',
            },
            content_type='application/json',
        )
        inc_id = json.loads(create_resp.data)['id']

        resp = client.put(
            f'/api/incidents/{inc_id}/status',
            json={'estado': 'CERRADO'},
            content_type='application/json',
        )
        assert resp.status_code == 400

    def test_add_comment(self, client, session):
        self._create_admin(session)
        user = User.query.filter_by(email='incadmin@test.com').first()
        self._login(client, user)

        create_resp = client.post(
            '/api/incidents',
            json={
                'titulo': 'Comment test',
                'descripcion': 'Testing comments',
                'categoria': 'SOFTWARE',
            },
            content_type='application/json',
        )
        inc_id = json.loads(create_resp.data)['id']

        resp = client.post(
            f'/api/incidents/{inc_id}/comments',
            json={'contenido': 'Test comment body'},
            content_type='application/json',
        )
        assert resp.status_code == 201
        data = json.loads(resp.data)
        assert data['contenido'] == 'Test comment body'

    def test_dashboard(self, client, session):
        self._create_admin(session)
        user = User.query.filter_by(email='incadmin@test.com').first()
        self._login(client, user)

        resp = client.get('/api/incidents/dashboard')
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert 'total_abiertos' in data
        assert 'vencidos' in data
        assert 'sla_compliance_7d' in data
        assert 'por_categoria' in data
