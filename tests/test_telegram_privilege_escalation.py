"""Pruebas dirigidas de escalada de privilegios en el panel/bot de Telegram.

Contexto del hallazgo: las rutas de telegram_routes.py solo exigian JWT (sin
comprobar rol) y handle_webhook_update ejecutaba las tools del MCP con el rol
fijo 'admin' para cualquier cuenta vinculada. Un usuario no administrador
(por ejemplo un paciente) podia vincular su Telegram y luego usar /pagos,
/pacientes o /sesiones para leer datos administrativos.

Estas pruebas fallan contra el codigo vulnerable y pasan tras el fix.
"""

import json
from datetime import UTC, datetime, timedelta

import pytest
from flask_jwt_extended import create_access_token

from app.extensions import db
from app.models import User
from app.models.telegram_user import TelegramUser


def _auth_headers(user_id):
    token = create_access_token(identity=str(user_id))
    return {'Authorization': f'Bearer {token}'}


@pytest.fixture
def paciente(session):
    """Usuario con rol de paciente: no debe tocar el panel de administracion."""
    user = User.query.filter_by(email='paciente_tg@example.com').first()
    if user is None:
        user = User(
            username='paciente_tg',
            email='paciente_tg@example.com',
            password='x',
            role='jugador',
        )
        db.session.add(user)
        db.session.commit()
    user.role = 'jugador'
    db.session.commit()
    yield user
    db.session.rollback()


@pytest.fixture
def admin_user(session):
    user = User.query.filter_by(email='admin_tg@example.com').first()
    if user is None:
        user = User(
            username='admin_tg',
            email='admin_tg@example.com',
            password='x',
            role='admin',
        )
        db.session.add(user)
        db.session.commit()
    user.role = 'admin'
    db.session.commit()
    yield user
    db.session.rollback()


def _make_pending_code(session, chat_id=999001, code='ABC123'):
    tg = TelegramUser.query.filter_by(telegram_chat_id=chat_id).first()
    if tg is None:
        tg = TelegramUser(telegram_chat_id=chat_id)
        session.add(tg)
    tg.telegram_username = 'atacante'
    tg.telegram_first_name = 'Atacante'
    tg.is_linked = False
    tg.admin_user_id = None
    tg.link_code = code
    tg.link_code_expires_at = datetime.now(UTC) + timedelta(minutes=10)
    session.commit()
    return tg


class TestLinkAccountRequiresAdmin:
    """POST /api/telegram/link no debe vincular cuentas no administrativas."""

    def test_paciente_no_puede_vincular(self, client, paciente, session):
        _make_pending_code(session)
        resp = client.post(
            '/api/telegram/link',
            headers=_auth_headers(paciente.id),
            content_type='application/json',
            data=json.dumps({'code': 'ABC123'}),
        )
        assert resp.status_code == 403, f'un paciente pudo vincular su Telegram: {resp.status_code} {resp.get_json()}'
        assert not TelegramUser.query.filter_by(link_code='ABC123', is_linked=True).first()

    def test_admin_si_puede_vincular(self, client, admin_user, session):
        tg = _make_pending_code(session, chat_id=999012, code='XYZ789')
        resp = client.post(
            '/api/telegram/link',
            headers=_auth_headers(admin_user.id),
            content_type='application/json',
            data=json.dumps({'code': 'XYZ789'}),
        )
        assert resp.status_code == 200
        assert TelegramUser.query.get(tg.id).is_linked is True


class TestAdminPanelRequiresAdmin:
    """Todo el panel de configuracion del bot es territorio de administracion."""

    PANEL = [
        ('get', '/api/telegram/dashboard', None),
        ('get', '/api/telegram/config', None),
        ('put', '/api/telegram/config', {}),
        ('get', '/api/telegram/faq', None),
        ('post', '/api/telegram/faq', {'question': 'x', 'answer': 'y'}),
        ('get', '/api/telegram/faq/proposed', None),
        ('post', '/api/telegram/faq/autogrow', None),
        ('post', '/api/telegram/faq/search', {'query': 'x'}),
        ('get', '/api/telegram/webhook/status', None),
        ('post', '/api/telegram/webhook/setup', {}),
        ('delete', '/api/telegram/webhook', None),
        ('post', '/api/telegram/unlink', {}),
        # /notifications/toggle ya no es del panel: cada usuario gestiona SOLO sus cuentas (tests/test_telegram_notifications.py)
        ('post', '/api/telegram/reply', {'chat_id': 1, 'text': 'x'}),
        ('post', '/api/telegram/test', {'chat_id': 1}),
    ]

    @pytest.mark.parametrize('method,path,body', PANEL)
    def test_no_admin_recib_403(self, client, paciente, method, path, body):
        resp = getattr(client, method)(
            path,
            headers=_auth_headers(paciente.id),
            content_type='application/json',
            data=json.dumps(body) if body is not None else None,
        )
        assert resp.status_code == 403, f'{method.upper()} {path} devolvio {resp.status_code} a un paciente'

    def test_sin_token_recib_401(self, client):
        resp = client.get('/api/telegram/dashboard')
        assert resp.status_code == 401


class TestWebhookDoesNotHardcodeAdminRole:
    """El rol ejecutado debe venir de la BD, no de un literal 'admin'."""

    def test_rol_real_de_usuario_no_admin(self, app, paciente, session):
        from app.services import telegram_bot_service as tbs

        tg = TelegramUser(
            telegram_chat_id=999003,
            telegram_username='paciente',
            is_linked=True,
            admin_user_id=paciente.id,
        )
        session.add(tg)
        session.commit()

        captured = {}

        def fake_process(chat_id, text, user_id, role, *a, **kw):
            captured['user_id'] = user_id
            captured['role'] = role
            return {'response': 'ok'}

        original = tbs.process_text_message
        original_send = tbs.send_telegram_message
        tbs.process_text_message = fake_process
        tbs.send_telegram_message = lambda *a, **kw: None
        try:
            with app.test_request_context():
                tbs._handle_quick_command(999003, tg, '/pagos', 'texto')
        finally:
            tbs.process_text_message = original
            tbs.send_telegram_message = original_send

        assert captured['role'] != 'admin', f"un usuario rol '{paciente.role}' ejecuto tools con role='admin'"
        assert captured['role'] == paciente.role
        assert captured['user_id'] == paciente.id

    def test_rol_admin_se_conserva_para_admin(self, app, admin_user, session):
        from app.services import telegram_bot_service as tbs

        tg = TelegramUser(
            telegram_chat_id=999004,
            telegram_username='admin',
            is_linked=True,
            admin_user_id=admin_user.id,
        )
        session.add(tg)
        session.commit()

        captured = {}

        def fake_process(chat_id, text, user_id, role, *a, **kw):
            captured['role'] = role
            return {'response': 'ok'}

        original = tbs.process_text_message
        original_send = tbs.send_telegram_message
        tbs.process_text_message = fake_process
        tbs.send_telegram_message = lambda *a, **kw: None
        try:
            with app.test_request_context():
                tbs._handle_quick_command(999004, tg, '/pagos', 'texto')
        finally:
            tbs.process_text_message = original
            tbs.send_telegram_message = original_send

        assert captured['role'] == 'admin'
