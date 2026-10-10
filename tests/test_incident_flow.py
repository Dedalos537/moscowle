"""Flujo de incidencias entre roles: reportar, ver, asignar, responder, cambiar estado y avisos."""

import uuid

from flask_jwt_extended import create_access_token

from app.extensions import db
from app.models import User
from app.models.notification_group import NotificationGroup, NotificationItem


def _user(role):
    tag = uuid.uuid4().hex[:8]
    u = User(username=f'{role[:3]}{tag}', email=f'{tag}@inc.test', password='x', role=role)
    db.session.add(u)
    db.session.commit()
    return u


def _h(u):
    return {'Authorization': 'Bearer ' + create_access_token(identity=str(u.id))}


class _Note:
    def __init__(self, item, group):
        self.message, self.link, self.title = item.message, item.link, group.title or ''


def _notes(u):
    rows = (
        db.session.query(NotificationItem, NotificationGroup)
        .join(NotificationGroup, NotificationGroup.id == NotificationItem.group_id)
        .filter(NotificationItem.user_id == u.id)
        .order_by(NotificationItem.id)
        .all()
    )
    return [_Note(i, g) for i, g in rows]


NEW = {
    'titulo': 'No carga el juego de memoria',
    'descripcion': 'Al abrir el juego en la sesión de hoy la pantalla queda en blanco.',
    'categoria': 'SOFTWARE',
    'impacto': 2,
    'urgencia': 3,
}


def test_full_flow_between_roles(client, app):
    admin, supervisor = _user('admin'), _user('supervisor')
    therapist, colleague = _user('terapista'), _user('terapista')

    # 1) El terapeuta reporta: queda sin responsable y coordinación (admin y supervisor) recibe el aviso.
    r = client.post('/api/incidents', json=NEW, headers=_h(therapist))
    assert r.status_code == 201, r.get_json()
    inc = r.get_json()
    iid = inc['id']
    assert inc['responsable_id'] is None and inc['prioridad'] == 6
    assert any(f'#{iid}' in n.message for n in _notes(supervisor))
    assert any(n.link == f'/admin/incidents/{iid}' for n in _notes(admin))

    # 2) Quien reporta no puede resolverse su propio caso ni lo ve un colega ajeno.
    assert (
        client.put(f'/api/incidents/{iid}/status', json={'estado': 'RESUELTO'}, headers=_h(therapist)).status_code
        == 403
    )
    assert client.get(f'/api/incidents/{iid}', headers=_h(colleague)).status_code == 403
    assert (
        client.post(
            f'/api/incidents/{iid}/comments', json={'contenido': 'Hola, ¿qué pasó?'}, headers=_h(colleague)
        ).status_code
        == 403
    )

    # 3) Coordinación asigna al colega: le llega el aviso, con enlace a su propia sección.
    r = client.put(f'/api/incidents/{iid}/assign', json={'responsable_id': colleague.id}, headers=_h(supervisor))
    assert r.status_code == 200, r.get_json()
    assert any(n.link == f'/therapist/incidents?id={iid}' for n in _notes(colleague))

    # 4) El responsable lo pone en atención: quien reportó recibe el cambio de estado.
    r = client.put(f'/api/incidents/{iid}/status', json={'estado': 'EN_CURSO'}, headers=_h(colleague))
    assert r.status_code == 200, r.get_json()
    assert any('En atención' in n.message and n.link == f'/therapist/incidents?id={iid}' for n in _notes(therapist))

    # 5) Respuesta pública del responsable -> aviso a quien reportó; nota interna -> no.
    before = len(_notes(therapist))
    client.post(f'/api/incidents/{iid}/comments', json={'contenido': 'Ya lo estamos revisando.'}, headers=_h(colleague))
    assert len(_notes(therapist)) == before + 1
    client.post(
        f'/api/incidents/{iid}/comments',
        json={'contenido': 'Nota interna: reiniciar caché', 'es_interno': True},
        headers=_h(colleague),
    )
    assert len(_notes(therapist)) == before + 1

    # 6) Resolver -> aviso de resolución a quien reportó.
    r = client.put(f'/api/incidents/{iid}/status', json={'estado': 'RESUELTO'}, headers=_h(colleague))
    assert r.status_code == 200
    assert any('resuelto' in n.message.lower() for n in _notes(therapist))


def test_patient_never_sees_internal_notes(client, app):
    admin, patient = _user('admin'), _user('jugador')
    r = client.post('/api/incidents', json={**NEW, 'categoria': 'OPERACIONES'}, headers=_h(patient))
    iid = r.get_json()['id']
    client.post(
        f'/api/incidents/{iid}/comments',
        json={'contenido': 'Interno: revisar cobro', 'es_interno': True},
        headers=_h(admin),
    )
    client.post(
        f'/api/incidents/{iid}/comments', json={'contenido': 'Gracias por avisar, lo vemos hoy.'}, headers=_h(admin)
    )
    # El paciente intenta marcar su comentario como interno: se guarda como público.
    r = client.post(
        f'/api/incidents/{iid}/comments',
        json={'contenido': 'Sigue sin funcionar', 'es_interno': True},
        headers=_h(patient),
    )
    assert r.get_json()['es_interno'] is False

    seen = [c['contenido'] for c in client.get(f'/api/incidents/{iid}', headers=_h(patient)).get_json()['comentarios']]
    assert 'Interno: revisar cobro' not in seen and 'Gracias por avisar, lo vemos hoy.' in seen
    staff = [c['contenido'] for c in client.get(f'/api/incidents/{iid}', headers=_h(admin)).get_json()['comentarios']]
    assert 'Interno: revisar cobro' in staff
    # La respuesta del paciente llega a coordinación (no hay responsable aún).
    assert any('Nueva respuesta' in (n.title or '') for n in _notes(admin))
    # El paciente no puede cambiar el estado de su incidencia.
    assert (
        client.put(f'/api/incidents/{iid}/status', json={'estado': 'RESUELTO'}, headers=_h(patient)).status_code == 403
    )
