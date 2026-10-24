"""Conversaciones del asistente del admin (PRP 015): guardar, compartir, preguntar, actualizar y programar.

- Preguntas de datos del centro → `assistant_analytics` (bloques con los números del sistema).
- El resto → la IA general (OpenCode/MiMo con las herramientas MCP, con la cadena de respaldo), como texto.
- Quién ve qué: cada conversación es de su autor. Compartida, la ven los demás admins; un supervisor solo ve
  las compartidas por supervisores de su misma sede (nunca datos de todo el centro).
"""

import re
from datetime import datetime, timedelta

from flask import current_app

from app.extensions import db
from app.models import User
from app.models.assistant_thread import AssistantMessage, AssistantSchedule, AssistantThread
from app.services import assistant_analytics as analytics

RETENTION_DAYS = 180
HISTORY_TURNS = 8


class AssistantError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


# ── acceso ──────────────────────────────────────────────────────────────────
def can_view(thread, user):
    if thread.user_id == user.id:
        return True
    if not thread.shared:
        return False
    author = db.session.get(User, thread.user_id)
    if user.role == 'admin':
        return True
    if user.role == 'supervisor' and author and author.role == 'supervisor':
        try:
            return analytics.scope_for(author) == analytics.scope_for(user)
        except analytics.ScopeError:
            return False
    return False


def get_thread(thread_id, user, *, write=False):
    thread = db.session.get(AssistantThread, thread_id)
    if not thread or not can_view(thread, user):
        raise AssistantError('Conversación no encontrada', 404)
    if write and thread.user_id != user.id:
        raise AssistantError('Solo quien la creó puede cambiarla', 403)
    return thread


def list_threads(user, query=None):
    own = AssistantThread.query.filter_by(user_id=user.id)
    shared = AssistantThread.query.filter(AssistantThread.shared.is_(True), AssistantThread.user_id != user.id)
    rows = own.all() + [t for t in shared.all() if can_view(t, user)]
    if query:
        q = query.lower()
        rows = [t for t in rows if q in (t.title or '').lower()]
    rows.sort(key=lambda t: (not t.pinned, -(t.updated_at or t.created_at).timestamp()))
    return [thread_dict(t, user) for t in rows]


def thread_dict(thread, user, with_messages=False):
    author = db.session.get(User, thread.user_id)
    out = {
        'id': thread.id,
        'title': thread.title,
        'pinned': thread.pinned,
        'shared': thread.shared,
        'mine': thread.user_id == user.id,
        'author': author.username if author else None,
        'created_at': thread.created_at.isoformat() + 'Z',
        'updated_at': (thread.updated_at or thread.created_at).isoformat() + 'Z',
    }
    if with_messages:
        out['messages'] = [message_dict(m, user) for m in thread.messages.all()]
        out['schedules'] = [
            schedule_dict(s) for s in AssistantSchedule.query.filter_by(thread_id=thread.id, user_id=user.id).all()
        ]
    return out


def _fresh_blocks(blocks, user):
    """Una acción aún sin confirmar se muestra con el formulario de hoy (p. ej. paciente por nombre, no por id),
    aunque se haya propuesto antes de un cambio; lo ya escrito por el usuario se conserva."""
    out = []
    for b in blocks or []:
        item = b
        if b.get('type') == 'action' and b.get('status') == 'pending' and b.get('tool'):
            try:
                fresh = action_block(b['tool'], b.get('args'), user)
                item = {**b, 'fields': fresh['fields'], 'title': fresh['title']}
            except Exception:  # noqa: BLE001 - herramienta retirada: queda como se guardó
                pass
        out.append(item)
    return out


def message_dict(m, user=None):
    return {
        'id': m.id,
        'role': m.role,
        'text': m.text,
        'blocks': _fresh_blocks(m.blocks, user) if user is not None else m.blocks or [],
        'sources': m.sources or [],
        'model': m.model,
        'question': m.question,
        'feedback': m.feedback,
        'created_at': m.created_at.isoformat() + 'Z',
    }


# ── preguntar ───────────────────────────────────────────────────────────────
def _history(thread):
    msgs = thread.messages.order_by(AssistantMessage.id.desc()).limit(HISTORY_TURNS * 2).all()
    return [{'role': m.role, 'content': m.text or ''} for m in reversed(msgs)]


# En esta pantalla hay formularios: el modelo no necesita preguntar dato por dato antes de proponer una acción.
SCREEN_HINT = (
    '[Pantalla del asistente: si el usuario pide crear, registrar, programar o cambiar algo, LLAMA YA a la '
    'herramienta de escritura con los datos que tengas, aunque falten obligatorios: el sistema le muestra un '
    'formulario para completar lo que falte y confirmar. NUNCA preguntes los datos uno por uno. Si nombra a una '
    'persona, búscala con las herramientas de consulta y usa su id. Mantén el hilo de la conversación.]\n'
)


# Nombres claros para los campos más comunes (la descripción de la herramienta es para el modelo, no para la gente).
FIELD_LABELS = {
    'username': 'Nombre completo',
    'name': 'Nombre',
    'email': 'Correo',
    'phone': 'Teléfono',
    'role': 'Tipo de usuario',
    'sede_id': 'Sede',
    'guardian': 'Apoderado',
    'guardian_name': 'Apoderado',
    'guardian_contact': 'Contacto del apoderado',
    'amount': 'Monto (S/)',
    'method': 'Método de pago',
    'date': 'Fecha',
    'start_time': 'Hora de inicio',
    'end_time': 'Hora de fin',
    'notes': 'Notas',
    'description': 'Descripción',
    'reason': 'Motivo',
    'password': 'Contraseña temporal',
    'document_number': 'DNI del paciente',
    'date_of_birth': 'Fecha de nacimiento',
    'sex': 'Sexo',
    'guardian_type': 'Tipo de apoderado',
    'guardian_dni': 'DNI del apoderado',
    'preliminary_diagnosis': 'Diagnóstico preliminar',
    'therapy_goals': 'Objetivos de terapia',
    'start_date': 'Fecha de inicio',
    'end_date': 'Fecha de fin',
    'total_amount': 'Monto total (S/)',
    'installments': 'Número de cuotas',
    'patient_id': 'Paciente',
    'therapist_id': 'Terapeuta',
    'assigned_therapist_id': 'Terapeuta asignado',
    'user_id': 'Usuario',
    'assignee_id': 'Responsable',
    'sede_ids': 'Sedes asignadas',
    'modality': 'Modalidad',
    'payment_frequency': 'Frecuencia',
    'plan_type': 'Tipo de plan',
    'payment_amount': 'Monto a pagar (S/)',
    'generate_schedule': 'Generar horario automático',
    'evaluation_date': 'Fecha de la sesión de evaluación',
    'days_of_week': 'Días de sesión',
    'salary_base': 'Base salarial (S/)',
    'contract_hours': 'Horas contratadas',
    'folder': 'Carpeta del Drive',
    'copies': 'Copias',
    'color': 'A color',
    'with_ai': 'Incluir informe terapéutico (IA)',
}

# Opciones con nombre (el esquema de la herramienta trae valores sueltos: 1, 'monthly', 0…).
FIELD_OPTIONS = {
    'modality': [
        {'value': 1, 'label': '1x semana (4 sesiones)'},
        {'value': 2, 'label': '2x semana (8 sesiones)'},
        {'value': 3, 'label': '3x semana (12 sesiones)'},
    ],
    'payment_frequency': [
        {'value': 'monthly', 'label': 'Mensual'},
        {'value': 'biweekly', 'label': 'Quincenal'},
        {'value': 'weekly', 'label': 'Semanal'},
    ],
    'plan_type': [{'value': 'individual', 'label': 'Individual'}, {'value': 'group', 'label': 'Grupal'}],
    'guardian_type': [
        {'value': 'padre', 'label': 'Padre'},
        {'value': 'madre', 'label': 'Madre'},
        {'value': 'tutor', 'label': 'Tutor'},
        {'value': 'otro', 'label': 'Otro'},
    ],
    'days_of_week': [
        {'value': i, 'label': d} for i, d in enumerate(['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado'])
    ],
}

# Crear usuario: los mismos pasos del panel de Usuarios, y cada campo solo para el tipo de usuario que lo usa.
_PATIENT = {'role': ['jugador']}
_STAFF_SEDES = {'role': ['terapista', 'supervisor']}
_SCHEDULE = {'role': ['jugador'], 'generate_schedule': [True]}
FORM_LAYOUT = {
    'create_user': {
        'username': ('Datos', None),
        'email': ('Datos', None),
        'role': ('Datos', None),
        'phone': ('Datos', None),
        'sede_id': ('Datos', _PATIENT),
        'sede_ids': ('Datos', _STAFF_SEDES),
        'modality': ('Plan y horario', _PATIENT),
        'payment_frequency': ('Plan y horario', _PATIENT),
        'plan_type': ('Plan y horario', _PATIENT),
        'payment_amount': ('Plan y horario', _PATIENT),
        'generate_schedule': ('Plan y horario', _PATIENT),
        'evaluation_date': ('Plan y horario', _SCHEDULE),
        'start_date': ('Plan y horario', _SCHEDULE),
        'start_time': ('Plan y horario', _SCHEDULE),
        'therapist_id': ('Plan y horario', _SCHEDULE),
        'days_of_week': ('Plan y horario', _SCHEDULE),
        'guardian': ('Apoderado', _PATIENT),
        'guardian_type': ('Apoderado', _PATIENT),
        'guardian_dni': ('Apoderado', _PATIENT),
        'guardian_contact': ('Apoderado', _PATIENT),
        'salary_base': ('Contrato', {'role': ['terapista']}),
        'contract_hours': ('Contrato', {'role': ['terapista']}),
    },
}
FORM_LAYOUT['drive_save_upload'] = {'folder': ('Guardar en el Drive', None), 'name': ('Guardar en el Drive', None)}
FORM_LAYOUT['print_drive_file'] = {
    'copies': ('Impresión', None),
    'color': ('Impresión', None),
}
# Valores por defecto del formulario (los mismos del panel).
FORM_DEFAULTS = {
    'create_user': {'payment_frequency': 'monthly', 'plan_type': 'individual', 'generate_schedule': True},
    'patient_report': {'with_ai': True},
    'print_drive_file': {'copies': 1, 'color': True},
}

# Campos que la herramienta pide por id: nadie se sabe los ids, así que se eligen por nombre en una lista con
# búsqueda y se manda el id. (roles que entran en la lista)
PERSON_FIELDS = {
    'patient_id': ('jugador',),
    'therapist_id': ('terapista',),
    'assigned_therapist_id': ('terapista',),
    'user_id': None,
    'assignee_id': ('admin', 'supervisor', 'terapista'),
}
ROLE_OPTIONS = [
    {'value': 'jugador', 'label': 'Paciente'},
    {'value': 'terapista', 'label': 'Terapeuta'},
    {'value': 'supervisor', 'label': 'Supervisor'},
    {'value': 'admin', 'label': 'Administrador'},
]


def _people(roles, user):
    """Personas para un campo de id, «Nombre · código»; el supervisor solo ve las de su sede."""
    # Un paciente sin correo es una cuenta «presencial» (is_active=False) pero es paciente igual: cuenta el estado.
    q = User.query.filter(
        db.or_(User.account_status.is_(None), User.account_status != 'retired'),
        db.or_(User.role == 'jugador', User.is_active.isnot(False)),
    )
    if roles:
        q = q.filter(User.role.in_(roles))
    if user is not None and user.role == 'supervisor':
        from app.services.assistant_analytics import scope_for

        try:
            q = q.filter(User.sede_id == scope_for(user))
        except Exception:  # noqa: BLE001 - sin sede asignada: lista vacía, el backend igual valida
            return []
    rows = q.order_by(User.username).limit(1000).all()
    return [{'value': u.id, 'label': f'{u.username} · {u.login_code}' if u.login_code else u.username} for u in rows]


def _short_title(text):
    """«Crea un contrato de servicio para un paciente con…» → «Crea un contrato de servicio»."""
    t = re.split(r'[:.(]', text)[0].strip()
    if len(t) > 44:
        cuts = [i for i in (t.find(w, 12) for w in (' con ', ' para ', ' y ', ' de un ', ' a un ')) if i > 0]
        if cuts:
            t = t[: min(cuts)]
    return t[:80]


def _field(key, spec, required, user=None):
    """Campo del formulario de una acción, a partir del esquema JSON de la herramienta."""
    kind = spec.get('type') or 'string'
    desc = spec.get('description') or ''
    default_label = (desc or key.replace('_', ' ')).split('(')[0].split(':')[0].split('.')[0]
    default_label = re.sub(r'\s*(YYYY-MM-DD|HH:MM)\b.*', '', default_label)
    out = {
        'key': key,
        'label': FIELD_LABELS.get(key) or default_label.strip()[:60] or key,
        'type': 'enum' if spec.get('enum') else kind,
        'required': key in required,
    }
    if spec.get('enum'):
        out['options'] = [{'value': o, 'label': str(o)} for o in spec['enum']]
    if key in FIELD_OPTIONS:
        out['options'] = FIELD_OPTIONS[key]
    if kind == 'array':
        out['type'] = 'list'
    # Qué control de fecha/hora usar (el esquema lo dice en la descripción).
    if 'YYYY-MM-DD HH:MM' in desc:
        out['input'] = 'datetime'
    elif 'YYYY-MM-DD' in desc or key.endswith('_date') or key == 'date':
        out['input'] = 'date'
    elif 'HH:MM' in desc or key.endswith('_time'):
        out['input'] = 'time'
    if key == 'role':
        out.update(type='enum', options=ROLE_OPTIONS)
    if key in ('sede_id', 'sede_ids'):
        from app.models import Sede

        sedes = Sede.query.filter(db.or_(Sede.is_active.is_(True), Sede.is_active.is_(None))).order_by(Sede.name).all()
        out.update(options=[{'value': x.id, 'label': x.name} for x in sedes])
        if key == 'sede_id':
            out['type'] = 'enum'
    if key in PERSON_FIELDS and kind == 'integer':
        out.update(type='enum', options=_people(PERSON_FIELDS[key], user), searchable=True)
    if out['type'] == 'enum' and len(out.get('options') or []) > 8:
        out['searchable'] = True
    return out


def action_block(name, args, user=None):
    """Bloque de acción por confirmar: los campos salen del esquema de la herramienta, con lo que ya dijo el usuario."""
    from app.services.tools_registry import TOOL_REGISTRY

    spec = TOOL_REGISTRY.get(name) or {}
    params = (spec.get('parameters') or {}).get('properties') or {}
    required = set((spec.get('parameters') or {}).get('required') or [])
    fields = [_field(k, v, required, user) for k, v in params.items()]
    layout = FORM_LAYOUT.get(name)
    if layout:
        fields = [f for f in fields if f['key'] in layout]
        fields.sort(key=lambda f: list(layout).index(f['key']))
        for f in fields:
            section, show_if = layout[f['key']]
            f['section'] = section
            if show_if:
                f['show_if'] = show_if
    args = {**FORM_DEFAULTS.get(name, {}), **(args or {})}
    title = _short_title(spec.get('description') or name)
    return {'type': 'action', 'tool': name, 'title': title, 'args': args, 'fields': fields, 'status': 'pending'}


def _noop(*_a, **_k):
    return None


def _from_agent(events, step):
    """Recorre los eventos de MiMo (opencode + herramientas MCP) y arma el resultado; cuenta el avance con `step`."""
    from app.services.tools_registry import TOOL_REGISTRY

    text, pending, calls = '', None, []
    for ev in events:
        kind = ev.get('type')
        if kind == 'thinking' and ev.get('content'):
            step(ev['content'][:160], ev.get('tool'))
        elif kind == 'tool_call':
            desc = (TOOL_REGISTRY.get(ev['name']) or {}).get('description') or ev['name']
            step(f'Consultando: {_short_title(desc).lower()}', ev['name'])
        elif kind == 'tool_result':
            calls.append({'name': ev['name']})
        elif kind == 'confirm':
            pending = {'name': ev['name'], 'args': ev.get('args') or {}}
        elif kind == 'final':
            text = ev.get('content') or text
        elif kind == 'done':
            pending = pending or ev.get('pending_confirm')
            calls = calls or [{'name': c.get('name')} for c in ev.get('tool_calls') or []]
    return {'response': text, 'tool_calls': calls, 'provider': 'opencode', 'pending': pending}


def _general_ai(question, user, history, step=_noop, model=None):
    """Lo que no es una cifra ni un formulario conocido: MiMo con todas las herramientas MCP del rol (las mismas del
    chat flotante), con el avance en vivo. Si MiMo no está, la cadena de respaldo.

    model: None/'auto'/'mimo' = MiMo primero; otro (p. ej. 'groq') = ese modelo de la cadena, sin pasar por MiMo."""
    from app.services import llm_client, opencode_agent
    from app.services.opencode_client import OpencodeUnavailableError

    result = None
    use_mimo = model in (None, '', 'auto', 'mimo')
    if use_mimo and opencode_agent.enabled_for(user):
        step('Pensando con MiMo…')
        try:
            result = _from_agent(opencode_agent.run(user, SCREEN_HINT + question, history=history, mode='grande'), step)
        except OpencodeUnavailableError as exc:
            current_app.logger.warning(f'asistente: MiMo no disponible, sigo con el respaldo: {exc}')
            step('MiMo no responde ahora; sigo con el modelo de respaldo…')
        except Exception as exc:  # noqa: BLE001
            current_app.logger.warning(f'asistente: MiMo falló: {exc}')
    if result is None:
        from app.routes.mcp_routes import mcp_service

        if not use_mimo:
            step(f'Respondiendo con {model}…')
        token = llm_client.PREFERRED_PROVIDER.set(None if use_mimo else model)
        try:
            raw = mcp_service.process_message(
                message=SCREEN_HINT + question,
                user_role=user.role,
                user_id=user.id,
                mode='grande',
                history=history,
                skip_opencode=True,
            )
        except Exception as exc:  # noqa: BLE001 - la IA puede caerse: se responde algo útil igual
            current_app.logger.warning(f'asistente: IA general no respondió: {exc}')
            raw = None
        finally:
            llm_client.PREFERRED_PROVIDER.reset(token)
        raw = raw or {}
        result = {
            'response': raw.get('response'),
            'tool_calls': raw.get('tool_calls') or [],
            'provider': raw.get('provider'),
            'pending': raw.get('pending_tool') if raw.get('requires_confirmation') else None,
        }
    text = result.get('response') or ''
    if not text or text.startswith(('Error procesando', 'All LLM providers')):
        # El error técnico del proveedor no le sirve a nadie en pantalla: va al log.
        if text:
            current_app.logger.warning(f'asistente: respaldo falló: {text[:300]}')
        text = (
            'Ahora no tengo un modelo de IA disponible (MiMo no responde y el respaldo falló). '
            'Las cifras del centro y los formularios siguen funcionando: prueba «¿cómo vamos este mes?» '
            'o «crear un paciente».'
        )
    pending = result.get('pending')
    if pending and pending.get('name'):
        return _action_answer(
            pending['name'], pending.get('args'), user, _model_label(result), intro=result.get('response')
        )
    return {
        'title': question[:80],
        'blocks': [{'type': 'text', 'md': text}],
        'sources': [{'tool': t.get('name') or t.get('tool'), 'scope': 'IA'} for t in result.get('tool_calls') or []],
        'model': _model_label(result),
    }


def _action_answer(tool, args, user, model, intro=None):
    block = action_block(tool, args, user)
    lead = 'Completa el formulario y confirma.' if not args else 'Revisa los datos, completa lo que falte y confirma.'
    return {
        'title': block['title'][:80],
        'blocks': [{'type': 'text', 'md': (intro or '').strip() or lead}, block],
        'sources': [{'tool': tool, 'scope': 'acción por confirmar'}],
        'model': model,
    }


# ── formularios al instante (sin esperar al modelo) ─────────────────────────
# «quiero crear un usuario», «registra un pago», «agenda sesiones a Liam»: se abre el formulario de la herramienta
# MCP al momento, con lo que se pueda deducir (rol, persona nombrada). Lo demás va a MiMo.
_DO = re.compile(
    r'\b(crea|crear|creame|registra|registrar|registrame|agrega|agregar|anade|anadir|nuevo|nueva|da de alta|'
    r'dar de alta|inscribe|inscribir|agenda|agendar|agendale|programa|programar|anota|anotar|quiero|quisiera|'
    r'necesito|hazme|haz)\b'
)
_ASKING = re.compile(r'\b(cuant[oa]s?|cuales|quienes|lista|listar|muestra|mostrar|ver|saber|como (se|hago|puedo))\b')
QUICK = [
    # (patrón del objeto, herramienta del admin/supervisor, herramienta del terapeuta, args)
    (r'\b(paciente|alumno|nino|nina|jugador)\b', 'create_user', 'request_patient_signup', {'role': 'jugador'}),
    (r'\b(terapeuta|terapista)\b', 'create_user', None, {'role': 'terapista'}),
    (r'\bsupervisor\b', 'create_user', None, {'role': 'supervisor'}),
    (r'\badministrador\b', 'create_user', None, {'role': 'admin'}),
    (r'\busuario\b', 'create_user', None, {}),
    (r'\bcontrato\b', 'create_service_contract', None, {}),
    (r'\b(pago|cobro|abono)\b', 'register_payment', 'register_payment', {}),
    (r'\bsesion(es)?\b', 'schedule_programmed_session', 'request_sessions', {}),
    (r'\bgasto\b', 'create_expense', None, {}),
    (r'\bincidencia\b', 'create_incident', None, {}),
    (r'\bgrupo\b', 'create_patient_group', None, {}),
]


def quick_action(question, user):
    """Herramienta + args si la pregunta es «haz X» de un formulario conocido; si no, None."""
    from app.services.tools_registry import TOOL_REGISTRY

    q = analytics._norm(question)
    if re.search(r'\b(informe|reporte|evolucion|historial clinico)\b', q) and user.role in ('admin', 'supervisor'):
        # «informe de Liam», «evolución de Liam»: el informe del alumno (con el paciente ya elegido si se nombra).
        args = {'with_ai': True}
        _prefill_people('patient_report', q, args, user)
        about_patient = re.search(r'\b(terapeutic[oa]|alumno|paciente|nino|nina|sesiones)\b', q)
        if args.get('patient_id') or (about_patient and _DO.search(q)):
            return 'patient_report', args
    if not _DO.search(q) or _ASKING.search(q):
        return None
    for pattern, staff_tool, therapist_tool, base_args in QUICK:
        if not re.search(pattern, q):
            continue
        tool = therapist_tool if user.role == 'terapista' else staff_tool
        spec = TOOL_REGISTRY.get(tool or '') or {}
        roles = spec.get('roles')
        if not tool or not spec or (roles and user.role not in roles):
            return None
        args = dict(base_args)
        named = _prefill_people(tool, q, args, user)
        # Si trae datos (un nombre nuevo, un monto, una fecha), MiMo los pone en el formulario; aquí se perderían.
        words = re.findall(r'[\wáéíóúñÁÉÍÓÚÑ]+', question)
        extra = [w for w in words[1:] if w[:1].isupper() and analytics._norm(w) not in named] or re.search(r'\d', q)
        return None if extra else (tool, args)
    return None


def _prefill_people(tool, q, args, user):
    """Si la pregunta nombra a un paciente/terapeuta que existe, ya va elegido en el formulario. Devuelve sus palabras."""
    named = set()
    for f in action_block(tool, {}, user)['fields']:
        if f['key'] not in PERSON_FIELDS:
            continue
        hits = [o for o in f.get('options') or [] if analytics._norm(o['label'].split(' · ')[0]) in q]
        if len(hits) == 1:
            args[f['key']] = hits[0]['value']
            named.update(analytics._norm(hits[0]['label'].split(' · ')[0]).split())
    return named


def _model_label(result):
    """Quién respondió, en palabras: «MiMo» o el respaldo (Ollama, Groq…) cuando MiMo no estuvo disponible."""
    provider = (result or {}).get('provider') or ''
    if provider == 'opencode':
        return 'MiMo (opencode)'
    return f'{provider} (respaldo)' if provider else 'IA del centro'


def compute(question, user, history=None, follow_ai=False, step=_noop, model=None):
    """La respuesta (sin guardar): datos del centro si se reconoce la pregunta; si no, la IA general.

    follow_ai: el hilo viene de una conversación con la IA (p. ej. creando un usuario). Un seguimiento como
    «¿qué falta?» sigue con ella; solo se pasa al análisis si la pregunta lo pide claramente.
    """
    try:
        res = analytics.answer(question, user, strict=follow_ai)
    except analytics.ScopeError as exc:
        raise AssistantError(str(exc), 403) from exc
    if res:
        return res
    quick = quick_action(question, user)
    if quick:
        return _action_answer(quick[0], quick[1], user, 'formulario del sistema')
    return _general_ai(question, user, history or [], step, model)


def _follows_ai(thread):
    if not thread:
        return False
    last = thread.messages.filter_by(role='assistant').order_by(AssistantMessage.id.desc()).first()
    return bool(last and last.model and last.model != analytics.MODEL_NAME)


def _plain(blocks):
    return '\n\n'.join(b['md'] for b in blocks if b.get('type') == 'text')


def ask(user, question, thread_id=None, step=_noop, model=None, attachment=None):
    question = (question or '').strip()
    if not question and not attachment:
        raise AssistantError('Escribe una pregunta')
    if len(question) > 2000:
        raise AssistantError('La pregunta es muy larga (máx. 2000 caracteres)')
    thread = get_thread(thread_id, user, write=True) if thread_id else None
    history = _history(thread) if thread else []
    if attachment:
        from app.services import assistant_files

        try:
            res = assistant_files.analyze(attachment, question, user, step=step, model=model)
        except assistant_files.FileError as exc:
            raise AssistantError(str(exc)) from exc
        label = f'📎 {attachment.get("name") or "archivo"}'
        question = f'{label} — {question}' if question else label
    else:
        res = compute(question, user, history, follow_ai=_follows_ai(thread), step=step, model=model)
    now = datetime.utcnow()
    if thread is None:
        thread = AssistantThread(user_id=user.id, title=(res.get('title') or question)[:160], created_at=now)
        db.session.add(thread)
        db.session.flush()
    db.session.add(AssistantMessage(thread_id=thread.id, role='user', text=question, created_at=now))
    answer = AssistantMessage(
        thread_id=thread.id,
        role='assistant',
        text=_plain(res['blocks']),
        blocks=res['blocks'],
        sources=res.get('sources') or [],
        model=res.get('model'),
        question=None if attachment else question,  # un archivo no se «actualiza» volviendo a preguntar
        created_at=now,
    )
    db.session.add(answer)
    thread.updated_at = now
    db.session.commit()
    return thread, answer


def models_status(user):
    """Para la barra de modelo: estado de MiMo (cuota) y los modelos de respaldo que se pueden elegir."""
    from app.services import llm_client, opencode_agent, opencode_client

    mimo = opencode_client.state()
    enabled = opencode_agent.assigned_to(user)
    reason = mimo.get('last_error') or ''
    return {
        'mimo': {
            'enabled': enabled,
            'available': enabled and mimo['configured'] and not mimo['blocked'],
            'blocked_for': mimo['blocked_for'],
            'quota': opencode_client._is_quota(reason),
            'reason': reason[:160] if mimo['blocked'] else '',
        },
        'models': [{'key': 'auto', 'label': 'MiMo (automático)', 'blocked': not enabled or mimo['blocked']}]
        + llm_client.available_providers(),
    }


def refresh(user, message_id):
    m = db.session.get(AssistantMessage, message_id)
    if not m or m.role != 'assistant' or not m.question:
        raise AssistantError('Respuesta no encontrada', 404)
    get_thread(m.thread_id, user, write=True)
    res = compute(m.question, user)
    m.blocks, m.sources, m.model, m.text = (
        res['blocks'],
        res.get('sources') or [],
        res.get('model'),
        _plain(res['blocks']),
    )
    m.created_at = datetime.utcnow()
    db.session.commit()
    return m


def run_action(user, message_id, args, block_index=None):
    """El usuario revisó el formulario y confirmó: se ejecuta con sus permisos y queda en la conversación."""
    from app.services.tools_registry import TOOL_REGISTRY, execute_tool

    m = db.session.get(AssistantMessage, message_id)
    if not m or m.role != 'assistant':
        raise AssistantError('Respuesta no encontrada', 404)
    thread = get_thread(m.thread_id, user, write=True)
    blocks = list(m.blocks or [])
    pending = [i for i, b in enumerate(blocks) if b.get('type') == 'action']
    idx = block_index if block_index in pending else next(iter(pending), None)
    if idx is None:
        raise AssistantError('Esta respuesta no tiene una acción por confirmar')
    block = dict(blocks[idx])
    if block.get('status') == 'done':
        raise AssistantError('Esa acción ya se hizo')
    name = block['tool']
    if name not in TOOL_REGISTRY:
        raise AssistantError('Esa acción ya no existe', 404)
    clean = {k: v for k, v in (args or {}).items() if v not in (None, '', [])}
    # Lo que no se muestra en el formulario (p. ej. el archivo subido) viaja tal cual se propuso.
    shown = {f['key'] for f in block.get('fields') or []}
    clean = {**{k: v for k, v in (block.get('args') or {}).items() if k not in shown}, **clean}
    result = execute_tool(name, clean, user_id=user.id, role=user.role)
    ok = isinstance(result, dict) and not result.get('error') and result.get('success', True) is not False
    message = (result or {}).get('message') if isinstance(result, dict) else None
    message = re.sub(r'\s*\(ID:? ?\d+\)', '', message or '') or None
    text = (
        f'Listo: {message}' if ok and message else 'Listo, quedó hecho.' if ok else f'No se pudo: {result.get("error")}'
    )
    block.update(status='done' if ok else 'error', args=clean, result_text=text)
    blocks[idx] = block
    m.blocks = blocks
    follow = _next_steps(name, clean, result, user) if ok else []
    reply = AssistantMessage(
        thread_id=thread.id,
        role='assistant',
        text=text,
        blocks=[{'type': 'text', 'md': text}, *follow],
        sources=[{'tool': name, 'scope': 'acción confirmada'}],
        model='acción confirmada',
        question=None,
    )
    db.session.add(reply)
    thread.updated_at = datetime.utcnow()
    db.session.commit()
    return m, reply


def _next_steps(tool, args, result, user):
    """Después de dar de alta a un paciente (o su contrato), lo que falta del flujo: contrato y sesiones.

    El panel de Usuarios lo hace todo en un paso; si en el formulario se dejó el plan o el horario en blanco, aquí se
    proponen con el paciente ya elegido para que no quede a medias."""
    from app.models import Appointment, User
    from app.models.contract import Contract

    file = (result or {}).get('file') if isinstance(result, dict) else None
    if file and file.get('path'):
        out = [{'type': 'file', 'name': file.get('name'), 'path': file['path'], 'size': file.get('size')}]
        if user.role == 'admin':
            out += [
                {'type': 'text', 'md': '¿Lo imprimo?'},
                action_block('print_drive_file', {'path': file['path']}, user),
            ]
        return out

    patient_id = None
    if tool == 'create_user' and (result or {}).get('role') == 'jugador':
        patient_id = result.get('user_id')
    elif tool in ('create_service_contract', 'create_full_patient'):
        patient_id = args.get('patient_id') or (result or {}).get('patient_id') or (result or {}).get('user_id')
    patient = db.session.get(User, int(patient_id)) if patient_id else None
    if not patient or patient.role != 'jugador':
        return []
    out, notes = [], []
    has_contract = Contract.query.filter(Contract.patient_id == patient.id, Contract.is_active.isnot(False)).count()
    sessions = Appointment.query.filter_by(patient_id=patient.id).count()
    if has_contract and tool == 'create_user':
        notes.append('ya tiene su contrato con las cuotas')
    if sessions and tool == 'create_user':
        notes.append(f'ya tiene {sessions} sesiones programadas')
    if not has_contract:
        c_args = {'patient_id': patient.id}
        if args.get('payment_amount'):
            c_args['total_amount'] = args['payment_amount']
        if args.get('start_date'):
            c_args['start_date'] = args['start_date']
        out += [{'type': 'text', 'md': f'**Siguiente paso:** el contrato de {patient.username}.'}]
        out.append(action_block('create_service_contract', c_args, user))
    if not sessions:
        s_args = {'patient_id': patient.id}
        for key in ('therapist_id', 'modality', 'start_date', 'start_time', 'days_of_week', 'evaluation_date'):
            if args.get(key) not in (None, '', []):
                s_args[key] = args[key]
        if not s_args.get('therapist_id') and patient.assigned_therapist_id:
            s_args['therapist_id'] = patient.assigned_therapist_id
        out += [{'type': 'text', 'md': f'**Y sus sesiones:** programa el horario de {patient.username}.'}]
        out.append(action_block('schedule_patient_plan', s_args, user))
    if notes:
        out.insert(0, {'type': 'text', 'md': f'{patient.username} ' + ' y '.join(notes) + '.'})
    return out


def set_feedback(user, message_id, value):
    m = db.session.get(AssistantMessage, message_id)
    if not m or m.role != 'assistant':
        raise AssistantError('Respuesta no encontrada', 404)
    get_thread(m.thread_id, user)
    m.feedback = 1 if value > 0 else -1 if value < 0 else None
    db.session.commit()
    return m


def update_thread(user, thread_id, data):
    thread = get_thread(thread_id, user, write=True)
    if 'title' in data and str(data['title']).strip():
        thread.title = str(data['title']).strip()[:160]
    for key in ('pinned', 'shared'):
        if key in data:
            setattr(thread, key, bool(data[key]))
    db.session.commit()
    return thread


def delete_thread(user, thread_id):
    thread = get_thread(thread_id, user, write=True)
    AssistantSchedule.query.filter_by(thread_id=thread.id).update({'thread_id': None})
    db.session.delete(thread)
    db.session.commit()


def purge_old(now=None):
    """Retención: conversaciones no fijadas sin actividad en 180 días."""
    limit = (now or datetime.utcnow()) - timedelta(days=RETENTION_DAYS)
    old = AssistantThread.query.filter(AssistantThread.pinned.is_(False), AssistantThread.updated_at < limit).all()
    for t in old:
        db.session.delete(t)
    db.session.commit()
    return len(old)


# ── reportes programados ────────────────────────────────────────────────────
CADENCES = ('daily', 'weekly')
CHANNELS = ('email', 'telegram', 'both')
WEEKDAYS = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']


def schedule_dict(s):
    when = f'cada día a las {s.hour:02d}:00'
    if s.cadence == 'weekly':
        when = f'cada {WEEKDAYS[s.weekday or 0]} a las {s.hour:02d}:00'
    return {
        'id': s.id,
        'question': s.question,
        'cadence': s.cadence,
        'weekday': s.weekday,
        'hour': s.hour,
        'channel': s.channel,
        'active': s.active,
        'thread_id': s.thread_id,
        'label': when,
        'last_run_at': s.last_run_at.isoformat() + 'Z' if s.last_run_at else None,
    }


def create_schedule(user, data):
    question = (data.get('question') or '').strip()
    if not question:
        raise AssistantError('Falta la pregunta a repetir')
    cadence = data.get('cadence') or 'weekly'
    channel = data.get('channel') or 'email'
    hour = int(data.get('hour') if data.get('hour') is not None else 8)
    weekday = int(data.get('weekday') or 0)
    if cadence not in CADENCES or channel not in CHANNELS or not 0 <= hour <= 23 or not 0 <= weekday <= 6:
        raise AssistantError('Programación no válida')
    if analytics.answer(question, user) is None:
        raise AssistantError(
            'Solo se pueden programar preguntas de datos del centro (resumen, sedes, equipo, deudores…).'
        )
    thread_id = data.get('thread_id')
    if thread_id:
        get_thread(int(thread_id), user, write=True)
    s = AssistantSchedule(
        user_id=user.id,
        thread_id=thread_id,
        question=question[:2000],
        cadence=cadence,
        weekday=weekday if cadence == 'weekly' else None,
        hour=hour,
        channel=channel,
    )
    db.session.add(s)
    db.session.commit()
    return s


def delete_schedule(user, schedule_id):
    s = db.session.get(AssistantSchedule, schedule_id)
    if not s or s.user_id != user.id:
        raise AssistantError('Programación no encontrada', 404)
    db.session.delete(s)
    db.session.commit()


def _due(s, now_lima):
    if not s.active or now_lima.hour != s.hour:
        return False
    if s.cadence == 'weekly' and now_lima.weekday() != (s.weekday or 0):
        return False
    return not (s.last_run_at and s.last_run_at > datetime.utcnow() - timedelta(hours=20))


def _render_text(res):
    lines = [_plain(res['blocks']).replace('**', '')]
    for b in res['blocks']:
        if b['type'] == 'kpis':
            for k in b['items']:
                lines.append(f'· {k["label"]}: {analytics._fmt(k["value"], k["format"])}')
        if b['type'] == 'table':
            lines.append(f'\n{b["title"]}:')
            for r in b['rows'][:15]:
                lines.append(
                    '· '
                    + ' · '.join(str(r.get(c['key']) if r.get(c['key']) is not None else '—') for c in b['columns'])
                )
    return '\n'.join(lines)


def run_schedules(now_lima=None):
    """Lo llama el scheduler cada hora: corre las preguntas programadas y manda la respuesta."""
    from zoneinfo import ZoneInfo

    now_lima = now_lima or datetime.now(ZoneInfo('America/Lima'))
    sent = 0
    for s in AssistantSchedule.query.filter_by(active=True).all():
        if not _due(s, now_lima):
            continue
        user = db.session.get(User, s.user_id)
        if not user or not user.is_active:
            continue
        try:
            res = analytics.answer(s.question, user)
        except analytics.ScopeError:
            continue
        if not res:
            continue
        text = _render_text(res)
        subject = f'[Moscowle] {res["title"]}'
        if s.channel in ('email', 'both'):
            _send_email(user, subject, text)
        if s.channel in ('telegram', 'both'):
            _send_telegram(user, f'*{res["title"]}*\n\n{text}')
        if s.thread_id:
            thread = db.session.get(AssistantThread, s.thread_id)
            if thread:
                db.session.add(
                    AssistantMessage(
                        thread_id=thread.id,
                        role='assistant',
                        text=_plain(res['blocks']),
                        blocks=res['blocks'],
                        sources=res.get('sources'),
                        model='reporte programado',
                        question=s.question,
                    )
                )
                thread.updated_at = datetime.utcnow()
        s.last_run_at = datetime.utcnow()
        db.session.commit()
        sent += 1
    return sent


def _send_email(user, subject, text):
    from app.services.email_service import EmailService, recipient_for

    to = recipient_for(user)
    if to:
        EmailService.send_notification_email(subject, [to], body=text, user_id=user.id)


def _send_telegram(user, text):
    try:
        from app.models.telegram_user import TelegramUser
        from app.services.telegram_bot_service import send_telegram_message

        for tg in TelegramUser.query.filter_by(admin_user_id=user.id, is_linked=True).all():
            send_telegram_message(tg.telegram_chat_id, text[:3900])
    except Exception as exc:  # noqa: BLE001
        current_app.logger.warning(f'asistente: no se pudo enviar por Telegram: {exc}')
