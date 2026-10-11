"""Subida de juegos al catálogo: web (.html o .zip con index.html), JClic (.jclic.zip), Clic 3.0 (.pcc, .zip con
.pac y actividades, o actividades sueltas) y Flash (.swf).

Todo queda en app/static/games y recibe su ficha en `game`. Los .zip se descomprimen con límites (cantidad, tamaño,
rutas) y, en los juegos web, solo con tipos de archivo que un juego necesita.
"""

import io
import json
import os
import re
import shutil
import unicodedata
import zipfile

from app.extensions import db
from app.models.game import Game
from app.services import clic3, game_catalog

MAX_UPLOAD = 60 * 1024 * 1024
MAX_FILES = 3000
MAX_TOTAL = 150 * 1024 * 1024
WEB_EXT = {
    '.html',
    '.htm',
    '.js',
    '.mjs',
    '.css',
    '.json',
    '.png',
    '.jpg',
    '.jpeg',
    '.gif',
    '.webp',
    '.svg',
    '.ico',
    '.mp3',
    '.ogg',
    '.wav',
    '.m4a',
    '.mp4',
    '.webm',
    '.woff',
    '.woff2',
    '.ttf',
    '.otf',
    '.txt',
    '.xml',
    '.wasm',
}


class UploadError(ValueError):
    pass


def slugify(text):
    text = unicodedata.normalize('NFKD', text or '').encode('ascii', 'ignore').decode()
    text = re.sub(r'[^a-zA-Z0-9]+', '_', text).strip('_').lower()
    return text[:50] or 'juego'


def _unique(base, rel):
    """Carpeta o archivo que no pise a otro juego: nombre, nombre_2, nombre_3…"""
    stem, ext = os.path.splitext(rel)
    candidate, n = rel, 2
    while os.path.exists(os.path.join(base, candidate)) or Game.query.filter_by(filename=candidate).first():
        candidate = f'{stem}_{n}{ext}'
        n += 1
    return candidate


def _register(filename, title, kind, filetype, meta):
    game = Game(title=title[:100], filename=filename, filetype=filetype, is_active=True)
    game.meta = json.dumps({'kind': kind, **meta}, ensure_ascii=False)
    db.session.add(game)
    db.session.commit()
    return game


def _safe_members(zf):
    infos = [i for i in zf.infolist() if not i.is_dir()]
    if len(infos) > MAX_FILES:
        raise UploadError('El .zip tiene demasiados archivos.')
    total = 0
    for info in infos:
        total += info.file_size
        if total > MAX_TOTAL:
            raise UploadError('El .zip es demasiado grande una vez descomprimido.')
        name = info.filename.replace('\\', '/')
        if name.startswith('/') or '..' in name.split('/'):
            raise UploadError('El .zip contiene rutas no permitidas.')
    return infos


def save_upload(filename, data, title):
    """Guarda el archivo subido y crea su ficha. Devuelve (game, informe)."""
    if not data:
        raise UploadError('El archivo está vacío.')
    if len(data) > MAX_UPLOAD:
        raise UploadError('El archivo supera los 60 MB.')
    title = (title or '').strip() or os.path.splitext(filename)[0]
    low = (filename or '').lower()
    base = game_catalog.games_dir()
    os.makedirs(base, exist_ok=True)
    report = {'activities': None, 'warnings': []}

    # Clic 3.0: se convierte a un proyecto JClic en su propia carpeta.
    if clic3.looks_like_clic3(low, data):
        try:
            files = clic3.files_from_upload(low, data)
            project = clic3.build_project(files, title)
        except (clic3.Clic3Error, zipfile.BadZipFile) as e:
            raise UploadError(str(e)) from None
        folder = _unique(base, f'clic3/{slugify(title)}')
        path = os.path.join(base, folder)
        os.makedirs(path, exist_ok=True)
        with open(os.path.join(path, 'project.jclic'), 'w', encoding='utf-8') as fh:
            fh.write(project.xml)
        for name, content in project.media.items():
            with open(os.path.join(path, name), 'wb') as fh:
                fh.write(content)
        entry = f'{folder}/project.jclic'
        game = _register(entry, title, 'clic3', 'clic3', {'entry': entry, 'folder': folder, 'source': filename})
        report.update(activities=project.activities, warnings=project.warnings[:20])
        return game, report

    if low.endswith('.jclic.zip'):
        rel = _unique(base, f'{slugify(title)}.jclic.zip')
        with open(os.path.join(base, rel), 'wb') as fh:
            fh.write(data)
        return _register(rel, title, 'jclic', 'jclic', {'entry': rel, 'source': filename}), report

    if low.endswith('.swf'):
        rel = _unique(base, f'{slugify(title)}.swf')
        with open(os.path.join(base, rel), 'wb') as fh:
            fh.write(data)
        return _register(rel, title, 'flash', 'flash', {'entry': rel, 'source': filename}), report

    if low.endswith(('.html', '.htm')):
        rel = _unique(base, f'{slugify(title)}.html')
        with open(os.path.join(base, rel), 'wb') as fh:
            fh.write(data)
        return _register(rel, title, 'html', 'html', {'source': filename}), report

    if low.endswith('.zip'):
        # Juego web empaquetado: una carpeta con index.html.
        try:
            zf = zipfile.ZipFile(io.BytesIO(data))
        except zipfile.BadZipFile:
            raise UploadError('El .zip está dañado.') from None
        with zf:
            infos = _safe_members(zf)
            names = [i.filename.replace('\\', '/') for i in infos]
            index = min((n for n in names if n.lower().endswith('index.html')), key=len, default=None)
            if not index:
                raise UploadError('El .zip no tiene un index.html.')
            prefix = index[: -len('index.html')]
            skipped = 0
            folder = _unique(base, slugify(title))
            path = os.path.join(base, folder)
            os.makedirs(path, exist_ok=True)
            try:
                for info, name in zip(infos, names, strict=True):
                    if not name.startswith(prefix):
                        continue
                    rel = name[len(prefix) :]
                    if os.path.splitext(rel)[1].lower() not in WEB_EXT or '__MACOSX' in rel:
                        skipped += 1
                        continue
                    dest = os.path.normpath(os.path.join(path, rel))
                    if not dest.startswith(path + os.sep):
                        raise UploadError('El .zip contiene rutas no permitidas.')
                    os.makedirs(os.path.dirname(dest), exist_ok=True)
                    with open(dest, 'wb') as fh:
                        fh.write(zf.read(info))
            except UploadError:
                shutil.rmtree(path, ignore_errors=True)
                raise
        if skipped:
            report['warnings'].append(f'Se omitieron {skipped} archivos que un juego web no necesita.')
        entry = f'{folder}/index.html'
        return _register(entry, title, 'html', 'html', {'folder': folder, 'source': filename}), report

    raise UploadError('Formato no admitido. Usa .html, .zip, .jclic.zip, .pcc, .pac o .swf.')
