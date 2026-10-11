"""API de la landing pública: contenido editable versionado y solicitudes de evaluación."""

import copy
import uuid

import pytest
from flask_jwt_extended import create_access_token

from app.extensions import db
from app.models import User
from app.models.landing import LandingContentVersion, LandingLead
from app.models.notification_group import NotificationItem
from app.services import landing_content


def _user(role):
    tag = uuid.uuid4().hex[:8]
    u = User(username=f'{role[:3]}{tag}', email=f'{tag}@landing.test', password='x', role=role)
    db.session.add(u)
    db.session.commit()
    return u


def _h(u):
    return {'Authorization': 'Bearer ' + create_access_token(identity=str(u.id))}


@pytest.fixture(autouse=True)
def _clean(app):
    with app.app_context():
        LandingLead.query.delete()
        LandingContentVersion.query.delete()
        db.session.commit()
    yield
    with app.app_context():
        LandingLead.query.delete()
        LandingContentVersion.query.delete()
        db.session.commit()


def test_public_content_falls_back_to_the_previous_site_text(client):
    r = client.get('/api/landing/content')
    assert r.status_code == 200
    body = r.get_json()
    assert body['version'] == 0
    assert body['content']['contact']['whatsapp'] == '51987277835'
    assert len(body['content']['services']) == 18
    assert 'max-age' in r.headers['Cache-Control']


def test_public_content_allows_the_landing_origin(client):
    for origin in ('https://centrojuanpabloii.com', 'https://www.centrojuanpabloii.com'):
        r = client.get('/api/landing/content', headers={'Origin': origin})
        assert r.headers['Access-Control-Allow-Origin'] == origin


def test_default_content_passes_its_own_validation():
    assert landing_content.validate(landing_content.default_content())


@pytest.mark.parametrize(
    ('path', 'value', 'message'),
    [
        (('hero', 'title'), '', 'hero.title: es obligatorio'),
        (('hero', 'title'), 'x' * 91, 'máximo 90'),
        (('contact', 'whatsapp'), '123', 'WhatsApp'),
        (('contact', 'email'), 'no-es-correo', 'correo no válido'),
        (('contact', 'maps_url'), 'javascript:alert(1)', 'https://'),
    ],
)
def test_validation_names_the_field(path, value, message):
    content = landing_content.default_content()
    content[path[0]][path[1]] = value
    with pytest.raises(landing_content.ContentError, match=message):
        landing_content.validate(content)


def test_whatsapp_number_is_normalized_and_unknown_keys_dropped():
    content = landing_content.default_content()
    content['contact']['whatsapp'] = '+51 921-507-470'
    content['evil'] = '<script>'
    clean = landing_content.validate(content)
    assert clean['contact']['whatsapp'] == '51921507470'
    assert 'evil' not in clean


def test_admin_publishes_versions_and_can_restore(client, app):
    admin = _user('admin')
    r = client.get('/api/landing/admin/content', headers=_h(admin))
    assert r.status_code == 200
    content = r.get_json()['content']

    edited = copy.deepcopy(content)
    edited['hero']['title'] = 'Nuevo título'
    r = client.put(
        '/api/landing/admin/content', json={'content': edited, 'note': 'Hero', 'base_version': 0}, headers=_h(admin)
    )
    assert r.status_code == 200, r.get_json()
    first = r.get_json()['version']
    assert client.get('/api/landing/content').get_json()['content']['hero']['title'] == 'Nuevo título'

    edited['hero']['title'] = 'Otro título'
    second = client.put(
        '/api/landing/admin/content', json={'content': edited, 'base_version': first}, headers=_h(admin)
    ).get_json()['version']

    # Publicar sobre una versión vieja avisa del conflicto en vez de pisar lo de otra persona.
    stale = client.put('/api/landing/admin/content', json={'content': edited, 'base_version': first}, headers=_h(admin))
    assert stale.status_code == 409

    r = client.post(f'/api/landing/admin/content/restore/{first}', headers=_h(admin))
    assert r.status_code == 200
    assert r.get_json()['version'] > second
    assert client.get('/api/landing/content').get_json()['content']['hero']['title'] == 'Nuevo título'


def test_invalid_publish_is_rejected_with_the_field(client):
    admin = _user('admin')
    content = landing_content.default_content()
    content['services'] = []
    r = client.put('/api/landing/admin/content', json={'content': content}, headers=_h(admin))
    assert r.status_code == 400
    assert 'services' in r.get_json()['error']


@pytest.mark.parametrize('role', ['terapista', 'paciente', 'supervisor'])
def test_only_admin_can_publish(client, role):
    u = _user(role)
    r = client.put('/api/landing/admin/content', json={'content': {}}, headers=_h(u))
    assert r.status_code == 403


def test_admin_endpoints_need_a_session(client):
    assert client.get('/api/landing/admin/content').status_code in (401, 403)
    assert client.get('/api/landing/admin/leads').status_code in (401, 403)


def test_form_lead_requires_name_and_phone(client):
    r = client.post('/api/landing/leads', json={'channel': 'form', 'name': 'Ana'})
    assert r.status_code == 400
    assert r.get_json()['field'] == 'phone'


def test_form_lead_is_stored_and_notifies_staff(client):
    admin = _user('admin')
    r = client.post(
        '/api/landing/leads',
        json={
            'channel': 'form',
            'name': 'Ana Ruiz',
            'phone': '987 654 321',
            'service': 'De Lenguaje',
            'patient_age': '5 años',
            'preferred_time': 'manana',
            'message': 'Mi hijo casi no habla',
        },
    )
    assert r.status_code == 201
    lead = db.session.get(LandingLead, r.get_json()['id'])
    assert (lead.name, lead.channel, lead.status, lead.preferred_time) == ('Ana Ruiz', 'form', 'new', 'manana')
    links = [n.link for n in NotificationItem.query.filter_by(user_id=admin.id).all()]
    assert f'/admin/settings?section=website&lead={lead.id}' in links


def test_whatsapp_tap_is_recorded_once(client):
    payload = {'channel': 'whatsapp', 'name': 'Luis', 'phone': '912345678', 'service': 'TDAH'}
    first = client.post('/api/landing/leads', json=payload).get_json()['id']
    again = client.post('/api/landing/leads', json={**payload, 'message': 'Hola'}).get_json()['id']
    assert first == again
    assert LandingLead.query.count() == 1
    assert db.session.get(LandingLead, first).message == 'Hola'


def test_honeypot_is_silently_dropped(client):
    r = client.post('/api/landing/leads', json={'channel': 'form', 'name': 'Bot', 'phone': '999999999', 'website': 'x'})
    assert r.status_code == 201
    assert LandingLead.query.count() == 0


def test_admin_works_the_inbox(client):
    admin = _user('admin')
    lead_id = client.post('/api/landing/leads', json={'channel': 'call', 'name': 'Rosa'}).get_json()['id']

    open_leads = client.get('/api/landing/admin/leads?status=open', headers=_h(admin)).get_json()
    assert [x['id'] for x in open_leads['leads']] == [lead_id]

    r = client.patch(
        f'/api/landing/admin/leads/{lead_id}',
        json={'status': 'scheduled', 'staff_note': 'Martes 10 a. m.'},
        headers=_h(admin),
    )
    assert r.get_json()['lead']['status'] == 'scheduled'
    assert r.get_json()['lead']['handled_by'] == admin.username
    assert client.get('/api/landing/admin/leads?status=open', headers=_h(admin)).get_json()['total'] == 0

    stats = client.get('/api/landing/admin/stats', headers=_h(admin)).get_json()
    assert stats['last_30_days']['call'] == 1
    assert stats['by_status']['scheduled'] == 1


def test_inbox_can_hide_anonymous_taps(client):
    admin = _user('admin')
    client.post('/api/landing/leads', json={'channel': 'whatsapp'})
    named = client.post('/api/landing/leads', json={'channel': 'call', 'name': 'Rosa'}).get_json()['id']
    rows = client.get('/api/landing/admin/leads?contact=1', headers=_h(admin)).get_json()['leads']
    assert [r['id'] for r in rows] == [named]
    stats = client.get('/api/landing/admin/stats', headers=_h(admin)).get_json()
    assert stats['last_30_days']['whatsapp'] == 1
