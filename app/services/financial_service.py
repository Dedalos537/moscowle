import calendar
import logging
from datetime import datetime, timedelta

from sqlalchemy import func

from app.extensions import db
from app.models import Expense, User, Appointment
from app.repositories.patient_repository import PatientRepository
from app.services.automation.financial_analysis import PatientFinancialStatus

logger = logging.getLogger(__name__)


class FinancialService:
    def __init__(self):
        self.repo = PatientRepository()

    def build_debt_report(self, days_ahead=7, month=None):
        """Reporte de deuda agrupado por sede"""
        today = datetime.utcnow().date()
        week_ahead = today + timedelta(days=days_ahead)

        # Determine filtering range based on month param
        filter_start = None
        filter_end = None

        if month == 'current':
            filter_start = today.replace(day=1)
            last_day = calendar.monthrange(today.year, today.month)[1]
            filter_end = today.replace(day=last_day)
        elif month and month != 'all':
            try:
                m_int = int(month)
                filter_start = today.replace(month=m_int, day=1)
                last_day = calendar.monthrange(today.year, m_int)[1]
                filter_end = today.replace(month=m_int, day=last_day)
            except Exception:
                logger.warning('Invalid month value: %s', month)

        patients = self.repo.get_active_patients()

        # Apply month filter: only include patients whose due date falls
        # within the selected month OR who are overdue from before it.
        if filter_start is not None and filter_end is not None:
            filtered = []
            for p in patients:
                dd = getattr(p, 'payment_due_date', None)
                if dd is None:
                    continue
                if filter_start <= dd <= filter_end or dd < filter_start:
                    filtered.append(p)
            patients = filtered

        deudores_by_sede = {}
        total_adeudado = 0.0
        total_deudores = 0
        vencidos_count = 0
        proximo_a_vencer_count = 0

        for patient in patients:
            try:
                monto = float(getattr(patient, 'payment_amount', 0.0) or 0.0)

                # Therapist name
                therapist_name = ''
                if patient.assigned_therapist:
                    therapist_name = patient.assigned_therapist.username or ''
                elif getattr(patient, 'assigned_therapist_id', None):
                    th = User.query.get(patient.assigned_therapist_id)
                    if th:
                        therapist_name = th.username or ''

                due_date = getattr(patient, 'payment_due_date', None)
                days_overdue = (today - due_date).days if due_date else 0

                if not due_date or monto <= 0:
                    status = 'sin_plan'
                    urgencia = 'baja'
                elif days_overdue > 0:
                    status = 'vencido'
                    urgencia = 'critica' if days_overdue > 7 else 'alta'
                    vencidos_count += 1
                elif today <= due_date <= week_ahead:
                    status = 'proximo'
                    urgencia = 'alta'
                    proximo_a_vencer_count += 1
                else:
                    status = 'al_dia'
                    urgencia = 'baja'

                sede_id, sede_name = self.repo.get_sede_for_patient(patient)
                sede_key = str(sede_id) if sede_id else 'sin_sede'
                if sede_key not in deudores_by_sede:
                    deudores_by_sede[sede_key] = {
                        'sede_name': sede_name or 'Sin Sede',
                        'sede_id': sede_id,
                        'total': 0.0,
                        'count': 0,
                        'deudores': [],
                    }

                deudor = {
                    'id': patient.id,
                    'paciente': patient.username or patient.email,
                    'username': patient.username or patient.email,
                    'email': patient.email,
                    'phone': patient.phone,
                    'payment_day': patient.payment_day,
                    'modality': patient.plan_type,
                    'modality_2': getattr(patient, 'modality_2', None),
                    'monto': round(monto, 2),
                    'payment_amount_2': round(float(getattr(patient, 'payment_amount_2', 0) or 0), 2),
                    'frequency': getattr(patient, 'payment_plan', ''),
                    'fecha_vencimiento': due_date.strftime('%Y-%m-%d') if due_date else '',
                    'dias_adeudo': days_overdue if days_overdue > 0 else 0,
                    'estado': status,
                    'urgencia': urgencia,
                    'sessions_total': getattr(patient, 'sessions_total', 0) or 0,
                    'sessions_attended': getattr(patient, 'sessions_attended', 0) or 0,
                    'sessions_remaining': getattr(patient, 'sessions_remaining', 0) or 0,
                    'therapist_name': therapist_name,
                    'has_plan_config': bool(due_date and monto > 0),
                }

                deudores_by_sede[sede_key]['deudores'].append(deudor)
                deudores_by_sede[sede_key]['total'] += monto
                deudores_by_sede[sede_key]['count'] += 1
                if status in ('vencido', 'proximo'):
                    total_adeudado += monto
                    total_deudores += 1

            except Exception as e:
                logger.warning('Error processing patient %s: %s', getattr(patient, 'id', 'unknown'), e)

        # Sort
        for s in deudores_by_sede.values():
            s['deudores'].sort(key=lambda x: 0 if x['urgencia'] == 'crítica' else 1 if x['urgencia'] == 'alta' else 2)

        summary = {
            'total_adeudado': round(total_adeudado, 2),
            'total_deudores': total_deudores,
            'siedes_afectadas': len(deudores_by_sede),
            'vencidos': vencidos_count,
            'proximo_a_vencer': proximo_a_vencer_count,
        }

        return {'summary': summary, 'por_sede': deudores_by_sede}

    def get_patient_overdue_info(self, patient_id):
        """Info de morosidad del paciente"""
        p = self.repo.get_patient(patient_id)
        if not p:
            return None
        due_date = getattr(p, 'payment_due_date', None)
        amount = float(getattr(p, 'payment_amount', 0.0) or 0.0)
        today = datetime.utcnow().date()
        days_overdue = max(0, (today - due_date).days) if due_date else 0

        # Use existing financial analysis to calculate balance
        balance = PatientFinancialStatus(p.id).calculate_balance()

        return {
            'id': p.id,
            'name': p.username or p.email,
            'email': p.email,
            'phone': getattr(p, 'phone', None),
            'due_date': due_date,
            'amount': amount,
            'days_overdue': days_overdue,
            'balance': round(float(balance), 2),
        }

    def get_expenses(self, start_date=None, end_date=None, category=None):
        q = Expense.query
        if start_date:
            q = q.filter(Expense.date >= start_date)
        if end_date:
            q = q.filter(Expense.date <= end_date)
        if category:
            q = q.filter(Expense.category == category)
        return q.order_by(Expense.date.desc()).all()

    def create_expense(self, data):
        try:
            date_val = data.get('date')
            if isinstance(date_val, str):
                date_val = datetime.strptime(date_val, '%Y-%m-%d')
            exp = Expense(
                category=data.get('category'),
                amount=float(data.get('amount')),
                date=date_val,
                description=data.get('description'),
                therapist_id=data.get('therapist_id'),
                method=data.get('method'),
                receipt_image_path=data.get('receipt_image_path')
            )
            db.session.add(exp)
            db.session.commit()
            return True, exp
        except Exception as e:
            return False, str(e)

    def get_therapist_financials(self, month=None, year=None):
        if not month: month = datetime.now().month
        if not year: year = datetime.now().year
        therapists = User.query.filter_by(role='terapista').filter_by(is_active=True).all()
        results = []
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)
        for t in therapists:
            rate = 0
            if t.salary_base and t.contract_hours and t.contract_hours > 0:
                rate = t.salary_base / t.contract_hours
            worked_minutes = db.session.query(func.sum(Appointment.duration_minutes))\
                .filter(Appointment.therapist_id == t.id)\
                .filter(Appointment.status == 'completed')\
                .filter(Appointment.start_time >= start_date)\
                .filter(Appointment.start_time < end_date)\
                .scalar() or 0
            worked_hours = worked_minutes / 60
            projected_pay = rate * worked_hours
            paid_amount = db.session.query(func.sum(Expense.amount))\
                .filter(Expense.therapist_id == t.id)\
                .filter(Expense.category == 'therapist_payment')\
                .filter(Expense.date >= start_date)\
                .filter(Expense.date < end_date)\
                .scalar() or 0
            results.append({
                'therapist': t,
                'rate': rate,
                'contract_hours': t.contract_hours,
                'worked_hours': worked_hours,
                'projected_pay': projected_pay,
                'paid': paid_amount,
                'balance': projected_pay - paid_amount
            })
        return results
