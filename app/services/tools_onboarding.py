"""Alta completa de un paciente desde el asistente: lo que el panel «Crear usuario» hace en un paso.

`create_user` ya acepta el plan y el horario; si el usuario los dejó en blanco, el asistente propone después el
contrato (`create_service_contract`) y las sesiones con esta herramienta, que usa el mismo generador que el panel
(salta feriados, la primera puede ser la evaluación).
"""

from datetime import datetime

from app.extensions import db
from app.models import Appointment, User
from app.services.tools_registry import CORE_TOOL_NAMES, tool

STAFF = {'admin', 'supervisor'}


@tool(
    name='schedule_patient_plan',
    description=(
        'Programa las sesiones del plan de un paciente (4, 8 o 12 sesiones según 1, 2 o 3 por semana) a partir de una '
        'fecha y hora, en los días elegidos, con su terapeuta. Salta feriados. Igual que «Generar horario automático» '
        'del panel de usuarios.'
    ),
    parameters={
        'type': 'object',
        'properties': {
            'patient_id': {'type': 'integer', 'description': 'Paciente'},
            'therapist_id': {'type': 'integer', 'description': 'Terapeuta de las sesiones'},
            'modality': {'type': 'integer', 'enum': [1, 2, 3], 'description': 'Sesiones por semana: 1, 2 o 3'},
            'start_date': {'type': 'string', 'description': 'Fecha de inicio YYYY-MM-DD'},
            'start_time': {'type': 'string', 'description': 'Hora de las sesiones HH:MM'},
            'days_of_week': {
                'type': 'array',
                'items': {'type': 'integer'},
                'description': 'Días de sesión: 0=lunes … 5=sábado',
            },
            'evaluation_date': {'type': 'string', 'description': 'Fecha de la sesión de evaluación YYYY-MM-DD'},
        },
        'required': ['patient_id', 'therapist_id', 'modality', 'start_date', 'start_time'],
    },
    category='write',
    roles=STAFF,
)
def handle_schedule_patient_plan(
    patient_id, therapist_id, modality, start_date, start_time, days_of_week=None, evaluation_date=None, **kwargs
):
    from app.services.admin_service import AdminService

    patient = db.session.get(User, int(patient_id))
    therapist = db.session.get(User, int(therapist_id))
    if not patient or patient.role != 'jugador':
        return {'error': 'Ese paciente no existe.'}
    if not therapist or therapist.role != 'terapista':
        return {'error': 'Ese terapeuta no existe.'}
    try:
        start = datetime.strptime(f'{start_date} {start_time}'[:16], '%Y-%m-%d %H:%M')
    except ValueError:
        return {'error': 'Fecha u hora inválida (usa AAAA-MM-DD y HH:MM).'}
    before = Appointment.query.filter_by(patient_id=patient.id).count()
    AdminService().generate_schedule(
        patient, therapist.id, start, int(modality), days_of_week or None, evaluation_date=evaluation_date
    )
    if not patient.assigned_therapist_id:
        patient.assigned_therapist_id = therapist.id
        db.session.commit()
    created = Appointment.query.filter_by(patient_id=patient.id).count() - before
    return {
        'success': True,
        'sessions_created': created,
        'message': f'{created} sesiones programadas para {patient.username} con {therapist.username}.',
    }


if 'schedule_patient_plan' not in CORE_TOOL_NAMES:
    CORE_TOOL_NAMES.append('schedule_patient_plan')
