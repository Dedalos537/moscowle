# Diego consulta la base + Notificaciones de Kanban + Login con huella

Date: 2026-09-05

## Goal

Tres mejoras pedidas por el usuario:

1. **Bot / Diego conectado a la base (MCP)**: que responda consultas de la BD, ej.
   "¿Cuántos usuarios tiene Milagros Barrutia asignados?" (hoy responde "No tengo esos
   datos" porque no existe herramienta que lo consulte).
2. **Notificaciones de Kanban**: al cambiar el estado de una tarea, notificar tanto en
   la app (inasistencia) como en Telegram.
3. **Login con huella (WebAuthn)**: permitir acceder con huella digital, registrando
   el dispositivo por usuario.

## Diseño / Decisiones (ya acordadas)

- El "MCP" que usa Diego es el sistema de tools del backend Python (`app/services/
  tools_registry.py` + `MCPService`), NO el proyecto `mcp-server/` (servidor MCP
  Node.js independiente, sin conexión al bot).
- Notificaciones: `NotificationService.notify_user(...)`; Telegram se envía solo con
  priority `high`/`urgent` (o cada 5º item). Cambio de columna = `priority='high'`
  para forzar Telegram. NUEVO grupo kanban en `notification_intelligence.py`.
- WebAuthn: librería `webauthn` (py_webauthn). Nuevas tablas
  `webauthn_credential` + `webauthn_challenge` via `db.create_all()` (nada de
  alembic). RP ID = `api-centrojuanpabloii.online` (mismo host de la SPA).
  Challenge en DB (gunicorn eventlet multi-worker: in-memory inseguro).
- Registro de la huella: en el panel de Ajustes del admin (patrón `.settings-card`).
- NUEVO icono `faFingerprint` en `fontawesome-icons.ts` (evitar bug del icono
  `telegram` que congelaba el panel — los iconos NO pueden usarse sin registrarse
  en `library.addIcons`).

## Task 1: Diego consulta la base (tool MCP `get_therapist_patients`)

**Files:** `app/services/tools_registry.py`, `app/services/mcp_service.py`,
`tests/test_mcp_therapist_caseload.py`

1. **`app/services/tools_registry.py`** — añadir después de `handle_list_users`:

```python
@tool(
    name='get_therapist_patients',
    description=(
        'Cantidad y lista de pacientes (jugadores) que tiene asignados un terapeuta. '
        'Uso tipico: "cuantos usuarios tiene el terapeuta Milagros" '
        '-> get_therapist_patients({"therapist_name": "Milagros"})'
    ),
    parameters={
        'type': 'object',
        'properties': {
            'therapist_name': {
                'type': 'string',
                'description': 'Nombre o email del terapeuta (minimo 2 caracteres)',
            },
        },
        'required': ['therapist_name'],
    },
    category='read',
    roles=ROLES_SUPERVISOR | {'terapista'},
)
def handle_get_therapist_patients(therapist_name=None, _user_id=None, _role=None, **kwargs):
    name = (str(therapist_name or '')).strip()
    if len(name) < 2:
        return {'error': 'Parametro "therapist_name" requerido (minimo 2 caracteres).'}
    therapist = User.query.filter(
        User.role == 'terapista',
        db.or_(User.username.ilike(f'%{name}%'), User.email.ilike(f'%{name}%')),
    ).first()
    if not therapist:
        return {'error': 'No se encontro un terapeuta con ese nombre.'}
    patients = (
        User.query.filter_by(role='jugador', assigned_therapist_id=therapist.id, is_active=True)
        .order_by(User.username)
        .all()
    )
    return {
        'success': True,
        'therapist': {'id': therapist.id, 'username': therapist.username, 'email': therapist.email},
        'count': len(patients),
        'patients': [
            {'id': p.id, 'username': p.username, 'email': p.email}
            for p in patients
        ],
    }
```

2. Añadir `'get_therapist_patients'` a `CORE_TOOL_NAMES` (junto a `list_users`).
3. **`app/services/mcp_service.py`** — en el prompt admin (SYSTEM_PROMPTS), aÑadir
   `get_therapist_patients` al listado de tools y reemplazar la regla "No tengo esos
   datos" (~línea 53):
   `- If I don\'t have data from a tool, and a tool exists that could answer the question, ALWAYS call that tool first. Only reply "No tengo esos datos" after calling a tool and receiving no data.`
4. Test **`tests/test_mcp_therapist_caseload.py`**:
   - crea terapeuta `Milagros Barrutia` + 2 jugadores activos asignados + 1 inactivo
     asignado + 1 no asignado;
   - `execute_tool('get_therapist_patients', {'therapist_name': 'Milagros'}, user_id=None, role='admin')`
     → `count == 2`, pacientes solo activos;
   - terapeuta inexistente → `{'error': ...}`;
   - nombre de 1 carácter → `{'error': ...}`.

**Verificar:** `ruff check` + `pytest tests/test_mcp_therapist_caseload.py`.

## Task 2: Notificaciones de Kanban (app + Telegram)

**Files:** `app/services/notification_intelligence.py`, `app/routes/kanban_routes.py`,
`tests/test_kanban_notifications.py`

1. **`app/services/notification_intelligence.py`**:
   - `GROUP_TTL`: añadir `'kanban': 3600,`
   - `builders` en `compute_group_key`:
     ```python
     'task_created': lambda k: (f"kanban:{k.get('task_id', 'unknown')}", 'system', 'normal'),
     'task_moved': lambda k: (f"kanban:{k.get('task_id', 'unknown')}", 'system', 'high'),
     'task_deleted': lambda k: (f"kanban:{k.get('task_id', 'unknown')}", 'system', 'normal'),
     ```
2. **`app/routes/kanban_routes.py`**: importar `NotificationService`. Añadir helpers
   (near top):

```python
_from_notification_service = NotificationService()

KANBAN_COLUMN_LABELS = {
    'todo': 'Por hacer',
    'in-progress': 'En progreso',
    'review': 'Revisión',
    'done': 'Hecho',
}

def _kanban_recipient(task):
    target = task.assigned_to_id or task.created_by_id
    from app.models.user import User as KanbanUser
    return KanbanUser.query.get(target) if target else None

def _kanban_link(recipient):
    if recipient.role in ('admin', 'supervisor'):
        return '/app/admin/kanban'
    if recipient.role == 'terapista':
        return '/app/therapist/kanban'
    return '/app/patient/kanban'

def _notify_kanban_task(task, event_type, title, message, priority='normal'):
    recipient = _kanban_recipient(task)
    if not recipient or not getattr(recipient, 'is_active', True):
        return
    _from_notification_service.notify_user(
        user_id=recipient.id,
        title=title,
        message=message,
        notif_type='info',
        link=_kanban_link(recipient),
        category='system',
        priority=priority,
        icon='tasks',
        event_type=event_type,
        event_kwargs={'task_id': task.id},
        metadata_json={'task_id': task.id, 'title': task.title, 'column': task.column},
    )
```

   - En `create_task` (POST /tasks, ~línea 138), tras `db.session.commit()`:
     ```python
     if task.assigned_to_id and task.assigned_to_id != user.id:
         _notify_kanban_task(
             task, 'task_created',
             'Nueva tarea asignada',
             f'Te asignaron una nueva tarea: {task.title}',
         )
     ```
   - En `update_task` (PATCH, ~líneas 210-260): `old_column = task.column` al INICIO
     del try, y tras commit:
     ```python
     if old_column != task.column and task.column in KANBAN_COLUMN_LABELS:
         _notify_kanban_task(
             task, 'task_moved',
             'Tarea de kanban actualizada',
             f'Tarea "{task.title}" cambió de "{KANBAN_COLUMN_LABELS.get(old_column, old_column)}" a "{KANBAN_COLUMN_LABELS.get(task.column, task.column)}"',
             priority='high',
         )
     ```
   - En `delete_task`: capturar `title` y `recipient` ANTES de borrar (task.id se
     conserva tras commit); notificar si `recipient and recipient.id != user.id`.
   - NOTA: cambiar columna desde "quick-move" y desde el modal pasan por el mismo
     PATCH → una sola fuente de notificación.
3. Test **`tests/test_kanban_notifications.py`** (client + JWT de staff):
   - crear staff (admin), terapeuta, task asignada al terapeuta;
   - PATCH columna → `in-progress` (Autorización Bearer del admin);
   - assert `NotificationGroup` con `group_key == 'kanban:{task_id}'` y un item con
     `priority='high'`; `NotificationItem` con `event_type == 'task_moved'`;
   - create → item `task_created` (`priority='normal'`).

**Verificar:** `ruff check` + `pytest tests/test_kanban_notifications.py`.

## Task 3: Backend WebAuthn (huella)

**Files:** `requirements.txt`, `app/models/webauthn.py`, `app/models/__init__.py`,
`config.py`, `app/services/webauthn_service.py`, `app/routes/webauthn.py`,
`app/__init__.py`, `tests/test_webauthn_routes.py`

1. `pip install webauthn` (si Python 3.14 local falla, usar python3.12 para el venv de
   pruebas) y añadir `webauthn` a `requirements.txt`.
2. **`app/models/webauthn.py`**:

```python
from datetime import datetime
from app.extensions import db


class WebAuthnCredential(db.Model):
    __tablename__ = 'webauthn_credential'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    credential_id = db.Column(db.String(600), unique=True, nullable=False, index=True)
    public_key = db.Column(db.Text, nullable=False)
    sign_count = db.Column(db.Integer, nullable=False, default=0)
    transports = db.Column(db.Text, nullable=True)
    device_name = db.Column(db.String(120), nullable=True)
    aaguid = db.Column(db.String(64), nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    last_used_at = db.Column(db.DateTime, nullable=True)


class WebAuthnChallenge(db.Model):
    __tablename__ = 'webauthn_challenge'
    id = db.Column(db.Integer, primary_key=True)
    challenge = db.Column(db.String(200), unique=True, nullable=False)
    user_handle = db.Column(db.String(64), nullable=False)
    operation = db.Column(db.String(16), nullable=False)  # register | login
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
```

   Importar ambos en `app/models/__init__.py`.
3. **`config.py`** (base de ambos configs):
   ```python
   WEBAUTHN_RP_ID = os.getenv('WEBAUTHN_RP_ID', 'api-centrojuanpabloii.online')
   WEBAUTHN_RP_NAME = os.getenv('WEBAUTHN_RP_NAME', 'Centro Juan Pablo II')
   WEBAUTHN_ORIGINS = os.getenv('WEBAUTHN_ORIGINS', f'https://{self.WEBAUTHN_RP_ID}')
   ```
4. **`app/services/webauthn_service.py`** — funciones puras (los endpoints
   gestionan requests/JSON). API py_webauthn v3:

```python
import os
from datetime import datetime, timedelta

from flask import current_app
from webauthn import (generate_authentication_options,
                      generate_registration_options,
                      verify_authentication_response,
                      verify_registration_response)
from webauthn.helpers import base64url_to_bytes, bytes_to_base64url
from webauthn.helpers.options_to_json import options_to_json
from webauthn.helpers.structs import (AttestationConveyancePreference,
                                      AuthenticatorSelectionCriteria,
                                      AuthenticationCredential,
                                      PublicKeyCredentialDescriptor,
                                      RegistrationCredential,
                                      ResidentKeyRequirement,
                                      UserVerificationRequirement)

from app.extensions import db
from app.models.user import User
from app.models.webauthn import WebAuthnChallenge, WebAuthnCredential

CHALLENGE_TTL_SECONDS = 300


def rp_id():
    return current_app.config.get('WEBAUTHN_RP_ID', 'api-centrojuanpabloii.online')


def rp_name():
    return current_app.config.get('WEBAUTHN_RP_NAME', 'Centro Juan Pablo II')


def origins():
    value = current_app.config.get('WEBAUTHN_ORIGINS')
    if isinstance(value, str):
        value = [o.strip() for o in value.split(',') if o.strip()]
    return value or [f'https://{rp_id()}']


def _save_challenge(user_id, challenge_b64, operation):
    WebAuthnChallenge.query.filter(WebAuthnChallenge.expires_at < datetime.utcnow()).delete()
    WebAuthnChallenge.query.filter_by(user_handle=str(user_id), operation=operation).delete()
    db.session.add(WebAuthnChallenge(
        challenge=challenge_b64,
        user_handle=str(user_id),
        operation=operation,
        expires_at=datetime.utcnow() + timedelta(seconds=CHALLENGE_TTL_SECONDS),
    ))
    db.session.commit()


def _pop_challenge(user_id, operation):
    row = (WebAuthnChallenge.query.filter_by(user_handle=str(user_id), operation=operation)
           .order_by(WebAuthnChallenge.id.desc()).first())
    if not row:
        return None
    db.session.delete(row)
    db.session.commit()
    return row


def default_challenge():
    return os.urandom(32)


def registration_options(user):
    existing = WebAuthnCredential.query.filter_by(user_id=user.id, is_active=True).all()
    options = generate_registration_options(
        rp_id=rp_id(),
        rp_name=rp_name(),
        user_id=str(user.id).encode(),
        user_name=user.email or user.username,
        user_display_name=user.username,
        attestation=AttestationConveyancePreference.NONE,
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.DISCOURAGED,
            user_verification=UserVerificationRequirement.PREFERRED,
        ),
        challenge=default_challenge(),
        exclude_credentials=[
            PublicKeyCredentialDescriptor(id=base64url_to_bytes(c.credential_id))
            for c in existing
        ],
    )
    _save_challenge(user.id, bytes_to_base64url(options.challenge), 'register')
    return options_to_json(options)


def authentication_options(user):
    creds = WebAuthnCredential.query.filter_by(user_id=user.id, is_active=True).all()
    if not creds:
        return None
    options = generate_authentication_options(
        rp_id=rp_id(),
        challenge=default_challenge(),
        user_verification=UserVerificationRequirement.PREFERRED,
        allow_credentials=[
            PublicKeyCredentialDescriptor(id=base64url_to_bytes(c.credential_id))
            for c in creds
        ],
    )
    _save_challenge(user.id, bytes_to_base64url(options.challenge), 'login')
    return {**options_to_json(options), 'user_handle': bytes_to_base64url(str(user.id).encode())}


def verify_registration(user, payload):
    challenge_row = _pop_challenge(user.id, 'register')
    if not challenge_row:
        return None, 'La solicitud de registro expiró, inténtalo de nuevo.'
    try:
        credential = RegistrationCredential.model_validate(payload.get('credential') or {})
        verification = verify_registration_response(
            credential=credential,
            expected_challenge=base64url_to_bytes(challenge_row.challenge),
            expected_origin=origins(),
            expected_rp_id=rp_id(),
            require_user_verification=False,
        )
    except Exception as exc:
        db.session.rollback()
        return None, f'Verificación fallida: {exc}'
    cred_id = bytes_to_base64url(verification.credential_id)
    if WebAuthnCredential.query.filter_by(user_id=user.id, credential_id=cred_id).first():
        return None, 'Este dispositivo ya está registrado.'
    db.session.add(WebAuthnCredential(
        user_id=user.id,
        credential_id=cred_id,
        public_key=bytes_to_base64url(verification.credential_public_key),
        sign_count=verification.sign_count,
        aaguid=bytes_to_base64url(verification.aaguid) if verification.aaguid else None,
        device_name=(payload.get('device_name') or 'Dispositivo')[:120],
        transports=(payload.get('transports') if payload.get('transports') else None),
    ))
    db.session.commit()
    return cred_id, None


def find_user_by_identifier(identifier):
    ident = (identifier or '').strip()
    if not ident:
        return None
    return User.query.filter(
        db.or_(User.email.ilike(ident), User.login_code.ilike(ident))
    ).first()


def verify_authentication(user, payload):
    challenge_row = _pop_challenge(user.id, 'login')
    if not challenge_row:
        return None, 'La solicitud de inicio de sesión expiró, inténtalo de nuevo.'
    try:
        credential = AuthenticationCredential.model_validate(payload.get('credential') or {})
    except Exception as exc:
        return None, f'Verificación fallida: {exc}'
    cred_id = bytes_to_base64url(credential.raw_id)
    credential_db = WebAuthnCredential.query.filter_by(
        user_id=user.id, credential_id=cred_id, is_active=True,
    ).first()
    if not credential_db:
        return None, 'Dispositivo no registrado para este usuario.'
    try:
        verification = verify_authentication_response(
            credential=credential,
            expected_challenge=base64url_to_bytes(challenge_row.challenge),
            expected_origin=origins(),
            expected_rp_id=rp_id(),
            credential_public_key=base64url_to_bytes(credential_db.public_key),
            credential_current_sign_count=credential_db.sign_count,
            require_user_verification=False,
        )
    except Exception as exc:
        return None, f'Verificación fallida: {exc}'
    credential_db.sign_count = verification.new_sign_count
    credential_db.last_used_at = datetime.utcnow()
    db.session.commit()
    return user, None
```

   NOTA: confirmar con la versión instalada que `expected_origin` acepta lista; si no,
   pasar `origins()[0]`.
5. **`app/routes/webauthn.py`** (blueprint `webauthn_bp`, url_prefix
   `/api/auth/webauthn`):

```python
from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import create_access_token, create_refresh_token, get_jwt_identity, jwt_required, set_access_cookies, set_refresh_cookies
from flask_wtf.csrf import generate_csrf

from app.extensions import db
from app.models.user import User
from app.models.webauthn import WebAuthnCredential
from app.routes.auth import _auto_start_session, _record_session
from app.services import webauthn_service

webauthn_bp = Blueprint('webauthn', __name__, url_prefix='/api/auth/webauthn')


def _current_identity():
    return User.query.get(int(get_jwt_identity())) if get_jwt_identity() else None


@webauthn_bp.route('/register/options', methods=['POST'])
@jwt_required()
def webauthn_register_options():
    user = _current_identity()
    if not user:
        return jsonify({'success': False, 'error': 'Usuario no encontrado'}), 404
    try:
        options = webauthn_service.registration_options(user)
        return jsonify({'success': True, 'options': options})
    except Exception as exc:
        current_app.logger.warning(f'webauthn register options: {exc}')
        return jsonify({'success': False, 'error': 'No se pudo iniciar el registro'}), 500


@webauthn_bp.route('/register/verify', methods=['POST'])
@jwt_required()
def webauthn_register_verify():
    user = _current_identity()
    if not user:
        return jsonify({'success': False, 'error': 'Usuario no encontrado'}), 404
    data = request.get_json(silent=True) or {}
    cred_id, error = webauthn_service.verify_registration(user, data)
    if error:
        return jsonify({'success': False, 'error': error}), 400
    return jsonify({'success': True, 'credential_id': cred_id})


@webauthn_bp.route('/login/options', methods=['POST'])
def webauthn_login_options():
    data = request.get_json(silent=True) or {}
    user = webauthn_service.find_user_by_identifier(data.get('identifier'))
    if not user or not getattr(user, 'is_active', True):
        return jsonify({'success': False, 'error': 'Usuario no encontrado'}), 404
    options = webauthn_service.authentication_options(user)
    if options is None:
        return jsonify({'success': False, 'error': 'Este usuario no tiene huella registrada'}), 404
    return jsonify({'success': True, 'options': options})


@webauthn_bp.route('/login/verify', methods=['POST'])
def webauthn_login_verify():
    data = request.get_json(silent=True) or {}
    user = webauthn_service.find_user_by_identifier(data.get('identifier'))
    if not user or not getattr(user, '_security', None):
        return jsonify({'success': False, 'error': 'Usuario no encontrado'}), 404
    if not getattr(user, 'is_active', True):
        return jsonify({'success': False, 'error': 'Cuenta desactivada'}), 401
    user, error = webauthn_service.verify_authentication(user, data)
    if error:
        return jsonify({'success': False, 'error': error}), 401
    _auto_start_session(user)
    access_token = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))
    _record_session(user, access_token, refresh_token)
    csrf_token = generate_csrf()
    response = jsonify({
        'success': True,
        'csrf_token': csrf_token,
        'access_token': access_token,
        'user': {
            'id': user.id, 'email': user.email, 'username': user.username,
            'role': user.role, 'login_code': user.login_code,
            'timezone': getattr(user, 'timezone', None) or 'America/Lima',
        },
    })
    set_access_cookies(response, access_token)
    set_refresh_cookies(response, refresh_token)
    return response


@webauthn_bp.route('/credentials', methods=['GET'])
@jwt_required()
def webauthn_credentials():
    user = _current_identity()
    if not user:
        return jsonify({'success': False, 'error': 'Usuario no encontrado'}), 404
    creds = WebAuthnCredential.query.filter_by(user_id=user.id, is_active=True).all()
    return jsonify({'success': True, 'credentials': [
        {'id': c.id, 'device_name': c.device_name, 'created_at': c.created_at.isoformat() if c.created_at else None}
        for c in creds
    ]})


@webauthn_bp.route('/credentials/<int:credential_id>', methods=['DELETE'])
@jwt_required()
def webauthn_delete_credential(credential_id):
    user = _current_identity()
    if not user:
        return jsonify({'success': False, 'error': 'Usuario no encontrado'}), 404
    cred = WebAuthnCredential.query.filter_by(id=credential_id, user_id=user.id).first()
    if not cred:
        return jsonify({'success': False, 'error': 'Dispositivo no encontrado'}), 404
    cred.is_active = False
    db.session.commit()
    return jsonify({'success': True})
```

   Fix: quitar el check sin sentido `user._security` del verify (dejar solo is_active).
6. **`app/__init__.py`** — registrar blueprint en `create_app` y `create_app_lite`
   (igual que kanban) + `csrf.exempt(webauthn_bp)` en ambas.
7. Test **`tests/test_webauthn_routes.py`** (app + client + JWT):
   - `register/options` sin token → 401;
   - `register/options` con token → 200 y `options.challenge` presente;
   - `login/options` identifier desconocido → 404;
   - `login/options` usuario sin credencial → 404 (`error` huella);
   - `login/options` usuario con credencial insertada directa en DB → 200 con
     `allowCredentials` y `user_handle`;
   - `register/verify` y `login/verify` con credential basura → 4xx con `error`.

**Verificar:** `pip install webauthn` + `ruff check` + `pytest`.

## Task 4: Frontend WebAuthn (login + settings + icono)

**Files:** `edysync/src/app/shared/fontawesome-icons.ts`,
`edysync/src/app/core/services/auth.service.ts`,
`edysync/src/app/features/auth/pages/login/login.ts`,
`edysync/src/app/features/auth/pages/login/login.html`,
`edysync/src/app/features/admin/pages/settings/settings.ts`,
`edysync/src/app/features/admin/pages/settings/settings.html`

1. **Icono**: importar `faFingerprint` y agregarlo a `fasIcons` (nunca usarlo sin
   registrarlo — bug del telegram).
2. **auth.service.ts**: añadir
   ```ts
   webauthnLoginOptions(identifier: string): Observable<any> {
     return this.http.post<any>('/api/auth/webauthn/login/options', { identifier });
   }
   completeWebauthnLogin(identifier: string, credential: any): Observable<any> {
     return this.http.post<any>('/api/auth/webauthn/login/verify', { identifier, credential })
       .pipe(tap(res => this._persistSession(res)));
   }
   webauthnRegisterOptions(device_name: string): Observable<any> {
     return this.http.post<any>('/api/auth/webauthn/register/options', { device_name });
   }
   webauthnRegisterVerify(credential: any, device_name: string): Observable<any> {
     return this.http.post<any>('/api/auth/webauthn/register/verify', { credential, device_name });
   }
   webauthnGetCredentials(): Observable<any> {
     return this.http.get<any>('/api/auth/webauthn/credentials');
   }
   webauthnDeleteCredential(id: number): Observable<any> {
     return this.http.delete<any>(`/api/auth/webauthn/credentials/${id}`);
   }
   ```
   Extraer la persistencia de sesión actual a `private _persistSession(res)` y
   reutilizarla en `login()` y `completeWebauthnLogin()`.
3. **login.ts/html**: botón "Ingresar con huella" (solo si
   `typeof window !== 'undefined' && window.PublicKeyCredential`). Flujo:
   `email` → `webauthnLoginOptions(email)` → `navigator.credentials.get({publicKey:
   options})` → serializar credential (helper `webauthnManager` local: id, rawId,
   clientDataJSON, authenticatorData, signature, userHandle, type,
   clientExtensionResults, base64url) → `completeWebauthnLogin` → navegar según
   role (igual que login).
4. **settings.ts/html**: tarjeta `.settings-card` "Huella digital (ingreso con
   huella)" con botón "Registrar dispositivo" + input opcional de nombre + lista con
   botón eliminar. Flujo: `webauthnRegisterOptions` → `navigator.credentials.create({publicKey})` →
   serializar (clientDataJSON + attestationObject) → `webauthnRegisterVerify` →
   recargar lista. Cargar lista on init si `window.PublicKeyCredential`.
   `FormsModule` en imports del componente si hace falta `ngModel`.

**Verificar:** `npx ng build --configuration production` (type-check + build).

## Task 5: Deploy + verificación E2E en vivo

1. Backend: `rsync -avz --delete --exclude='__pycache__' --exclude='*.pyc' -e "sshpass -p Rucula_530 ssh -o StrictHostKeyChecking=accept-new" app/ diego@192.168.1.41:/home/diego/moscowle_ia/app/`; instalar `webauthn` en el venv del server (`pip install webauthn` dentro del venv); reiniciar servicio (`echo Rucula_530 | sudo -S systemctl restart moscowle.service`). Ver logs: `/home/diego/moscowle_ia/logs/gunicorn_err.log`.
2. Tablas nuevas: confirmar `SHOW TABLES` → `webauthn_credential`, `webauthn_challenge` (db.create_all en boot).
3. Frontend: `npx ng build --configuration production` + rsync `dist/edysync/browser/` → `/home/diego/moscowle_ia/edysync/dist/edysync/browser/`.
4. **Verify MCP (Diego)**: pregunta por Telegram "¿Cuántos usuarios tiene Milagros Barrutia asignados?" → debe responder con count + lista (no "No tengo esos datos"). Si no se puede por Telegram, probar MCPService directo en consola del server.
5. **Verify kanban notif**: crear tarea asignada a otro usuario + moverla → consultar notifs API (GET endpoint de notificaciones del assignee) → debe existir grupo `kanban:{task_id}` y en Telegram del asignado (si tiene Telegram vinculado). Determinar endpoint de notifs revisando `app/routes/notifications_routes.py` en implementación.
6. **Verify WebAuthn**: con CDP (`http://127.0.0.1:9223`, perfil `/tmp/od-agent-browser-chrome`), `WebAuthn.enable` + `WebAuthn.addVirtualAuthenticator` sobre la página de login en vivo: registrar huella en settings del admin → logout → login con huella → página según role. Confirmar `faFingerprint` pinta sin congelar el panel.

## Commits (convención del repo, un commit por tarea)

- `feat(bot): tool get_therapist_patients para consultar pacientes por terapeuta`
- `feat(kanban): notificar en la app y telegram al cambiar estado de tarea`
- `feat(auth): login con huella digital webauthn + registro en ajustes`

## Checklist final

- [ ] ruff sin errores
- [ ] pytest verde (sin y con webauthn instalado)
- [ ] `npx ng build --configuration production` OK
- [ ] deploy backend + frontend a prod
- [ ] verificación en vivo: bot responde consulta, notif kanban visible, login huella funciona con authenticator virtual CDP
- [ ] 3 commits pushed, working tree limpio
