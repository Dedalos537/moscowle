"""Adjuntos de mensajes: una sola regla para guardar, clasificar y servir.

Antes había tres copias (chat, mensajes antiguos y portal del paciente) y la lista de tipos para ENVIAR no coincidía
con la de DESCARGAR: un .pptx, un .csv, una foto .heic de iPhone o un video .3gp de Android se guardaban "bien" y
luego la descarga respondía 403. Ahora el envío solo acepta lo que la descarga sirve, y lo rechaza con un mensaje
claro si no.
"""

import os
import re
import unicodedata
import uuid

from flask import current_app

# Tipos permitidos (envío y descarga usan esta misma lista: config.ALLOWED_UPLOAD_EXTENSIONS la importa).
IMAGE = {'jpg', 'jpeg', 'png', 'gif', 'webp', 'heic', 'heif', 'bmp'}
VIDEO = {'mp4', 'mov', 'm4v', '3gp', 'mkv', 'avi', 'webm'}
AUDIO = {'mp3', 'wav', 'ogg', 'oga', 'opus', 'm4a', 'aac', 'amr', 'flac', 'weba'}
DOCUMENT = {'pdf', 'doc', 'docx', 'odt', 'rtf', 'txt', 'xls', 'xlsx', 'ods', 'csv', 'ppt', 'pptx', 'odp'}
ARCHIVE = {'zip', 'rar', '7z'}
ALLOWED = IMAGE | VIDEO | AUDIO | DOCUMENT | ARCHIVE

# Se muestran dentro de la página; lo demás se descarga siempre (nunca se ejecuta en el dominio de la app).
INLINE = (IMAGE - {'heic', 'heif'}) | VIDEO | AUDIO | {'pdf'}

MAX_BYTES = 50 * 1024 * 1024  # el túnel de Cloudflare corta en 100 MB; 50 MB deja margen y es suficiente para chat
UUID_PREFIX = re.compile(r'^[0-9a-f]{32}_')


class AttachmentError(ValueError):
    pass


def folder() -> str:
    base = current_app.config.get('UPLOAD_FOLDER') or os.path.join(current_app.instance_path, 'uploads')
    path = os.path.join(base, 'messages')
    os.makedirs(path, exist_ok=True)
    return path


def ext_of(name: str) -> str:
    return name.rsplit('.', 1)[-1].lower() if '.' in name else ''


def clean_name(name: str) -> str:
    """Nombre legible y seguro: conserva tildes y ñ (secure_filename las borraba), sin rutas ni caracteres raros."""
    name = unicodedata.normalize('NFC', os.path.basename(str(name or '').replace('\\', '/')))
    name = re.sub(r'[\x00-\x1f<>:"/\\|?*]+', '', name).strip().strip('.')
    name = re.sub(r'\s+', '_', name)
    if not name or name.startswith('.'):
        name = 'archivo' + name
    stem, dot, ext = name.rpartition('.')
    if dot:
        return f'{stem[:100]}.{ext[:10]}'
    return name[:110]


def classify(ext: str, mime: str) -> str:
    """Tipo para mostrar el adjunto. El MIME manda (un .webm puede ser video o nota de voz)."""
    mime = (mime or '').lower()
    if mime.startswith('image/') and ext in IMAGE:
        return 'image'
    if mime.startswith('video/') and ext in VIDEO:
        return 'video'
    if mime.startswith('audio/') and ext in AUDIO | {'webm', 'mp4'}:
        return 'audio'
    if ext in IMAGE:
        return 'image'
    if ext in AUDIO:
        return 'audio'
    if ext in VIDEO:
        return 'video'
    return 'file'


def save(file) -> tuple[str, str]:
    """Guarda el archivo subido. Devuelve (nombre_guardado, tipo). Lanza AttachmentError con un mensaje para el usuario."""
    name = clean_name(file.filename)
    ext = ext_of(name)
    if ext not in ALLOWED:
        raise AttachmentError(
            f'No se pueden enviar archivos .{ext or "sin extensión"}. Envía imágenes, audio, video, PDF, Word, '
            'Excel, PowerPoint, texto o un .zip.'
        )
    stored = f'{uuid.uuid4().hex}_{name}'
    path = os.path.join(folder(), stored)
    size = 0
    try:
        with open(path, 'wb') as out:
            while True:
                chunk = file.stream.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_BYTES:
                    raise AttachmentError(
                        f'El archivo pesa más de {MAX_BYTES // 1024 // 1024} MB. Comprímelo o envía un enlace.'
                    )
                out.write(chunk)
    except AttachmentError:
        os.remove(path)
        raise
    if size == 0:
        os.remove(path)
        raise AttachmentError('El archivo está vacío.')
    return stored, classify(ext, file.mimetype)


def display_name(stored: str | None) -> str | None:
    return UUID_PREFIX.sub('', stored) if stored else None
