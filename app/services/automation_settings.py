"""Interruptor de los avisos automáticos a padres/apoderados (recordatorios de sesión y cobranza por WhatsApp/SMS).

Modos:
  - ``all``   : se avisa a todos (comportamiento normal).
  - ``pilot`` : solo se avisa al paciente piloto elegido; sirve para probar con una sola familia.
  - ``off``   : no sale ningún aviso automático.
Además se puede apagar por canal (WhatsApp / SMS) y por tipo (sesiones / cobranza).

Los envíos manuales hechos por un administrador (CRM, botón «enviar recordatorio») no pasan por aquí: son decisión explícita.
"""

from app.extensions import db
from app.models.system_setting import SystemSetting
from app.services import live_sync

MODES = ('all', 'pilot', 'off')
FLAGS = ('whatsapp', 'sms', 'sessions', 'debts', 'whatsapp_bot')
DEFAULTS = {
    'mode': 'all',
    'pilot_patient_id': None,
    'whatsapp': True,
    'sms': True,
    'sessions': True,
    'debts': True,
    'whatsapp_bot': True,
}


def _key(name):
    return f'automation.{name}'


def _read(name, default=None):
    try:
        row = db.session.get(SystemSetting, _key(name))
        return row.value if row is not None else default
    except Exception:
        db.session.rollback()
        return default


def get():
    """Configuración vigente (con valores por defecto si nunca se tocó)."""
    mode = _read('mode', DEFAULTS['mode'])
    pilot = _read('pilot_patient_id')
    out = {
        'mode': mode if mode in MODES else DEFAULTS['mode'],
        'pilot_patient_id': int(pilot) if pilot and str(pilot).isdigit() else None,
    }
    for flag in FLAGS:
        raw = _read(flag)
        out[flag] = DEFAULTS[flag] if raw is None else raw == '1'
    return out


def pilot_patient():
    from app.models.user import User

    pid = get()['pilot_patient_id']
    user = db.session.get(User, pid) if pid else None
    return {'id': user.id, 'username': user.username} if user else None


def update(data, user_id=None):
    """Valida y guarda. Devuelve (config_vigente, errores)."""
    from app.models.user import User

    errors = {}
    clean = {}
    if 'mode' in data:
        if data['mode'] not in MODES:
            errors['mode'] = 'Modo inválido'
        else:
            clean['mode'] = data['mode']
    for flag in FLAGS:
        if flag in data:
            if not isinstance(data[flag], bool):
                errors[flag] = 'Debe ser verdadero o falso'
            else:
                clean[flag] = '1' if data[flag] else '0'
    if 'pilot_patient_id' in data:
        raw = data['pilot_patient_id']
        if raw in (None, ''):
            clean['pilot_patient_id'] = ''
        else:
            patient = db.session.get(User, int(raw)) if str(raw).isdigit() else None
            if not patient or patient.role != 'jugador':
                errors['pilot_patient_id'] = 'Elige un paciente existente'
            else:
                clean['pilot_patient_id'] = str(patient.id)
    effective_mode = clean.get('mode', get()['mode'])
    effective_pilot = clean.get('pilot_patient_id', str(get()['pilot_patient_id'] or ''))
    if not errors and effective_mode == 'pilot' and not effective_pilot:
        errors['pilot_patient_id'] = 'Elige el paciente con el que quieres hacer la prueba'
    if errors:
        return get(), errors
    for name, value in clean.items():
        row = db.session.get(SystemSetting, _key(name))
        if row is None:
            row = SystemSetting(key=_key(name))
            db.session.add(row)
        row.value = value
        row.updated_by_id = user_id
    db.session.commit()
    live_sync.bump('channels')
    return get(), {}


def allows(patient_id, kind, channel):
    """¿Puede salir un aviso automático de tipo `kind` ('sessions'|'debts') por `channel` ('whatsapp'|'sms') a este paciente?

    Devuelve (True, None) o (False, motivo).
    """
    cfg = get()
    if cfg['mode'] == 'off':
        return False, 'Los avisos automáticos están desactivados'
    if cfg['mode'] == 'pilot' and cfg['pilot_patient_id'] != patient_id:
        return False, 'Modo de prueba: solo recibe el paciente piloto'
    if kind in ('sessions', 'debts') and not cfg[kind]:
        return False, 'Este tipo de aviso está desactivado'
    if channel in ('whatsapp', 'sms') and not cfg[channel]:
        return False, f'El canal {channel} está desactivado'
    return True, None
