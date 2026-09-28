"""Resolucion de entidades del mensaje a datos reales de la base.

Por que esto NO lo hace el LLM:
"sedes talara y piura" tiene que convertirse en sede_id=1 y sede_id=2. Eso es
una busqueda exacta sobre la tabla Sede, no un problema de lenguaje. Un modelo
de 1.5B no puede resolverlo de forma fiable y antes terminaba inventando el
numero de sedes. Aqui es codigo: determinista, testeable y sin coste de GPU.

El resolutor tambien es la primera barrera de datos: si el rol no tiene acceso
a una entidad, no se resuelve, y el modelo nunca ve el identificador.
"""

import re
import unicodedata

# Palabras que activan la busqueda de una sede en el mensaje.
_SEDE_CUES = (
    'sede', 'sedes', 'sucursal', 'sucursales', 'establecimiento',
    'establecimientos', 'local', 'locales', 'centro',
)

# Expresiones temporales que el modelo deberia normalizar, no inventar.
_TEMPORAL_PATTERNS = {
    'hoy': ['hoy', 'este dia', 'dia de hoy', 'a dia de hoy'],
    'manana': ['manana', 'mañana', 'el dia siguiente', 'proximo dia'],
    'ayer': ['ayer', 'el dia anterior'],
    'semana_pasada': ['semana pasada', 'semana anterior', 'la semana pasada'],
    'mes_pasado': ['mes pasado', 'mes anterior', 'el mes pasado'],
    'este_mes': ['este mes', 'mes actual', 'del mes', 'mensualidad', 'mensual'],
    'anio_pasado': ['ano pasado', 'anio anterior', 'el ano pasado'],
}

_NON_WORD_RE = re.compile(r'[^a-z0-9]+')


def _strip_accents(text):
    return ''.join(
        c for c in unicodedata.normalize('NFD', (text or '').lower())
        if unicodedata.category(c) != 'Mn'
    )


def _norm(text):
    """minusculas, sin acentos, solo alfanumericos y espacios colapsados."""
    clean = _strip_accents(text)
    clean = _NON_WORD_RE.sub(' ', clean)
    return ' '.join(clean.split())


def _contains_phrase(haystack_norm, original_low):
    """True si la frase aparece como subcadena, respetando acentos en el original.

    Se comparan dos formas porque el usuario puede escribir con o sin tildes y
    la BD puede tener nombres con tildes.
    """
    return _norm(original_low) in haystack_norm


class ResolvedEntities:
    """Resultado de la resolucion. Vacio significa 'nada que inyectar'."""

    __slots__ = ('sedes', 'patients', 'therapists', 'temporal', 'raw_message')

    def __init__(self, sedes=None, patients=None, therapists=None, temporal=None, raw_message=''):
        self.sedes = sedes or []
        self.patients = patients or []
        self.therapists = therapists or []
        self.temporal = temporal or []
        self.raw_message = raw_message

    def __bool__(self):
        return bool(self.sedes or self.patients or self.therapists or self.temporal)

    def to_prompt_context(self):
        """Texto compacto para pegar en el prompt del sintetizador.

        Se inyecta como HECHO VERIFICADO, no como sugerencia: el modelo debe
        usar estos identificadores tal cual.
        """
        lines = []
        if self.sedes:
            items = ', '.join(f'{s["name"]} (id={s["id"]})' for s in self.sedes)
            lines.append(f'Sedes referenciadas en la consulta: {items}.')
        if self.patients:
            items = ', '.join(f'{p.get("username") or p.get("email")} (id={p["id"]})' for p in self.patients)
            lines.append(f'Pacientes referenciados: {items}.')
        if self.therapists:
            items = ', '.join(f'{t.get("username") or t.get("email")} (id={t["id"]})' for t in self.therapists)
            lines.append(f'Terapeutas referenciados: {items}.')
        if self.temporal:
            lines.append(f'Referencia temporal mencionada: {", ".join(self.temporal)}.')
        return '\n'.join(lines)

    def __repr__(self):
        return (
            f'<Entities sedes={self.sedes} patients={len(self.patients)} '
            f'therapists={len(self.therapists)} temporal={self.temporal}>'
        )


def _resolve_sedes(message):
    """Busca sedes por nombre dentro del mensaje.

    La palabra 'sede' NO es obligatoria: en produccion la gente escribe
    'cuantos pacientes hay en Talara' sin decir 'sede'. El nombre propio de
    una sede es un token suficientemente especifico, asi que si aparece en el
    mensaje se resuelve. La palabra 'sede' solo sirve para ordenar primero las
    coincidencias explicitas.
    """
    norm_msg = _norm(message)
    if not norm_msg:
        return []
    hay_cue = any(c in norm_msg for c in ('sede', 'sucursal', 'establecimiento', 'local', 'centro'))
    try:
        from app.models.user import Sede
    except Exception:
        return []
    try:
        sedes = Sede.query.filter_by(is_active=True).all()
    except Exception:
        return []
    encontrados = []
    for sede in sedes:
        nombre_norm = _norm(getattr(sede, 'name', '') or '')
        # Un nombre de sede es especifico: exigir 4 caracteres evita ruido.
        if not nombre_norm or len(nombre_norm) < 4:
            continue
        tokens = norm_msg.split()
        coincide = nombre_norm in norm_msg or any(
            tok == nombre_norm or tok.startswith(nombre_norm) for tok in tokens
        )
        if coincide:
            encontrados.append(
                {'id': sede.id, 'name': sede.name, 'address': sede.address or '', '_cue': hay_cue}
            )
    # Las mencionadas explicitamente ('sede Talara') van primero.
    encontrados.sort(key=lambda s: (not s['_cue'], s['name']))
    for item in encontrados:
        item.pop('_cue', None)
    return encontrados


def _resolve_people(message, role):
    """Resuelve pacientes/terapeutas solo si el rol tiene acceso a ellos.

    Un jugador no puede enumerar la agenda por nombre: por eso el resolutor
    devuelve vacio antes de tocar la base, y no despues de filtrar.
    """
    if role not in ('admin', 'supervisor', 'terapista'):
        return [], []
    try:
        from app.models.user import User
    except Exception:
        return [], []
    norm_msg = _norm(message)
    if not norm_msg:
        return [], []
    try:
        candidatos = User.query.filter(User.is_active.is_(True)).limit(500).all()
    except Exception:
        return [], []

    patients, therapists = [], []
    for user in candidatos:
        username = _norm(getattr(user, 'username', '') or '')
        if username and len(username) > 3 and username in norm_msg:
            entry = {'id': user.id, 'username': user.username, 'email': user.email, 'role': user.role}
            (therapists if user.role == 'terapista' else patients).append(entry)
    return patients, therapists


def _resolve_temporal(message):
    norm_msg = _norm(message)
    temporal = []
    for key, phrases in _TEMPORAL_PATTERNS.items():
        for phrase in phrases:
            if _norm(phrase) in norm_msg:
                temporal.append(key)
                break
    return temporal


def resolve_entities(message, role=None):
    """Punto de entrada. Devuelve ResolvedEntities (puede estar vacio)."""
    if not message:
        return ResolvedEntities(raw_message='')
    try:
        sedes = _resolve_sedes(message)
        patients, therapists = _resolve_people(message, role)
        temporal = _resolve_temporal(message)
        return ResolvedEntities(
            sedes=sedes, patients=patients, therapists=therapists,
            temporal=temporal, raw_message=message,
        )
    except Exception:
        # La resolucion es una mejora, nunca un punto de falla: si algo falla
        # el chat sigue funcionando con lo que el modelo infiera.
        return ResolvedEntities(raw_message=message)
