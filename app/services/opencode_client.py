"""Cliente mínimo de `opencode serve` (PRP 009).

Dos instancias en VM-APP, cada una con su usuario del sistema:

- `chat` (`OPENCODE_URL`, 127.0.0.1:4096): cerebro del asistente. Su carpeta solo tiene `AGENTS.md`; el usuario
  `opencode` no puede leer el repo, la base ni el `.env`. Cualquier pedido de permiso de sus herramientas de
  código se rechaza.
- `dev` (`OPENCODE_DEV_URL`, 127.0.0.1:4097): modo desarrollador del admin. Lee el repo en solo lectura y los logs;
  solo se aprueban (una vez) los comandos de la lista blanca de `DEV_ALLOWED_COMMANDS`.

OpenCode corre tal como viene (el nivel gratis de MiMo rechaza agentes y configuraciones propias): la seguridad
la ponen el sistema operativo (systemd endurecido, usuarios sin sudo) y este cliente, que solo llama a las rutas
de la lista blanca. `/session/:id/shell`, `/command`, `/config` y `/auth` no se pueden llamar.

Cuota agotada, 403 del nivel gratis, 5xx o timeout → `OpencodeUnavailableError` y la instancia queda en pausa:
el asistente cae a la cadena actual hasta que vuelva.
"""

import contextlib
import logging
import os
import re
import threading
import time

import requests

logger = logging.getLogger(__name__)

PROVIDER_ID = 'opencode'
MODEL_ID = 'mimo-v2.6-flash-free'
COOLDOWN = 15 * 60
QUOTA_COOLDOWN = 60 * 60

_ENV = {'chat': ('OPENCODE_URL', 'OPENCODE_PASSWORD'), 'dev': ('OPENCODE_DEV_URL', 'OPENCODE_DEV_PASSWORD')}

_ALLOWED = (
    ('POST', re.compile(r'^/session$')),
    ('POST', re.compile(r'^/session/ses_[\w-]+/message$')),
    ('POST', re.compile(r'^/session/ses_[\w-]+/abort$')),
    ('DELETE', re.compile(r'^/session/ses_[\w-]+$')),
    ('GET', re.compile(r'^/permission$')),
    ('POST', re.compile(r'^/permission/per_[\w-]+/reply$')),
    ('GET', re.compile(r'^/doc$')),
)

# Modo desarrollador: comandos de solo lectura que se aprueban si OpenCode pide permiso.
DEV_ALLOWED_COMMANDS = (
    re.compile(
        r'^journalctl( -u (moscowle|nginx|cups|opencode-moscowle))?( -n \d+| --since "[^"]+"| --no-pager| -p \w+)*$'
    ),
    re.compile(r'^systemctl status [\w@.-]+( --no-pager)?$'),
    re.compile(r'^git (-C /home/diego/moscowle_ia )?(log|status|show|diff)( [\w./:@^~-]+)*$'),
    re.compile(r'^(df -h|free -m|uptime|nproc|lpstat -[pt])$'),
    re.compile(r'^tail -n \d+ /home/diego/moscowle_ia/logs/[\w.-]+$'),
    re.compile(r'^(rg|grep -rn) [^;&|`$<>]+ (/home/diego/moscowle_ia/)?(app|edysync/src|scripts|tests|docs)[\w./-]*$'),
)
_SECRET_RE = re.compile(r'\.env|\.pem|id_rsa|id_ed25519|secret|password|token', re.I)

_state = {name: {'until': 0.0, 'error': ''} for name in _ENV}


class OpencodeUnavailableError(Exception):
    """opencode no está, no responde o se acabó la cuota: usar la cadena actual."""


class OpencodeForbiddenError(Exception):
    """Ruta fuera de la lista blanca."""


def base_url(inst='chat'):
    return (os.environ.get(_ENV[inst][0]) or '').rstrip('/')


def configured(inst='chat'):
    return bool(base_url(inst) and os.environ.get(_ENV[inst][1]))


def blocked(inst='chat'):
    return time.time() < _state[inst]['until']


def block(reason, seconds=COOLDOWN, inst='chat'):
    _state[inst].update(until=time.time() + seconds, error=str(reason)[:300])
    logger.warning('opencode[%s] en pausa %ss: %s', inst, seconds, _state[inst]['error'])


def unblock(inst='chat'):
    _state[inst]['until'] = 0.0


def state(inst='chat'):
    return {
        'configured': configured(inst),
        'blocked': blocked(inst),
        'blocked_for': max(0, int(_state[inst]['until'] - time.time())),
        'last_error': _state[inst]['error'],
        'model': f'{PROVIDER_ID}/{MODEL_ID}',
    }


def _request(method, path, *, json_body=None, timeout=60, inst='chat', check_block=True):
    if not any(m == method and rx.match(path) for m, rx in _ALLOWED):
        raise OpencodeForbiddenError(f'{method} {path}')
    if not configured(inst):
        raise OpencodeUnavailableError(f'opencode[{inst}] no está configurado')
    if check_block and blocked(inst):
        raise OpencodeUnavailableError(f'opencode[{inst}] en pausa: {_state[inst]["error"]}')
    try:
        resp = requests.request(
            method,
            base_url(inst) + path,
            json=json_body,
            auth=('opencode', os.environ[_ENV[inst][1]]),
            timeout=(1.5, timeout),
        )
    except requests.RequestException as exc:
        block(exc, inst=inst)
        raise OpencodeUnavailableError(str(exc)) from exc
    if resp.status_code >= 500 or resp.status_code in (401, 403, 429):
        block(f'HTTP {resp.status_code}', inst=inst)
        raise OpencodeUnavailableError(f'HTTP {resp.status_code}')
    if resp.status_code >= 400:
        raise OpencodeUnavailableError(f'HTTP {resp.status_code}: {resp.text[:200]}')
    return resp.json() if resp.content else {}


def ping(inst='chat'):
    try:
        _request('GET', '/doc', timeout=5, inst=inst, check_block=False)
        return True
    except (OpencodeUnavailableError, ValueError):
        return False


def create_session(title, inst='chat'):
    return _request('POST', '/session', json_body={'title': title[:80]}, timeout=10, inst=inst)['id']


def delete_session(session_id, inst='chat'):
    with contextlib.suppress(OpencodeUnavailableError, OpencodeForbiddenError):
        _request('DELETE', f'/session/{session_id}', timeout=10, inst=inst, check_block=False)


def dev_command_allowed(command):
    cmd = ' '.join((command or '').split())
    if not cmd or _SECRET_RE.search(cmd):
        return False
    return any(rx.match(cmd) for rx in DEV_ALLOWED_COMMANDS)


def _decide(req, inst):
    """`reject` siempre en `chat`; en `dev`, `once` solo para comandos de solo lectura de la lista blanca."""
    if inst != 'dev':
        return 'reject'
    perm = req.get('permission') or ''
    patterns = req.get('patterns') or []
    if perm == 'bash' and patterns and all(dev_command_allowed(p) for p in patterns):
        return 'once'
    if perm in ('read', 'grep', 'glob', 'list') and patterns and not any(_SECRET_RE.search(p) for p in patterns):
        return 'once'
    return 'reject'


def _answer_permissions(inst, log=None):
    try:
        for req in _request('GET', '/permission', timeout=5, inst=inst, check_block=False) or []:
            rid = req.get('id') if isinstance(req, dict) else None
            if not rid:
                continue
            reply = _decide(req, inst)
            _request('POST', f'/permission/{rid}/reply', json_body={'reply': reply}, timeout=5, inst=inst)
            if log is not None:
                log.append({'permission': req.get('permission'), 'patterns': req.get('patterns'), 'reply': reply})
    except (OpencodeUnavailableError, OpencodeForbiddenError, ValueError):
        pass


def _model_error(info):
    err = (info or {}).get('error') or {}
    data = err.get('data') or {}
    return data.get('message') or err.get('name') or ''


def send(session_id, text, images=(), timeout=90, inst='chat'):
    """Manda un mensaje y devuelve `{'text', 'tools', 'tokens', 'permissions'}`. Imágenes como data URL."""
    parts = [{'type': 'text', 'text': text}]
    for img in images or ():
        parts.append(
            {'type': 'file', 'mime': img['mime'], 'filename': img.get('filename', 'imagen'), 'url': img['url']}
        )
    body = {'model': {'providerID': PROVIDER_ID, 'modelID': MODEL_ID}, 'parts': parts}

    # Si OpenCode pide permiso para una herramienta, el mensaje se queda esperando: un vigilante responde
    # mientras tanto (con eventlet es un greenlet).
    done = threading.Event()
    perms: list = []

    def _watch():
        while not done.wait(1.0):
            _answer_permissions(inst, perms)

    threading.Thread(target=_watch, daemon=True).start()
    try:
        data = _request('POST', f'/session/{session_id}/message', json_body=body, timeout=timeout, inst=inst)
    finally:
        done.set()
    info = data.get('info') or {}
    err = _model_error(info)
    if err:
        low = err.lower()
        quota = any(k in low for k in ('free tier', 'quota', 'rate limit', 'limit reached', 'too many'))
        block(err, QUOTA_COOLDOWN if quota else COOLDOWN, inst=inst)
        raise OpencodeUnavailableError(err)
    out = data.get('parts') or []
    text_out = '\n'.join(p.get('text', '') for p in out if p.get('type') == 'text').strip()
    tools = [
        {
            'tool': p.get('tool'),
            'input': (p.get('state') or {}).get('input'),
            'status': (p.get('state') or {}).get('status'),
        }
        for p in out
        if p.get('type') == 'tool'
    ]
    return {'text': text_out, 'tools': tools, 'tokens': info.get('tokens') or {}, 'permissions': perms}
