import uuid
from datetime import datetime, timedelta

from app.extensions import bcrypt
from app.models import Appointment, Sede, User, db
from app.services.email_service import EmailService
from app.services.notification_service import NotificationService

HOLIDAYS_2026 = [
    '2026-01-01',
    '2026-04-02',
    '2026-04-03',
    '2026-05-01',
    '2026-06-29',
    '2026-07-28',
    '2026-07-29',
    '2026-08-30',
    '2026-10-08',
    '2026-11-01',
    '2026-12-08',
    '2026-12-25',
]


class AdminService:
    def __init__(self):
        self.notification_service = NotificationService()
        self.email_service = EmailService()

    def assign_therapist(self, patient_id, therapist_id=None, therapist_ids=None):
        patient = User.query.get(patient_id)

        if not patient:
            return False, 'Usuario no encontrado'

        if patient.role != 'jugador':
            return False, 'Roles inválidos'

        if therapist_ids is not None:
            if not isinstance(therapist_ids, list):
                return False, 'Formato inválido'

            if len(therapist_ids) > 3:
                return False, 'Máximo 3 terapeutas permitidos por paciente'

            new_therapists = []
            for tid in therapist_ids:
                t = User.query.get(tid)
                if t and t.role == 'terapista':
                    new_therapists.append(t)

            patient.therapists = new_therapists

            if new_therapists:
                patient.assigned_therapist_id = new_therapists[0].id
            else:
                patient.assigned_therapist_id = None

            db.session.commit()

            try:
                self.notification_service.create_notification(patient.id, 'Terapeutas actualizados')
                for t in new_therapists:
                    self.notification_service.create_notification(t.id, f'Nuevo paciente asignado: {patient.username}')
            except Exception:
                pass

            return True, 'Asignación actualizada correctamente'

        therapist = User.query.get(therapist_id)
        if not therapist or therapist.role != 'terapista':
            return False, 'Terapeuta inválido'

        patient.assigned_therapist_id = therapist.id
        if therapist not in patient.therapists:
            patient.therapists.append(therapist)

        db.session.commit()

        try:
            self.notification_service.create_notification(patient.id, f'Terapeuta asignado: {therapist.username}')
            self.notification_service.create_notification(therapist.id, f'Nuevo paciente asignado: {patient.username}')
        except Exception:
            pass

        return True, 'Asignación exitosa'

    def create_user(self, data):
        email = data.get('email', '').strip().lower()
        role = data.get('role')
        username = data.get('username')

        if email:
            if User.query.filter_by(email=email).first():
                return False, 'El correo ya está registrado'

        is_active = True
        plain_password = None

        if not email:
            email = f'noemail_{uuid.uuid4().hex[:8]}@local'
            plain_password = uuid.uuid4().hex
            is_active = False
        else:
            plain_password = self.email_service.generate_password()
            is_active = True

        hashed_password = bcrypt.generate_password_hash(plain_password).decode('utf-8')

        user = User(
            username=username or email.split('@')[0],
            email=email,
            password=hashed_password,
            role=role,
            is_active=is_active,
        )

        if data.get('phone'):
            user.phone = data.get('phone')
        if data.get('guardian'):
            user.guardian_name = data.get('guardian')

        try:
            sede_id = data.get('sede_id')
            if role == 'jugador' and sede_id:
                sede = Sede.query.get(sede_id)
                if sede and sede.active:
                    user.sede_id = sede.id

            if role == 'terapista':
                sede_ids = data.get('sede_ids', [])
                if isinstance(sede_ids, str):
                    sede_ids = [int(x) for x in sede_ids.split(',')]

                if sede_ids and isinstance(sede_ids, list):
                    for sid in sede_ids:
                        s = Sede.query.get(sid)
                        if s and s.active:
                            user.assigned_sedes.append(s)
        except Exception as e:
            print(f'Error assigning sede: {e}')

        if role == 'jugador':
            try:
                modality = int(data.get('modality', 0))
                payment_amount = float(data.get('payment_amount', 0))
                payment_freq = data.get('payment_frequency', 'monthly')

                total_sessions = 0
                if modality == 1:
                    total_sessions = 4
                elif modality == 2:
                    total_sessions = 8
                elif modality == 3:
                    total_sessions = 12

                user.payment_amount = payment_amount
                user.payment_plan = payment_freq
                user.plan_type = data.get('plan_type', 'individual')
                user.sessions_total = total_sessions
                user.sessions_attended = 0

                if total_sessions > 0:
                    user.session_cost = payment_amount / total_sessions

                therapist_id = data.get('therapist_id')
                if therapist_id:
                    user.assigned_therapist_id = therapist_id

            except Exception as e:
                print(f'Error parsing plan data: {e}')

        if role == 'terapista':
            try:
                user.salary_base = float(data.get('salary_base', 0))
                user.contract_hours = int(data.get('contract_hours', 0))
            except Exception:
                pass

        db.session.add(user)
        db.session.commit()

        if role == 'jugador' and data.get('generate_schedule') == True:
            try:
                start_date_str = data.get('start_date')
                start_time_str = data.get('start_time')
                therapist_id = data.get('therapist_id')
                modality = int(data.get('modality', 0))
                days_selected = data.get('days_of_week', [])

                if start_date_str and start_time_str and therapist_id and modality > 0:
                    start_dt = datetime.strptime(f'{start_date_str} {start_time_str}', '%Y-%m-%d %H:%M')
                    self.generate_schedule(user, therapist_id, start_dt, modality, days_selected)
            except Exception as e:
                print(f'Error generating schedule: {e}')

        if is_active and 'noemail_' not in email:
            try:
                self.email_service.send_welcome_email(email, plain_password, user.username)
            except Exception:
                pass

        return True, {'user': user, 'temp_password': plain_password if is_active else 'N/A (Presencial)'}

    def generate_schedule(self, user, therapist_id, start_dt, modality, days_of_week=None):
        total_sessions = 0
        if modality == 1:
            total_sessions = 4
        elif modality == 2:
            total_sessions = 8
        elif modality == 3:
            total_sessions = 12
        else:
            return

        if not days_of_week:
            days_of_week = [start_dt.weekday()]
            if modality == 2:
                days_of_week.append((start_dt.weekday() + 3) % 7)
            elif modality == 3:
                days_of_week.append((start_dt.weekday() + 2) % 7)
                days_of_week.append((start_dt.weekday() + 4) % 7)

        days_of_week = [int(d) for d in days_of_week]
        days_of_week = sorted(list(set(days_of_week)))

        created_count = 0
        current_date = start_dt

        safety_break = 0
        while created_count < total_sessions and safety_break < 365:
            safety_break += 1

            if current_date.weekday() in days_of_week:
                is_holiday = current_date.strftime('%Y-%m-%d') in HOLIDAYS_2026

                notes = ''
                if is_holiday:
                    notes = 'WARNING: Scheduled on Holiday'

                appt_dt = datetime(
                    current_date.year, current_date.month, current_date.day, start_dt.hour, start_dt.minute
                )

                appt = Appointment(
                    patient_id=user.id,
                    therapist_id=therapist_id,
                    start_time=appt_dt,
                    end_time=appt_dt + timedelta(minutes=45),
                    title=f'Sesión {created_count + 1}',
                    status='scheduled',
                    games='[]',
                    notes=notes,
                )
                db.session.add(appt)
                created_count += 1

            current_date += timedelta(days=1)

        db.session.commit()

    def reset_user_password(self, user_id, new_password=None):
        """Resetear contraseña de usuario"""
        user = User.query.get(user_id)
        if not user:
            return False, 'Usuario no encontrado'

        plain_password = new_password if new_password else self.email_service.generate_password()
        hashed_password = bcrypt.generate_password_hash(plain_password).decode('utf-8')

        user.password = hashed_password
        user.admin_password_changed_count += 1
        db.session.commit()

        try:
            msg_type = 'manual' if new_password else 'automatico'
            self.email_service.send_email(
                user.email,
                'Tu contraseña ha sido actualizada',
                f'Hola {user.username},\n\nTu contraseña ha sido actualizada ({msg_type}).\nNueva contraseña: {plain_password}\n\nPor favor, contacta con soporte si no solicitaste esto.',
            )
        except Exception:
            pass

        return True, plain_password

    def update_user(self, data):
        user_id = data.get('id')
        user = User.query.get(user_id)
        if not user:
            return False, 'Usuario no encontrado'

        if 'username' in data:
            user.username = data['username']

        if 'role' in data:
            user.role = data['role']
        if 'is_active' in data:
            user.is_active = bool(data['is_active'])

        if 'sede_id' in data and user.role == 'jugador':
            try:
                sid = int(data['sede_id']) if data['sede_id'] else 0
                if sid:
                    s = Sede.query.get(sid)
                    if s and s.active:
                        user.sede_id = s.id
                else:
                    user.sede_id = None
            except:
                pass

        if 'sede_ids' in data and user.role == 'terapista':
            try:
                sids = data.get('sede_ids')
                if isinstance(sids, str):
                    import json

                    try:
                        sids = json.loads(sids)
                    except:
                        sids = [int(x) for x in sids.split(',') if x.strip()]

                if isinstance(sids, list):
                    current_sedes = list(user.assigned_sedes)
                    for s in current_sedes:
                        user.assigned_sedes.remove(s)

                    for sid in sids:
                        s = Sede.query.get(sid)
                        if s and s.active:
                            user.assigned_sedes.append(s)
            except Exception as e:
                print(f'Error updating sedes: {e}')

        if user.role == 'jugador':
            try:
                if 'modality' in data:
                    modality = int(data.get('modality', 0))
                    total_sessions = 0
                    if modality == 1:
                        total_sessions = 4
                    elif modality == 2:
                        total_sessions = 8
                    elif modality == 3:
                        total_sessions = 12
                    else:
                        total_sessions = 0

                    if modality > 0:
                        user.sessions_total = total_sessions

                if 'payment_plan' in data:
                    user.payment_plan = data.get('payment_plan')

                if 'plan_type' in data:
                    user.plan_type = data.get('plan_type')

                if 'payment_amount' in data:
                    user.payment_amount = float(data.get('payment_amount', 0))

                if 'sessions_attended' in data:
                    user.sessions_attended = int(data.get('sessions_attended', 0))

                amount = user.payment_amount or 0
                total = user.sessions_total or 0
                if total > 0:
                    user.session_cost = amount / total
                else:
                    user.session_cost = 0

                if 'has_second_shift' in data:
                    user.has_second_shift = bool(data.get('has_second_shift'))

                if user.has_second_shift:
                    if 'modality_2' in data:
                        mod_2 = int(data.get('modality_2', 0))
                        total_2 = 0
                        if mod_2 == 1:
                            total_2 = 4
                        elif mod_2 == 2:
                            total_2 = 8
                        elif mod_2 == 3:
                            total_2 = 12

                        user.modality_2 = mod_2
                        user.sessions_total_2 = total_2

                    if 'plan_type_2' in data:
                        user.plan_type_2 = data.get('plan_type_2')

                    if 'payment_amount_2' in data:
                        user.payment_amount_2 = float(data.get('payment_amount_2', 0))

                    if 'sessions_attended_2' in data:
                        user.sessions_attended_2 = int(data.get('sessions_attended_2', 0))

                    amt2 = user.payment_amount_2 or 0
                    tot2 = user.sessions_total_2 or 0
                    if tot2 > 0:
                        user.session_cost_2 = amt2 / tot2
                    else:
                        user.session_cost_2 = 0

            except Exception as e:
                print(f'Error updating plan: {e}')

        if user.role == 'terapista':
            try:
                if 'salary_base' in data:
                    user.salary_base = float(data.get('salary_base', 0))
                if 'contract_hours' in data:
                    user.contract_hours = int(data.get('contract_hours', 0))

                if 'work_start_time' in data:
                    user.work_start_time = data.get('work_start_time')
                if 'work_end_time' in data:
                    user.work_end_time = data.get('work_end_time')
                if 'work_days' in data:
                    user.work_days = data.get('work_days')

            except Exception as e:
                print(f'Error updating therapist plan: {e}')

        db.session.commit()
        return True, user

    def list_users(self, role=None):
        q = User.query
        if role in ('terapista', 'jugador'):
            q = q.filter_by(role=role)
        return q.order_by(User.username.asc()).all()

    def broadcast_message(self, sender_id, subject, body, target, receiver_id=None):
        from flask import url_for

        from app.models import Message

        recipients = []
        if target == 'single' and receiver_id:
            u = User.query.get(receiver_id)
            if not u:
                return False, 'Destinatario no encontrado'
            recipients = [u]
        else:
            q = User.query
            if target in ('terapista', 'jugador'):
                q = q.filter_by(role=target)
            recipients = q.all()

        for u in recipients:
            msg = Message(sender_id=sender_id, receiver_id=u.id, subject=subject, body=body)
            db.session.add(msg)
            try:
                self.notification_service.create_notification(
                    u.id, f'Mensaje del administrador: {subject or "Sin asunto"}', link=url_for('main.messages_list')
                )

                self.email_service.send_new_message_email(
                    u.email, u.username, 'Administrador', body[:100] + '...' if body and len(body) > 100 else body
                )
            except Exception:
                pass

        db.session.commit()
        return True, len(recipients)
