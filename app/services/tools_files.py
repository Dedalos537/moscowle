"""Archivos del asistente: informe completo de un alumno, guardar en el Drive del centro e imprimir (PRP 016).

Son herramientas MCP como las demás: las usa el asistente, el chat flotante y cualquier proveedor de IA.
- `patient_report`: un TXT con sus datos, contrato, TODAS las sesiones (estado, asistencia, notas, juegos y
  resultados), métricas de evolución y un informe terapéutico redactado por la IA (si hay una disponible).
- `drive_save_upload`: guarda en el Drive un archivo que se subió al chat.
- `print_drive_file`: manda a imprimir un archivo del Drive.
"""

import os
import shutil
from datetime import datetime
from statistics import mean

from flask import current_app

from app.extensions import db
from app.models import Appointment, User
from app.services.tools_registry import CORE_TOOL_NAMES, tool

STAFF = {'admin', 'supervisor'}
REPORTS_DIR = 'Informes'
UPLOADS_DIR = 'Asistente'


def upload_dir():
    path = os.path.join(current_app.instance_path, 'uploads', 'mcp')  # se sirve en /uploads/mcp (comprobantes)
    os.makedirs(path, exist_ok=True)
    return path


def upload_path(token, user_id=None):
    """Ruta de un archivo subido al chat. El token lleva el id de quien lo subió: nadie usa el de otro."""
    name = os.path.basename(str(token or ''))
    if not name or name != token or (user_id is not None and not name.startswith(f'{int(user_id)}_')):
        raise ValueError('Archivo no encontrado')
    path = os.path.join(upload_dir(), name)
    if not os.path.isfile(path):
        raise ValueError('Archivo no encontrado')
    return path


def _ensure_folder(rel):
    from app.services import drive_service as drive

    path = drive.resolve(rel, must_exist=False)
    path.mkdir(parents=True, exist_ok=True)
    return rel


def _fmt(dt):
    return dt.strftime('%d/%m/%Y %H:%M') if dt else '—'


# ── informe del alumno ──────────────────────────────────────────────────────
def build_patient_report(patient, ai_text=None):
    """Texto del informe (sin IA). `ai_text(prompt)` opcional devuelve la redacción terapéutica."""
    from app.models.appointment import SessionMetrics
    from app.models.contract import Contract, Installment
    from app.models.report import SessionAudit

    sessions = Appointment.query.filter_by(patient_id=patient.id).order_by(Appointment.start_time).all()
    metrics = SessionMetrics.query.filter_by(user_id=patient.id).order_by(SessionMetrics.date).all()
    contracts = Contract.query.filter_by(patient_id=patient.id).all()
    therapist = db.session.get(User, patient.assigned_therapist_id) if patient.assigned_therapist_id else None
    now = datetime.utcnow()
    done = [a for a in sessions if a.status == 'completed']
    cancelled = [a for a in sessions if a.status in ('cancelled', 'canceled')]
    upcoming = [a for a in sessions if a.start_time >= now and a.status not in ('cancelled', 'canceled')]
    attended = [a for a in sessions if (a.attendance or '') in ('present', 'attended', 'asistio')]
    absent = [a for a in sessions if (a.attendance or '') in ('absent', 'falta', 'no_show')]

    L = []
    L += [f'INFORME DEL PACIENTE — {patient.username}', f'Generado: {now.strftime("%d/%m/%Y %H:%M")} (UTC)', '=' * 72]
    L += ['', 'DATOS']
    for label, value in (
        ('Código', patient.login_code),
        ('Sede', getattr(patient.sede_item, 'name', None)),
        ('Terapeuta asignado', therapist.username if therapist else None),
        ('Fecha de nacimiento', patient.date_of_birth),
        ('Diagnóstico preliminar', patient.preliminary_diagnosis),
        ('Objetivos de terapia', patient.therapy_goals),
        ('Apoderado', patient.guardian_name),
        ('Contacto del apoderado', patient.guardian_contact),
        ('Notas', patient.notes),
    ):
        if value:
            L.append(f'- {label}: {value}')

    L += ['', 'CONTRATOS']
    if not contracts:
        L.append('- Sin contrato registrado.')
    for c in contracts:
        insts = Installment.query.filter_by(contract_id=c.id).all()
        paid = sum(i.paid_amount or 0 for i in insts)
        L.append(
            f'- {getattr(c, "name", None) or "Contrato"}: S/ {c.total_amount:,.2f} · {len(insts)} cuotas · '
            f'pagado S/ {paid:,.2f} · {"activo" if c.is_active is not False else "cancelado"}'
        )

    L += ['', 'RESUMEN DE SESIONES']
    L.append(
        f'- Total: {len(sessions)} · realizadas: {len(done)} · canceladas: {len(cancelled)} · próximas: {len(upcoming)}'
    )
    if attended or absent:
        rate = len(attended) / max(1, len(attended) + len(absent)) * 100
        L.append(f'- Asistencia registrada: {len(attended)} presentes, {len(absent)} faltas ({rate:.0f} %)')

    L += ['', 'EVOLUCIÓN EN LOS JUEGOS']
    if not metrics:
        L.append('- Sin resultados de juegos todavía.')
    else:
        by_game = {}
        for m in metrics:
            by_game.setdefault(m.game_name, []).append(m)
        for game, rows in by_game.items():
            first, last = rows[0], rows[-1]
            trend = (last.accurracy or 0) - (first.accurracy or 0)
            L.append(
                f'- {game}: {len(rows)} partidas · precisión {first.accurracy:.0f} % → {last.accurracy:.0f} % '
                f'({"+" if trend >= 0 else ""}{trend:.0f}) · tiempo medio {mean(r.avg_time or 0 for r in rows):.1f} s'
            )

    L += ['', 'DETALLE DE CADA SESIÓN']
    for i, a in enumerate(sessions, 1):
        ther = db.session.get(User, a.therapist_id)
        L.append(f'{i:>3}. {_fmt(a.start_time)} · {a.title or "Sesión"} · {a.status}'
                 f'{" · " + a.attendance if a.attendance and a.attendance != "pending" else ""}'
                 f' · {ther.username if ther else "—"}')  # fmt: skip
        if a.notes:
            L.append(f'     Notas: {a.notes.strip()[:600]}')
        games = a.games_list if isinstance(a.games_list, list) else []
        if games:
            L.append(f'     Juegos: {", ".join(str(g) for g in games)[:300]}')
        audit = SessionAudit.query.filter_by(appointment_id=a.id).first()
        if audit and audit.planned_text:
            L.append(f'     Planificado: {audit.planned_text.strip()[:600]}')
        for m in [m for m in metrics if m.session_id == a.id]:
            L.append(f'     Resultado {m.game_name}: precisión {m.accurracy:.0f} %, tiempo {m.avg_time:.1f} s')

    text = '\n'.join(L)
    if ai_text:
        prompt = (
            'Eres terapeuta de un centro de terapias en Perú. Con SOLO los datos de abajo (no inventes nada), redacta '
            'un INFORME TERAPÉUTICO en español con estas secciones: 1) Resumen del caso, 2) Asistencia y '
            'continuidad, 3) Evolución observada (cita juegos y notas concretas), 4) Fortalezas, 5) Áreas a '
            'trabajar, 6) Recomendaciones para el próximo periodo. Si faltan datos para una sección, dilo. Texto '
            'plano, sin markdown.\n\n' + text[:14000]
        )
        narrative = ai_text(prompt)
        if narrative:
            text += (
                '\n\n' + '=' * 72 + '\nINFORME TERAPÉUTICO (redactado por la IA a partir de los datos)\n\n' + narrative
            )
        else:
            text += '\n\n(No había un modelo de IA disponible para redactar el informe terapéutico.)'
    return text


@tool(
    name='patient_report',
    description=(
        'Arma el informe completo de un paciente/alumno: datos, contrato, todas sus sesiones (notas, juegos y '
        'resultados), asistencia, evolución y un informe terapéutico redactado. Lo guarda como TXT en el Drive '
        '(Informes/<paciente>) para descargarlo o imprimirlo.'
    ),
    parameters={
        'type': 'object',
        'properties': {
            'patient_id': {'type': 'integer', 'description': 'Paciente'},
            'with_ai': {'type': 'boolean', 'description': 'Incluir el informe terapéutico redactado por la IA'},
        },
        'required': ['patient_id'],
    },
    category='write',
    roles=STAFF,
)
def handle_patient_report(patient_id, with_ai=True, _user_id=None, **kwargs):
    from app.services import assistant_files
    from app.services import drive_service as drive

    patient = db.session.get(User, int(patient_id))
    if not patient or patient.role != 'jugador':
        return {'error': 'Ese paciente no existe.'}
    user = db.session.get(User, int(_user_id)) if _user_id else None
    writer = (lambda p: assistant_files.ai_text(p, user)[0]) if with_ai is not False and user else None
    text = build_patient_report(patient, writer)
    folder = _ensure_folder(f'{REPORTS_DIR}/{drive.clean_name(patient.username)}')
    entry = drive.save_bytes(folder, f'Informe {datetime.now().strftime("%Y-%m-%d %H%M")}.txt', text.encode('utf-8'))
    return {
        'success': True,
        'file': {'name': entry['name'], 'path': entry['path'], 'size': entry.get('size')},
        'preview': text[:1500],
        'message': f'Informe de {patient.username} listo ({len(text.splitlines())} líneas). Quedó en el Drive.',
    }


# ── Drive e impresión ───────────────────────────────────────────────────────
@tool(
    name='drive_save_upload',
    description='Guarda en el Drive del centro un archivo que se subió al chat (para tenerlo o imprimirlo).',
    parameters={
        'type': 'object',
        'properties': {
            'upload': {'type': 'string', 'description': 'Archivo subido al chat'},
            'folder': {'type': 'string', 'description': 'Carpeta del Drive, p. ej. «Pacientes/Liam»'},
            'name': {'type': 'string', 'description': 'Nombre del archivo'},
        },
        'required': ['upload', 'folder'],
    },
    category='write',
    roles={'admin'},
)
def handle_drive_save_upload(upload, folder, name=None, _user_id=None, **kwargs):
    from app.services import drive_service as drive

    try:
        src = upload_path(upload, _user_id)
    except ValueError as exc:
        return {'error': str(exc)}
    ext = os.path.splitext(src)[1]
    final = drive.clean_name(name or os.path.basename(src).split('_', 2)[-1])
    if not os.path.splitext(final)[1]:
        final += ext
    rel = _ensure_folder('/'.join(drive.clean_name(p) for p in str(folder).split('/') if p.strip()) or UPLOADS_DIR)
    size = os.path.getsize(src)
    drive.ensure_space(size)
    target = drive._unique(drive.resolve(rel), final)
    shutil.copyfile(src, target)
    drive._bump_usage(size)
    entry = drive._entry(target)
    return {
        'success': True,
        'file': {'name': entry['name'], 'path': entry['path'], 'size': size},
        'message': f'Guardado en el Drive: {entry["path"]}.',
    }


@tool(
    name='print_drive_file',
    description='Manda a imprimir un archivo del Drive del centro (PDF, imagen, Word, texto) en la impresora del centro.',
    parameters={
        'type': 'object',
        'properties': {
            'path': {'type': 'string', 'description': 'Ruta del archivo en el Drive'},
            'copies': {'type': 'integer', 'description': 'Copias (1 a 50)'},
            'color': {'type': 'boolean', 'description': 'A color'},
        },
        'required': ['path'],
    },
    category='write',
    roles={'admin'},
)
def handle_print_drive_file(path, copies=1, color=True, _user_id=None, **kwargs):
    from app.services import drive_service as drive
    from app.services import print_service

    try:
        st = print_service.status()
        printer = st.get('default') or next((p['name'] for p in st.get('printers') or []), None)
        if not st.get('available') or not printer:
            return {'error': st.get('help') or 'No hay una impresora disponible ahora.'}
        job = print_service.create_job(
            path, {'printer': printer, 'copies': copies or 1, 'color': color}, user_id=_user_id
        )
    except drive.DriveError as exc:
        return {'error': str(exc)}
    if job.status == 'failed':
        return {'error': job.error or 'La impresora no aceptó el trabajo.'}
    return {'success': True, 'message': f'Enviado a imprimir en {printer} ({job.copies} copia(s)).'}


for _name in ('patient_report', 'drive_save_upload', 'print_drive_file'):
    if _name not in CORE_TOOL_NAMES:
        CORE_TOOL_NAMES.append(_name)
