"""Índice de intenciones GENERADO desde el catálogo de tools.

Sustituye al mapa hardcodeado ``_LOCAL_FORCE_TOOLS`` (keywords escritas a mano
por tool): las frases disparadoras se derivan de lo que el registro ya declara
— descripción, nombre y parámetros de cada tool — más un léxico genérico
compartido (grupos de conceptos ES y traducción EN→ES de tokens de nombre).

Uso:
    hit = match_intent('cuántas sedes hay', allowed={'list_sedes'})
    -> ('list_sedes', None)   # (tool, arg_spec)

El caller (``mcp_service._force_intent_tool``) resuelve ``arg_spec`` con los
extractores genéricos de fecha/mes que ya existen.

Garantías:
* Solo tools de lectura (o la creación de grupos, que pasa por el gate de
  confirmación) entran al índice.
* Un comando con verbo de escritura ("crea", "elimina"...) jamás fuerza una
  tool de lectura: eso lo decide el router con function-calling.
* La fuerza solo aplica a mensajes que además pasan la "puerta de sustantivo"
  (el mensaje debe mencionar un sustantivo saliente de la tool), lo que evita
  que una palabra genérica como "centro" dispare la tool equivocada.
"""

from __future__ import annotations

import re
import unicodedata
from functools import lru_cache

from app.services.tools_registry import TOOL_REGISTRY

# ---------------------------------------------------------------------------
# Léxico genérico: traducciones de tokens de nombre (EN) -> ES.
# Vocabulario compartido, NO mapeos por tool.
# ---------------------------------------------------------------------------
_NAME_LEXICON = {
    'debtors': 'deudores',
    'debtor': 'deudores',
    'expenses': 'gastos',
    'expense': 'gastos',
    'sessions': 'sesiones',
    'session': 'sesiones',
    'patients': 'pacientes',
    'patient': 'pacientes',
    'users': 'usuarios',
    'user': 'usuarios',
    'financial': 'financiero',
    'finance': 'financiero',
    'summary': 'resumen',
    'growth': 'crecimiento',
    'collection': 'cobranza',
    'stats': 'estadisticas',
    'statistics': 'estadisticas',
    'attendance': 'asistencia',
    'payments': 'pagos',
    'payment': 'pagos',
    'incidents': 'incidencias',
    'incident': 'incidencias',
    'therapist': 'terapeuta',
    'therapists': 'terapeutas',
    'appointments': 'citas',
    'reports': 'reporte',
    'report': 'reporte',
    'detail': 'detalle',
    'details': 'detalle',
    'group': 'grupo',
    'groups': 'grupos',
    'contract': 'contrato',
    'contracts': 'contratos',
    'notification': 'notificaciones',
    'notifications': 'notificaciones',
    'sede': 'sede',
    'current': 'actual',
    'datetime': 'fecha',
    'day': 'dia',
    'date': 'fecha',
    'month': 'mes',
}

# Grupos de conceptos en español: si una tool menciona un miembro, el resto
# también se vuelve frase candidata ("deudores" <-> "morosos" <-> "debe"...).
_CONCEPT_GROUPS = (
    ('agenda', 'sesiones', 'sesion', 'citas', 'cita', 'calendario'),
    ('gastos', 'gasto', 'egresos', 'egreso'),
    (
        'deudores',
        'deudor',
        'morosos',
        'moroso',
        'deuda',
        'deudas',
        'debe',
        'deben',
        'adeuda',
        'adeudan',
        'atrasos',
        'atraso',
    ),
    ('cobranza', 'recaudacion', 'cobrado', 'cobros', 'cobro', 'genero', 'generado', 'recaudo', 'recaudado'),
    ('pacientes', 'paciente', 'jugadores', 'jugador', 'alumnos', 'alumno'),
    ('usuarios', 'usuario'),
    ('sedes', 'sede', 'sucursales', 'sucursal'),
    ('financiero', 'finanzas', 'finanza', 'ingresos', 'ingreso', 'utilidad', 'ganancia'),
    ('terapeutas', 'terapeuta', 'terapista', 'terapistas'),
    ('desempeno', 'scorecard', 'metas', 'meta', 'cumplimiento', 'indicadores', 'kpi', 'kpis', 'rinde', 'rinden'),
)
_CONCEPT_INDEX = {word: group for group in _CONCEPT_GROUPS for word in group}


def _expand(word: str) -> set[str]:
    group = _CONCEPT_INDEX.get(word)
    return set(group) if group else {word}


_STOPWORDS = frozenset(
    [
        'de',
        'del',
        'la',
        'el',
        'los',
        'las',
        'un',
        'una',
        'unos',
        'unas',
        'y',
        'o',
        'en',
        'con',
        'por',
        'para',
        'que',
        'se',
        'su',
        'sus',
        'al',
        'lo',
        'como',
        'mas',
        'muy',
        'todo',
        'todos',
        'toda',
        'todas',
        'mismo',
        'mismo',
        'cada',
        'desde',
        'entre',
        'sobre',
        'hasta',
        'sin',
        'tras',
        'ante',
        'bajo',
        'cuando',
        'donde',
        'cual',
        'cuales',
        'quien',
        'quienes',
        'porque',
        'pero',
        'sino',
        'ya',
        'tambien',
        'solo',
        'este',
        'esta',
        'esto',
        'estos',
        'estas',
        'ese',
        'esa',
        'eso',
        'aquel',
        'retorna',
        'devuelve',
        'muestra',
        'lista',
        'listar',
        'obtener',
        'obtiene',
        'sistema',
        'actual',
        'filtra',
        'filtrar',
        'filtros',
        'opcionales',
        'opcion',
        'especifico',
        'especifica',
        'mediante',
        'segun',
        'puede',
        'pueden',
        'permiten',
        'permitiendo',
        'incluye',
        'incluyen',
        'datos',
        'info',
        'informacion',
        'ver',
        'las',
        'las',
    ]
)

_QUERY_MARKERS = frozenset(
    [
        'que',
        'cuales',
        'cuanto',
        'cuantos',
        'cuantas',
        'cuanta',
        'quien',
        'lista',
        'listar',
        'muestr',
        'dame',
        'dime',
        'necesito',
        'necesitas',
        'quiere',
        'ver',
        'hay',
        'estado',
        'resumen',
        'reporte',
        'reporta',
        'detalla',
        'actualmente',
        'dias',
        'hoy',
        'manana',
        'ayer',
        'este',
        'mes',
        'semana',
        'cual',
        'cuanto',
        'debe',
        'pendiente',
    ]
)

_WRITE_VERB_RE = re.compile(
    r'\b(crea|crear|creo|registra|registrar|registro|actualiza|actualizar|'
    r'elimina|eliminar|borra|borrar|asigna|asignar|agrega|agregar|modifica|modificar|'
    r'programa|programar|envia|enviar|marca|marcar|cierra|cerrar|paga|pagar|'
    r'reprograma|reprogramar|cambia|cambiar|edita|editar|mueve|mover|corrige|corregir|'
    r'quita|quitar|anula|anular|cancela|cancelar|pospone|posponer|activa|activar|'
    r'desactiva|desactivar|completa|completar)\b'
)

_COUNT_RE = re.compile(r'\bcuant(?:es|as|a|o|os)\b|\bcuanto\b|\btotal de\b|\bcantidad de\b|\bnumero de\b')

_METRIC_RE = re.compile(r'\b(metricas?|crecimiento|rendimiento|eficiencia|efficiency)\b')

# Tokens de nombre que NO son entidades (verbos/abreviaturas del catálogo).
_NAME_NON_ENTITIES = frozenset(
    [
        'get',
        'list',
        'search',
        'create',
        'add',
        'update',
        'delete',
        'fetch',
        'build',
        'send',
        'check',
        'view',
        'show',
        'detail',
        'summary',
        'stats',
        'report',
        'all',
        'current',
        'datetime',
        'day',
        'date',
        'month',
    ]
)

_BOT_CONTEXT_RE = re.compile(r'\b(tu nombre|eres tu|como estas|quien eres|que puedes hacer|tu edad|me quieres)\b')

_ROL_RE = re.compile(r'rol:\s*([a-záéíóúñ,\s]+)', re.IGNORECASE)

# Pista temporal en el mensaje: permite saltarse la puerta de sustantivos a
# las tools con parámetro de fecha (p.ej. "qué hay el lunes").
_DATE_HINT_RE = re.compile(
    r'\b(hoy|manana|ayer|lunes|martes|miercoles|jueves|viernes|sabado|domingo)\b'
    r'|\b\d{1,2}\s*[/\-]\s*\d{1,2}\b'
)


def norm(value) -> str:
    """Minúsculas sin acentos, espacios colapsados (matching robusto)."""
    text = unicodedata.normalize('NFD', str(value or '').lower())
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    return re.sub(r'\s+', ' ', text).strip()


def _words(text: str) -> list[str]:
    return re.findall(r'[a-z]+', norm(text))


def _content_words(text: str) -> list[str]:
    return [t for t in _words(text) if t not in _STOPWORDS and len(t) > 2]


def _match(phrase: str, msg_norm: str) -> bool:
    """Coincide por palabra completa (plural incluido) sobre el msg normalizado."""
    if not phrase:
        return False
    return re.search(rf'\b{re.escape(phrase)}(?:s|es)?\b', msg_norm) is not None


def _role_variants(role: str) -> list[str]:
    """Plurales/variantes ES de un rol: terapista -> terapista(s), terapeuta(s);
    jugador -> jugador(es); supervisor -> supervisor(es); admin -> admin(s)."""
    role = norm(role)
    out = {role, f'{role}s'}
    if role.endswith(('r', 'z')):
        out.add(f'{role}es')
    if role.endswith('ista'):
        alt = role[:-4] + 'euta'  # terapista -> terapeuta
        out |= {alt, f'{alt}s'}
    return sorted(v for v in out if v)


def _ngrams(words: list[str], size: int) -> list[str]:
    return [' '.join(words[i : i + size]) for i in range(len(words) - size + 1)]


def _phrase_candidates(entry: dict) -> tuple[set[str], set[str], bool, frozenset]:
    """Frases, sustantivos de puerta, flag estadístico y palabras de rol."""
    desc = entry.get('description') or ''
    params = (entry.get('parameters') or {}).get('properties') or {}
    phrases: set[str] = set()

    # 1) Tokens del nombre traducidos con el léxico genérico.
    for tok in re.findall(r'[a-z]+', (entry['name'] or '').lower()):
        phrases.add(norm(_NAME_LEXICON.get(tok, tok)))

    # 2) Sustantivos salientes (primeros 6) en crudo + sus conceptos ("debe",
    #    "morosos"... entran como frases de la propia tool).
    nouns = _content_words(desc)[:6]
    phrases.update(nouns)
    for n in nouns[:3]:
        phrases.update(_expand(n))

    # 3) Sustantivos de puerta: los 3 primeros + sus expansiones de concepto.
    gate_nouns = set()
    for n in nouns[:3]:
        gate_nouns |= _expand(n)
    gate_nouns = {norm(g) for g in gate_nouns if len(g) > 2}

    # 4) N-gramas de 2 y 3 palabras de la PRIMERA oración (incluye
    #    interiores con partículas: "reporte de deudores", "deudores por sede").
    first_sentence = re.split(r'[.:]', desc)[0]
    sent_words = _words(first_sentence)
    for size in (3, 2):
        for gram in _ngrams(sent_words, size):
            if any(w not in _STOPWORDS and len(w) > 2 for w in gram.split()):
                phrases.add(gram)

    # 4b) Frases de uso entre comillas (la descripción enseña el patrón real:
    #     'Uso tipico: "cuantos usuarios tiene el terapeuta Milagros"').
    #     De ahí salen n-gramas como "tiene el terapeuta", que ganan por largo.
    for quoted in re.findall(r'["\x60](.{6,}?)["\x60]', desc):
        q_words = _words(quoted)
        for size in (3, 2):
            for gram in _ngrams(q_words, size):
                if any(w not in _STOPWORDS and len(w) > 2 for w in gram.split()):
                    phrases.add(gram)

    # 5) Plantillas de consulta por sustantivo (nouns[:3] + conceptos).
    template_nouns: list[str] = []
    for n in nouns[:3]:
        template_nouns.extend(sorted(_expand(n)))
    for n in dict.fromkeys(template_nouns):
        for tpl in (
            'lista de {n}',
            'lista {n}',
            '{n} del centro',
            'cuantos {n}',
            'cuantas {n}',
            'numero de {n}',
            'total de {n}',
            'cantidad de {n}',
            'reporte de {n}',
            'resumen de {n}',
            'ver {n}',
            'cuantos pacientes {n}',
            'pacientes que {n}',
            'pacientes con {n}',
        ):
            phrases.add(tpl.format(n=n))
        if 'month' in params:
            phrases.add(f'{n} del mes')
        if 'date' in params or 'day' in params:
            for tpl in ('{n} de hoy', '{n} de manana', '{n} del dia'):
                phrases.add(tpl.format(n=n))

    # 6) Roles enumerados en la descripción (p.ej. "Filtrar por rol: admin,
    #    terapista, jugador"): frases de conteo/listado por rol.
    role_words: set[str] = set()
    rol = _ROL_RE.search(desc)
    if rol:
        for part in rol.group(1).split(','):
            for variant in _role_variants(part):
                if not variant:
                    continue
                role_words.add(variant)
                phrases |= {
                    f'cuantos {variant}',
                    f'cuantas {variant}',
                    f'lista de {variant}',
                    variant,
                }

    gate_nouns |= {norm(r) for r in role_words}

    if 'month' in params:
        phrases.add('este mes')
    if 'date' in params or 'day' in params:
        phrases |= {'de hoy', 'de manana', 'del dia'}

    # Semántica de conteo REAL en la descripción (la tool sabe contar).
    can_count = bool(re.search(r'estadistic', desc, re.IGNORECASE)) and bool(
        re.search(r'cuant|cantidad|total', desc, re.IGNORECASE)
    )
    mentions_count = bool(re.search(r'cuant|cantidad', desc, re.IGNORECASE))
    is_metric = bool(_METRIC_RE.search(desc, re.IGNORECASE))

    # Entidades que nacen en el NOMBRE de la tool (get_therapist_x -> terapeuta):
    # una tool atada a una entidad concreta no se fuerza si el mensaje no la nombra
    # (salvo que la entidad sea el sustantivo principal de su descripción).
    entities = set()
    for tok in re.findall(r'[a-z]+', (entry['name'] or '').lower()):
        if tok in _NAME_NON_ENTITIES:
            continue
        es = norm(_NAME_LEXICON.get(tok, tok))
        if es and es not in _STOPWORDS and len(es) > 3:
            entities.add(es)

    primary_noun = nouns[0] if nouns else ''
    phrases = {norm(p) for p in phrases if p and len(p.strip()) >= 4}
    phrases.discard('')
    return (
        phrases,
        gate_nouns,
        frozenset(role_words),
        can_count,
        mentions_count,
        is_metric,
        frozenset(entities),
        primary_noun,
    )


def _arg_spec(entry: dict) -> str | None:
    if entry['name'] == 'create_group_sessions':
        return 'group_session'
    params = (entry.get('parameters') or {}).get('properties') or {}
    if 'month' in params:
        return 'month'
    if 'date' in params or 'day' in params:
        return 'date'
    # Tool con filtro de rol real (enum): el caller resuelve el valor desde el
    # mensaje ('cuántos terapeutas' -> role=terapista) contra ese mismo enum.
    if 'role' in params and (params.get('role') or {}).get('enum'):
        return 'role'
    # Tool atada a un terapeuta por nombre (get_therapist_patients...).
    if 'therapist_name' in params:
        return 'therapist'
    return None


def _indexable(entry: dict) -> bool:
    """Solo tools de lectura + la creación de grupos (gate de confirmación)."""
    return entry.get('category') != 'write' or entry['name'] == 'create_group_sessions'


@lru_cache(maxsize=4)
def build_intent_index(names: tuple[str, ...] = ()) -> tuple[dict, ...]:
    """Índice generado (orden de registro = último desempate)."""
    wanted = set(names) or set(TOOL_REGISTRY)
    index = []
    for name, entry in TOOL_REGISTRY.items():
        if name not in wanted or not _indexable(entry):
            continue
        phrases, gate, role_words, can_count, mentions_count, is_metric, entities, primary = _phrase_candidates(entry)
        index.append(
            {
                'name': name,
                'phrases': tuple(sorted(phrases, key=lambda p: (-len(p), p))),
                'gate': frozenset(gate),
                'arg_spec': _arg_spec(entry),
                'role_words': role_words,
                'can_count': can_count,
                'mentions_count': mentions_count,
                'is_metric': is_metric,
                'entities': entities,
                'primary_noun': primary,
            }
        )
    return tuple(index)


def match_intent(message: str, allowed_names) -> tuple[str, str | None] | None:
    """Mejor (tool, arg_spec) determinista para ``message`` dentro de ``allowed_names``.

    Filtros previos: tools atadas a una entidad ajena y tools de métricas sin
    consulta de conteo/palabra métrica nunca se fuerzan.
    Orden de desempate: frase más larga (más específica) > bonus (rol +3,
    desc con semántica de conteo +2 / solo cantidades +1) > pista temporal para
    tools de fecha > número de frases > menos parámetros > orden del registro.
    """
    msg = norm(message)
    if not msg or len(msg) < 4 or _BOT_CONTEXT_RE.search(msg):
        return None
    is_count_query = bool(_COUNT_RE.search(msg))
    has_query_marker = is_count_query or any(_match(m, msg) for m in _QUERY_MARKERS)
    has_write_verb = bool(_WRITE_VERB_RE.search(msg))
    has_date_hint = bool(_DATE_HINT_RE.search(msg))

    best = None  # (len, bonus, date_bias, nmatches, -order, tool, arg_spec)
    for order, entry in enumerate(build_intent_index()):
        if entry['name'] not in allowed_names:
            continue
        if has_write_verb and entry['name'] != 'create_group_sessions':
            continue

        # Tool atada a una entidad concreta (terapeuta, grupo...): solo si el
        # mensaje la nombra (con sus sinónimos de concepto) o si esa entidad es
        # el tema de su descripción. Las de fecha se salen con pista temporal.
        if entry['entities']:
            named = any(_match(e2, msg) for e in entry['entities'] for e2 in _expand(norm(e)))
            primary_is_entity = entry['primary_noun'] in entry['entities']
            entity_ok = named or primary_is_entity or (entry['arg_spec'] == 'date' and has_date_hint)
            if not entity_ok:
                continue

        # Tool de métricas: solo en consultas de conteo o con palabra métrica.
        if entry['is_metric'] and not is_count_query and not _METRIC_RE.search(msg):
            continue

        # Puerta de sustantivo: el mensaje debe tocar un sustantivo saliente.
        # Las tools de fecha se salen si el mensaje trae una pista temporal
        # ("qué hay el lunes") aunque no nombre la entidad.
        date_bypass = False
        gate_ok = any(_match(g, msg) for g in entry['gate'])
        if not gate_ok and entry['arg_spec'] == 'date' and has_date_hint:
            gate_ok = True
            date_bypass = True
        if not gate_ok:
            continue

        matched_len = 0
        nmatches = 0
        matched_role = False
        touches_subject = False
        primary = entry['primary_noun']
        for phrase in entry['phrases']:
            if ' ' not in phrase and len(phrase) < 6 and not has_query_marker:
                continue  # palabra suelta débil sin contexto de consulta
            if _match(phrase, msg):
                nmatches += 1
                if primary and _match(primary, phrase):
                    touches_subject = True  # la frase toca el tema CENTRAL de la tool
                if len(phrase) > matched_len:
                    matched_len = len(phrase)
                    matched_role = any(_match(rw, phrase) for rw in entry['role_words'])
        if date_bypass and not matched_len:
            matched_len, nmatches = 6, 1  # pista temporal basta para una tool de fecha
        if not matched_len:
            continue
        if entry['name'] == 'create_group_sessions' and matched_len < 8:
            continue  # la creación de grupo exige frase fuerte (evita falsos)

        bonus = 1 if touches_subject else 0
        if matched_role:
            bonus += 3  # filtro por rol enumerado en la descripción: máxima confianza
        if is_count_query:
            if entry['can_count']:
                bonus += 2  # la descripción dice explícitamente que cuenta
            elif entry['mentions_count']:
                bonus += 1
        date_bias = 1 if (has_date_hint and entry['arg_spec'] == 'date') else 0

        score = (matched_len, bonus, date_bias, nmatches, -order)
        if best is None or score > best[0]:
            best = (score, entry['name'], entry['arg_spec'])

    if best is None:
        return None
    return best[1], best[2]
