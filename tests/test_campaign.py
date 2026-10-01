"""Campañas: armar destinatarios, no repetir, y poder pausar sin duplicar."""
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
    User.query.filter(User.username.like('camp_%')).delete(synchronize_session=False)
    session.commit()


class _SMSFalso:
    def __init__(self):
        self.entregas = []

    def is_available(self):
        return True

    def send_sms_message(self, phone, body):
        self.entregas.append((phone, body))
        return {'ok': True, 'provider_message_id': 'SM-camp'}


def _paciente(session, username, activo=True, telefono='999111222'):
    from app.models.user import User

    p = User(username=username, email=f'{username}@x.com', password='x', role='jugador',
             is_active=activo, phone=telefono)
    session.add(p)
    session.commit()
    return p


def _svc():
    from app.services.messaging import MessagingService

    return MessagingService(sms=_SMSFalso(), MIN_GAP_SECONDS=0, DAILY_CAPS={'sms': 100, 'whatsapp': 100})


def _campana(session, name='avisos', canal='sms', segmento='active'):
    from app.models.campaign import Campaign

    c = Campaign(name=name, channel=canal, message='Hola {nombre}, tu turno es manana',
                 segment=segmento, status='draft')
    session.add(c)
    session.commit()
    return c


def test_la_campana_salta_a_quien_no_se_puede_avisar(db, session):
    activo = _paciente(session, 'camp_activo')
    _paciente(session, 'camp_baja', activo=False)
    _paciente(session, 'camp_sin_tel', telefono=None)

    from app.models.user import User

    c = _campana(session)
    svc = _svc()
    prep = svc.prepare_campaign(c, User.query.filter(User.username.like('camp_%')).all())

    from app.models.campaign import CampaignSend

    rows = CampaignSend.query.filter_by(campaign_id=c.id).all()
    estados = {r.patient_id: r.status for r in rows}
    assert estados[activo.id] == 'pending'
    assert prep['skipped'] == 2, 'uno desactivado y uno sin numero'


def test_enviar_una_campana_registra_quien_la_recibio(db, session):
    a = _paciente(session, 'camp_uno')
    b = _paciente(session, 'camp_dos')
    c = _campana(session)
    svc = _svc()
    svc.prepare_campaign(c, [a, b])

    r = svc.run_campaign(c.id, pace=False)
    assert r['sent'] == 2
    assert r['status'] == 'sent'
    assert len(svc.sms.entregas) == 2

    from app.models.message_log import MessageLog

    assert MessageLog.query.filter_by(campaign_id=c.id, status='sent').count() == 2


def test_no_reenvia_a_quien_ya_recibio(db, session):
    """Reanudar una campana no debe duplicar el mensaje."""
    a = _paciente(session, 'camp_reanuda')
    c = _campana(session)
    svc = _svc()
    svc.prepare_campaign(c, [a])

    svc.run_campaign(c.id, max_messages=1, pace=False)
    # El puente se cae a mitad: el envio queda pendiente.
    from app.models.campaign import CampaignSend

    CampaignSend.query.filter_by(campaign_id=c.id).update({'status': 'pending'})
    c.status = 'paused'
    session.commit()

    svc.run_campaign(c.id, pace=False)
    assert len(svc.sms.entregas) == 1, 'el reintento mando el mismo mensaje dos veces'


def test_el_boton_dry_run_no_manda_nada(db, session):
    a = _paciente(session, 'camp_dry')
    c = _campana(session)
    svc = _svc()
    svc.prepare_campaign(c, [a])

    pendientes = svc.check_repeat(a, 'Hola, tu turno es manana', 'sms')
    assert pendientes == (True, None)
    assert svc.sms.entregas == [], 'el dry run no puede enviar'


def test_nombre_puesto_en_el_texto(db, session):
    a = _paciente(session, 'camp_nombre', telefono='999555444')
    a.first_name = 'Lucia'
    c = _campana(session)
    svc = _svc()
    svc.prepare_campaign(c, [a])
    svc.run_campaign(c.id, pace=False)

    assert 'Lucia' in svc.sms.entregas[0][1], 'la primera vez del nombre no se sustituyo'
