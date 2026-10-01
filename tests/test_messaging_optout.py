"""El opt-out tiene que cortar el envio de verdad.

Antes: is_active=False no lo miraba NINGUN servicio de cobranza ni de
recordatorios. Un paciente dado de baja seguia recibiendo WhatsApp y SMS.
"""
import pytest


@pytest.fixture(autouse=True)
def _limpiar(db, session):
    from app.models.campaign import Campaign, CampaignSend
    from app.models.message_log import MessageLog
    from app.models.user import User

    session.rollback()
    yield
    session.rollback()
    MessageLog.query.delete(synchronize_session=False)
    CampaignSend.query.delete(synchronize_session=False)
    Campaign.query.delete(synchronize_session=False)
    User.query.filter(User.username.like('msg_%')).delete(synchronize_session=False)
    session.commit()


def _paciente(session, username, **extra):
    from app.models.user import User

    p = User(username=username, email=f'{username}@x.com', password='x',
             role='jugador', **extra)
    session.add(p)
    session.commit()
    return p


class _FalsoSMS:
    """Doble de prueba: el envio tiene que quedar registrado igual."""

    def __init__(self, disponible=True, **kw):
        self.disponible = disponible
        self.entregas = []

    def is_available(self):
        return self.disponible

    def send_sms_message(self, phone, body):
        self.entregas.append((phone, body))
        return {'ok': True, 'provider_message_id': 'SM-test'}


def _svc(**kw):
    """Servicio con SMS simulado, para no depender de credenciales reales."""
    from app.services.messaging import MessagingService

    kw.setdefault('sms', _FalsoSMS())
    return MessagingService(**kw)


def test_desactivado_no_se_puede_avisar(db, session):
    p = _paciente(session, 'msg_desactivado', phone='999888777', is_active=False)
    ok, motivo = _svc().check_contactable(p, 'whatsapp')
    assert ok is False
    assert 'desactivado' in motivo.lower()


def test_sin_numero_no_se_puede_avisar(db, session):
    p = _paciente(session, 'msg_sin_numero', is_active=True, phone=None)
    ok, motivo = _svc().check_contactable(p, 'sms')
    assert ok is False
    assert 'numero' in motivo.lower()


def test_el_envio_se_queda_registrado_como_omitido(db, session):
    """No debe 'enviar' y devolver exito: tiene que quedar en el log."""
    p = _paciente(session, 'msg_omitido', is_active=False, phone='999888777')
    r = _svc().send_to_patient(p.id, 'hola', channel='whatsapp')

    assert r['status'] == 'skipped', 'un desactivado jamas se marca como enviado'
    assert r['patient_id'] == p.id

    from app.models.message_log import MessageLog

    log = MessageLog.query.filter_by(patient_id=p.id).first()
    assert log is not None, 'el intento tiene que quedar registrado'
    assert log.status == 'skipped'


def test_no_repetir_el_mismo_mensaje_seguidamente(db, session):
    p = _paciente(session, 'msg_repetido', is_active=True, phone='999888777')
    svc = _svc(daily_caps={'whatsapp': 100, 'sms': 100})
    svc.send_to_patient(p.id, 'aviso 1', channel='sms')

    r = svc.send_to_patient(p.id, 'aviso 1', channel='sms')
    assert r['status'] == 'skipped', 'el mismo texto dos veces seguidas es un bug de reintento'
    assert 'menos de' in r['reason']


def test_tope_diario_se_respeta(db, session):
    p = _paciente(session, 'msg_tope', is_active=True, phone='999888777')
    svc = _svc(daily_caps={'sms': 2, 'whatsapp': 2})
    for i in range(2):
        assert svc.send_to_patient(p.id, f'aviso {i}', channel='sms')['status'] == 'sent'

    r = svc.send_to_patient(p.id, 'aviso de mas', channel='sms')
    assert r['status'] == 'skipped'
    assert 'tope' in r['reason'].lower()


def test_preferir_el_contacto_del_apoderado(db, session):
    p = _paciente(session, 'msg_apoderado', is_active=True,
                  phone='999888777', guardian_contact='988777666')
    assert _svc().resolve_phone(p) == '988777666'


def test_plantilla_con_campo_faltante_no_revienta(db, session):
    """str.format reventaba con cualquier llave de mas y se perdia el envio."""
    from app.services.messaging import MessagingService

    texto = 'Hola {nombre}, tu cuota {monto} vence {fecha_inexistente}'
    out = MessagingService.render(texto, {'nombre': 'Ana', 'monto': '380'})
    assert 'Ana' in out and '380' in out
    assert '{fecha_inexistente}' in out, 'lo que no se puede rellenar se deja visible'
