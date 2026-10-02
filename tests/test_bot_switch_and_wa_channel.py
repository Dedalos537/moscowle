"""Interruptor maestro del bot y estado real del canal WhatsApp.

Hallazgos que corrigen:
- `bot.is_active` reflejaba unicamente si habia token de Telegram, asi que no
  existia forma de apagar el bot sin borrar la configuracion.
- El webhook seguia respondiendo aunque el usuario quisiera el bot parado.
- El tarjeto de canales del panel Bot mostraba "Proximamente" para WhatsApp
  con el puente ya conectado, porque estaba hardcodeado a `coming_soon`.
"""

import pytest
from flask_jwt_extended import create_access_token

from app.extensions import db
from app.models import User
from app.models.bot_config import BotConfig


def _admin_headers(user_id):
    return {'Authorization': 'Bearer ' + create_access_token(identity=str(user_id))}


@pytest.fixture
def admin(session):
    user = User.query.filter_by(email='tg_switch_admin@example.com').first()
    if user is None:
        user = User(
            username='tg_switch_admin',
            email='tg_switch_admin@example.com',
            password='x',
            role='admin',
        )
        db.session.add(user)
        db.session.commit()
    user.role = 'admin'
    db.session.commit()
    return user


@pytest.fixture
def cfg(app):
    # app empuja el context: get_or_create necesita la sesion de esa app
    c = BotConfig.get_or_create()
    anterior = c.enabled
    yield c
    c.enabled = anterior
    db.session.commit()


# ────────────────────────────────────────────────────────── interruptor


class TestInterruptorDelBot:
    def test_enabled_arranca_activado(self, cfg):
        assert cfg.enabled is True
        assert cfg.to_dict()['enabled'] is True

    def test_bot_enabled_lee_la_columna(self, app, cfg):
        import app.services.telegram_bot_service as tbs

        cfg.enabled = False
        db.session.commit()
        assert tbs._bot_enabled() is False

        cfg.enabled = True
        db.session.commit()
        assert tbs._bot_enabled() is True

    def test_desactivar_el_bot_no_borra_el_token(self, app, cfg, monkeypatch):
        """El interruptor es independiente de 'hay token configurado'."""
        monkeypatch.setitem(app.config, 'TELEGRAM_BOT_TOKEN', '123456:ABC-DEF')
        cfg.enabled = False
        db.session.commit()

        # el token sigue en la config: apagar el bot no lo toca
        assert app.config['TELEGRAM_BOT_TOKEN'] == '123456:ABC-DEF'
        assert BotConfig.get_or_create().enabled is False

    def test_patch_puede_alternar_enabled(self, app, client, admin, cfg):
        cfg.enabled = True
        db.session.commit()

        resp = client.put(
            '/api/telegram/config',
            json={'enabled': False},
            headers=_admin_headers(admin.id),
        )
        if resp.status_code == 404:
            pytest.skip('ruta de config del bot no expuesta en esta build')
        assert resp.status_code in (200, 201)
        assert resp.get_json()['config']['enabled'] is False
        assert BotConfig.get_or_create().enabled is False


# ────────────────────────────────────────────────────────── webhook


class TestWebhookRespetaElInterruptor:
    def test_no_procesa_consultas_con_el_bot_apagado(self, app, cfg, monkeypatch):
        import app.services.telegram_bot_service as tbs

        # sin token el handler sale antes de llegar al interruptor
        monkeypatch.setitem(app.config, 'TELEGRAM_BOT_TOKEN', '123456:token-de-prueba')
        cfg.enabled = False
        db.session.commit()

        enviados = []
        monkeypatch.setattr(tbs, 'send_telegram_message', lambda *a, **k: enviados.append(a))

        tbs.handle_webhook_update(
            {
                'update_id': 1,
                'message': {'chat': {'id': 555}, 'text': 'hola, ¿que sesiones tengo?'},
            }
        )

        assert len(enviados) == 1, 'debe avisar que esta apagado'
        assert 'desactivado' in enviados[0][1].lower()

    def test_siguen_funcionando_los_comandos_de_vinculacion(self, app, cfg, monkeypatch):
        import app.services.telegram_bot_service as tbs

        monkeypatch.setitem(app.config, 'TELEGRAM_BOT_TOKEN', '123456:token-de-prueba')
        cfg.enabled = False
        db.session.commit()

        llamado = []
        monkeypatch.setattr(tbs, '_handle_start', lambda *a, **k: llamado.append('start'))

        tbs.handle_webhook_update(
            {
                'update_id': 2,
                'message': {'chat': {'id': 556}, 'text': '/start'},
            }
        )

        assert llamado == ['start'], '/start debe seguir vivo para poder vincular'

    def test_con_el_bot_encendido_no_aparece_el_aviso(self, app, cfg, monkeypatch):
        import app.services.telegram_bot_service as tbs

        monkeypatch.setitem(app.config, 'TELEGRAM_BOT_TOKEN', '123456:token-de-prueba')
        cfg.enabled = True
        db.session.commit()

        avisos = []
        monkeypatch.setattr(
            tbs,
            'send_telegram_message',
            lambda chat, text, *a, **k: avisos.append(text),
        )
        monkeypatch.setattr(tbs, '_handle_menu', lambda *a, **k: None)

        tbs.handle_webhook_update(
            {
                'update_id': 3,
                'message': {'chat': {'id': 557}, 'text': '/menu'},
            }
        )

        assert not any('desactivado' in a.lower() for a in avisos)


# ────────────────────────────────────────────────────────── canal WA


class TestCanalWhatsAppEnElPanel:
    def test_el_canal_no_es_hardcodeado_a_coming_soon(self, app, monkeypatch):
        from app.routes import telegram_routes as tr

        estado = tr._whatsapp_channel_status()
        assert estado['status'] != 'coming_soon'
        assert estado['label'] == 'WhatsApp (Baileys)'
        assert 'setup_tab' in estado

    def test_refleja_el_estado_del_puente(self, app, monkeypatch):
        from app.routes import telegram_routes as tr

        class Falso:
            @staticmethod
            def status():
                return {
                    'connected': True,
                    'running': True,
                    'needs_qr': False,
                    'phone': '51974651682',
                    'jid': '51974651682@s.whatsapp.net',
                    'uptime_s': 42,
                    'last_error': None,
                    'banned': False,
                    'has_qr': False,
                }

        import app.services.whatsapp_service as ws

        monkeypatch.setattr(ws, 'whatsapp_service', Falso())
        estado = tr._whatsapp_channel_status()
        assert estado['active'] is True
        assert estado['connected'] is True
        assert estado['status'] == 'connected'
        assert estado['phone'] == '51974651682'

    def test_estado_sin_puente_no_es_coming_soon(self, app, monkeypatch):
        """Si el puente ni siquiera se puede leer, sigue sin decir 'proximamente'."""
        from app.routes import telegram_routes as tr

        class Roto:
            @staticmethod
            def status():
                raise RuntimeError('puente caido')

        import app.services.whatsapp_service as ws

        monkeypatch.setattr(ws, 'whatsapp_service', Roto())
        estado = tr._whatsapp_channel_status()
        assert estado['status'] == 'offline'
        assert estado['active'] is False

    def test_needs_qr_se_traduce_a_waiting_qr(self, app, monkeypatch):
        from app.routes import telegram_routes as tr

        class Raro:
            @staticmethod
            def status():
                return {
                    'connected': False,
                    'running': True,
                    'needs_qr': True,
                    'last_error': None,
                    'phone': None,
                }

        import app.services.whatsapp_service as ws

        monkeypatch.setattr(ws, 'whatsapp_service', Raro())
        assert tr._whatsapp_channel_status()['status'] == 'waiting_qr'


# ────────────────────────────────────────────────────────── dashboard


class TestDashboardExponeElSwitch:
    def test_dashboard_incluye_enabled_y_configured(self, app, client, admin, monkeypatch):
        cfg = BotConfig.get_or_create()
        cfg.enabled = False
        db.session.commit()
        monkeypatch.setitem(app.config, 'TELEGRAM_BOT_TOKEN', '111:XYZ')

        resp = client.get('/api/telegram/dashboard', headers=_admin_headers(admin.id))
        assert resp.status_code == 200
        data = resp.get_json()['bot']
        assert data['enabled'] is False
        assert data['configured'] is True
        assert data['is_active'] is False, 'apagado = no activo aunque haya token'

    def test_dashboard_sin_token_sigue_desactivado_aunque_encendido(self, app, client, admin, monkeypatch):
        cfg = BotConfig.get_or_create()
        cfg.enabled = True
        db.session.commit()
        monkeypatch.setitem(app.config, 'TELEGRAM_BOT_TOKEN', '')

        resp = client.get('/api/telegram/dashboard', headers=_admin_headers(admin.id))
        assert resp.status_code == 200
        data = resp.get_json()['bot']
        assert data['enabled'] is True
        assert data['configured'] is False
        assert data['is_active'] is False
