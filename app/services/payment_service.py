import contextlib
from datetime import datetime, timedelta

from sqlalchemy import func

from app.models import Expense, Payment, User, db
from app.services.email_service import EmailService
from app.services.notification_service import NotificationService


class PaymentService:
    def __init__(self):
        self.email_service = EmailService()
        self.notification_service = NotificationService()

    def get_patients_payment_status(self):
        """Estado de pago de pacientes — bulk queries, sin N+1"""
        patients = User.query.filter_by(role='jugador').all()
        today = datetime.utcnow().date()
        patient_ids = [p.id for p in patients]

        latest_by_patient = {}
        if patient_ids:
            latest_subq = (
                db.session.query(Payment.patient_id, func.max(Payment.id).label('max_id'))
                .filter(Payment.patient_id.in_(patient_ids))
                .group_by(Payment.patient_id)
                .subquery()
            )
            latest_payments = db.session.query(Payment).join(latest_subq, Payment.id == latest_subq.c.max_id).all()
            latest_by_patient = {p.patient_id: p for p in latest_payments}

        totals_by_patient = {}
        if patient_ids:
            totals = (
                db.session.query(Payment.patient_id, func.sum(Payment.amount).label('total'))
                .filter(Payment.patient_id.in_(patient_ids))
                .group_by(Payment.patient_id)
                .all()
            )
            totals_by_patient = {pid: total for pid, total in totals}

        results = []
        for p in patients:
            status = 'active'
            days_overdue = 0

            if not p.is_active:
                status = 'inactive'
            elif p.payment_due_date and p.payment_due_date < today:
                status = 'overdue'
                days_overdue = (today - p.payment_due_date).days

            latest_payment = latest_by_patient.get(p.id)

            attended_1 = p.sessions_attended or 0
            attended_2 = p.sessions_attended_2 or 0
            consumed_1 = 0
            consumed_2 = 0

            if p.plan_type == 'group':
                consumed_1 = p.payment_amount or 0
            else:
                cost_1 = p.session_cost or 0
                consumed_1 = attended_1 * cost_1

            if p.has_second_shift:
                if p.plan_type_2 == 'group':
                    consumed_2 = p.payment_amount_2 or 0
                else:
                    cost_2 = p.session_cost_2 or 0
                    consumed_2 = attended_2 * cost_2

            total_consumed = consumed_1 + consumed_2
            total_paid = totals_by_patient.get(p.id, 0) or 0
            debt = total_consumed - total_paid

            plan_label = p.payment_plan or 'Mensual'
            if p.has_second_shift:
                plan_label += ' (+2do Turno)'

            results.append(
                {
                    'user': p,
                    'status': status,
                    'full_status_label': 'Al día'
                    if status == 'active'
                    else 'Vencido'
                    if status == 'overdue'
                    else 'Inactivo',
                    'days_overdue': days_overdue,
                    'last_payment_date': latest_payment.date if latest_payment else None,
                    'last_payment_amount': latest_payment.amount if latest_payment else None,
                    'debt': debt,
                    'sessions_attended': attended_1 + attended_2,
                    'sessions_total': (p.sessions_total or 0) + (p.sessions_total_2 or 0),
                    'session_cost': cost_1,
                }
            )
        return results

    def register_payment(
        self,
        patient_id,
        amount,
        method,
        reference,
        next_due_date_str,
        receipt_path=None,
        discount=0.0,
        payment_date=None,
    ):
        """Registrar pago y actualizar estado"""
        user = User.query.get(patient_id)
        if not user:
            return False, 'Usuario no encontrado'

        try:
            payment_datetime = payment_date if payment_date else datetime.utcnow()

            new_payment = Payment(
                patient_id=patient_id,
                amount=amount,
                method=method,
                reference=reference,
                receipt_image_path=receipt_path,
                discount=discount,
                date=payment_datetime,
            )
            db.session.add(new_payment)

            billing_info = self.get_billing_info(patient_id)
            if billing_info:
                user.sessions_total = billing_info.get('suggested_sessions', 4)
                user.sessions_attended = 0

            if next_due_date_str:
                if isinstance(next_due_date_str, str):
                    user.payment_due_date = datetime.strptime(next_due_date_str, '%Y-%m-%d').date()
                else:
                    user.payment_due_date = next_due_date_str

            if not user.is_active:
                user.is_active = True

            db.session.commit()

            with contextlib.suppress(Exception):
                self.email_service.send_payment_confirmation(
                    user.email, user.username, amount, new_payment.date, method
                )

            return True, new_payment
        except Exception as e:
            db.session.rollback()
            return False, str(e)

    def update_payment_settings(self, patient_id, amount, due_date_str, frequency):
        """Actualizar plan de pago"""
        user = User.query.get(patient_id)
        if not user:
            return False, 'Usuario no encontrado'

        try:
            if amount:
                user.payment_amount = float(amount)
            if due_date_str:
                user.payment_due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
            if frequency:
                user.payment_plan = frequency

            db.session.commit()
            return True, 'Configuración actualizada'
        except Exception as e:
            db.session.rollback()
            return False, str(e)

    def check_and_deactivate_overdue(self):
        """Desactivar usuarios vencidos"""
        today = datetime.utcnow().date()
        overdue_users = User.query.filter(
            User.role == 'jugador', User.is_active, User.payment_due_date < today
        ).all()

        count = 0
        for user in overdue_users:
            user.is_active = False
            count += 1

        if count > 0:
            db.session.commit()

        return count

    def check_upcoming_due_dates(self):
        """Revisar próximos pagos para recordatorios"""
        target_users = User.query.filter(
            User.role == 'jugador', User.is_active, User.payment_due_date.isnot(None)
        ).all()
        today = datetime.utcnow().date()

        sent_count = 0
        for user in target_users:
            if not user.payment_due_date:
                continue

            delta = (user.payment_due_date - today).days

            if delta in {3, 0}:
                is_urgent = delta == 0

                self.email_service.send_payment_reminder(
                    user.email, user.username, delta, user.payment_due_date, user.payment_amount or 0
                )

                msg = f' Tu pago de S/ {user.payment_amount} vence {"HOY" if is_urgent else "en 3 días"}. Por favor regulariza para evitar bloqueos.'
                self.notification_service.create_notification(user.id, msg, link='/patient/dashboard')

                sent_count += 1

        return sent_count

    def get_billing_info(self, patient_id):
        """Calcular próxima fecha de facturación (lógica 4/8/12 sesiones)"""
        user = User.query.get(patient_id)
        if not user:
            return None

        today = datetime.utcnow().date()
        base_date = user.payment_due_date if user.payment_due_date else today

        pay_day = user.payment_day or base_date.day

        import calendar

        if user.payment_plan == 'quincenal':
            suggested_date = base_date + timedelta(days=15)
        else:
            next_month = base_date.month % 12 + 1
            next_year = base_date.year + (base_date.month // 12)
            last_day = calendar.monthrange(next_year, next_month)[1]
            target_day = min(pay_day, last_day)
            suggested_date = base_date.replace(year=next_year, month=next_month, day=target_day)

        suggested_sessions = 4

        plan = str(user.payment_plan).lower()
        if '2' in plan:
            suggested_sessions = 8
        elif '3' in plan or 'tres' in plan:
            suggested_sessions = 12
        elif 'quincenal' in plan:
            suggested_sessions = 4

        remaining = (user.sessions_total or 0) - (user.sessions_attended or 0)
        to_recover = 0
        if remaining != 0 and user.plan_type == 'individual':
            to_recover = max(-2, min(2, remaining))

        return {
            'suggested_date': suggested_date.strftime('%Y-%m-%d'),
            'suggested_sessions': max(1, suggested_sessions + to_recover),
            'recovery_msg': f'Ajuste de {to_recover} sesiones (pendientes: {remaining})' if to_recover != 0 else None,
            'current_plan': user.payment_plan,
            'current_amount': user.payment_amount or 0.0,
            'absences': user.sessions_total - user.sessions_attended
            if user.sessions_total > user.sessions_attended
            else 0,
            'document_number': user.document_number,
            'guardian_name': user.guardian_name,
            'guardian_dni': user.guardian_dni,
        }

    def get_financial_summary(self, month=None, year=None):
        """Métricas financieras para dashboard. Opcional: month (1-12), year."""
        today = datetime.utcnow().date()
        target_month = month or today.month
        target_year = year or today.year

        start_date = datetime(target_year, target_month, 1)
        import calendar

        last_day = calendar.monthrange(target_year, target_month)[1]
        end_date = datetime(target_year, target_month, last_day, 23, 59, 59)

        income_query = (
            db.session.query(func.sum(Payment.amount))
            .filter(Payment.date >= start_date, Payment.date <= end_date)
            .scalar()
        )

        monthly_income_real = income_query or 0.0

        active_players = User.query.filter_by(role='jugador', is_active=True).all()
        monthly_income_expected = 0.0
        for p in active_players:
            amt = p.payment_amount or 0
            if p.payment_plan == 'quincenal':
                monthly_income_expected += amt * 2
            else:
                monthly_income_expected += amt

        overdue_users = User.query.filter(User.role == 'jugador', User.payment_due_date < today).all()

        overdue_amount = sum([u.payment_amount or 0 for u in overdue_users])

        expenses_query = (
            db.session.query(func.sum(Expense.amount))
            .filter(Expense.date >= start_date, Expense.date <= end_date)
            .scalar()
        )
        monthly_expenses = expenses_query or 0.0

        return {
            'month_name': start_date.strftime('%B'),
            'income_real': monthly_income_real,
            'income_expected': monthly_income_expected,
            'overdue_amount': overdue_amount,
            'overdue_users_count': len(overdue_users),
            'expenses': monthly_expenses,
            'net_profit': monthly_income_real - monthly_expenses,
        }

    def get_payment_history(self, limit=1000):

        return Payment.query.order_by(Payment.date.desc()).limit(limit).all()
