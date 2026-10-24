"""PRP 014: servicios del host y la Epson encontrados por quiénes son, no por una IP fija."""

import importlib.util
import json
import uuid
from pathlib import Path

import pytest

from app.extensions import db
from app.models import User
from app.services import scan_service, server_monitor

DAEMON = Path(__file__).resolve().parents[1] / 'deploy' / 'scanner' / 'moscowle_scand.py'


@pytest.fixture
def scand(tmp_path, monkeypatch):
    monkeypatch.setenv('SCAND_STATE_DIR', str(tmp_path))
    monkeypatch.delenv('STATE_DIRECTORY', raising=False)
    spec = importlib.util.spec_from_file_location('scand_test', DAEMON)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_discover_prefers_mdns_and_skips_other_epson_by_mac(scand, monkeypatch):
    scand._save_identity({'mac': 'aa:aa:aa:aa:aa:aa'})
    monkeypatch.setattr(
        scand,
        '_mdns_epsons',
        lambda: [('EPSON vecino', 'EPSONX.local', '192.168.1.50'), ('EPSON L4150', 'EPSON1.local', '192.168.1.40')],
    )
    monkeypatch.setattr(
        scand, '_mac_of', lambda ip: {'192.168.1.50': 'bb:bb:bb:bb:bb:bb', '192.168.1.40': 'aa:aa:aa:aa:aa:aa'}[ip]
    )
    found = scand.discover()
    assert found['ip'] == '192.168.1.40' and found['mdns'] == 'EPSON1.local' and found['via'] == 'mdns'


def test_discover_by_mac_when_mdns_is_silent(scand, monkeypatch):
    scand._save_identity({'mac': 'aa:aa:aa:aa:aa:aa'})
    monkeypatch.setattr(scand, '_mdns_epsons', lambda: [])
    monkeypatch.setattr(scand, '_sweep_9100', lambda: ['192.168.1.20', '192.168.1.77'])
    monkeypatch.setattr(
        scand, '_mac_of', lambda ip: 'aa:aa:aa:aa:aa:aa' if ip == '192.168.1.77' else 'cc:cc:cc:cc:cc:cc'
    )
    assert scand.discover()['ip'] == '192.168.1.77'


def test_repair_points_cups_by_name_and_records_change(scand, monkeypatch):
    scand._save_identity({'mac': 'aa:aa:aa:aa:aa:aa', 'ip': '192.168.1.233'})
    uri = {'v': 'socket://192.168.1.233:9100'}
    monkeypatch.setattr(scand, 'printer_uri', lambda: uri['v'])
    monkeypatch.setattr(scand, '_reachable', lambda host, port=9100, timeout=3: host != '192.168.1.233')
    monkeypatch.setattr(scand, '_mdns_epsons', lambda: [('EPSON L4150', 'EPSON1.local', '192.168.1.40')])
    monkeypatch.setattr(scand, '_mac_of', lambda ip: 'aa:aa:aa:aa:aa:aa')
    monkeypatch.setattr(scand, '_resolves', lambda host: True)
    monkeypatch.setattr(scand, '_point_cups', lambda new: uri.update(v=new))
    out = scand.repair_printer()
    assert uri['v'] == 'socket://EPSON1.local:9100'
    assert out['changed'] and 'EPSON1.local' in out['message']
    ident = json.loads((Path(scand.IDENTITY_FILE)).read_text())
    assert ident['last_change']['from'] == '192.168.1.233' and ident['last_change']['to'] == '192.168.1.40'


def test_links_follow_the_current_ip(app, monkeypatch):
    monkeypatch.setattr(
        scan_service,
        'where',
        lambda force=False: {
            'host': {'lan_ip': '192.168.1.6', 'mdns': 'moscowle.local'},
            'services': {'cockpit': {'up': True}},
        },
    )
    with app.test_request_context():
        links = {link['id']: link for link in server_monitor.infra_links()}
    assert (
        links['cockpit']['url'] == 'https://192.168.1.6:9090/'
        and links['cockpit']['alt'] == 'https://moscowle.local:9090/'
    )
    assert links['prometheus']['url'] == 'http://192.168.1.6:3000/explore'  # Prometheus va por Grafana (con login)
    assert links['app']['url'] == 'http://192.168.1.6/app/'


def test_links_fall_back_to_mdns_name_when_host_is_silent(app, monkeypatch):
    monkeypatch.setattr(scan_service, 'where', lambda force=False: None)
    with app.test_request_context():
        links = {link['id']: link for link in server_monitor.infra_links()}
    assert links['grafana']['url'] == 'http://moscowle.local:3000/' and links['grafana']['alt'] is None


def test_printer_notices_go_out_once(app, monkeypatch):
    tag = uuid.uuid4().hex[:6]
    db.session.add(User(username=f'adm{tag}', email=f'{tag}@gmail.com', password='x', role='admin'))
    db.session.commit()
    sent = []
    monkeypatch.setattr(scan_service, 'configured', lambda: True)
    monkeypatch.setattr(scan_service, '_notify_admins', lambda title, message, priority: sent.append(title))
    state = {'reachable': True, 'last_change': {'from': '1.1.1.1', 'to': '1.1.1.2', 'at': 123.0 + len(tag)}}
    monkeypatch.setattr(scan_service, 'printer_state', lambda: state)
    scan_service.check_printer()
    scan_service.check_printer()
    assert sent == ['La impresora cambió de IP']
    state['reachable'] = False
    scan_service.check_printer()
    scan_service.check_printer()
    assert sent.count('La impresora no está en la red') == 1


def test_repair_uses_usb_when_epson_left_the_wifi(scand, monkeypatch):
    usb = 'usb://EPSON/L4150%20Series?serial=X123'
    pointed = []
    monkeypatch.setattr(scand, 'printer_uri', lambda: pointed[-1] if pointed else 'socket://192.168.1.50:9100')
    monkeypatch.setattr(scand, '_reachable', lambda *a, **k: False)
    monkeypatch.setattr(scand, 'discover', lambda: None)
    monkeypatch.setattr(scand, '_mdns_epsons', lambda: [])
    monkeypatch.setattr(scand, '_usb_epson', lambda: usb)
    monkeypatch.setattr(scand, '_point_cups', pointed.append)
    res = scand.repair_printer()
    assert pointed == [usb] and res['usb'] and res['reachable'] and 'USB' in res['message']
