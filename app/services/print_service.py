"""Impresión remota desde el drive usando CUPS del servidor.

El servidor (VM-APP) imprime con los comandos estándar de CUPS (`lpstat`, `lp`, `cancel`). Las impresoras de la red
aparecen solas si CUPS tiene `cups-browsed`/IPP Everywhere, o se agregan una vez con `lpadmin`. Si CUPS no está
instalado, la API lo dice con claridad y el panel muestra cómo activarlo; nada se rompe.

Los trabajos programados se guardan en `print_job` y un job del scheduler los envía cuando llega su hora.
"""

import logging
import re
import shutil
import subprocess
from datetime import UTC, datetime

from app.extensions import db
from app.models.print_job import PrintJob
from app.services import drive_preview
from app.services import drive_service as drive

logger = logging.getLogger(__name__)
_SAFE_PRINTER = re.compile(r'^[A-Za-z0-9_.\-@]{1,127}$')
_PAGE_RANGE = re.compile(r'^\s*\d+(\s*-\s*\d+)?(\s*,\s*\d+(\s*-\s*\d+)?)*\s*$')


def _now():
    return datetime.now(UTC).replace(tzinfo=None)


def _bin(name):
    return shutil.which(name)


def _run(args, timeout=20):
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False)  # noqa: S603


def _printer_state(text):
    """Estado legible de la línea de `lpstat -p` (CUPS responde en inglés o en español según el idioma)."""
    t = text.lower()
    if 'disabled' in t or 'deshabilit' in t:
        return 'disabled'
    if 'printing' in t or 'imprim' in t:
        return 'printing'
    if 'idle' in t or 'inactiv' in t:
        return 'idle'
    return 'unknown'


def status() -> dict:
    """{'available': bool, 'printers': [...], 'default': str|None, 'help': str|None}."""
    lpstat = _bin('lpstat')
    if not lpstat or not _bin('lp'):
        return {
            'available': False,
            'printers': [],
            'default': None,
            'help': 'El servidor no tiene CUPS. Instálalo con «sudo apt install cups cups-browsed» y agrega la '
            'impresora de la red; aparecerá aquí sola.',
        }
    printers = []
    try:
        out = _run([lpstat, '-p']).stdout
        for line in out.splitlines():
            m = re.match(r'^(?:printer|la impresora|impresora) (\S+) (.*)$', line)
            if m:
                printers.append({'name': m.group(1), 'state': _printer_state(m.group(2)), 'detail': m.group(2).strip()})
        default = _run([lpstat, '-d']).stdout
        dm = re.search(r':\s*(\S+)\s*$', default.strip())
        default_name = dm.group(1) if dm and dm.group(1) in {p['name'] for p in printers} else None
    except Exception as exc:
        logger.warning('No se pudo consultar CUPS: %s', exc)
        return {'available': False, 'printers': [], 'default': None, 'help': f'CUPS no respondió: {exc}'}
    return {
        'available': True,
        'printers': printers,
        'default': default_name,
        'help': None
        if printers
        else 'CUPS está instalado pero no tiene impresoras. Agrega la de la red desde '
        'http://localhost:631 en el servidor o con «lpadmin».',
    }


def validate(data: dict) -> dict:
    printer = str(data.get('printer') or '').strip()
    if not _SAFE_PRINTER.match(printer):
        raise drive.DriveError('Elige una impresora')
    copies = int(data.get('copies') or 1)
    if not 1 <= copies <= 50:
        raise drive.DriveError('Copias: entre 1 y 50')
    page_range = (data.get('page_range') or '').strip() or None
    if page_range and not _PAGE_RANGE.match(page_range):
        raise drive.DriveError('Páginas: usa un formato como 1-3,5')
    scheduled = data.get('scheduled_at')
    when = None
    if scheduled:
        try:
            when = datetime.fromisoformat(str(scheduled).replace('Z', '+00:00')).astimezone(UTC).replace(tzinfo=None)
        except ValueError as exc:
            raise drive.DriveError('Fecha de programación no válida') from exc
        if when < _now():
            raise drive.DriveError('La hora programada ya pasó')
    return {
        'printer': printer,
        'copies': copies,
        'duplex': bool(data.get('duplex')),
        'color': data.get('color', True) is not False,
        'page_range': page_range.replace(' ', '') if page_range else None,
        'scheduled_at': when,
    }


def create_job(rel: str, data: dict, user_id=None) -> PrintJob:
    path = drive.resolve(rel)
    if path.is_dir():
        raise drive.DriveError('No se puede imprimir una carpeta')
    if drive.kind_of(path.name) not in ('pdf', 'image', 'text', 'word', 'slides', 'sheet'):
        raise drive.DriveError('Este tipo de archivo no se puede imprimir')
    opts = validate(data)
    if not status()['available']:
        raise drive.DriveError('No hay servicio de impresión en el servidor', 503)
    job = PrintJob(file_path=drive.rel_of(path), file_name=path.name, created_by_id=user_id, **opts)
    db.session.add(job)
    db.session.commit()
    if job.scheduled_at is None:
        send(job)
    return job


def send(job: PrintJob) -> PrintJob:
    """Manda un trabajo a CUPS. Nunca lanza: el resultado queda en el propio trabajo."""
    try:
        source = drive_preview.printable_pdf(job.file_path)
        if source is None:
            raise drive.DriveError('Para imprimir documentos de Office el servidor necesita LibreOffice')
        args = [_bin('lp'), '-d', job.printer, '-n', str(job.copies), '-t', job.file_name[:100]]
        args += ['-o', 'sides=two-sided-long-edge' if job.duplex else 'sides=one-sided']
        if not job.color:
            args += ['-o', 'print-color-mode=monochrome']
        if job.page_range:
            args += ['-o', f'page-ranges={job.page_range}']
        args += ['--', str(source)]
        result = _run(args, timeout=60)
        if result.returncode != 0:
            raise drive.DriveError((result.stderr or result.stdout or 'CUPS rechazó el trabajo').strip()[:250])
        m = re.search(r'(\S+-\d+)', result.stdout or '')
        job.cups_job = m.group(1) if m else None
        job.status, job.error, job.sent_at = 'sent', None, _now()
    except Exception as exc:
        job.status, job.error = 'failed', str(exc)[:250]
    db.session.commit()
    return job


def cancel(job: PrintJob) -> PrintJob:
    if job.status == 'scheduled':
        job.status = 'cancelled'
    elif job.status == 'sent' and job.cups_job and _bin('cancel'):
        _run([_bin('cancel'), job.cups_job])
        job.status = 'cancelled'
    else:
        raise drive.DriveError('Este trabajo ya no se puede cancelar')
    db.session.commit()
    return job


def dispatch_due() -> int:
    """Envía los trabajos programados cuya hora ya llegó (lo llama el scheduler cada minuto)."""
    due = PrintJob.query.filter(PrintJob.status == 'scheduled', PrintJob.scheduled_at <= _now()).limit(20).all()
    for job in due:
        send(job)
    return len(due)
