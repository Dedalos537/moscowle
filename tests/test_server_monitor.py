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
    with patch.object(server_monitor, 'cpu_percent', return_value=12.5):
        data = client.get('/api/server-monitor/status', headers=_h('admin')).get_json()
    assert data['cpu']['pct'] == 12.5
    assert {s['unit'] for s in data['services']} == set(server_monitor.SERVICES)
    assert any(c['name'] == 'Base de datos' and c['ok'] for c in data['checks'])
    assert 'cockpit_url' in data


def test_services_use_a_fixed_list_only(app):
    calls = []

    def fake_run(args, **kw):
        calls.append(args)
        return type('R', (), {'stdout': 'active\n'})()

    with (
        patch('app.services.server_monitor.shutil.which', return_value='/bin/systemctl'),
        patch('app.services.server_monitor.subprocess.run', side_effect=fake_run),
    ):
        out = server_monitor.services()
    assert all(a[:2] == ['/bin/systemctl', 'is-active'] and a[2] in server_monitor.SERVICES for a in calls)
    assert all(s['state'] == 'active' for s in out)


def test_record_and_history(client, app):
    with (
        patch.object(server_monitor, 'cpu_percent', return_value=40.0),
        patch.object(server_monitor, 'services', return_value=[{'unit': 'nginx', 'label': 'x', 'state': 'failed'}]),
    ):
        server_monitor.record()
    snaps = client.get('/api/server-monitor/history?hours=1', headers=_h('admin')).get_json()['snapshots']
    assert snaps and snaps[-1]['cpu_pct'] == 40.0 and snaps[-1]['services_down'] == ['nginx']
