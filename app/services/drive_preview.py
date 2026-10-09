"""Previsualizaciones del drive sin dependencias nuevas en el servidor.

- Imágenes: miniatura WEBP con Pillow, cacheada en ``.thumbs`` (se invalida por fecha de modificación).
- PDF: el navegador lo muestra tal cual (se sirve el archivo).
- DOCX: HTML sencillo y seguro con python-docx (títulos, párrafos, listas, tablas e imágenes incrustadas).
- PPTX: diapositiva por diapositiva leyendo el XML del paquete (títulos, textos e imágenes).
- Texto: primeros 200 KB.
- Si el servidor tiene LibreOffice (``soffice``), Word/PowerPoint/Excel se convierten a PDF para verlos idénticos;
  el resultado se guarda en ``.previews`` y se reutiliza mientras el archivo no cambie.

Todo el HTML se arma escapando el texto: nada del documento llega al navegador como marcado.
"""

import base64
import hashlib
import html
import re
import shutil
import subprocess
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET  # noqa: S405 - XML de un paquete OOXML; se lee solo texto y rutas internas

from app.services import drive_service as drive

THUMB_SIZE = (320, 320)
TEXT_LIMIT = 200 * 1024
_IMG_MIME = {'png': 'image/png', 'jpeg': 'image/jpeg', 'jpg': 'image/jpeg', 'gif': 'image/gif', 'webp': 'image/webp'}


def _cache_key(path: Path, suffix: str) -> str:
    st = path.stat()
    raw = f'{drive.rel_of(path)}|{st.st_mtime_ns}|{st.st_size}'.encode()
    return hashlib.sha1(raw, usedforsecurity=False).hexdigest() + suffix


# ── miniaturas ───────────────────────────────────────────────────────────────
def thumbnail(rel: str) -> Path | None:
    path = drive.resolve(rel)
    if drive.kind_of(path.name) != 'image' or path.suffix.lower() in ('.svg', '.heic', '.avif'):
        return None
    cached = drive.root() / '.thumbs' / _cache_key(path, '.webp')
    if cached.exists():
        return cached
    try:
        from PIL import Image, ImageOps

        with Image.open(path) as original:
            thumb = ImageOps.exif_transpose(original)
            thumb.thumbnail(THUMB_SIZE)
            if thumb.mode not in ('RGB', 'RGBA'):
                thumb = thumb.convert('RGBA' if 'A' in thumb.getbands() else 'RGB')
            thumb.save(cached, 'WEBP', quality=78, method=4)
        return cached
    except Exception:
        return None


# ── LibreOffice (opcional) ───────────────────────────────────────────────────
def soffice_bin():
    return shutil.which('soffice') or shutil.which('libreoffice')


def office_pdf(path: Path) -> Path | None:
    """PDF fiel de un documento de Office si LibreOffice está instalado; None si no."""
    binary = soffice_bin()
    if not binary:
        return None
    cached = drive.root() / '.previews' / _cache_key(path, '.pdf')
    if cached.exists():
        return cached
    work = drive.root() / '.previews' / f'work-{cached.stem}'
    work.mkdir(exist_ok=True)
    try:
        subprocess.run(  # noqa: S603 - binario resuelto con which y argumentos fijos
            [binary, '--headless', '--convert-to', 'pdf', '--outdir', str(work), str(path)],
            check=True,
            timeout=90,
            capture_output=True,
        )
        produced = next(work.glob('*.pdf'), None)
        if produced is None:
            return None
        produced.replace(cached)
        return cached
    except Exception:
        return None
    finally:
        shutil.rmtree(work, ignore_errors=True)


# ── DOCX → HTML ──────────────────────────────────────────────────────────────
def _docx_html(path: Path) -> str:
    import docx  # python-docx

    document = docx.Document(str(path))
    images = {}
    for rel in document.part.rels.values():
        if 'image' in rel.reltype:
            blob = rel.target_part.blob
            ext = rel.target_part.content_type.split('/')[-1]
            if len(blob) <= 3 * 1024 * 1024:
                images[rel.rId] = f'data:image/{ext};base64,' + base64.b64encode(blob).decode()

    out = []
    body = document.element.body
    for child in body.iterchildren():
        tag = child.tag.rsplit('}', 1)[-1]
        if tag == 'p':
            out.append(_docx_paragraph(child, images))
        elif tag == 'tbl':
            rows = []
            for tr in child.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tr'):
                cells = []
                for tc in tr.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tc'):
                    text = ''.join(
                        t.text or '' for t in tc.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t')
                    )
                    cells.append(f'<td>{html.escape(text)}</td>')
                rows.append('<tr>' + ''.join(cells) + '</tr>')
            out.append('<table>' + ''.join(rows) + '</table>')
    return '\n'.join(x for x in out if x)


_W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
_R_EMBED = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed'


def _docx_paragraph(p, images) -> str:
    style = ''
    ppr = p.find(f'{_W}pPr')
    if ppr is not None:
        st = ppr.find(f'{_W}pStyle')
        if st is not None:
            style = (st.get(f'{_W}val') or '').lower()
    parts = []
    for run in p.iter(f'{_W}r'):
        text = ''.join(t.text or '' for t in run.iter(f'{_W}t'))
        rpr = run.find(f'{_W}rPr')
        piece = html.escape(text)
        if piece and rpr is not None:
            if rpr.find(f'{_W}b') is not None:
                piece = f'<strong>{piece}</strong>'
            if rpr.find(f'{_W}i') is not None:
                piece = f'<em>{piece}</em>'
        parts.append(piece)
        for blip in run.iter('{http://schemas.openxmlformats.org/drawingml/2006/main}blip'):
            src = images.get(blip.get(_R_EMBED))
            if src:
                parts.append(f'<img src="{src}" alt="">')
    content = ''.join(parts)
    if not content.strip():
        return ''
    if style.startswith('heading') or style.startswith('ttulo') or style.startswith('titulo') or style == 'title':
        level = re.sub(r'\D', '', style) or '1'
        level = str(min(max(int(level), 1), 4))
        return f'<h{level}>{content}</h{level}>'
    if 'list' in style or (ppr is not None and ppr.find(f'{_W}numPr') is not None):
        return f'<p class="li">• {content}</p>'
    return f'<p>{content}</p>'


# ── PPTX → diapositivas ──────────────────────────────────────────────────────
_A = '{http://schemas.openxmlformats.org/drawingml/2006/main}'
_P = '{http://schemas.openxmlformats.org/presentationml/2006/main}'


def _pptx_slides(path: Path) -> list:
    slides = []
    with zipfile.ZipFile(path) as zf:
        names = sorted(
            (n for n in zf.namelist() if re.fullmatch(r'ppt/slides/slide\d+\.xml', n)),
            key=lambda n: int(re.search(r'(\d+)', n.rsplit('/', 1)[-1]).group(1)),
        )
        for n in names[:200]:
            root = ET.fromstring(zf.read(n))  # noqa: S314 - XML interno del paquete, sin entidades externas
            rels = {}
            rel_name = n.replace('slides/', 'slides/_rels/') + '.rels'
            if rel_name in zf.namelist():
                for r in ET.fromstring(zf.read(rel_name)):  # noqa: S314
                    rels[r.get('Id')] = r.get('Target')
            texts = []
            for sp in root.iter(f'{_P}sp'):
                paras = []
                for para in sp.iter(f'{_A}p'):
                    line = ''.join(t.text or '' for t in para.iter(f'{_A}t')).strip()
                    if line:
                        paras.append(line)
                if paras:
                    texts.append(paras)
            pics = []
            for blip in root.iter(f'{_A}blip'):
                target = rels.get(blip.get(_R_EMBED))
                if not target:
                    continue
                media = 'ppt/' + target.replace('../', '')
                ext = media.rsplit('.', 1)[-1].lower()
                if media in zf.namelist() and ext in _IMG_MIME:
                    blob = zf.read(media)
                    if len(blob) <= 2 * 1024 * 1024:
                        pics.append(f'data:{_IMG_MIME[ext]};base64,' + base64.b64encode(blob).decode())
            slides.append(
                {'title': texts[0][0] if texts else '', 'blocks': texts[1:] if texts else [], 'images': pics[:4]}
            )
    return slides


# ── punto de entrada ─────────────────────────────────────────────────────────
def describe(rel: str) -> dict:
    """Cómo previsualizar un archivo: {'mode': 'image'|'pdf'|'html'|'slides'|'text'|'none', ...}."""
    path = drive.resolve(rel)
    if path.is_dir():
        raise drive.DriveError('Es una carpeta')
    kind = drive.kind_of(path.name)
    ext = path.suffix.lower().lstrip('.')
    if kind == 'image':
        return {'mode': 'image'}
    if kind == 'pdf':
        return {'mode': 'pdf'}
    if kind in ('audio', 'video'):
        return {'mode': kind}
    if kind in ('word', 'slides', 'sheet') and ext != 'csv':
        if office_pdf(path):
            return {'mode': 'pdf', 'converted': True}
        try:
            if ext == 'docx':
                return {'mode': 'html', 'html': _docx_html(path)}
            if ext == 'pptx':
                return {'mode': 'slides', 'slides': _pptx_slides(path)}
        except Exception:
            return {'mode': 'none', 'reason': 'No se pudo leer el documento (¿está dañado?)'}
        return {
            'mode': 'none',
            'reason': 'Para ver este formato instala LibreOffice en el servidor. Puedes descargarlo.',
        }
    if kind == 'text' or ext == 'csv':
        with open(path, 'rb') as fh:
            raw = fh.read(TEXT_LIMIT)
        return {
            'mode': 'text',
            'text': raw.decode('utf-8', errors='replace'),
            'truncated': path.stat().st_size > TEXT_LIMIT,
        }
    if kind == 'archive' and ext == 'zip':
        try:
            with zipfile.ZipFile(path) as zf:
                items = [{'name': m.filename, 'size': m.file_size} for m in zf.infolist()[:300]]
            return {'mode': 'archive', 'items': items}
        except zipfile.BadZipFile:
            return {'mode': 'none', 'reason': 'El .zip está dañado'}
    return {'mode': 'none', 'reason': 'Este tipo de archivo no tiene vista previa. Puedes descargarlo.'}


def printable_pdf(rel: str) -> Path | None:
    """Archivo listo para imprimir: PDF/imagen/texto tal cual; Office convertido con LibreOffice."""
    path = drive.resolve(rel)
    kind = drive.kind_of(path.name)
    if kind in ('pdf', 'image', 'text'):
        return path
    if kind in ('word', 'slides', 'sheet'):
        return office_pdf(path)
    return None
