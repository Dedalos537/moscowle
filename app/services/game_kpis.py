"""Niveles de KPI de los juegos: qué se mide en cada juego, con qué umbrales y en qué nivel está cada paciente.

Solo lo ve el equipo (terapeuta, supervisor, administrador). Los pacientes nunca reciben KPIs ni niveles: el juego
muestra su propio marcador (monedas, vidas), no indicadores clínicos.

Cada juego guarda su perfil en Game.meta['kpis']: para cada indicador, tres umbrales que separan cuatro niveles
(Inicial, En proceso, Logrado, Destacado). En indicadores donde menos es mejor (tiempo, errores) los umbrales van
de mayor a menor.
"""

import json
import statistics
from datetime import datetime, timedelta

from app.models.appointment import SessionMetrics

LEVELS = [
    {'id': 'inicial', 'label': 'Inicial'},
    {'id': 'en_proceso', 'label': 'En proceso'},
    {'id': 'logrado', 'label': 'Logrado'},
    {'id': 'destacado', 'label': 'Destacado'},
]

# Indicadores que puede medir un juego. «better» indica qué dirección es mejor.
KPIS = {
    'accuracy': {'label': 'Precisión', 'unit': '%', 'better': 'high'},
    'avg_time': {'label': 'Tiempo de respuesta', 'unit': 's', 'better': 'low'},
    'completion': {'label': 'Avance', 'unit': '%', 'better': 'high'},
    'errors': {'label': 'Errores por intento', 'unit': '', 'better': 'low'},
    'collected': {'label': 'Objetos recogidos', 'unit': '%', 'better': 'high'},
}

# Perfiles por tipo de juego. Un admin puede ajustar los umbrales de cada juego.
DEFAULT_PROFILES = {
    'platformer': {
        'completion': [25, 50, 85],
        'errors': [6, 3, 1],
        'collected': [25, 50, 80],
    },
    'activities': {
        'accuracy': [50, 70, 85],
        'avg_time': [20, 12, 6],
        'completion': [40, 70, 95],
    },
    'reflex': {
        'accuracy': [50, 70, 85],
        'avg_time': [1.2, 0.8, 0.5],
    },
    # Supermercado: elegir bien (precisión), terminar la compra y pagar (avance), equivocarse poco (errores por
    # ronda) y el tiempo por producto de la lista.
    'shopping': {
        'accuracy': [60, 80, 95],
        'completion': [40, 70, 95],
        'errors': [4, 2, 0.5],
        'avg_time': [25, 15, 8],
    },
}

RECENT = 5


class KpiError(ValueError):
    pass


def default_profile(kind):
    family = {'platformer': 'platformer', 'jclic': 'activities', 'clic3': 'activities', 'simulation': 'shopping'}.get(
        kind, 'reflex'
    )
    return {k: list(v) for k, v in DEFAULT_PROFILES[family].items()}


def validate_profile(profile):
    """{kpi: [t1, t2, t3]} con indicadores conocidos y umbrales en el orden que corresponde a su dirección."""
    if not isinstance(profile, dict) or not profile:
        raise KpiError('Elige al menos un indicador.')
    clean = {}
    for key, thresholds in profile.items():
        spec = KPIS.get(key)
        if spec is None:
            raise KpiError(f'Indicador desconocido: {key}')
        if not isinstance(thresholds, list) or len(thresholds) != 3:
            raise KpiError(f'{spec["label"]}: se necesitan 3 umbrales.')
        try:
            values = [round(float(t), 2) for t in thresholds]
        except (TypeError, ValueError):
            raise KpiError(f'{spec["label"]}: los umbrales deben ser números.') from None
        if any(v < 0 for v in values):
            raise KpiError(f'{spec["label"]}: los umbrales no pueden ser negativos.')
        ordered = sorted(values) if spec['better'] == 'high' else sorted(values, reverse=True)
        if values != ordered or len(set(values)) != 3:
            hint = 'de menor a mayor' if spec['better'] == 'high' else 'de mayor a menor (menos es mejor)'
            raise KpiError(f'{spec["label"]}: los umbrales van {hint} y sin repetirse.')
        if spec['unit'] == '%' and values[-1 if spec['better'] == 'high' else 0] > 100:
            raise KpiError(f'{spec["label"]}: un porcentaje no pasa de 100.')
        clean[key] = values
    return clean


def game_profile(game):
    meta = _meta(game)
    profile = meta.get('kpis')
    if isinstance(profile, dict) and profile:
        try:
            return validate_profile(profile)
        except KpiError:
            pass
    return default_profile(meta.get('kind') or getattr(game, 'filetype', 'html'))


def _meta(game):
    if game is None or not game.meta:
        return {}
    try:
        value = json.loads(game.meta)
        return value if isinstance(value, dict) else {}
    except (TypeError, ValueError):
        return {}


def metric_values(m):
    """Indicadores de una partida guardada. Lo que el juego no informó queda fuera."""
    details = {}
    if m.details:
        try:
            details = json.loads(m.details) or {}
        except (TypeError, ValueError):
            details = {}
    kpis = details.get('kpis') if isinstance(details.get('kpis'), dict) else {}
    out = {}
    acc = m.accurracy
    if acc is not None and (acc > 0 or 'accuracy' in kpis):
        out['accuracy'] = acc * 100 if acc <= 1 else acc
    if m.avg_time and m.avg_time > 0:
        out['avg_time'] = m.avg_time
    for key in ('completion', 'errors', 'collected'):
        value = kpis.get(key)
        if isinstance(value, (int, float)) and value >= 0:
            out[key] = float(value)
    if 'errors' not in out and isinstance(details.get('deaths'), (int, float)):
        out['errors'] = float(details['deaths'])
    return out


def level_for(key, value, thresholds):
    """Índice 0..3 del nivel alcanzado."""
    better_high = KPIS[key]['better'] == 'high'
    level = 0
    for i, t in enumerate(thresholds):
        if (value >= t) if better_high else (value <= t):
            level = i + 1
    return level


def patient_levels(game, user_id, now=None):
    """Nivel por indicador con la mediana de las últimas partidas, el nivel general y la tendencia."""
    profile = game_profile(game)
    rows = (
        SessionMetrics.query.filter(
            SessionMetrics.user_id == user_id,
            (SessionMetrics.game_id == game.id) | (SessionMetrics.game_name == game.filename),
        )
        .order_by(SessionMetrics.date.desc())
        .limit(RECENT * 2)
        .all()
    )
    recent, previous = rows[:RECENT], rows[RECENT:]
    if not recent:
        return {'plays': 0, 'level': None, 'kpis': [], 'last_played': None, 'trend': None}

    def summarize(sample):
        values = {}
        for m in sample:
            for k, v in metric_values(m).items():
                values.setdefault(k, []).append(v)
        return {k: statistics.median(v) for k, v in values.items()}

    now_vals, prev_vals = summarize(recent), summarize(previous)
    kpis = []
    for key, thresholds in profile.items():
        if key not in now_vals:
            continue
        value = round(now_vals[key], 2)
        lvl = level_for(key, value, thresholds)
        prev_lvl = level_for(key, prev_vals[key], thresholds) if key in prev_vals else None
        kpis.append(
            {
                'key': key,
                'label': KPIS[key]['label'],
                'unit': KPIS[key]['unit'],
                'value': value,
                'level': LEVELS[lvl]['id'],
                'level_index': lvl,
                'thresholds': thresholds,
                'trend': None if prev_lvl is None else (lvl > prev_lvl) - (lvl < prev_lvl),
            }
        )
    overall = round(sum(k['level_index'] for k in kpis) / len(kpis)) if kpis else None
    total = SessionMetrics.query.filter(
        SessionMetrics.user_id == user_id,
        (SessionMetrics.game_id == game.id) | (SessionMetrics.game_name == game.filename),
    ).count()
    week_ago = (now or datetime.utcnow()) - timedelta(days=7)
    return {
        'plays': total,
        'plays_week': sum(1 for m in rows if m.date and m.date >= week_ago),
        'level': None if overall is None else LEVELS[overall]['id'],
        'level_index': overall,
        'kpis': kpis,
        'last_played': recent[0].date.isoformat() if recent[0].date else None,
    }
