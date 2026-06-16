import json
from datetime import datetime, timedelta

from app.models import Appointment, SmartAction, User, db


class WorkflowEngine:
    """
    Cerebro de Automatización del ERP Moscowle.
    Escanea incoherencias, pendientes y oportunidades de automatización
    en todo el sistema.
    """

    def generate_daily_actions(self):
        """
        Escaneo integral de todas las entidades para generar SmartActions.
        """
        now = datetime.utcnow()
        today = now.date()
        actions_generated = 0

        past_sessions = Appointment.query.filter(
            Appointment.start_time < now - timedelta(hours=2), Appointment.status == 'scheduled'
        ).all()

        for sess in past_sessions:
            desc = f'Sesión de {sess.patient.username} con {sess.therapist.username} del {sess.start_time.strftime("%d/%m")} no marcada.'
            self._create_smart_action(
                module='sesiones',
                description=desc,
                automation_level='requires_confirmation',
                payload={
                    'action': 'complete_session',
                    'appointment_id': sess.id,
                    'patient_id': sess.patient_id,
                    'date': sess.start_time.isoformat(),
                },
            )
            actions_generated += 1

        no_sede = User.query.filter_by(role='jugador', is_active=True, sede_id=None).all()
        for u in no_sede:
            self._create_smart_action(
                module='usuarios',
                description=f'Paciente {u.username} no tiene sede asignada.',
                automation_level='manual',
                payload={'user_id': u.id, 'action': 'assign_sede'},
            )
            actions_generated += 1

        critical_patients = User.query.filter(
            User.role == 'jugador',
            User.is_active == True,
            User.sessions_total > 0,
            User.sessions_attended >= User.sessions_total,
        ).all()

        for u in critical_patients:
            self._create_smart_action(
                module='pagos',
                description=f'Paciente {u.username} agotó sesiones ({u.sessions_attended}/{u.sessions_total}). Generar cobro.',
                automation_level='requires_confirmation',
                payload={
                    'action': 'request_payment',
                    'user_id': u.id,
                    'amount': u.payment_amount,
                    'modality': u.payment_plan,
                },
            )
            actions_generated += 1

        if today.day == 1 or today.day == 15:
            self._create_smart_action(
                module='finanzas',
                description=f'Recordatorio mensual: Registrar gastos de servicios (Luz/Agua/Internet) del día {today.day}.',
                automation_level='manual',
                payload={'action': 'register_expense', 'category': 'servicios'},
            )
            actions_generated += 1

        db.session.commit()
        return actions_generated

    def _create_smart_action(self, module, description, automation_level, payload):
        """
        Evita duplicados si la tarea ya existe y está pendiente.
        """
        payload_str = json.dumps(payload)
        exists = SmartAction.query.filter_by(module=module, description=description, status='pending').first()

        if not exists:
            action = SmartAction(
                module=module, description=description, automation_level=automation_level, suggested_payload=payload_str
            )
            db.session.add(action)
