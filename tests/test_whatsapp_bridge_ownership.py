"""Reglas de propiedad del puente de WhatsApp.

Solo debe haber un proceso con las credenciales de la cuenta abiertas a la
vez: con dos, WhatsApp expulsa al primero (440 connectionReplaced) y la
sesion nunca queda conectada.
"""

import os
import subprocess
import time

import pytest

from app.services import whatsapp_service as ws


def _write_pid_file(pid):
    with open(ws.PID_FILE, 'w') as fh:
        fh.write(str(pid))


# ---------------------------------------------------------------- autostart


def test_no_autostart_en_contextos_que_no_son_el_servidor(monkeypatch):
    """Tests y scripts de diagnostico no deben levantar un puente.

    Cada create_app() llamado desde un script abria la misma sesion de
    WhatsApp y echaba a la del servidor.
    """
    monkeypatch.delenv('WHATSAPP_AUTOSTART', raising=False)
    monkeypatch.setattr(ws.sys, 'argv', ['pytest', 'tests/'])
    assert ws._autostart_allowed() is False

    monkeypatch.setattr(ws.sys, 'argv', ['/tmp/mktok.py'])
    assert ws._autostart_allowed() is False


def test_autostart_si_estamos_en_gunicorn(monkeypatch):
    monkeypatch.delenv('WHATSAPP_AUTOSTART', raising=False)
    monkeypatch.setattr(ws.sys, 'argv', ['/venv/bin/gunicorn', 'server_ubuntu:app'])
    assert ws._autostart_allowed() is True


def test_autostart_se_puede_fuerzar_desde_el_entorno(monkeypatch):
    monkeypatch.setenv('WHATSAPP_AUTOSTART', '1')
    monkeypatch.setattr(ws.sys, 'argv', ['/tmp/script.py'])
    assert ws._autostart_allowed() is True

    monkeypatch.setenv('WHATSAPP_AUTOSTART', '0')
    monkeypatch.setattr(ws.sys, 'argv', ['/venv/bin/gunicorn', 'server_ubuntu:app'])
    assert ws._autostart_allowed() is False


def test_start_no_spawnea_fuera_del_servidor(monkeypatch):
    monkeypatch.setenv('WHATSAPP_AUTOSTART', '0')
    svc = ws.WhatsAppService()
    assert svc.start() is False
    assert svc._process is None


# ----------------------------------------------------------------- el lock


def _fork_lock_owner():
    """Lanza un hijo que toma el lock y avisa por pipe cuando lo tiene.

    Sin ese sincronismo el padre correria antes que el hijo y ganaria el
    lock por casualidad, lo que haria fallar el test de exclusion.
    """
    ready, ready_w = os.pipe()
    pid = os.fork()
    if pid == 0:
        os.close(ready)
        child = ws.WhatsAppService()
        ok = child._acquire_lock()
        try:
            os.write(ready_w, b'1' if ok else b'0')
            if ok:
                # muere sin pasar por _release_lock
                os._exit(0)
            os._exit(1)
        finally:
            os._exit(1)
    os.close(ready_w)
    got = os.read(ready, 1)
    os.close(ready)
    return pid, got == b'1'


def test_lock_unico_entre_dos_procesos():
    """Dos procesos no pueden poseer el puente a la vez."""
    pid, child_got = _fork_lock_owner()
    try:
        assert child_got, 'el hijo debia poder tomar el lock'
        parent = ws.WhatsAppService()
        assert parent._acquire_lock() is False
    finally:
        os.waitpid(pid, 0)


def test_lock_se_libera_solo_al_mor_el_proceso():
    """Un flock no queda viciado si el proceso muere sin liberarlo."""
    pid, child_got = _fork_lock_owner()
    assert child_got
    _, status = os.waitpid(pid, 0)
    assert os.WEXITSTATUS(status) == 0

    parent = ws.WhatsAppService()
    assert parent._acquire_lock() is True
    parent._release_lock()


def test_lock_reentrant_en_el_mismo_proceso():
    svc = ws.WhatsAppService()
    try:
        assert svc._acquire_lock() is True
        assert svc._acquire_lock() is True
    finally:
        svc._release_lock()
    assert svc._lock_fd is None


# --------------------------------------------------------- puentes dobles


def test_pids_running_bridge_detecta_solo_los_de_este_directorio(tmp_path):
    fake = tmp_path / 'otro'
    fake.mkdir()
    (fake / 'index.js').write_text('// nada')
    intruso = subprocess.Popen(['sleep', '30'], cwd=str(fake))

    try:
        pids = ws._pids_running_bridge()
        assert intruso.pid not in pids
    finally:
        intruso.kill()
        intruso.wait()


def test_kill_bridge_pids_termina_los_duplicados(tmp_path):
    fake = os.path.join(str(tmp_path), 'puente')
    os.makedirs(fake, exist_ok=True)
    with open(os.path.join(fake, 'index.js'), 'w') as fh:
        fh.write('// nada')
    p = subprocess.Popen(['sleep', '30'], cwd=fake)

    try:
        ws._kill_bridge_pids([p.pid])
        assert p.poll() is not None
    finally:
        if p.poll() is None:
            p.kill()
            p.wait()


def test_kill_bridge_pids_con_pid_inexistente_no_explota():
    assert ws._kill_bridge_pids([2**22 + 7]) is None


# ---------------------------------------------------------------- pid file


def test_write_pid_file(monkeypatch, tmp_path):
    pid_file = tmp_path / 'bridge.pid'
    monkeypatch.setattr(ws, 'PID_FILE', str(pid_file))
    _write_pid_file(1234)
    assert pid_file.read_text().strip() == '1234'


@pytest.mark.parametrize('raw', ['', 'no-numero', '\n  \n'])
def test_pid_file_vacio_o_corrupto(monkeypatch, tmp_path, raw):
    pid_file = tmp_path / 'bridge.pid'
    monkeypatch.setattr(ws, 'PID_FILE', str(pid_file))
    pid_file.write_text(raw)
    # sin pid valido no hay nada que matar
    assert ws._kill_bridge_pids([]) is None


# ------------------------------------------------------------- reintento


def test_retry_start_no_lanza_hilos_si_ya_esta_intentando(monkeypatch):
    """Un solo hilo de reintento: si no, dos workers se pisarian."""
    svc = ws.WhatsAppService()
    svc._retrying = True
    llamadas = []
    monkeypatch.setattr(svc, 'start', lambda: llamadas.append(1))
    svc._retry_start()
    assert llamadas == []


def test_retry_start_libera_la_bandera_al_terminar(monkeypatch):
    svc = ws.WhatsAppService()
    monkeypatch.setattr(ws, 'LOCK_RETRY_SECONDS', 0)
    monkeypatch.setattr(svc, 'start', lambda: False)
    svc._retry_start()
    # el hilo se lanza daemon y termina enseguida con 0 segundos de espera
    for _ in range(50):
        if not svc._retrying:
            break
        time.sleep(0.05)
    assert svc._retrying is False


def test_start_reintenta_si_alguien_tiene_el_lock(monkeypatch):
    """Con el lock ocupado no se spawnea, pero si se programa el reintento."""
    svc = ws.WhatsAppService()
    monkeypatch.setenv('WHATSAPP_AUTOSTART', '1')
    monkeypatch.setattr(svc, '_acquire_lock', lambda: False)
    llamadas = []
    monkeypatch.setattr(svc, '_retry_start', lambda: llamadas.append(1))
    assert svc.start() is False
    assert llamadas == [1]
    assert svc._process is None
