"""A quien se le manda un SMS y desde donde sale.

Dos errores que solo se veian cuando el proveedor rechazaba el envio:

  * guardian_contact mezcla telefono y correo. Con el correo puesto,
    resolve_phone devolvia el correo y el SMS salia hacia una direccion
    de correo. En los datos reales hay un paciente asi.
  * El numero se guardaba local ('937657870'). Ni Twilio ni el gateway
    aceptan eso: sin normalizar a +51 el envio falla siempre.
"""

import pytest


@pytest.fixture(autouse=True)
def _limpiar(db, session):
    from app.models.user import User

    session.rollback()
    yield
    session.rollback()
    User.query.filter(User.username.like('smsdest_%')).delete(synchronize_session=False)
    session.commit()


def _paciente(session, username, **extra):
    from app.models.user import User

    p = User(username=username, email=f'{username}@x.com', password='x', role='jugador', **extra)
    session.add(p)
    session.commit()
    return p


class _DobleSMS:
    def __init__(self):
        self.entregas = []

    def is_available(self):
        return True

    def send_sms_message(self, phone, body):
        self.entregas.append((phone, body))
        return {'ok': True, 'provider_message_id': 'SM-test'}


def _svc():
    from app.services.messaging import MessagingService

    return MessagingService(sms=_DobleSMS())


# ------------------------------------------------------- a quien se escribe


def test_el_apoderado_con_correo_no_es_destino_de_sms(db, session):
    p = _paciente(
        session,
        'smsdest_correo',
        phone='939293130',
        guardian_contact='liz.v.marilyn@gmail.com',
    )
    assert _svc().resolve_phone(p) == '939293130'


def test_el_apoderado_con_telefono_sigue_mandando(db, session):
    p = _paciente(session, 'smsdest_apod', phone='939293130', guardian_contact='937657870')
    assert _svc().resolve_phone(p) == '937657870'


def test_si_unico_dato_es_un_correo_no_hay_destino(db, session):
    p = _paciente(session, 'smsdest_vacio', phone='', guardian_contact='liz.v.marilyn@gmail.com')
    ok, motivo = _svc().check_contactable(p, 'sms')
    assert ok is False
    assert 'numero' in motivo.lower()


def test_el_sms_tambien_valida_el_numero(db, session):
    """Antes solo lo validaba whatsapp: un correo pasaba al proveedor."""
    p = _paciente(session, 'smsdest_corto', phone='123')
    ok, motivo = _svc().check_contactable(p, 'sms')
    assert ok is False
    assert 'valido' in motivo.lower()


def test_sms_con_telefono_valido_y_apoderado_de_correo(db, session):
    p = _paciente(
        session,
        'smsdest_ok',
        phone='937657870',
        guardian_contact='liz.v.marilyn@gmail.com',
    )
    ok, motivo = _svc().check_contactable(p, 'sms')
    assert ok is True
    assert motivo is None


# ------------------------------------------------------- desde donde sale


def test_el_numero_se_normaliza_a_e164():
    from app.services.sms_whatsapp_service import to_e164

    assert to_e164('937657870') == '+51937657870'
    assert to_e164('+51937657870') == '+51937657870'
    assert to_e164('51937657870') == '+51937657870'
    assert to_e164('0937657870') == '+51937657870'
    assert to_e164('(937) 657 870') == '+51937657870'
    assert to_e164('') == ''
    assert to_e164(None) == ''
    assert to_e164('liz.v.marilyn@gmail.com') == ''


def test_el_sms_sale_por_el_celular_del_centro(monkeypatch):
    pytest.importorskip('requests')
    import app.services.sms_whatsapp_service as mod

    llamada = {}

    class _Resp:
        status_code = 200

        @staticmethod
        def json():
            return {'success': True, 'message': 'exito', 'message_id': 'ABCDFESD'}

    def _post(url, headers=None, json=None, timeout=None):
        llamada.update(url=url, headers=headers, body=json, timeout=timeout)
        return _Resp()

    monkeypatch.setenv('SMS_GATEWAY_TOKEN', 'tok-de-prueba')
    monkeypatch.setattr(mod.requests, 'post', _post)

    svc = mod.SMSWhatsAppService()
    assert svc.gateway_available is True
    assert svc.is_available() is True

    out = svc.send_sms_message('937657870', 'Hola')

    assert out == {'ok': True, 'provider_message_id': 'ABCDFESD'}
    assert llamada['url'] == 'https://api.sms.json.pe/send'
    assert llamada['headers']['Authorization'] == 'Bearer tok-de-prueba'
    assert llamada['body']['number'] == '51937657870', 'el gateway pide el codigo de pais sin +'
    assert llamada['body']['message'] == 'Hola'


def test_si_el_celular_no_puede_enviar_el_error_vuelve(monkeypatch):
    pytest.importorskip('requests')
    import app.services.sms_whatsapp_service as mod

    class _Resp:
        status_code = 400

        @staticmethod
        def json():
            return {'success': False, 'message': 'Bad Request'}

    monkeypatch.setenv('SMS_GATEWAY_TOKEN', 'tok-de-prueba')
    monkeypatch.setattr(mod.requests, 'post', lambda *a, **kw: _Resp())

    svc = mod.SMSWhatsAppService()
    out = svc.send_sms_message('937657870', 'Hola')

    assert out['ok'] is False
    assert 'Gateway' in out['error']


def test_sin_token_no_hay_proveedor_sms():
    """Sin configurar, el error tiene que decir que no hay proveedor."""
    import app.services.sms_whatsapp_service as mod

    svc = mod.SMSWhatsAppService.__new__(mod.SMSWhatsAppService)
    svc.gateway_url = 'https://api.sms.json.pe'
    svc.gateway_token = ''
    svc.gateway_available = False
    svc.twilio_available = False
    svc.pywhatkit_available = False

    assert svc.is_available() is False
    out = svc.send_sms_message('937657870', 'Hola')
    assert out['ok'] is False
    assert 'proveedor' in out['error'].lower()


def test_un_fallo_de_sms_no_se_cuenta_como_enviado():
    """_dispatch contaba el truthy del dict, y el dict de un fallo tambien es truthy."""
    from app.services.session_reminder_service import SessionReminderService

    class _Messaging:
        @staticmethod
        def send_whatsapp_message(phone, body):
            return True

        @staticmethod
        def send_sms_message(phone, body):
            return {'ok': False, 'error': 'Gateway: Bad Request'}

    svc = SessionReminderService.__new__(SessionReminderService)
    svc.messaging = _Messaging()
    counts = {'sent_whatsapp': 0, 'sent_sms': 0}

    svc._dispatch('937657870', 'hola', counts)

    assert counts['sent_sms'] == 0, 'un fallo no es un envio'
    assert counts['sent_whatsapp'] == 1
