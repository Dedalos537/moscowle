"""Estado del servidor: solo admin, solo lectura y con historial en la BD."""

import uuid
from unittest.mock import patch

from flask_jwt_extended import create_access_token

from app.extensions import db
from app.models import User
from app.services import server_monitor


def _h(role):
    tag = uuid.uuid4().hex[:8]
    u = User(username=f'{role[:3]}{tag}', email=f'{tag}@srv.test', password='x', role=role)
    db.session.add(u)
    db.session.commit()
    return {'Authorization': 'Bearer ' + create_access_token(identity=str(u.id))}


def test_only_admin_sees_server_status(client, app):
    assert client.get('/api/server-monitor/status', headers=_h('supervisor')).status_code == 403
    assert client.get('/api/server-monitor/history', headers=_h('terapista')).status_code == 403
    assert client.get('/api/server-monitor/status').status_code == 401


def test_status_shape(client, app):
    def offline(*a, **k):
        raise OSError('sin red en el test')

    with (
        patch.object(server_monitor, 'cpu_percent', return_value=12.5),
        patch.object(server_monitor, '_tcp', side_effect=offline),
        patch.object(server_monitor, '_http', side_effect=offline),
    ):
        server_monitor._cache.update(at=0.0, rows=None)
        data = client.get('/api/server-monitor/status', headers=_h('admin')).get_json()
    assert data['cpu']['pct'] == 12.5
    assert {s['unit'] for s in data['services']} == {unit for unit, *_ in server_monitor.SERVICES}
    assert all(s['where'] in ('VM-APP', 'Host', 'VM-DB') for s in data['services'])
    assert any(c['name'] == 'Base de datos' and c['ok'] for c in data['checks'])
    assert 'cockpit_url' in data


def test_host_services_are_checked_on_the_host_not_with_vm_systemctl(app, monkeypatch):
    """En VM-APP no existen nginx, CUPS, cloudflared ni Ollama: antes salían «Detenido» aunque funcionaran."""
    monkeypatch.delenv('OPENCODE_URL', raising=False)
    monkeypatch.delenv('OPENCODE_DEV_URL', raising=False)
    monkeypatch.delenv('SCAN_TOKEN', raising=False)
    probes = []
    with (
        patch.object(server_monitor, '_systemd', return_value='inactive'),  # lo que decía systemd de la VM
        patch.object(server_monitor, '_host', return_value='192.168.122.1'),
        patch.object(server_monitor, '_tcp', side_effect=lambda h, p, timeout=2.0: probes.append((h, p)) or True),
        patch.object(server_monitor, '_http', side_effect=lambda url, timeout=4.0: probes.append(url) or 200),
    ):
        out = {s['unit']: s for s in server_monitor.services(force=True)}
    for unit in ('nginx', 'cups', 'cloudflared', 'ollama', 'mysql'):
        assert out[unit]['state'] == 'active', out[unit]
    assert ('192.168.122.1', 631) in probes and 'http://192.168.122.1/app/' in probes
    assert out['opencode']['state'] == 'off' and out['moscowle-scand']['state'] == 'off'  # no instalados: no «caídos»


def test_a_service_that_does_not_answer_is_reported_down(app):
    def refuse(h, p, timeout=2.0):
        raise OSError('connection refused')

    with (
        patch.object(server_monitor, '_systemd', return_value='active'),
        patch.object(server_monitor, '_host', return_value='192.168.122.1'),
        patch.object(server_monitor, '_tcp', side_effect=refuse),
        patch.object(server_monitor, '_http', return_value=200),
    ):
        out = {s['unit']: s for s in server_monitor.services(force=True)}
    assert out['cups']['state'] == 'inactive' and '631' in out['cups']['detail']


def test_frontend_static_files_are_not_rate_limited(client, app):
    """Toda la clínica sale por la misma IP: con ~60 archivos por carga se llegaba al límite y todos veían 429."""
    codes = {client.get('/app/').status_code for _ in range(5)}
    assert 429 not in codes


def test_record_and_history(client, app):
    with (
        patch.object(server_monitor, 'cpu_percent', return_value=40.0),
        patch.object(server_monitor, 'services', return_value=[{'unit': 'nginx', 'label': 'x', 'state': 'failed'}]),
    ):
        server_monitor.record()
    snaps = client.get('/api/server-monitor/history?hours=1', headers=_h('admin')).get_json()['snapshots']
    assert snaps and snaps[-1]['cpu_pct'] == 40.0 and snaps[-1]['services_down'] == ['nginx']
