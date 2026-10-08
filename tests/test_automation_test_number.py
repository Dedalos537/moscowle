"""«Enviar prueba» de cobranza: va al número de pruebas con las plantillas guardadas."""

import uuid
from unittest.mock import patch

from flask_jwt_extended import create_access_token

from app.extensions import db
from app.models import User
from app.services import channel_settings


def _admin_headers():
    tag = uuid.uuid4().hex[:8]
    u = User(username=f'adm{tag}', email=f'{tag}@atn.test', password='x', role='admin')
    db.session.add(u)
    db.session.commit()
    return {'Authorization': 'Bearer ' + create_access_token(identity=str(u.id))}


def test_requires_a_test_number(client, app):
    with patch.object(channel_settings, 'get', return_value=''):
        r = client.post('/api/automation/test-number', headers=_admin_headers())
    assert r.status_code == 400


def test_sends_templates_by_whatsapp_and_sms(client, app):
    sent = {}
    values = {
        'destination': '+51937541253',
        'sms_template': 'Hola {patient_name} {amount:.2f}',
        'whatsapp_template': '',
    }
    with (
        patch.object(channel_settings, 'get', side_effect=lambda f, d='': values.get(f, d)),
        patch(
            'app.services.whatsapp_service.whatsapp_service.send_message',
            side_effect=lambda p, t: sent.setdefault('wa', (p, t)),
        ),
        patch(
            'app.services.sms_whatsapp_service.SMSWhatsAppService.send_sms_message',
            side_effect=lambda p, t: sent.setdefault('sms', (p, t)) and {'ok': True},
        ),
    ):
        r = client.post('/api/automation/test-number', headers=_admin_headers())
    assert r.status_code == 200, r.get_json()
    assert r.get_json()['results']['whatsapp']['ok'] and r.get_json()['results']['sms']['ok']
    assert sent['sms'][0] == '+51937541253' and 'Hola Mateo Rojas 120.00' in sent['sms'][1]
    assert sent['wa'][1].startswith('[PRUEBA]')
