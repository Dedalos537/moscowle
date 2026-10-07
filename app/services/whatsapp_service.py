"""WhatsApp por Baileys: conexion con WhatsApp Web desde el numero del centro.

Se escanea un QR una vez y la sesion queda en disco. A partir de ahi el puente
arranca solo con el servicio.

Lo que cambia respecto a la version anterior:

  - Los envios esperan confirmacion. Antes `send_message` devolvia
    `{'sent': True}` nada mas escribir en stdin, asi que el log de cobranza
    marcaba como enviado un mensaje que quizas nunca salio.
  - `.start()` ahora se llama de verdad al crear la app, asi que el puente
    existe y no cae siempre al link de wa.me.
  - `connected_phone` expone de que numero sale la comunicacion, que es la
    pregunta que hay que poder responder.
  - Reintenta solo ante caidas de red. Si WhatsApp revoca la sesion para y
    avisa, en vez de martillear la API.
"""

import atexit
import contextlib
import fcntl
import json
import logging
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time

logger = logging.getLogger(__name__)

BRIDGE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'whatsapp_bridge'))
PID_FILE = os.path.join(BRIDGE_DIR, '.bridge.pid')
SESSION_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'whatsapp_sessions'))

# Baileys reporta los errores de envio en su mayoria como codigo numerico.
# Estos dos son los que un humano tiene que entender.
_FRIENDLY = {
    'wa_401': 'WhatsApp cerrado: el contacto no te tiene en su lista',
    'wa_403': 'WhatsApp rechazo el envio',
    'wa_404': 'WhatsApp no tiene ese numero',
    'wa_429': 'WhatsApp pidio parar: se mando demasiado rapido',
    'wa_500': 'WhatsApp fallo por su lado',
    'lid_sin_telefono': 'WhatsApp no revela el telefono de este contacto, asi que no se le pudo escribir. Contestale desde el celular del centro',
    'timeout': 'WhatsApp no confirmo el envio a tiempo',
}


def _node_bin():
    """Ubica el binario de node.

    node suele vivir en nvm, que no esta en el PATH de los servicios de
    systemd, asi que buscarlo con shutil.which no alcanza: se recorre
    ~/.nvm y /usr/local por si acaso.
    """
    found = shutil.which('node')
    if found:
        return found

    candidates = []
    nvm_dir = os.environ.get('NVM_DIR') or os.path.expanduser('~/.nvm')
    versions = os.path.join(nvm_dir, 'versions', 'node')
    if os.path.isdir(versions):
        for name in sorted(os.listdir(versions), reverse=True):
            candidates.append(os.path.join(versions, name, 'bin', 'node'))
    candidates += ['/usr/local/bin/node', '/usr/bin/node']

    for path in candidates:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    return None


def _pid_alive(pid):
    try:
        os.kill(pid, 0)
    except (OSError, ValueError):
        return False
    return True


def _ppid_of(pid):
    """PPID de un proceso, o None si no se puede leer."""
    try:
        with open(f'/proc/{pid}/stat') as fh:
            # El campo comm puede traer espacios y parentesis: se corta desde
            # el ultimo parentesis para no desplazar los campos.
            tail = fh.read().rsplit(')', 1)[1].split()
            return int(tail[1])
    except (OSError, ValueError, IndexError):
        return None


LOCK_FILE = os.path.join(BRIDGE_DIR, '.bridge.lock')
LOCK_RETRY_SECONDS = int(os.environ.get('WHATSAPP_LOCK_RETRY_SECONDS', '30'))


def _pids_running_bridge():
    """PIDs de procesos que ejecutan el puente de este directorio.

    Se mira el cwd real en vez del nombre del comando: dos workers de
    gunicorn ejecutan exactamente lo mismo y el nombre no los distingue.
    """
    if not os.path.isdir('/proc'):
        return []
    found = []
    for name in os.listdir('/proc'):
        if not name.isdigit():
            continue
        pid = int(name)
        if pid == os.getpid():
            continue
        try:
            if os.readlink(f'/proc/{pid}/cwd') != BRIDGE_DIR:
                continue
            with open(f'/proc/{pid}/cmdline', 'rb') as fh:
                cmd = fh.read().replace(b'\\0', b' ').decode('utf-8', 'replace')
        except OSError:
            continue
        if 'index.js' in cmd:
            found.append(pid)
    return found


def _kill_bridge_pids(pids):
    for pid in pids:
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            continue
        for _ in range(30):
            if not _pid_alive(pid):
                break
            time.sleep(0.1)
        if _pid_alive(pid):
            with contextlib.suppress(OSError):
                os.kill(pid, signal.SIGKILL)
        logger.warning('Puente de WhatsApp duplicado (%s) terminado', pid)


def _autostart_allowed():
    """Arranca solo en el servidor.

    create_app corre en tests, en scripts de diagnostico y en el worker de
    gunicorn. Si todos levantaran un puente, cada uno usaria las mismas
    credenciales y WhatsApp los expulsaria en cadena (440 connectionReplaced):
    la sesion nunca quedaria conectada. Fuera del servidor no hace falta
    ningun puente, asi que no se arranca.
    """
    flag = os.environ.get('WHATSAPP_AUTOSTART', '').strip().lower()
    if flag in ('1', 'true', 'yes', 'on'):
        return True
    if flag in ('0', 'false', 'no', 'off'):
        return False
    argv0 = os.path.basename(sys.argv[0] or '').lower()
    return 'gunicorn' in argv0 or argv0 in ('uwsgi', 'waitress-serve')


class WhatsAppBridgeError(RuntimeError):
    """Fallo enviando por WhatsApp. El motivo ya viene en castellano."""


class WhatsAppService:
    """Cliente del puente Baileys."""

    def __init__(self):
        self._process = None
        self._lock = threading.Lock()
        self._lock_fd = None
        self._retrying = False
        self._ready = threading.Event()
        self._needs_qr = False
        self._incoming_handler = None
        self._banned = False
        self.connected = False
        self.connected_phone = None
        self.connected_jid = None
        self.qr_code = None
        self.last_error = None
        self.started_at = None
        # Envios en vuelo: ref -> (evento, resultado). El hilo de stdout
        # resuelve el que corresponda con la respuesta.
        self._pending = {}
        self._seq = 0

    # ---------------------------------------------------------------- ciclo

    def _retry_start(self):
        """Vuelve a intentar spawneear hasta que el lock este libre."""
        if self._retrying:
            return
        self._retrying = True

        def _run():
            deadline = time.time() + LOCK_RETRY_SECONDS
            try:
                while time.time() < deadline:
                    if self.start():
                        return
                    time.sleep(1.0)
                logger.error('Se agoto la espera del lock del puente de WhatsApp')
            finally:
                self._retrying = False

        threading.Thread(target=_run, daemon=True).start()

    def _acquire_lock(self):
        """Toma el lock del directorio del puente.

        Es un flock: si el proceso muere sin liberarlo el kernel lo suelta
        solo, asi que no queda un lock viciado tras un HUP. Devuelve False si
        otro proceso lo tiene ya.
        """
        if self._lock_fd is not None:
            return True
        try:
            fd = os.open(LOCK_FILE, os.O_RDWR | os.O_CREAT, 0o644)
        except OSError as e:
            logger.warning('No se pudo abrir %s: %s', LOCK_FILE, e)
            return False
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            os.close(fd)
            return False
        self._lock_fd = fd
        return True

    def _release_lock(self):
        fd, self._lock_fd = self._lock_fd, None
        if fd is None:
            return
        with contextlib.suppress(OSError):
            fcntl.flock(fd, fcntl.LOCK_UN)
        with contextlib.suppress(OSError):
            os.close(fd)

    def start(self):
        """Arranca el puente. Devuelve True si el proceso levanto."""
        if self._process and self._process.poll() is None:
            return True

        if not _autostart_allowed():
            logger.info('Puente de WhatsApp no arrancado fuera del servidor')
            return False

        main_js = os.path.join(BRIDGE_DIR, 'index.js')
        if not os.path.exists(main_js):
            logger.warning('Puente de WhatsApp no encontrado en %s', BRIDGE_DIR)
            return False

        node = _node_bin()
        if not node:
            logger.error('Node.js no esta instalado, WhatsApp no puede funcionar')
            return False

        # Un solo puente por sesion. Dos procesos usando las mismas credenciales
        # hacen que WhatsApp expulse al primero (440 connectionReplaced) en un
        # bucle: por eso la cuenta nunca quedaba conectada.
        if not self._acquire_lock():
            # Al hacer HUP el worker nuevo arranca mientras el viejo aun vive
            # y conserva el lock. Si desistimos, no queda ningun puente en pie
            # cuando el viejo muera, asi que reintentamos hasta que lo suelte.
            logger.warning('Otro proceso ya tiene el puente de WhatsApp, reintento en %ss', LOCK_RETRY_SECONDS)
            self._retry_start()
            return False

        _kill_bridge_pids(_pids_running_bridge())

        try:
            self._process = subprocess.Popen(  # noqa: S603 - node y args fijos
                [node, 'index.js'],
                cwd=BRIDGE_DIR,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                env={**os.environ, 'BRIDGE_LOG_LEVEL': os.environ.get('BRIDGE_LOG_LEVEL', 'warn')},
            )
        except FileNotFoundError:
            logger.error('No se pudo ejecutar node en %s', node)
            self._release_lock()
            return False

        try:
            with open(PID_FILE, 'w') as fh:
                fh.write(str(self._process.pid))
        except OSError as e:
            logger.warning('No se pudo escribir %s: %s', PID_FILE, e)

        # Si el worker muere sin poder limpiar (HUP, SIGTERM), el hijo se va a
        # quedar huerfano y a pelear con el siguiente. El atexit lo cierra.
        atexit.register(self._terminate_bridge)

        self.started_at = time.time()
        self._needs_qr = False
        self._banned = False
        threading.Thread(target=self._read_stdout, daemon=True).start()
        threading.Thread(target=self._drain_stderr, daemon=True).start()
        return True

    def _terminate_bridge(self):
        """Cierra el puente propio sin mandar 'logout' (no hay stdin garantizado)."""
        proc = self._process
        if not proc or proc.poll() is not None:
            return
        try:
            os.kill(proc.pid, signal.SIGTERM)
        except OSError:
            return
        for _ in range(30):
            if proc.poll() is not None:
                break
            time.sleep(0.1)
        if proc.poll() is None:
            with contextlib.suppress(OSError):
                os.kill(proc.pid, signal.SIGKILL)

    def stop(self):
        if self._process and self._process.poll() is None:
            with contextlib.suppress(Exception):
                self._write({'type': 'logout'})
            try:
                self._process.terminate()
                self._process.wait(timeout=10)
            except Exception:
                with contextlib.suppress(Exception):
                    self._process.kill()
        self._process = None
        self._release_lock()
        self._reset_state()

    def _reset_state(self):
        self.connected = False
        self.connected_phone = None
        self.connected_jid = None
        self.qr_code = None
        self._ready.clear()
        self._fail_pending('WhatsApp se desconecto')

    def _fail_pending(self, error):
        for _ref, (event, box) in list(self._pending.items()):
            box['error'] = error
            event.set()
        self._pending.clear()

    # ------------------------------------------------------------- lectura

    def _read_stdout(self):
        proc = self._process
        if not proc or not proc.stdout:
            return
        for raw_line in proc.stdout:
            line = raw_line.strip()
            if not line:
                continue
            try:
                self._handle(json.loads(line))
            except json.JSONDecodeError:
                logger.debug('Linea no JSON del puente de WhatsApp: %s', line[:120])

    def _drain_stderr(self):
        proc = self._process
        if not proc or not proc.stderr:
            return
        for line in proc.stderr:
            # stderr trae los logs de pino. El puente corre en nivel warn,
            # asi que solo llegan avisos y errores: es el unico lugar donde
            # se ve por que se cae la sesion, asi que van a info.
            (logger.warning if ('[wa-upsert]' in line or '[wa-lid]' in line) else logger.info)(
                '[baileys] %s', line.rstrip()
            )

    def _handle(self, msg):
        kind = msg.get('type')

        if kind == 'qr':
            self.qr_code = msg.get('qr')
            self.connected = False
            self._ready.clear()

        elif kind == 'ready':
            self.connected = True
            self.qr_code = None
            self._needs_qr = False
            self.connected_jid = msg.get('jid')
            # El jid trae el indice de dispositivo (51974651682:2). El telefono
            # que se muestra y con el que se envia no lo lleva.
            self.connected_phone = self.normalize_phone(str(msg.get('phone') or '').split(':')[0])
            self.last_error = None
            self._ready.set()
            logger.info('WhatsApp conectado como %s', self.connected_phone)

        elif kind == 'incoming':
            logger.warning('WhatsApp: mensaje entrante recibido del puente (lid=%s)', bool(msg.get('lid')))
            handler = self._incoming_handler
            if handler:
                try:
                    handler(msg)
                except Exception:
                    logger.exception('Falló el procesamiento de un mensaje entrante de WhatsApp')

        elif kind == 'send_result':
            ref = msg.get('ref')
            entry = self._pending.get(ref) if ref else None
            if entry:
                event, box = entry
                box['result'] = msg
                event.set()
                self._pending.pop(ref, None)

        elif kind in ('disconnected', 'reconnecting'):
            self.connected = False
            self._ready.clear()
            # El codigo de desconexion explica por que se cayo: 401 es que
            # WhatsApp nos expulso, 408 timeout, 440 reemplazado, 515 reinicio.
            if kind == 'disconnected':
                logger.warning(
                    'WhatsApp desconectado (reason=%s logged_out=%s banned=%s)',
                    msg.get('reason'),
                    msg.get('logged_out'),
                    msg.get('banned'),
                )
            self._fail_pending('WhatsApp se desconecto, reintentando')

        elif kind == 'needs_qr':
            self._needs_qr = True
            self._banned = bool(msg.get('banned'))
            self.connected = False
            self._ready.clear()
            self.last_error = (
                'WhatsApp baneo este numero' if self._banned else 'Hay que volver a escanear el QR de WhatsApp'
            )
            self._fail_pending(self.last_error)
            logger.error('Puente de WhatsApp: %s', self.last_error)

        elif kind in ('error', 'fatal'):
            self.last_error = msg.get('message')
            logger.error('Error del puente de WhatsApp: %s', self.last_error)
            if kind == 'fatal':
                self._reset_state()

    # --------------------------------------------------------------- envio

    def _write(self, payload):
        if not self._process or self._process.poll() is not None:
            raise WhatsAppBridgeError('El puente de WhatsApp no esta corriendo')
        try:
            self._process.stdin.write(json.dumps(payload) + '\n')
            self._process.stdin.flush()
        except (BrokenPipeError, ValueError) as exc:
            raise WhatsAppBridgeError('El puente de WhatsApp no responde') from exc

    def send_typing(self, phone, lid=False, state='composing'):
        """«Escribiendo…» en el chat de la persona. Mejor esfuerzo: nunca lanza."""
        try:
            if self.connected:
                self._write(
                    {'type': 'presence', 'phone': re.sub(r'\D', '', str(phone or '')), 'lid': bool(lid), 'state': state}
                )
        except Exception:
            logger.debug('No se pudo enviar el indicador de escritura', exc_info=True)

    def send_message(self, phone, message, timeout=35, lid=False):
        """Envia y espera confirmacion. Devuelve dict con provider_message_id.

        Lanza WhatsAppBridgeError si no sale. No devuelve 'sent: True'
        mientras no haya confirmacion: un log que dice enviado y no se
        envio es peor que no tener log.
        """
        digits = re.sub(r'\D', '', str(phone or ''))
        if not digits:
            raise WhatsAppBridgeError('El numero esta vacio')

        if self._banned:
            raise WhatsAppBridgeError('WhatsApp baneo este numero, hay que parar los envios')
        if self._needs_qr:
            raise WhatsAppBridgeError('Hay que volver a escanear el QR de WhatsApp')
        if not self.connected:
            self.start()
            if not self._ready.wait(timeout=10):
                raise WhatsAppBridgeError(self.last_error or 'WhatsApp no esta conectado todavia')

        with self._lock:
            self._seq += 1
            ref = f'ref{self._seq}'
            event = threading.Event()
            box = {}
            self._pending[ref] = (event, box)

        try:
            self._write({'type': 'send', 'ref': ref, 'phone': digits, 'message': message, 'lid': bool(lid)})
        except WhatsAppBridgeError:
            self._pending.pop(ref, None)
            raise

        if not event.wait(timeout=timeout):
            self._pending.pop(ref, None)
            raise WhatsAppBridgeError('WhatsApp no respondio a tiempo')

        result = box.get('result') or {}
        if box.get('error') or not result.get('ok'):
            raise WhatsAppBridgeError(
                _FRIENDLY.get(result.get('error'), result.get('error') or box.get('error') or 'fallo desconocido')
            )

        return {
            'sent': True,
            'method': 'baileys',
            'to': digits,
            'provider_message_id': result.get('provider_message_id'),
        }

    # ------------------------------------------------------------- estado

    @property
    def is_connected(self):
        return bool(self.connected)

    @property
    def needs_qr(self):
        return self._needs_qr

    @property
    def is_banned(self):
        return self._banned

    def status(self):
        """Estado para la pantalla de configuracion y para la IA."""
        return {
            'connected': bool(self.connected),
            'needs_qr': self._needs_qr,
            'banned': self._banned,
            'phone': self.connected_phone,
            'jid': self.connected_jid,
            'has_qr': bool(self.qr_code),
            'running': bool(self._process and self._process.poll() is None),
            'last_error': self.last_error,
            'uptime_s': int(time.time() - self.started_at) if self.started_at else 0,
        }

    def set_incoming_handler(self, handler):
        """Función que recibe cada mensaje entrante (dict del puente). Se ejecuta en el hilo lector del puente."""
        self._incoming_handler = handler

    @staticmethod
    def normalize_phone(phone):
        """Numero peruano en formato internacional, sin signos."""
        digits = re.sub(r'\D', '', str(phone or ''))
        if digits.startswith('0'):
            digits = '51' + digits[1:]
        if digits and not digits.startswith('51'):
            digits = '51' + digits
        return digits


whatsapp_service = WhatsAppService()
