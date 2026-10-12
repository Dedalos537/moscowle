"""Catálogo de juegos: une los archivos de app/static/games con su ficha en la tabla `game`.

La ficha extra (tipo, área, edades, perfil de KPIs) vive en Game.meta (JSON), así no hace falta migrar la tabla.
Los archivos que no tienen ficha la reciben al listar el catálogo, con los datos conocidos de los juegos de serie.
"""

import json
import os
import re
from urllib.parse import quote

from flask import current_app

from app.extensions import db
from app.models.game import Game
from app.services import game_kpis

KINDS = {
    'platformer': 'Plataformas',
    'reflex': 'Reflejos',
    'simulation': 'Simulación',
    'jclic': 'Actividades JClic',
    'clic3': 'Actividades Clic 3.0',
    'flash': 'Flash',
    'html': 'Juego web',
}

# Juegos de serie: datos que no se pueden deducir del archivo.
BUILTIN = {
    'super_rpg_bros/index.html': {
        'title': 'Super RPG Bros.',
        'kind': 'platformer',
        'area': 'Coordinación y planificación motora',
        'ages': '6-14',
        'description': 'Plataformas en 4 niveles: correr, saltar en el momento justo, esquivar y planificar la ruta.',
    },
    'supermercado/index.html': {
        'title': 'Supermercado',
        'kind': 'simulation',
        'area': 'Planificación, memoria y manejo del dinero',
        'ages': '6-18',
        'description': 'Recorre el súper con tu carrito, toma lo que pide la lista y paga en la caja con soles.',
    },
    'mario_forever.html': {
        'title': 'Mario Forever',
        'kind': 'platformer',
        'area': 'Coordinación visomotora',
        'ages': '6-14',
        'description': 'Recreación del clásico de plataformas.',
    },
    'starter.html': {
        'title': 'Reflejos',
        'kind': 'reflex',
        'area': 'Atención y tiempo de reacción',
        'ages': '5-99',
        'description': 'Toca el objetivo lo más rápido posible.',
    },
}

# Páginas que no son juegos (restos de versiones anteriores o marcadores vacíos).
HIDDEN = {'games.html', 'patient_interface.html', 'aprender_a_mover_las_flechas.html', 'cuento_cenicienta.html'}
_PLACEHOLDER = 'Juego IA (fallback)'


def games_dir():
    return os.path.join(current_app.root_path, 'static', 'games')


def meta_of(game):
    if not game or not game.meta:
        return {}
    try:
        value = json.loads(game.meta)
        return value if isinstance(value, dict) else {}
    except (TypeError, ValueError):
        return {}


def set_meta(game, **values):
    meta = meta_of(game)
    for key, value in values.items():
        if value is None:
            meta.pop(key, None)
        else:
            meta[key] = value
    game.meta = json.dumps(meta, ensure_ascii=False)


def kind_of(game):
    return meta_of(game).get('kind') or (game.filetype if game.filetype in KINDS else 'html')


def _is_placeholder(path):
    try:
        if os.path.getsize(path) > 600:
            return False
        with open(path, encoding='utf-8', errors='ignore') as fh:
            return _PLACEHOLDER in fh.read()
    except OSError:
        return True


def discover_files():
    """Juegos HTML en disco: archivos sueltos y carpetas con index.html."""
    base = games_dir()
    found = []
    try:
        entries = sorted(os.listdir(base))
    except OSError:
        return found
    for name in entries:
        if name.startswith(('_', '.')) or name in HIDDEN or name in ('vendor', 'clic3'):
            continue
        path = os.path.join(base, name)
        if os.path.isdir(path) and os.path.isfile(os.path.join(path, 'index.html')):
            found.append(f'{name}/index.html')
        elif name.lower().endswith(('.html', '.htm')) and not _is_placeholder(path):
            found.append(name)
    return found


def sync_catalog():
    """Crea la ficha de los juegos que están en disco y aún no la tienen."""
    known = {g.filename for g in Game.query.all()}
    added = False
    for filename in discover_files():
        if filename in known:
            continue
        info = BUILTIN.get(filename, {})
        game = Game(
            title=info.get('title') or _pretty(filename),
            filename=filename,
            filetype='html',
            description=info.get('description'),
            is_active=True,
        )
        set_meta(
            game,
            kind=info.get('kind', 'html'),
            area=info.get('area'),
            ages=info.get('ages'),
        )
        db.session.add(game)
        added = True
    if added:
        db.session.commit()


def _pretty(filename):
    stem = re.sub(r'(/index)?\.html?$', '', filename, flags=re.I)
    return stem.replace('_', ' ').replace('-', ' ').strip().title() or filename


def play_url(game):
    """Dirección para jugar. Los paquetes JClic, Clic 3.0 y Flash pasan por su lanzador."""
    kind = kind_of(game)
    meta = meta_of(game)
    title = quote(game.title or '')
    if kind in ('jclic', 'clic3'):
        project = meta.get('entry') or game.filename
        return f'/static/games/_jclic_launcher.html?game={quote(project)}&title={title}'
    if kind == 'flash':
        return f'/static/games/_flash_launcher.html?game={quote(meta.get("entry") or game.filename)}&title={title}'
    return f'/static/games/{game.filename}'


def file_exists(game):
    meta = meta_of(game)
    target = meta.get('entry') or game.filename
    return os.path.exists(os.path.join(games_dir(), target))


def serialize(game, staff):
    meta = meta_of(game)
    kind = kind_of(game)
    data = {
        'id': game.id,
        'title': game.title,
        'filename': game.filename,
        'kind': kind,
        'kind_label': KINDS.get(kind, 'Juego'),
        'area': meta.get('area'),
        'ages': meta.get('ages'),
        'description': game.description,
        'thumbnail': game.thumbnail,
        'is_active': bool(game.is_active),
        'play_url': play_url(game),
    }
    if staff:
        data['kpis'] = game_kpis.game_profile(game)
        data['kpis_custom'] = isinstance(meta.get('kpis'), dict)
        data['available'] = file_exists(game)
        data['source'] = meta.get('source')
    return data
