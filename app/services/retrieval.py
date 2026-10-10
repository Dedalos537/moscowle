"""Recuperacion de herramientas para el MCP.

Por que NO embeddings aqui (decision de arquitectura, medida):
el catalogo tiene 67 herramientas. Recuperdor vectorial sobre 67 documentos no
aporta nada frente a BM25, y cuesta un modelo de ~470 MB y ~30 ms por consulta
en una CPU sin GPU. La recuperacion hibridaBM25 + sinonimos + senal de
lectura/escritura es determinista, instantanea y mas precisa a esta escala.

Donde SIwir vectors: la base de conocimiento de la pagina (features, FAQ,
politicas), que si tiene cientos de documentos. Ver knowledge.py.

Problema que corrige: _select_local_tools hacia coincidencia de palabras clave
y seccionaba el catalogo. "cuantos alumnos hay por sede" caia en el grupo
'usuarios' y ofrecia create_user y delete_user, sin offering get_sede_stats.
"""

import math
import re
import unicodedata
from collections import defaultdict

# Sinónimos por tool: terminos que el usuario escribe y que no estan en la
# descripcion de la tool. Es la capa que un embedding tendria que aprender, aqui
# es explicita, auditable y no depende de un modelo.
SYNONYMS = {
    'get_sede_scorecard': (
        'scorecard',
        'balanced',
        'desempeño',
        'desempeno',
        'rendimiento',
        'rinde',
        'metas',
        'meta',
        'indicadores',
        'kpi',
        'kpis',
        'cumplimiento',
        'como va',
        'como van',
        'mejor sede',
        'peor sede',
        'compara sedes',
        'comparar sedes',
    ),
    'get_sede_stats': (
        'sede',
        'sedes',
        'alumnos',
        'pacientes',
        'por sede',
        'cuantos por sede',
        'asignados',
        'asignado',
        'terapeutas por sede',
        'cuantos',
        'cantidad',
        'distribucion',
        'distribuir',
        'reparto',
        'sede de',
        'sedes de',
    ),
    'list_sedes': (
        'sede',
        'sedes',
        'sucursales',
        'establecimientos',
        'donde',
        'ubicacion',
        'direcciones',
        'locales',
        'sucursal',
    ),
    'get_sessions_day': (
        'sesiones',
        'citas',
        'agenda',
        'turnos',
        'hoy',
        'dia',
        'manana',
        'agenda de',
        'citas de',
        'horarios',
    ),
    'get_sessions': (
        'sesiones',
        'citas',
        'historial de sesiones',
        'agenda',
        'turnos',
    ),
    'get_debtors': (
        'deben',
        'deuda',
        'deudas',
        'morosos',
        'morosidad',
        'quien debe',
        'cuanto deben',
        'saldos pendientes',
        'pendientes de pago',
    ),
    'get_financial_summary': (
        'financiero',
        'finanzas',
        'resumen',
        'ingresos',
        'balance',
        'utilidad',
        'facturacion',
        'cuanto genero',
    ),
    'list_patients': (
        'pacientes',
        'alumnos',
        'listado',
        'todos los pacientes',
        'cuantos pacientes',
        'directorio',
    ),
    'search_patients': (
        'buscar',
        'busqueda',
        'encontrar',
        'ubicar',
        'buscar paciente',
        'localizar',
    ),
    'register_payment': (
        'pago',
        'pagos',
        'cobrar',
        'cobro',
        'registrar pago',
        'abono',
        'ingresar pago',
        'registrar cobro',
        'nuevo pago',
    ),
    'get_payment_history': (
        'pagos',
        'historial de pagos',
        'pagos de',
        'historial',
        'abonos',
    ),
    'delete_user': (
        'eliminar',
        'borrar',
        'dar de baja',
        'suprimir',
        'elimina',
        'borra',
        'baja de usuario',
    ),
    'cancel_contract': (
        'anular',
        'cancelar contrato',
        'dar de baja contrato',
        'terminar contrato',
    ),
    'list_contracts': (
        'contratos',
        'contrato',
        'convenios',
    ),
    'list_users': (
        'usuarios',
        'personal',
        'empleados',
        'terapeutas',
        'administradores',
        'quien trabaja',
        'lista de usuarios',
    ),
    'get_therapist_financials': (
        'terapia',
        'terapeutas',
        'cuanto genero',
        'produccion',
        'por terapeuta',
    ),
    'get_therapist_efficiency': (
        'eficiencia',
        'rendimiento',
        'productividad',
        'terapeutas',
    ),
    'get_therapist_patients': (
        'mis pacientes',
        'pacientes asignados',
        'mis alumnos',
        'terapista',
    ),
    'get_user_detail': (
        'quien es',
        'detalle de',
        'ficha de',
        'informacion de',
        'perfil de',
    ),
    'create_patient_group': (
        'grupo',
        'grupos',
        'crear grupo',
        'nuevo grupo',
        'grupo de pacientes',
    ),
    'list_patient_groups': (
        'grupos',
        'grupo de pacientes',
        'grupos de terapia',
    ),
    'get_monthly_reports': (
        'reportes',
        'informe',
        'informes',
        'reporte mensual',
        'estadisticas',
    ),
    'list_expenses': (
        'gastos',
        'egresos',
        'gasto',
    ),
    'create_expense': (
        'registrar gasto',
        'nuevo gasto',
        'gasto de',
        'anadir gasto',
    ),
    'update_expense': (
        'editar gasto',
        'corregir gasto',
        'cambiar gasto',
        'modificar gasto',
        'actualizar gasto',
    ),
    'delete_expense': (
        'eliminar gasto',
        'borrar gasto',
        'quitar gasto',
        'anular gasto',
    ),
    'update_user': (
        'editar usuario',
        'cambiar correo',
        'cambiar telefono',
        'cambiar nombre',
        'actualizar usuario',
        'modificar usuario',
    ),
    'reschedule_session': (
        'reprogramar',
        'mover sesion',
        'cambiar sesion',
        'cambiar horario',
        'cambiar la hora',
        'pasar la sesion',
        'posponer',
    ),
    'send_payment_reminder': (
        'recordatorio',
        'recordar pago',
        'avisar deuda',
        'cobrar pendiente',
    ),
    'broadcast_message': (
        'mensaje general',
        'avisar a todos',
        'broadcast',
        'comunicado',
        'enviar a todos',
    ),
    'send_direct_message': (
        'mensaje',
        'enviar mensaje',
        'avisar',
        'notificar',
        'escribir a',
    ),
    'get_notifications': (
        'notificaciones',
        'avisos',
        'pendientes',
        'bandeja',
    ),
    'get_current_datetime': (
        'fecha',
        'hora',
        'que dia',
        'que hora',
        'hoy es',
        'dia de hoy',
    ),
    'get_patient_detail': (
        'ficha del paciente',
        'historia clinica',
        'expediente',
        'detalle del paciente',
    ),
    'get_patient_stats': (
        'estadisticas de pacientes',
        'cuantos pacientes',
        'resumen de pacientes',
    ),
}

# Palabras que delatan una intencion de lectura (conteo/consulta).
_READ_HINTS = (
    'cuantos',
    'cuantas',
    'cuanto',
    'cuanta',
    'quien',
    'que',
    'cual',
    'cuales',
    'listar',
    'lista',
    'mostrar',
    'muestra',
    'ver',
    'dime',
    'consultar',
    'buscar',
    'cuantas veces',
    'resumen',
    'reporte',
    'estadisticas',
    'tiene',
    'hay',
)

# Palabras que delatan una intencion de escritura.
_WRITE_HINTS = (
    'crear',
    'crea',
    'nuevo',
    'nueva',
    'registrar',
    'registra',
    'anadir',
    'agrega',
    'eliminar',
    'elimina',
    'borrar',
    'borra',
    'dar de baja',
    'anular',
    'cancela',
    'cancelar',
    'actualizar',
    'actualiza',
    'editar',
    'edita',
    'cambiar',
    'asignar',
    'asigna',
    'enviar',
    'envia',
    'cobra',
    'cobrar',
)

# Tools de escritura que son "naturales" en una consulta de lectura (cobrar,
# avisar) y por eso no contaminan el resultado de una consulta de conteo.
_WRITE_IS_SAFE_FOR_READ = {
    'register_payment',
    'edit_payment',
    'send_payment_reminder',
    'broadcast_message',
    'send_direct_message',
    'generate_weekly_report',
}

_WORD_RE = re.compile(r'[a-z0-9]+')
# Palabras vacias del espanol, quitadas antes de puntuar.
_STOPWORDS = {
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
    'que',
    'en',
    'por',
    'para',
    'con',
    'al',
    'a',
    'es',
    'son',
    'hay',
    'me',
    'mi',
    'se',
    'su',
    'sus',
    'lo',
    'le',
    'les',
    'nos',
    'the',
    'of',
    'to',
    'and',
}


def _strip_accents(text):
    return ''.join(c for c in unicodedata.normalize('NFD', text.lower()) if unicodedata.category(c) != 'Mn')


def _tokenize(text):
    return [w for w in _WORD_RE.findall(_strip_accents(text)) if w not in _STOPWORDS and len(w) > 2]


def _token_set_distance(a, b):
    """Distancia de token: ambos deben aparecer en el texto."""
    ta, tb = set(_tokenize(a)), set(_tokenize(b))
    if not ta:
        return 1.0
    return 1.0 - len(ta & tb) / len(ta)


class RetrievedTool:
    """Tool candidata con su puntaje, para depurar y para el prompt."""

    __slots__ = ('name', 'description', 'category', 'roles', 'score', 'reason')

    def __init__(self, name, description, category, roles, score, reason=''):
        self.name = name
        self.description = description
        self.category = category
        self.roles = set(roles)
        self.score = score
        self.reason = reason

    def __repr__(self):
        return f'<{self.name} {self.score:.2f} {self.reason}>'

    def to_schema(self):
        return {
            'type': 'function',
            'function': {
                'name': self.name,
                'description': self.description,
                'parameters': {},
            },
        }


class ToolRetriever:
    """Recuperador BM25 + sinonimos + senal de lectura/escritura.

    Persistente: el indice se construye una vez (67 docs) y se reutiliza.
    Determinista: la misma consulta da siempre el mismo resultado, lo que hace
    testeable y auditable el comportamiento del bot.
    """

    def __init__(self, tools):
        self._tools = dict(tools)
        self._docs = {}
        self._df = defaultdict(int)
        self._avg_len = 0.0
        self._build_index()

    def _doc_text(self, name, entry):
        parts = [name.replace('_', ' '), entry.get('description', '')]
        parts.extend(SYNONYMS.get(name, ()))
        params = (entry.get('parameters') or {}).get('properties', {})
        parts.extend(str(p) for p in params)
        return ' '.join(parts)

    def _build_index(self):
        for name, entry in self._tools.items():
            tokens = _tokenize(self._doc_text(name, entry))
            tf = defaultdict(int)
            for t in tokens:
                tf[t] += 1
            self._docs[name] = {'tf': tf, 'len': len(tokens), 'entry': entry}
            for term in tf:
                self._df[term] += 1
        lengths = [d['len'] for d in self._docs.values()]
        self._avg_len = (sum(lengths) / len(lengths)) if lengths else 0.0
        self._n = len(self._docs) or 1

    def _bm25(self, name, q_tokens):
        doc = self._docs[name]
        if not doc['len'] or not q_tokens:
            return 0.0
        score = 0.0
        for term in q_tokens:
            f = doc['tf'].get(term, 0)
            if not f:
                continue
            idf = math.log(1 + (self._n - self._df[term] + 0.5) / (self._df[term] + 0.5))
            denom = f + 1.2 * (1 - 0.75 + 0.75 * doc['len'] / self._avg_len)
            score += idf * (f * 2.2) / denom
        return score

    def _classify(self, message):
        low = _strip_accents(message)
        read = any(_strip_accents(h) in low for h in _READ_HINTS)
        write = any(_strip_accents(h) in low for h in _WRITE_HINTS)
        return read, write

    def search(self, message, role=None, k=6, include_writes=None):
        """Devuelve las k tools mas relevantes para el mensaje.

        include_writes: si es None se decide por la senal de lectura/escritura
        del mensaje. Fijalo a False para forzar solo lectura (util en el
        sintetizador para no proponer escrituras en una consulta de consulta).
        """
        message = message or ''
        q_tokens = _tokenize(message)
        is_read, is_write = self._classify(message)
        # Si el mensaje no dice ni leer ni escribir, asumimos lectura: es el
        # caso mas comun y el mas seguro (no、执行 escrituras por sorpresa).
        wants_write = is_write and not (is_read and not is_write)
        if include_writes is None:
            include_writes = wants_write
        allow = _WRITE_IS_SAFE_FOR_READ if (is_read and not wants_write) else set()

        scored = []
        for name, doc in self._docs.items():
            entry = doc['entry']
            if role and role not in entry.get('roles', set()):
                continue
            is_write_tool = entry.get('category') == 'write'
            if is_write_tool and not include_writes and name not in allow:
                continue

            score = self._bm25(name, q_tokens)
            reason = []
            if score > 0:
                reason.append('bm25')
            # Bonificacion por coincidencia de sinonimos (capa que el modelo
            # deberia aprender pero aqui es explicita).
            for syn in SYNONYMS.get(name, ()):
                if _strip_accents(syn) in _strip_accents(message):
                    score += 2.5
                    reason.append('sinonimo')
                    break
            if score > 0:
                scored.append(
                    RetrievedTool(
                        name,
                        entry.get('description', ''),
                        entry.get('category', 'read'),
                        entry.get('roles', set()),
                        score,
                        '+'.join(sorted(set(reason))),
                    )
                )

        if not scored:
            # Sin coincidencias: devolver lecturas seguras, no nada. Un prompt
            # vacio hace que el modelo invente.
            for name, doc in self._docs.items():
                entry = doc['entry']
                if role and role not in entry.get('roles', set()):
                    continue
                if entry.get('category') != 'read':
                    continue
                scored.append(
                    RetrievedTool(
                        name,
                        entry.get('description', ''),
                        'read',
                        entry.get('roles', set()),
                        0.01,
                        'fallback',
                    )
                )
            return scored[:k]

        scored.sort(key=lambda t: -t.score)
        return scored[:k]
