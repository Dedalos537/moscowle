from datetime import datetime, timedelta
from app.repositories.patient_repository import PatientRepository
from app.services.automation.financial_analysis import PatientFinancialStatus
from app.services.email_service import EmailService
import calendar

class FinancialService:
    def __init__(self):
        self.repo = PatientRepository()

    def build_debt_report(self, days_ahead=7, month=None):
        """
        Build report grouped by sede similar to existing `check_upcoming_payments` and `/admin/deudores`.
        Returns: { 'summary': {...}, 'por_sede': {...} }
        
        Args:
            days_ahead (int): For upcoming payments.
            month (str): "current", "all", or "01"-"12".
        """
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
            except:
                pass # Fallback to all if month is invalid

        patients = self.repo.get_active_patients()

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
                    from app.models import User
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
                        'deudores': []
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

            except Exception:
                continue

        # Sort
        for s in deudores_by_sede.values():
            s['deudores'].sort(key=lambda x: (0 if x['urgencia']=='crítica' else 1 if x['urgencia']=='alta' else 2))

        summary = {
            'total_adeudado': round(total_adeudado, 2),
            'total_deudores': total_deudores,
            'siedes_afectadas': len(deudores_by_sede),
            'vencidos': vencidos_count,
            'proximo_a_vencer': proximo_a_vencer_count
        }

        return {'summary': summary, 'por_sede': deudores_by_sede}

    def get_patient_overdue_info(self, patient_id):
        """Return computed overdue info for a patient: amount, due_date, days_overdue, balance."""
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
            'balance': round(float(balance), 2)
        }
