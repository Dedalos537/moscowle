"""Pruebas de configuracion del bot: identidad, secreto del webhook y su fuente.

Hallazgos que corrigen:
- "¿quien eres?" respondia con el literal 'Soy Diego' aunque el panel permite
  cambiar el nombre en BotConfig.
- El dashboard devolvia el secreto del webhook en claro.
- El setup escribia el secreto en os.environ mientras la validacion leia
  current_app.config, dejando al proceso validando con el valor anterior.
"""

import json

import pytest
from flask_jwt_extended import create_access_token

from app.extensions import db
from app.models import User
from app.models.bot_config import BotConfig


def _admin_headers(user_id):
    return {'Authorization': 'Bearer ' + create_access_token(identity=str(user_id))}


@pytest.fixture
def admin(session):
    user = User.query.filter_by(email='tg_cfg_admin@example.com').first()
    if user is None:
        user = User(
            username='tg_cfg_admin',
            email='tg_cfg_admin@example.com',
            password='x',
            role='admin',
        )
        db.session.add(user)
        db.session.commit()
    user.role = 'admin'
    db.session.commit()
    return user


class TestIdentidadConfigurable:
    def test_usa_el_nombre_de_botconfig(self, app, monkeypatch):
        import app.services.telegram_bot_service as tbs

        cfg = BotConfig.get_or_create()
        anterior = cfg.bot_name
        cfg.bot_name = 'Chasqui'
        db.session.commit()
        try:
            nombre, _emoji = tbs._bot_identity()
            assert nombre == 'Chasqui'
        finally:
            cfg.bot_name = anterior
            db.session.commit()

    def test_respuesta_de_identidad_refleja_el_nombre(self, app, monkeypatch):
        import app.services.telegram_bot_service as tbs

        enviados = []
        monkeypatch.setattr(tbs, 'send_telegram_message', lambda *a, **k: enviados.append(a[1]))
        monkeypatch.setattr(tbs, '_bot_identity', lambda: ('Chasqui', '🦜'))

        cfg = BotConfig.get_or_create()
        anterior = cfg.bot_name
        cfg.bot_name = 'Chasqui'
        db.session.commit()
        try:
            out = tbs.process_text_message(1, '¿quién eres?', 1, 'admin')
            assert 'Chasqui' in out['response'], out['response']
            assert 'Diego' not in out['response']
        finally:
            cfg.bot_name = anterior
            db.session.commit()

    def test_no_hay_nombre_diego_hardcodeado(self):
        import inspect
        import re

        import app.services.telegram_bot_service as tbs

        src = inspect.getsource(tbs)
        assert not re.search(r"'Soy Diego", src), 'la identidad sigue hardcodeada'


class TestSecretoDelWebhook:
    def test_dashboard_no_devuelve_el_secreto_en_claro(self, client, admin, app):
        app.config['TELEGRAM_WEBHOOK_SECRET'] = 'secreto-supersecreto-1234'
        resp = client.get('/api/telegram/dashboard', headers=_admin_headers(admin.id))
        assert resp.status_code == 200
        body = json.dumps(resp.get_json())
        assert 'secreto-supersecreto-1234' not in body, 'el dashboard filtro el secreto en claro'
        bot = resp.get_json()['bot']
        assert bot['webhook_secret_configured'] is True
        assert bot['webhook_secret'].startswith('secr') and bot['webhook_secret'].endswith('1234')
        assert '*' in bot['webhook_secret']

    def test_dashboard_sin_secreto_configurado(self, client, admin, app):
        app.config['TELEGRAM_WEBHOOK_SECRET'] = ''
        resp = client.get('/api/telegram/dashboard', headers=_admin_headers(admin.id))
        bot = resp.get_json()['bot']
        assert bot['webhook_secret_configured'] is False
        assert bot['webhook_secret'] == ''

    def _fake_set_webhook(self, monkeypatch):
        # _tg_request se importa dentro de la funcion, hay que parchearlo
        # en el servicio, no en el modulo de rutas.
        import app.services.telegram_bot_service as tbs

        captured = {}

        def fake_tg_request(method, payload, token):
            captured['method'] = method
            captured['payload'] = payload
            return {'ok': True, 'result': True}

        monkeypatch.setattr(tbs, '_tg_request', fake_tg_request)
        return captured

    def test_setup_actualiza_current_app_config(self, client, admin, app, monkeypatch):
        """Tras el setup, el proceso debe validar con el secreto nuevo."""
        import app.routes.telegram_routes as tr

        app.config['TELEGRAM_BOT_TOKEN'] = '123456:token-de-prueba'
        app.config['TELEGRAM_WEBHOOK_SECRET'] = 'secreto-viejo'
        captured = self._fake_set_webhook(monkeypatch)

        resp = client.post(
            '/api/telegram/webhook/setup',
            headers=_admin_headers(admin.id),
            json={'url': 'https://ejemplo.test/hook', 'secret_token': 'secreto-nuevo-9999'},
        )
        assert resp.status_code == 200
        assert resp.get_json()['ok'] is True
        assert resp.get_json()['applied'] is True
        assert captured['payload']['secret_token'] == 'secreto-nuevo-9999'

        # la fuente unica quedo actualizada: esto es lo que valida el webhook
        assert tr._webhook_secret() == 'secreto-nuevo-9999', (
            'el proceso seguiria validando con el secreto anterior'
        )
        assert app.config['TELEGRAM_WEBHOOK_SECRET'] == 'secreto-nuevo-9999'

    def test_setup_sin_secreto_no_pisa_el_vigente(self, client, admin, app, monkeypatch):
        app.config['TELEGRAM_BOT_TOKEN'] = '123456:token-de-prueba'
        app.config['TELEGRAM_WEBHOOK_SECRET'] = 'secreto-vigente'
        self._fake_set_webhook(monkeypatch)
        resp = client.post(
            '/api/telegram/webhook/setup',
            headers=_admin_headers(admin.id),
            json={'url': 'https://ejemplo.test/hook'},
        )
        assert resp.status_code == 200
        assert resp.get_json()['applied'] is False
        assert app.config['TELEGRAM_WEBHOOK_SECRET'] == 'secreto-vigente'

    def test_webhook_rechaza_secreto_incorrecto(self, client, app):
        app.config['TELEGRAM_WEBHOOK_SECRET'] = 'el-trueque'
        resp = client.post(
            '/api/telegram/webhook',
            headers={'X-Telegram-Bot-Api-Secret-Token': 'el-falso'},
            json={'update_id': 999999},
        )
        assert resp.status_code == 403

    def test_webhook_acepta_secreto_correcto(self, client, app, monkeypatch):
        app.config['TELEGRAM_WEBHOOK_SECRET'] = 'el-trueque'
        import app.routes.telegram_routes as tr

        monkeypatch.setattr(tr, '_is_duplicate', lambda uid: True)
        resp = client.post(
            '/api/telegram/webhook',
            headers={'X-Telegram-Bot-Api-Secret-Token': 'el-trueque'},
            json={'update_id': 999999},
        )
        assert resp.status_code == 200
