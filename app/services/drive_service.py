"""Drive del administrador: archivos en el disco del servidor, confinados a una carpeta y con cuota.

Reglas de seguridad (todas pasan por ``resolve``):
  - Toda ruta que llega del cliente es RELATIVA a la raíz del drive y se normaliza; cualquier intento de salir de la
    raíz («..», rutas absolutas, enlaces simbólicos que apunten afuera) se rechaza.
  - Las carpetas internas (``.trash``, ``.uploads``, ``.thumbs``, ``.previews``) no se pueden listar ni tocar.
  - La cuota (30 GB por defecto, ``DRIVE_QUOTA_GB``) se comprueba ANTES de escribir: subidas, copias y descompresión.
  - Descomprimir revisa el tamaño total declarado y cada nombre (zip-slip) antes de extraer nada.

Rendimiento: el listado usa ``os.scandir`` (una sola llamada por carpeta) y el uso total se calcula una vez y luego se
actualiza de forma incremental; nunca se recorre todo el árbol en cada petición.
"""

import json
import os
import shutil
import tarfile
import threading
import time
import unicodedata
import uuid
import zipfile
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from flask import current_app

INTERNAL = ('.trash', '.uploads', '.thumbs', '.previews', '.meta')
MAX_NAME = 180
CHUNK_MAX = 16 * 1024 * 1024  # cada parte de una subida (Cloudflare corta cuerpos de más de 100 MB)
UPLOAD_TTL = 24 * 3600

_usage_lock = threading.Lock()
_usage = {'bytes': None, 'at': 0.0}


class DriveError(ValueError):
    """Error de uso con mensaje para mostrar tal cual."""

    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


# ── raíz, cuota y rutas ──────────────────────────────────────────────────────
def root() -> Path:
    base = current_app.config.get('DRIVE_ROOT') or os.path.join(current_app.instance_path, 'drive')
    path = Path(base).resolve()
    path.mkdir(parents=True, exist_ok=True)
    for name in INTERNAL:
        (path / name).mkdir(exist_ok=True)
    return path


def quota_bytes() -> int:
    return int(float(current_app.config.get('DRIVE_QUOTA_GB') or 30) * 1024**3)


def clean_name(name: str) -> str:
    """Nombre de archivo o carpeta válido (sin barras, sin control, sin puntos solos)."""
    name = unicodedata.normalize('NFC', str(name or '')).strip()
    name = ''.join(c for c in name if c.isprintable() and c not in '/\\\x00')
    if name in ('', '.', '..') or name.startswith('.'):
        raise DriveError('Nombre no válido')
    if len(name) > MAX_NAME:
        raise DriveError(f'El nombre no puede pasar de {MAX_NAME} caracteres')
    return name


def resolve(rel: str, must_exist=True) -> Path:
    """Ruta absoluta dentro de la raíz para una ruta relativa del cliente; DriveError si sale de ella."""
    base = root()
    rel = str(rel or '').replace('\\', '/').strip('/')
    parts = [p for p in PurePosixPath(rel).parts if p not in ('', '.')]
    if any(p == '..' for p in parts):
        raise DriveError('Ruta no válida', 400)
    if parts and parts[0] in INTERNAL:
        raise DriveError('Ruta no válida', 400)
    target = base.joinpath(*parts) if parts else base
    real = target.resolve()
    if real != base and base not in real.parents:
        raise DriveError('Ruta no válida', 400)
    if must_exist and not real.exists():
        raise DriveError('No existe', 404)
    return real


def rel_of(path: Path) -> str:
    return path.resolve().relative_to(root()).as_posix() if path.resolve() != root() else ''


# ── uso ──────────────────────────────────────────────────────────────────────
def _scan_usage() -> int:
    total = 0
    for dirpath, _dirs, files in os.walk(root()):
        if os.path.basename(dirpath) in ('.thumbs', '.previews'):
            continue
        for f in files:
            try:
                total += os.lstat(os.path.join(dirpath, f)).st_size
            except OSError:
                continue
    return total


def usage() -> dict:
    with _usage_lock:
        if _usage['bytes'] is None or time.time() - _usage['at'] > 600:
            _usage['bytes'] = _scan_usage()
            _usage['at'] = time.time()
        used = _usage['bytes']
    quota = quota_bytes()
    return {'used': used, 'quota': quota, 'free': max(0, quota - used)}


def _bump_usage(delta: int):
    with _usage_lock:
        if _usage['bytes'] is not None:
            _usage['bytes'] = max(0, _usage['bytes'] + int(delta))


def ensure_space(needed: int):
    if needed > usage()['free']:
        raise DriveError('No hay espacio suficiente en el drive (cuota de %.0f GB)' % (quota_bytes() / 1024**3), 507)


def _tree_size(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    total = 0
    for dirpath, _d, files in os.walk(path):
        for f in files:
            try:
                total += os.lstat(os.path.join(dirpath, f)).st_size
            except OSError:
                continue
    return total


# ── metadatos ligeros (destacados) ───────────────────────────────────────────
def _meta_file() -> Path:
    return root() / '.meta' / 'starred.json'


def starred() -> set:
    try:
        return set(json.loads(_meta_file().read_text()))
    except (OSError, ValueError):
        return set()


def set_starred(rel: str, on: bool):
    resolve(rel)
    items = starred()
    (items.add if on else items.discard)(rel)
    _meta_file().write_text(json.dumps(sorted(items)))


# ── listado ──────────────────────────────────────────────────────────────────
KIND_BY_EXT = {
    'image': {'png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp', 'svg', 'heic', 'avif'},
    'pdf': {'pdf'},
    'word': {'doc', 'docx', 'odt', 'rtf'},
    'slides': {'ppt', 'pptx', 'odp'},
    'sheet': {'xls', 'xlsx', 'ods', 'csv'},
    'archive': {'zip', 'tar', 'gz', 'tgz', 'rar', '7z'},
    'audio': {'mp3', 'wav', 'ogg', 'm4a', 'flac'},
    'video': {'mp4', 'webm', 'mov', 'mkv'},
    'text': {'txt', 'md', 'json', 'log', 'xml', 'yml', 'yaml', 'html', 'css', 'js', 'py'},
}


def kind_of(name: str, is_dir=False) -> str:
    if is_dir:
        return 'folder'
    ext = name.rsplit('.', 1)[-1].lower() if '.' in name else ''
    for kind, exts in KIND_BY_EXT.items():
        if ext in exts:
            return kind
    return 'file'


def _entry(path: Path, stat=None, stars=None) -> dict:
    st = stat or path.stat()
    is_dir = path.is_dir()
    rel = rel_of(path)
    item = {
        'name': path.name,
        'path': rel,
        'type': 'dir' if is_dir else 'file',
        'kind': kind_of(path.name, is_dir),
        'size': 0 if is_dir else st.st_size,
        'modified': datetime.fromtimestamp(st.st_mtime, tz=UTC).isoformat(),
        'starred': rel in (stars if stars is not None else starred()),
    }
    if is_dir:
        try:
            item['items'] = sum(1 for e in os.scandir(path) if not e.name.startswith('.'))
        except OSError:
            item['items'] = 0
    return item


def list_dir(rel: str) -> dict:
    folder = resolve(rel)
    if not folder.is_dir():
        raise DriveError('No es una carpeta')
    stars = starred()
    entries = []
    with os.scandir(folder) as it:
        for e in it:
            if e.name.startswith('.') or e.is_symlink():
                continue
            try:
                entries.append(_entry(Path(e.path), e.stat(), stars))
            except OSError:
                continue
    entries.sort(key=lambda x: (x['type'] != 'dir', x['name'].lower()))
    return {'path': rel_of(folder), 'entries': entries, 'usage': usage()}


def search(query: str, limit=200) -> list:
    q = unicodedata.normalize('NFC', (query or '').strip()).lower()
    if len(q) < 2:
        return []
    stars, found = starred(), []
    for dirpath, dirs, files in os.walk(root()):
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        for name in dirs + files:
            if q in name.lower() and not name.startswith('.'):
                found.append(_entry(Path(dirpath) / name, stars=stars))
                if len(found) >= limit:
                    return found
    return found


def recent(limit=60) -> list:
    items = []
    for dirpath, dirs, files in os.walk(root()):
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        for f in files:
            if f.startswith('.'):
                continue
            p = os.path.join(dirpath, f)
            try:
                items.append((os.stat(p).st_mtime, p))
            except OSError:
                continue
    items.sort(reverse=True)
    stars = starred()
    return [_entry(Path(p), stars=stars) for _t, p in items[:limit]]


def starred_entries() -> list:
    out, stars = [], starred()
    for rel in sorted(stars):
        try:
            out.append(_entry(resolve(rel), stars=stars))
        except DriveError:
            continue
    return out


# ── operaciones ──────────────────────────────────────────────────────────────
def _unique(folder: Path, name: str) -> Path:
    """«informe.pdf» → «informe (2).pdf» si ya existe, como hace Archivos de GNOME."""
    target = folder / name
    if not target.exists():
        return target
    stem, dot, ext = name.rpartition('.') if '.' in name and not name.startswith('.') else (name, '', '')
    stem = stem or name
    n = 2
    while True:
        candidate = folder / (f'{stem} ({n}).{ext}' if dot else f'{name} ({n})')
        if not candidate.exists():
            return candidate
        n += 1


def mkdir(parent_rel: str, name: str) -> dict:
    parent = resolve(parent_rel)
    target = _unique(parent, clean_name(name))
    target.mkdir()
    return _entry(target)


def rename(rel: str, new_name: str) -> dict:
    src = resolve(rel)
    if src == root():
        raise DriveError('No se puede renombrar la raíz')
    dst = src.parent / clean_name(new_name)
    if dst.exists() and dst != src:
        raise DriveError('Ya existe un elemento con ese nombre', 409)
    src.rename(dst)
    _move_star(rel, rel_of(dst))
    return _entry(dst)


def _move_star(old: str, new: str):
    stars = starred()
    changed = {s for s in stars if s == old or s.startswith(old + '/')}
    if changed:
        stars -= changed
        stars |= {new + s[len(old) :] for s in changed}
        _meta_file().write_text(json.dumps(sorted(stars)))


def _drop_star(rel: str):
    stars = starred()
    kept = {s for s in stars if not (s == rel or s.startswith(rel + '/'))}
    if kept != stars:
        _meta_file().write_text(json.dumps(sorted(kept)))


def move(paths: list, dest_rel: str) -> list:
    dest = resolve(dest_rel)
    if not dest.is_dir():
        raise DriveError('El destino no es una carpeta')
    out = []
    for rel in paths:
        src = resolve(rel)
        if src == root():
            raise DriveError('No se puede mover la raíz')
        if dest == src or src in dest.parents:
            raise DriveError('No puedes mover una carpeta dentro de sí misma')
        if src.parent == dest:
            out.append(_entry(src))
            continue
        target = _unique(dest, src.name)
        shutil.move(str(src), str(target))
        _move_star(rel, rel_of(target))
        out.append(_entry(target))
    return out


def copy(paths: list, dest_rel: str) -> list:
    dest = resolve(dest_rel)
    if not dest.is_dir():
        raise DriveError('El destino no es una carpeta')
    sources = [resolve(r) for r in paths]
    for src in sources:
        if src.is_dir() and (dest == src or src in dest.parents):
            raise DriveError('No puedes copiar una carpeta dentro de sí misma')
    ensure_space(sum(_tree_size(s) for s in sources))
    out = []
    for src in sources:
        target = _unique(dest, src.name)
        if src.is_dir():
            shutil.copytree(src, target, symlinks=False)
        else:
            shutil.copy2(src, target)
        _bump_usage(_tree_size(target))
        out.append(_entry(target))
    return out


# ── papelera ─────────────────────────────────────────────────────────────────
def _trash_dir() -> Path:
    return root() / '.trash'


def trash(paths: list) -> int:
    count = 0
    for rel in paths:
        src = resolve(rel)
        if src == root():
            raise DriveError('No se puede eliminar la raíz')
        tid = uuid.uuid4().hex
        holder = _trash_dir() / tid
        holder.mkdir()
        shutil.move(str(src), str(holder / src.name))
        (holder / '.info.json').write_text(
            json.dumps({'original': rel, 'name': src.name, 'deleted_at': datetime.now(UTC).isoformat()})
        )
        _drop_star(rel)
        count += 1
    return count


def trash_list() -> list:
    out = []
    for holder in sorted(_trash_dir().iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            info = json.loads((holder / '.info.json').read_text())
            item = holder / info['name']
            st = item.stat()
        except (OSError, ValueError, KeyError):
            continue
        out.append(
            {
                'id': holder.name,
                'name': info['name'],
                'original': info['original'],
                'deleted_at': info['deleted_at'],
                'type': 'dir' if item.is_dir() else 'file',
                'kind': kind_of(info['name'], item.is_dir()),
                'size': 0 if item.is_dir() else st.st_size,
            }
        )
    return out


def _holder(tid: str) -> Path:
    if not tid or not tid.isalnum():
        raise DriveError('Elemento no válido')
    holder = _trash_dir() / tid
    if not holder.is_dir():
        raise DriveError('No está en la papelera', 404)
    return holder


def restore(ids: list) -> int:
    count = 0
    for tid in ids:
        holder = _holder(tid)
        info = json.loads((holder / '.info.json').read_text())
        original = PurePosixPath(info['original'])
        parent_rel = str(original.parent) if str(original.parent) != '.' else ''
        try:
            parent = resolve(parent_rel)
        except DriveError:
            parent = root()
        target = _unique(parent, info['name'])
        shutil.move(str(holder / info['name']), str(target))
        shutil.rmtree(holder, ignore_errors=True)
        count += 1
    return count


def purge(ids=None) -> int:
    """Borra definitivamente de la papelera (todo si ids es None)."""
    holders = [_holder(t) for t in ids] if ids is not None else [p for p in _trash_dir().iterdir() if p.is_dir()]
    freed = sum(_tree_size(h) for h in holders)
    for h in holders:
        shutil.rmtree(h, ignore_errors=True)
    _bump_usage(-freed)
    return len(holders)


# ── subida por partes ────────────────────────────────────────────────────────
def upload_init(parent_rel: str, name: str, size: int) -> dict:
    parent = resolve(parent_rel)
    if not parent.is_dir():
        raise DriveError('El destino no es una carpeta')
    clean_name(name.rsplit('/', maxsplit=1)[-1])
    size = int(size or 0)
    if size < 0:
        raise DriveError('Tamaño no válido')
    ensure_space(size)
    uid = uuid.uuid4().hex
    (root() / '.uploads' / uid).write_bytes(b'')
    (root() / '.uploads' / f'{uid}.json').write_text(json.dumps({'parent': parent_rel, 'name': name, 'size': size}))
    return {'upload_id': uid, 'chunk_size': 8 * 1024 * 1024}


def _upload_paths(uid: str):
    if not uid or not uid.isalnum():
        raise DriveError('Subida no válida')
    data, meta = root() / '.uploads' / uid, root() / '.uploads' / f'{uid}.json'
    if not data.exists() or not meta.exists():
        raise DriveError('La subida expiró o no existe', 404)
    return data, meta


def upload_chunk(uid: str, offset: int, stream, length: int) -> int:
    data, meta = _upload_paths(uid)
    info = json.loads(meta.read_text())
    if length > CHUNK_MAX:
        raise DriveError('Parte demasiado grande')
    current = data.stat().st_size
    if int(offset) != current:
        raise DriveError(f'Parte fuera de orden (el servidor tiene {current} bytes)', 409)
    if current + length > info['size']:
        raise DriveError('La subida supera el tamaño anunciado')
    written = 0
    with open(data, 'ab') as fh:
        while True:
            chunk = stream.read(1024 * 1024)
            if not chunk:
                break
            written += len(chunk)
            if written > length:
                raise DriveError('La parte trae más datos de los anunciados')
            fh.write(chunk)
    return current + written


def upload_complete(uid: str) -> dict:
    data, meta = _upload_paths(uid)
    info = json.loads(meta.read_text())
    if data.stat().st_size != info['size']:
        raise DriveError('La subida está incompleta', 409)
    parent = resolve(info['parent'])
    # Subir una carpeta: el nombre puede traer subcarpetas («fotos/2026/a.jpg»), se crean dentro del destino.
    parts = [clean_name(p) for p in str(info['name']).split('/') if p]
    for part in parts[:-1]:
        parent = parent / part
        parent.mkdir(exist_ok=True)
    target = _unique(parent, parts[-1])
    os.replace(data, target)
    meta.unlink(missing_ok=True)
    _bump_usage(info['size'])
    return _entry(target)


def upload_abort(uid: str):
    try:
        data, meta = _upload_paths(uid)
    except DriveError:
        return
    data.unlink(missing_ok=True)
    meta.unlink(missing_ok=True)


def cleanup_stale_uploads():
    limit = time.time() - UPLOAD_TTL
    for p in (root() / '.uploads').iterdir():
        try:
            if p.stat().st_mtime < limit:
                p.unlink()
        except OSError:
            continue


# ── comprimir y descomprimir ─────────────────────────────────────────────────
def compress(paths: list, dest_rel: str, name: str) -> dict:
    sources = [resolve(r) for r in paths]
    if not sources:
        raise DriveError('Elige qué comprimir')
    dest = resolve(dest_rel)
    ensure_space(sum(_tree_size(s) for s in sources))
    zip_name = clean_name(name if name.lower().endswith('.zip') else f'{name}.zip')
    target = _unique(dest, zip_name)
    tmp = root() / '.uploads' / f'zip-{uuid.uuid4().hex}'
    try:
        with zipfile.ZipFile(tmp, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
            for src in sources:
                if src.is_file():
                    zf.write(src, src.name)
                    continue
                for dirpath, dirs, files in os.walk(src):
                    dirs[:] = [d for d in dirs if not d.startswith('.')]
                    base = Path(dirpath)
                    arc_dir = base.relative_to(src.parent).as_posix()
                    if not files and not dirs:
                        zf.writestr(arc_dir + '/', '')
                    for f in files:
                        zf.write(base / f, f'{arc_dir}/{f}')
        os.replace(tmp, target)
    finally:
        tmp.unlink(missing_ok=True)
    _bump_usage(target.stat().st_size)
    return _entry(target)


def _safe_member(dest: Path, name: str) -> Path:
    parts = [p for p in PurePosixPath(name.replace('\\', '/')).parts if p not in ('', '.', '/')]
    if not parts or any(p == '..' for p in parts) or parts[0].endswith(':'):
        raise DriveError(f'El archivo comprimido trae una ruta peligrosa: {name}')
    target = dest.joinpath(*parts).resolve()
    if dest != target and dest not in target.parents:
        raise DriveError(f'El archivo comprimido trae una ruta peligrosa: {name}')
    return target


def extract(rel: str, dest_rel=None) -> dict:
    archive = resolve(rel)
    name = archive.name.lower()
    parent = resolve(dest_rel) if dest_rel is not None else archive.parent
    stem = archive.name
    for suffix in ('.tar.gz', '.tgz', '.zip', '.tar'):
        if name.endswith(suffix):
            stem = archive.name[: -len(suffix)]
            break
    dest = _unique(parent, clean_name(stem or 'extraído'))
    if name.endswith('.zip'):
        with zipfile.ZipFile(archive) as zf:
            members = [m for m in zf.infolist() if not m.filename.startswith('__MACOSX')]
            total = sum(m.file_size for m in members)
            if len(members) > 20000:
                raise DriveError('El archivo comprimido tiene demasiados elementos')
            ensure_space(total)
            dest.mkdir()
            for m in members:
                target = _safe_member(dest, m.filename)
                if m.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(m) as src, open(target, 'wb') as out:
                    shutil.copyfileobj(src, out, 1024 * 1024)
    elif name.endswith(('.tar', '.tar.gz', '.tgz')):
        with tarfile.open(archive) as tf:
            members = [m for m in tf.getmembers() if m.isfile() or m.isdir()]
            ensure_space(sum(m.size for m in members))
            dest.mkdir()
            for m in members:
                target = _safe_member(dest, m.name)
                if m.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                src = tf.extractfile(m)
                if src is None:
                    continue
                with src, open(target, 'wb') as out:
                    shutil.copyfileobj(src, out, 1024 * 1024)
    else:
        raise DriveError('Solo se pueden descomprimir .zip, .tar y .tar.gz')
    _bump_usage(_tree_size(dest))
    return _entry(dest)
