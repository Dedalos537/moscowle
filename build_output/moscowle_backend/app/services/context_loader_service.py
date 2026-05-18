"""
Context Loader Service - Carga TODOS los datos de la BD para la IA
Permite que la IA tenga contexto completo y actualizado
"""
import json
import logging
from datetime import datetime, timedelta
from app.extensions import db
from app.models import User, Payment, Appointment, Expense, Sede

logger = logging.getLogger('app')

class ContextLoader:
    """
    Carga contexto completo de la BD para la IA
    Incluye: usuarios, pagos, sesiones, gastos, sedes, métricas
    """
    
    @staticmethod
    def get_active_patients_context() -> dict:
        """Obtiene info de TODOS los pacientes activos"""
        patients = User.query.filter_by(role='jugador', is_active=True).all()
        
        context = {
            'total': len(patients),
            'patients': []
        }
        
        for p in patients:
            # Info del paciente
            patient_data = {
                'id': p.id,
                'name': p.username,
                'email': p.email,
                'phone': p.phone,
                'payment_amount': float(p.payment_amount) if p.payment_amount else 0,
                'payment_due_date': p.payment_due_date.isoformat() if p.payment_due_date else None,
                'sessions_attended': p.sessions_attended,
            }
            
            # Sesiones próximas
            next_session = Appointment.query.filter(
                Appointment.patient_id == p.id,
                Appointment.start_time >= datetime.now(),
                Appointment.status.in_(['pending', 'confirmed'])
            ).order_by(Appointment.start_time).first()
            
            if next_session:
                patient_data['next_session'] = {
                    'date': next_session.start_time.isoformat(),
                    'status': next_session.status
                }
            
            # Pago más reciente
            last_payment = Payment.query.filter_by(
                patient_id=p.id
            ).order_by(Payment.date.desc()).first()
            
            if last_payment:
                patient_data['last_payment'] = {
                    'amount': float(last_payment.amount),
                    'date': last_payment.date.isoformat(),
                    'status': last_payment.status
                }
            
            context['patients'].append(patient_data)
        
        return context
    
    @staticmethod
    def get_financial_context() -> dict:
        """Obtiene contexto financiero completo"""
        from app.services.business_analytics_service import (
            calculate_revenue_metrics,
            get_unpaid_users,
            get_weekly_due_payments
        )
        
        today = datetime.now().date()
        current_month_start = today.replace(day=1)
        
        return {
            'current_month': current_month_start.isoformat(),
            'revenue_metrics': calculate_revenue_metrics(),
            'unpaid_users': get_unpaid_users(),
            'weekly_due': get_weekly_due_payments(),
            'total_expenses': float(db.session.query(db.func.sum(Expense.amount)).filter(
                db.func.year(Expense.date) == today.year,
                db.func.month(Expense.date) == today.month
            ).scalar() or 0),
            'total_payments': float(db.session.query(db.func.sum(Payment.amount)).filter(
                db.func.year(Payment.date) == today.year,
                db.func.month(Payment.date) == today.month
            ).scalar() or 0),
        }
    
    @staticmethod
    def get_sessions_context() -> dict:
        """Obtiene contexto de sesiones/citas"""
        today = datetime.now()
        this_week_start = today - timedelta(days=today.weekday())
        this_week_end = this_week_start + timedelta(days=6, hours=23, minutes=59)
        
        sessions = Appointment.query.filter(
            Appointment.start_time >= this_week_start,
            Appointment.start_time <= this_week_end
        ).all()
        
        sessions_by_status = {
            'pending': [],
            'confirmed': [],
            'completed': [],
            'cancelled': []
        }
        
        for session in sessions:
            patient = User.query.get(session.patient_id)
            session_data = {
                'id': session.id,
                'patient': patient.username,
                'date': session.start_time.isoformat(),
                'status': session.status,
                'attendance': session.attendance
            }
            sessions_by_status[session.status].append(session_data)
        
        return {
            'total_this_week': len(sessions),
            'sessions_by_status': sessions_by_status,
            'pending_count': len(sessions_by_status['pending']),
            'completed_count': len(sessions_by_status['completed'])
        }
    
    @staticmethod
    def get_sedes_context() -> dict:
        """Obtiene contexto de sedes/ubicaciones"""
        sedes = Sede.query.filter_by(active=True).all()
        
        context = {
            'total': len(sedes),
            'sedes': []
        }
        
        for sede in sedes:
            patients = User.query.filter_by(sede_id=sede.id, role='jugador', is_active=True).count()
            
            sede_data = {
                'id': sede.id,
                'name': sede.name,
                'address': sede.address,
                'active_patients': patients
            }
            context['sedes'].append(sede_data)
        
        return context
    
    @staticmethod
    def get_therapists_context() -> dict:
        """Obtiene contexto de terapeutas"""
        therapists = User.query.filter_by(role='therapist', is_active=True).all()
        
        context = {
            'total': len(therapists),
            'therapists': []
        }
        
        for therapist in therapists:
            # Contar pacientes asignados
            assigned_patients = User.query.filter_by(
                assigned_therapist_id=therapist.id,
                is_active=True
            ).count()
            
            # Sesiones esta semana
            today = datetime.now()
            this_week_start = today - timedelta(days=today.weekday())
            this_week_end = this_week_start + timedelta(days=6, hours=23, minutes=59)
            
            sessions_this_week = Appointment.query.filter(
                Appointment.therapist_id == therapist.id,
                Appointment.start_time >= this_week_start,
                Appointment.start_time <= this_week_end
            ).count()
            
            therapist_data = {
                'id': therapist.id,
                'name': therapist.username,
                'email': therapist.email,
                'patients_assigned': assigned_patients,
                'sessions_this_week': sessions_this_week
            }
            context['therapists'].append(therapist_data)
        
        return context
    
    @staticmethod
    def get_full_context() -> dict:
        """
        Obtiene TODOS los contextos combinados
        Este es el que se pasa a la IA
        """
        try:
            logger.info("Loading full context from database...")
            
            context = {
                'timestamp': datetime.now().isoformat(),
                'patients': ContextLoader.get_active_patients_context(),
                'financial': ContextLoader.get_financial_context(),
                'sessions': ContextLoader.get_sessions_context(),
                'sedes': ContextLoader.get_sedes_context(),
                'therapists': ContextLoader.get_therapists_context(),
            }
            
            logger.info(f"Context loaded: {context['patients']['total']} patients, "
                       f"{len(context['therapists']['therapists'])} therapists")
            
            return context
        except Exception as e:
            logger.error(f"Error loading context: {e}")
            return {}
    
    @staticmethod
    def format_context_for_llama(context: dict) -> str:
        """
        Formatea el contexto para pasarlo a Llama en el prompt
        """
        if not context:
            return ""
        
        text = """
=== CONTEXTO DE DATOS DEL CENTRO (ACTUALIZADO AL DÍA) ===

## PACIENTES ACTIVOS
"""
        if context.get('patients', {}).get('patients'):
            patients_list = context['patients']['patients']
            text += f"Total: {context['patients']['total']} pacientes\n"
            for p in patients_list[:5]:  # Primeros 5
                text += f"- {p['name']}: "
                if p.get('last_payment'):
                    text += f"Último pago: S/. {p['last_payment']['amount']} ({p['last_payment']['date'][:10]})"
                else:
                    text += "Sin pagos registrados"
                text += "\n"
            if context['patients']['total'] > 5:
                text += f"... y {context['patients']['total'] - 5} más\n"
        
        text += "\n## FINANZAS (ESTE MES)\n"
        if context.get('financial'):
            fin = context['financial'].get('revenue_metrics', {})
            text += f"- Ingresos: S/. {fin.get('total_income', 0):.2f}\n"
            text += f"- Egresos: S/. {fin.get('total_expenses', 0):.2f}\n"
            text += f"- Ganancia: S/. {fin.get('net_profit', 0):.2f}\n"
            text += f"- Cobranza: {fin.get('collection_rate', 0):.1f}%\n"
            
            unpaid = context['financial'].get('unpaid_users', {})
            text += f"- Deudores: {unpaid.get('total_unpaid', 0)} alumnos\n"
        
        text += "\n## SESIONES (ESTA SEMANA)\n"
        if context.get('sessions'):
            text += f"- Total: {context['sessions']['total_this_week']} sesiones\n"
            text += f"- Completadas: {context['sessions']['completed_count']}\n"
            text += f"- Pendientes: {context['sessions']['pending_count']}\n"
        
        text += "\n## UBICACIONES\n"
        if context.get('sedes', {}).get('sedes'):
            for sede in context['sedes']['sedes']:
                text += f"- {sede['name']}: {sede['active_patients']} pacientes\n"
        
        text += "\n## TERAPEUTAS\n"
        if context.get('therapists', {}).get('therapists'):
            therapists_list = context['therapists']['therapists']
            text += f"Total: {context['therapists']['total']}\n"
            for t in therapists_list[:3]:
                text += f"- {t['name']}: {t['patients_assigned']} pacientes, {t['sessions_this_week']} sesiones esta semana\n"
        
        text += "\n=== FIN DEL CONTEXTO ===\n"
        
        return text


# Instancia global del loader
context_loader = ContextLoader()
