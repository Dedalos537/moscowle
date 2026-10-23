"""Asistente del admin (PRP 015): responde preguntas del centro con bloques (texto, KPIs, gráficas, tablas, personas).

Los números NUNCA los escribe el modelo: salen de los mismos cálculos del Dashboard y del scorecard de sedes
(`center_dashboard`, `sede_scorecard`), así el asistente dice lo mismo que el resto de la plataforma.

- `scope_for(user)`: alcance de datos. El admin ve todo el centro; el supervisor, solo su sede.
- `answer(question, user)`: entiende la pregunta (intención, periodo, indicador) y arma los bloques.
  Si no es una pregunta de datos conocida, devuelve None y quien llama usa la IA general (OpenCode/MCP).
"""

import re
import unicodedata
from collections import defaultdict

from app.models import Payment, Sede, User, db
from app.services import center_dashboard
from app.services import sede_scorecard as bsc
from app.services.report_service import lima_today, utc_bounds

MAX_ROWS = 500
MODEL_NAME = 'datos del centro'
METHOD_LABELS = {
    'yape': 'Yape',
    'plin': 'Plin',
    'cash': 'Efectivo',
    'transfer': 'Transferencia',
    'card': 'Tarjeta',
    'yape_plin': 'Yape/Plin',
}
MONTHS_ES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']

# Palabras de la pregunta → indicador del scorecard (claves de bsc.KPIS).
METRIC_WORDS = [
    ('revenue', ('ingreso', 'cobrad', 'factur', 'recaud', 'ganan', 'plata', 'dinero')),
    ('collection', ('cobranza',)),
    ('overdue', ('deuda', 'moros', 'vencid')),
    ('ticket', ('ticket', 'por sesion')),
    ('active_patients', ('atendid', 'pacientes activos')),
    ('new_patients', ('nuevos', 'altas', 'inscrit')),
    ('attendance', ('asistencia', 'asisti', 'inasistencia')),
    ('retention', ('continuidad', 'retencion')),
    ('sessions_done', ('sesiones realizadas', 'sesiones')),
    ('cancel_rate', ('cancelac', 'cancelad')),
    ('closure', ('cerrad', 'sin cerrar', 'agenda cerrada')),
    ('accuracy', ('precision', 'juegos')),
    ('open_incidents', ('incidenc', 'incidente')),
    ('load', ('carga', 'por terapeuta')),
]
SUMMARY_KEYS = ('revenue', 'sessions_done', 'attendance', 'active_patients', 'overdue', 'new_patients')


class ScopeError(Exception):
    pass


def _norm(text):
    text = unicodedata.normalize('NFKD', (text or '').lower())
    return ''.join(c for c in text if not unicodedata.combining(c))


def scope_for(user):
    """sede_id del alcance (None = todo el centro). El supervisor queda limitado a su sede."""
    if user.role == 'admin':
        return None
    if user.role == 'supervisor':
        sede_id = user.sede_id or next((s.id for s in (user.assigned_sedes or [])), None)
        if not sede_id:
            raise ScopeError(
                'Tu usuario de supervisor no tiene una sede asignada: pídele al administrador que la asigne.'
            )
        return sede_id
    raise ScopeError('El asistente del centro es solo para administración.')


def _period(q):
    if 'trimestre' in q:
        return 'quarter'
    if re.search(r'\b(ano|anual|este ano|el ano)\b', q):
        return 'year'
    return 'month'


def _metrics(q):
    found = []
    for key, words in METRIC_WORDS:
        if any(w in q for w in words) and key not in found:
            found.append(key)
    return found


def _intent(q):
    if re.search(r'metodo|yape|plin|efectivo|transferencia', q) and 'pago' in q:
        return 'payment_methods'
    if 'sede' in q and re.search(r'compar|por sede|cada sede|entre sedes|sedes', q):
        return 'by_sede'
    if re.search(r'terapeuta|equipo|terapista', q):
        return 'team'
    if re.search(r'deudor|deben|morosos|quien debe|quienes deben', q):
        return 'debtors'
    if re.search(r'riesgo|abandon|dejar|perder', q):
        return 'risks'
    if re.search(r'altas|bajas|crec|entraron|salieron|retirad', q):
        return 'flow'
    if re.search(r'tendencia|evolucion|ultimos meses|historial|mes a mes|grafic', q):
        return 'trend'
    if re.search(r'resumen|como vamos|como va|kpi|indicador|balance|estado del centro|compar', q) or _metrics(q):
        return 'summary'
    return None


def _month_label(iso):
    y, m, _ = iso.split('-')
    return f'{MONTHS_ES[int(m) - 1]} {y[2:]}'


def _kpi_block(pulse, keys):
    by_key = {k['key']: k for k in pulse}
    items = []
    for key in keys:
        k = by_key.get(key)
        if not k:
            continue
        delta = None
        if k['value'] is not None and k['previous'] not in (None, 0):
            delta = round((k['value'] - k['previous']) / abs(k['previous']), 4)
        items.append(
            {
                'key': key,
                'label': k['label'],
                'value': k['value'],
                'previous': k['previous'],
                'format': k['unit'],
                'delta': delta,
                'good_when': k['direction'],
                'status': k['status'],
            }
        )
    return {'type': 'kpis', 'items': items}


def _fmt(value, unit):
    if value is None:
        return 'sin datos'
    if unit == 'money':
        return f'S/ {value:,.2f}'
    if unit == 'pct':
        return f'{value:.1f} %'
    if unit == 'dec':
        return f'{value:.1f}'
    return f'{int(value):,}'


def _change(k):
    if k['value'] is None or k['previous'] in (None, 0):
        return ''
    diff = (k['value'] - k['previous']) / abs(k['previous']) * 100
    word = 'más' if diff >= 0 else 'menos'
    return f' ({abs(diff):.0f} % {word} que el periodo anterior)'


def _scope_label(sede_id):
    if not sede_id:
        return 'todo el centro'
    sede = db.session.get(Sede, sede_id)
    return f'la sede {sede.name}' if sede else 'tu sede'


def _source(tool, data, sede_id):
    return {
        'tool': tool,
        'range': f'{data["range"]["from"]}..{data["range"]["to"]}',
        'previous': f'{data["previous_range"]["from"]}..{data["previous_range"]["to"]}',
        'scope': _scope_label(sede_id),
    }


# ── respuestas ───────────────────────────────────────────────────────────────
def _summary(data, sede_id, metrics):
    keys = metrics or list(SUMMARY_KEYS)
    pulse = {k['key']: k for k in data['pulse']}
    lines = [f'**{data["period_label"]}** en {_scope_label(sede_id)}:']
    for key in keys[:4]:
        k = pulse.get(key)
        if k:
            lines.append(f'- {k["label"]}: **{_fmt(k["value"], k["unit"])}**{_change(k)}')
    main = keys[0]
    k = pulse.get(main)
    blocks = [{'type': 'text', 'md': '\n'.join(lines)}, _kpi_block(data['pulse'], keys)]
    if k and any(v is not None for v in k['trend']):
        blocks.append(
            {
                'type': 'chart',
                'kind': 'line',
                'title': f'{k["label"]} · últimos 6 meses',
                'x': [_month_label(m) for m in data['months']],
                'series': [{'name': k['label'], 'data': k['trend']}],
                'format': k['unit'],
            }
        )
    return f'{data["period_label"]}: resumen', blocks


def _trend(data, sede_id, metrics):
    keys = (metrics or ['revenue', 'sessions_done'])[:3]
    pulse = {k['key']: k for k in data['pulse']}
    units = {pulse[k]['unit'] for k in keys if k in pulse}
    # Una sola escala por gráfica: indicadores con unidades distintas van en gráficas separadas.
    blocks = []
    for unit in units:
        group = [pulse[k] for k in keys if k in pulse and pulse[k]['unit'] == unit]
        blocks.append(
            {
                'type': 'chart',
                'kind': 'line',
                'title': ' y '.join(k['label'] for k in group) + ' · últimos 6 meses',
                'x': [_month_label(m) for m in data['months']],
                'series': [{'name': k['label'], 'data': k['trend']} for k in group],
                'format': unit,
            }
        )
    lines = [f'Evolución de los últimos 6 meses en {_scope_label(sede_id)}:']
    for key in keys:
        k = pulse.get(key)
        if not k:
            continue
        vals = [v for v in k['trend'] if v is not None]
        if len(vals) >= 2:
            lines.append(f'- {k["label"]}: de {_fmt(vals[0], k["unit"])} a {_fmt(vals[-1], k["unit"])}')
    return 'Tendencia de 6 meses', [{'type': 'text', 'md': '\n'.join(lines)}, *blocks]


def _by_sede(data, sede_id, metrics, period):
    if sede_id:
        title, blocks = _summary(data, sede_id, metrics)
        blocks.insert(0, {'type': 'text', 'md': 'Como supervisor ves solo tu sede; esto es lo de tu sede.'})
        return title, blocks
    sedes = data['sedes']
    if not sedes:
        return 'Comparativo de sedes', [{'type': 'text', 'md': 'No hay sedes activas para comparar.'}]
    keys = metrics or ['revenue', 'sessions_done', 'attendance', 'active_patients', 'overdue']
    labels = {k[0]: (k[2], k[3]) for k in bsc.KPIS}
    columns = [{'key': 'sede', 'label': 'Sede'}, {'key': 'score', 'label': 'Puntaje', 'format': 'int'}]
    columns += [{'key': k, 'label': labels[k][0], 'format': labels[k][1]} for k in keys if k in labels]
    rows = []
    for s in sedes:
        row = {'sede': s['name'], 'score': s['score']}
        for k in keys:
            row[k] = (s['kpis'].get(k) or {}).get('value')
        rows.append(row)
    main = keys[0]
    best = max(rows, key=lambda r: r[main] if r[main] is not None else float('-inf'))
    text = (
        f'{data["period_label"]}, comparando {len(rows)} sedes: la de mejor {labels[main][0].lower()} es '
        f'**{best["sede"]}** ({_fmt(best[main], labels[main][1])}).'
    )
    chart_keys = [k for k in keys if labels.get(k, (None, None))[1] == labels[main][1]][:3]
    return f'Sedes · {data["period_label"].lower()}', [
        {'type': 'text', 'md': text},
        {
            'type': 'chart',
            'kind': 'bar',
            'title': ' y '.join(labels[k][0] for k in chart_keys) + ' por sede',
            'x': [r['sede'] for r in rows],
            'series': [{'name': labels[k][0], 'data': [r[k] for r in rows]} for k in chart_keys],
            'format': labels[main][1],
        },
        {'type': 'table', 'title': 'Comparativo de sedes', 'columns': columns, 'rows': rows, 'totals': False},
    ]


def _team(data, sede_id):
    rows = data['team'][:MAX_ROWS]
    if not rows:
        return 'Equipo', [{'type': 'text', 'md': 'No hay sesiones de terapeutas en este periodo.'}]
    top = rows[0]
    text = (
        f'{data["period_label"]} en {_scope_label(sede_id)}: {len(rows)} terapeutas con sesiones. '
        f'Más sesiones realizadas: **{top["name"]}** ({top["sessions_done"]}).'
    )
    columns = [
        {'key': 'name', 'label': 'Terapeuta'},
        {'key': 'sessions_done', 'label': 'Realizadas', 'format': 'int'},
        {'key': 'sessions_scheduled', 'label': 'Programadas', 'format': 'int'},
        {'key': 'patients', 'label': 'Pacientes', 'format': 'int'},
        {'key': 'attendance', 'label': 'Asistencia', 'format': 'pct'},
        {'key': 'cancel_rate', 'label': 'Cancelaciones', 'format': 'pct'},
        {'key': 'next_7_days', 'label': 'Próx. 7 días', 'format': 'int'},
    ]
    shown = rows[:12]
    return 'Equipo de terapeutas', [
        {'type': 'text', 'md': text},
        {
            'type': 'chart',
            'kind': 'bar',
            'title': 'Sesiones realizadas y programadas',
            'x': [r['name'] for r in shown],
            'series': [
                {'name': 'Realizadas', 'data': [r['sessions_done'] for r in shown]},
                {'name': 'Programadas', 'data': [r['sessions_scheduled'] for r in shown]},
            ],
            'format': 'int',
        },
        {'type': 'table', 'title': 'Terapeutas', 'columns': columns, 'rows': rows, 'totals': True},
    ]


def _people_items(items):
    return [
        {
            'id': r['patient']['id'],
            'name': r['patient']['name'],
            'code': r['patient']['code'],
            'detail': ' · '.join(x['label'] for x in r['reasons']),
            'amount': r['overdue'] or None,
            'link': f'/admin/patients/{r["patient"]["id"]}',
        }
        for r in items
    ]


def _risks(data, sede_id):
    risks = data['risks']
    if not risks['items']:
        return 'Pacientes en riesgo', [
            {'type': 'text', 'md': f'No hay pacientes en riesgo en {_scope_label(sede_id)}.'}
        ]
    by_kind = risks['by_kind']
    kinds = [(center_dashboard.RISK_KINDS[k][0], n) for k, n in sorted(by_kind.items(), key=lambda kv: -kv[1])]
    text = f'**{risks["total"]} pacientes** con señales de abandono en {_scope_label(sede_id)}. ' + ', '.join(
        f'{label.lower()}: {n}' for label, n in kinds
    )
    return 'Pacientes en riesgo', [
        {'type': 'text', 'md': text + '.'},
        {
            'type': 'chart',
            'kind': 'doughnut',
            'title': 'Motivos de riesgo',
            'x': [label for label, _ in kinds],
            'series': [{'name': 'Pacientes', 'data': [n for _, n in kinds]}],
            'format': 'int',
        },
        {'type': 'people', 'title': 'A quién contactar primero', 'items': _people_items(risks['items'][:25])},
    ]


def _debtors(data, sede_id):
    rows = [r for r in data['risks']['items'] if r['overdue']]
    rows.sort(key=lambda r: -r['overdue'])
    if not rows:
        return 'Deudores', [{'type': 'text', 'md': f'Nadie tiene cuotas vencidas en {_scope_label(sede_id)}.'}]
    total = sum(r['overdue'] for r in rows)
    text = (
        f'**{len(rows)} pacientes** con cuotas vencidas en {_scope_label(sede_id)}, por **S/ {total:,.2f}** en total.'
    )
    table_rows = [
        {
            'patient': r['patient']['name'],
            'code': r['patient']['code'],
            'overdue': r['overdue'],
            'next_session': r['next_session'],
            'link': f'/admin/patients/{r["patient"]["id"]}',
        }
        for r in rows
    ]
    return 'Deudores', [
        {'type': 'text', 'md': text},
        {
            'type': 'table',
            'title': 'Deuda vencida por paciente',
            'columns': [
                {'key': 'patient', 'label': 'Paciente', 'link': 'link', 'person_code': 'code'},
                {'key': 'overdue', 'label': 'Debe', 'format': 'money'},
                {'key': 'next_session', 'label': 'Próxima sesión', 'format': 'date'},
            ],
            'rows': table_rows,
            'totals': True,
        },
    ]


def _flow(data, sede_id):
    flow = data['flow']
    new, left = sum(m['new'] for m in flow), sum(m['left'] for m in flow)
    text = (
        f'En los últimos 6 meses en {_scope_label(sede_id)} entraron **{new}** pacientes y salieron **{left}** '
        f'(neto {new - left:+d}).'
    )
    return 'Altas y bajas', [
        {'type': 'text', 'md': text},
        {
            'type': 'chart',
            'kind': 'bar',
            'title': 'Altas y bajas por mes',
            'x': [_month_label(m['month']) for m in flow],
            'series': [
                {'name': 'Altas', 'data': [m['new'] for m in flow]},
                {'name': 'Bajas', 'data': [m['left'] for m in flow]},
            ],
            'format': 'int',
        },
    ]


def _payment_methods(data, sede_id):
    first, last = data['range']['from'], data['range']['to']
    from datetime import date

    start, end = utc_bounds(date.fromisoformat(first), date.fromisoformat(last))
    q = db.session.query(Payment.method, Payment.amount, Payment.date).filter(
        Payment.date >= start, Payment.date < end, Payment.status == 'completed', Payment.is_active.isnot(False)
    )
    if sede_id:
        q = q.join(User, User.id == Payment.patient_id).filter(User.sede_id == sede_id)
    by_method = defaultdict(lambda: [0, 0.0])
    for method, amount, _ in q.all():
        label = METHOD_LABELS.get((method or '').lower(), (method or 'Otro').capitalize())
        by_method[label][0] += 1
        by_method[label][1] += amount or 0
    if not by_method:
        return 'Pagos por método', [{'type': 'text', 'md': 'No hay pagos registrados en el periodo.'}]
    rows = sorted(
        ({'method': k, 'count': v[0], 'amount': round(v[1], 2)} for k, v in by_method.items()),
        key=lambda r: -r['amount'],
    )
    total = sum(r['amount'] for r in rows)
    text = (
        f'{data["period_label"]} en {_scope_label(sede_id)}: S/ {total:,.2f} en {sum(r["count"] for r in rows)} pagos. '
        f'El método más usado por monto es **{rows[0]["method"]}** ({rows[0]["amount"] / total * 100:.0f} %).'
    )
    return 'Pagos por método', [
        {'type': 'text', 'md': text},
        {
            'type': 'chart',
            'kind': 'doughnut',
            'title': 'Monto por método de pago',
            'x': [r['method'] for r in rows],
            'series': [{'name': 'Monto', 'data': [r['amount'] for r in rows]}],
            'format': 'money',
        },
        {
            'type': 'table',
            'title': 'Pagos por método',
            'columns': [
                {'key': 'method', 'label': 'Método'},
                {'key': 'count', 'label': 'Pagos', 'format': 'int'},
                {'key': 'amount', 'label': 'Monto', 'format': 'money'},
            ],
            'rows': rows,
            'totals': True,
        },
    ]


# Pedidos de datos inequívocos: valen aunque la conversación venga de otra cosa (strict).
EXPLICIT = re.compile(
    r'resumen|como vamos|kpi|indicador|compar|tendencia|evolucion|sedes|deudor|deben|riesgo|abandon|'
    r'altas|bajas|metodo|ingresos|cobranza|grafic|tabla'
)


def answer(question, user, today=None, strict=False):
    """Bloques para una pregunta de datos del centro, o None si no es una pregunta de datos conocida.

    strict: en medio de una conversación con la IA, solo se responde aquí si el pedido de datos es explícito.
    """
    q = _norm(question)
    intent = _intent(q)
    if not intent or (strict and not EXPLICIT.search(q)):
        return None
    sede_id = scope_for(user)
    period = _period(q)
    metrics = _metrics(q)
    data = center_dashboard.dashboard(period=period, sede_id=sede_id, today=today or lima_today())
    if intent == 'by_sede':
        title, blocks = _by_sede(data, sede_id, metrics, period)
    elif intent == 'team':
        title, blocks = _team(data, sede_id)
    elif intent == 'risks':
        title, blocks = _risks(data, sede_id)
    elif intent == 'debtors':
        title, blocks = _debtors(data, sede_id)
    elif intent == 'flow':
        title, blocks = _flow(data, sede_id)
    elif intent == 'trend':
        title, blocks = _trend(data, sede_id, metrics)
    elif intent == 'payment_methods':
        title, blocks = _payment_methods(data, sede_id)
    else:
        title, blocks = _summary(data, sede_id, metrics)
    return {
        'title': title,
        'intent': intent,
        'period': period,
        'blocks': [validate_block(b) for b in blocks if b],
        'sources': [_source(f'center_dashboard.{intent}', data, sede_id)],
        'model': MODEL_NAME,
    }


# ── validación de bloques (el frontend solo dibuja lo que pasa por aquí) ─────
BLOCK_TYPES = {'text', 'kpis', 'chart', 'table', 'people', 'action'}
CHART_KINDS = {'line', 'bar', 'doughnut'}


def validate_block(block):
    t = block.get('type')
    if t not in BLOCK_TYPES:
        raise ValueError(f'Bloque desconocido: {t}')
    if t == 'chart':
        if block.get('kind') not in CHART_KINDS:
            raise ValueError('Tipo de gráfica no válido')
        block['series'] = block['series'][:12]
        n = len(block['x'])
        for s in block['series']:
            s['data'] = list(s['data'])[:n]
    if t == 'table':
        block['rows'] = block['rows'][:MAX_ROWS]
    if t == 'people':
        block['items'] = block['items'][:MAX_ROWS]
    return block


def suggestions(user):
    """Preguntas sugeridas según el día y el rol (pantalla vacía)."""
    today = lima_today()
    base = ['¿Cómo vamos este mes?', 'Pacientes en riesgo de dejar el centro', 'Tendencia de ingresos y sesiones']
    if user.role == 'admin':
        base.insert(1, 'Compara las sedes este trimestre')
    if today.day >= 25 or today.day <= 5:
        base.insert(0, '¿Quiénes deben cuotas vencidas?')
    if today.weekday() == 0:
        base.insert(0, '¿Cómo están los terapeutas esta semana?')
    base.append('Pagos por método este mes')
    return base[:6]
