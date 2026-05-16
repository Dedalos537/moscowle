"""Servicio de Análisis de Negocio Avanzado - Datos Reales con IA"""
import json
import logging
from datetime import datetime, timedelta
from app.extensions import db
from app.models import User, Payment, Expense
import ollama

logger = logging.getLogger('app')
client = ollama.Client(host='http://127.0.0.1:11434')

# ==================== ANÁLISIS DE PAGOS ====================

def get_unpaid_users():
    """Obtiene usuarios que NO han pagado en este mes"""
    try:
        current_month = datetime.now().month
        current_year = datetime.now().year
        
        # Obtener todos los pacientes activos
        all_patients = User.query.filter_by(role='jugador', is_active=True).all()
        
        unpaid = []
        for patient in all_patients:
            # Verificar si tiene pagos este mes
            has_paid_this_month = Payment.query.filter(
                Payment.patient_id == patient.id,
                db.func.year(Payment.date) == current_year,
                db.func.month(Payment.date) == current_month,
                Payment.status == 'completed'
            ).first()
            
            if not has_paid_this_month:
                due_date = patient.payment_due_date or datetime.now().date()
                unpaid.append({
                    'id': patient.id,
                    'name': patient.username or patient.email,
                    'email': patient.email,
                    'phone': patient.phone,
                    'amount_due': patient.payment_amount or 0.0,
                    'due_date': str(due_date),
                    'days_overdue': (datetime.now().date() - due_date).days if due_date else 0
                })
        
        return {
            'total_unpaid': len(unpaid),
            'users': unpaid,
            'total_debt': sum(u['amount_due'] for u in unpaid)
        }
    except Exception as e:
        logger.error(f"Error getting unpaid users: {e}")
        return {'total_unpaid': 0, 'users': [], 'total_debt': 0}

def get_weekly_due_payments():
    """Obtiene quiénes deben pagar en los próximos 7 días"""
    try:
        today = datetime.now().date()
        week_later = today + timedelta(days=7)
        
        # Pacientes con fecha de pago en la próxima semana
        due_this_week = []
        
        all_patients = User.query.filter_by(role='jugador', is_active=True).all()
        
        for patient in all_patients:
            due_date = patient.payment_due_date
            if due_date and today <= due_date <= week_later:
                # Verificar si ya pagó este mes
                has_paid_this_month = Payment.query.filter(
                    Payment.patient_id == patient.id,
                    db.func.year(Payment.date) == datetime.now().year,
                    db.func.month(Payment.date) == datetime.now().month,
                    Payment.status == 'completed'
                ).first()
                
                if not has_paid_this_month:
                    due_this_week.append({
                        'name': patient.username or patient.email,
                        'email': patient.email,
                        'phone': patient.phone,
                        'amount': patient.payment_amount or 0.0,
                        'due_date': str(due_date),
                        'days_until_due': (due_date - today).days
                    })
        
        # Ordenar por días hasta vencimiento
        due_this_week.sort(key=lambda x: x['days_until_due'])
        
        return {
            'count': len(due_this_week),
            'payments': due_this_week,
            'total_amount': sum(p['amount'] for p in due_this_week)
        }
    except Exception as e:
        logger.error(f"Error getting weekly due payments: {e}")
        return {'count': 0, 'payments': [], 'total_amount': 0}

# ==================== ANÁLISIS DE RENTABILIDAD ====================

def calculate_revenue_metrics():
    """Calcula métricas de ingresos y egresos"""
    try:
        current_month = datetime.now().month
        current_year = datetime.now().year
        
        # Ingresos este mes
        current_month_income = db.session.query(db.func.sum(Payment.amount)).filter(
            db.func.year(Payment.date) == current_year,
            db.func.month(Payment.date) == current_month,
            Payment.status == 'completed'
        ).scalar() or 0
        
        # Egresos este mes
        current_month_expenses = db.session.query(db.func.sum(Expense.amount)).filter(
            db.func.year(Expense.date) == current_year,
            db.func.month(Expense.date) == current_month
        ).scalar() or 0
        
        # Total de pacientes
        total_patients = User.query.filter_by(role='jugador', is_active=True).count()
        
        # Pacientes que pagaron este mes
        paid_patients = db.session.query(db.func.count(db.distinct(Payment.patient_id))).filter(
            db.func.year(Payment.date) == current_year,
            db.func.month(Payment.date) == current_month,
            Payment.status == 'completed'
        ).scalar() or 0
        
        # Promedio de ingresos por paciente
        avg_patient_income = current_month_income / paid_patients if paid_patients > 0 else 0
        
        # Ganancia neta
        net_profit = current_month_income - current_month_expenses
        profit_margin = (net_profit / current_month_income * 100) if current_month_income > 0 else 0
        
        return {
            'period': f"{current_year}-{current_month:02d}",
            'total_income': float(current_month_income),
            'total_expenses': float(current_month_expenses),
            'net_profit': float(net_profit),
            'profit_margin_percent': float(profit_margin),
            'total_patients': int(total_patients),
            'paid_patients': int(paid_patients),
            'avg_income_per_paid_patient': float(avg_patient_income),
            'collection_rate': float(paid_patients / total_patients * 100) if total_patients > 0 else 0
        }
    except Exception as e:
        logger.error(f"Error calculating revenue metrics: {e}")
        return {}

def estimate_breakeven_point(target_profit: float = 0):
    """Calcula cuántos alumnos se necesitan para cierta ganancia"""
    try:
        metrics = calculate_revenue_metrics()
        if not metrics:
            return None
        
        total_patients = metrics['total_patients']
        avg_income = metrics['avg_income_per_paid_patient']
        
        # Estimar gastos fijos diarios
        current_month = datetime.now().month
        current_year = datetime.now().year
        
        current_expenses = db.session.query(db.func.sum(Expense.amount)).filter(
            db.func.year(Expense.date) == current_year,
            db.func.month(Expense.date) == current_month
        ).scalar() or 0
        
        # Gastos estimados mensuales
        monthly_overhead = float(current_expenses) / 30  # Gastos diarios
        
        # Fórmula: (target_profit + monthly_overhead) / avg_income_per_patient
        if avg_income > 0:
            students_needed = (target_profit + (monthly_overhead * 30)) / avg_income
            return {
                'target_profit': float(target_profit),
                'current_students': int(total_patients),
                'students_needed': max(int(students_needed), total_patients),
                'additional_students': max(0, int(students_needed) - total_patients),
                'estimated_monthly_revenue': float(students_needed * avg_income),
                'feasibility': 'achievable' if students_needed <= total_patients + 10 else 'difficult'
            }
    except Exception as e:
        logger.error(f"Error estimating breakeven: {e}")
        return None

# ==================== RECOMENDACIONES Y ANÁLISIS IA ====================

def get_schedule_recommendations():
    """usa IA para recomendar mejoras de horarios"""
    try:
        metrics = calculate_revenue_metrics()
        unpaid = get_unpaid_users()
        weekly = get_weekly_due_payments()
        
        context = f"""Analiza estos datos de negocio de Centro de Terapias:
        
Ingresos: S/. {metrics['total_income']:.2f}
Egresos: S/. {metrics['total_expenses']:.2f}
Ganancia: S/. {metrics['net_profit']:.2f}
Margen de ganancia: {metrics['profit_margin_percent']:.1f}%
Total de alumnos: {metrics['total_patients']}
Alumnos que pagaron: {metrics['paid_patients']}
Tasa de cobranza: {metrics['collection_rate']:.1f}%

Usuarios sin pagar: {unpaid['total_unpaid']}
Deuda acumulada: S/. {unpaid['total_debt']:.2f}

Próximos 7 días - personas que deben pagar: {weekly['count']}
Ingresos esperados próxima semana: S/. {weekly['total_amount']:.2f}

Dame 3 RECOMENDACIONES ESPECÍFICAS para mejorar los horarios y aumentar cobranza. Sé conciso."""
        
        response = client.chat(
            model='llama3.1:8b',
            messages=[{'role': 'user', 'content': context}],
            options={'temperature': 0.3}
        )
        
        recommendations = response['message']['content']
        return {'recommendations': recommendations}
    except Exception as e:
        logger.error(f"Error generating recommendations: {e}")
        return {'recommendations': 'No se pudo generar recomendaciones'}

def generate_business_report():
    """Genera un informe completo de negocio"""
    try:
        metrics = calculate_revenue_metrics()
        unpaid = get_unpaid_users()
        weekly = get_weekly_due_payments()
        
        report_text = f"""
================================================
   REPORTE FINANCIERO - CENTRO DE TERAPIAS
   Mes: {datetime.now().strftime('%B %Y')}
================================================

RESUMEN FINANCIERO
------------------------------------------------
Total de Alumnos: {metrics['total_patients']}
Ingresos Total: S/. {metrics['total_income']:.2f}
Egresos Total: S/. {metrics['total_expenses']:.2f}
Ganancia Neta: S/. {metrics['net_profit']:.2f}
Margen de Ganancia: {metrics['profit_margin_percent']:.1f}%

COBRANZA
------------------------------------------------
Alumnos que Pagaron: {metrics['paid_patients']} ({metrics['collection_rate']:.1f}%)
Alumnos sin Pagar: {unpaid['total_unpaid']}
Deuda Acumulada: S/. {unpaid['total_debt']:.2f}

PROXIMOS 7 DIAS
------------------------------------------------
Pendientes de Pago: {weekly['count']} alumnos
Ingresos Esperados: S/. {weekly['total_amount']:.2f}

USUARIOS MOROSOS (Sin pagar este mes)
------------------------------------------------"""
        
        for user in unpaid['users'][:10]:  # Top 10
            days = user['days_overdue']
            status = "URGENTE" if days > 7 else "ATENCION"
            report_text += f"\n{status} {user['name']} - S/. {user['amount_due']:.2f} ({days} dias vencido)"
        
        if len(unpaid['users']) > 10:
            report_text += f"\n... y {len(unpaid['users']) - 10} mas"
        
        report_text += f"\n\nPROMEDIO POR ALUMNO: S/. {metrics['avg_income_per_paid_patient']:.2f}/mes"
        report_text += f"\n\nNOTA: Este reporte fue generado automaticamente por la IA"
        
        return report_text
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        return "Error al generar reporte"

def answer_business_question(question: str):
    """Responde preguntas de negocio usando datos reales + IA"""
    try:
        # Obtener datos para contexto
        metrics = calculate_revenue_metrics()
        unpaid = get_unpaid_users()
        weekly = get_weekly_due_payments()
        breakeven = estimate_breakeven_point(target_profit=5000)
        
        context = f"""Eres un asesor financiero de Centro de Terapias. Tienes estos datos REALES:

FINANZAS (Este mes):
- Ingresos: S/. {metrics['total_income']:.2f}
- Egresos: S/. {metrics['total_expenses']:.2f}
- Ganancia: S/. {metrics['net_profit']:.2f}
- Margen: {metrics['profit_margin_percent']:.1f}%

PACIENTES:
- Total: {metrics['total_patients']}
- Pagaron: {metrics['paid_patients']} ({metrics['collection_rate']:.1f}%)
- Sin pagar: {unpaid['total_unpaid']}
- Deuda acumulada: S/. {unpaid['total_debt']:.2f}

PRÓXIMA SEMANA:
- Pendientes de pago: {weekly['count']} ({weekly['total_amount']:.2f} S/.)

RENTABILIDAD:
- Promedio por alumno: S/. {metrics['avg_income_per_paid_patient']:.2f}
- Para ganancia de S/. 5000: Se necesitan {breakeven['students_needed'] if breakeven else '?'} alumnos

La pregunta del usuario es: "{question}"

Responde de forma concisa y basada en estos DATOS REALES. Si la pregunta es sobre números, cite los datos exactos."""
        
        response = client.chat(
            model='llama3.1:8b',
            messages=[{'role': 'user', 'content': context}],
            options={'temperature': 0.2}
        )
        
        answer = response['message']['content']
        logger.info(f"Business question answered: {question[:50]}")
        
        return {
            'question': question,
            'answer': answer,
            'data_sources': 'BD Real (Users, Payments, Expenses)'
        }
    except Exception as e:
        logger.error(f"Error answering business question: {e}")
        return {
            'question': question,
            'answer': f"Error procesando pregunta: {str(e)[:50]}",
            'data_sources': 'error'
        }

# ==================== ANÁLISIS DE FOTOS (VISION) ====================

def analyze_payment_voucher_with_vision(image_path: str):
    """Analiza una foto de boleta usando visión (si está disponible)"""
    try:
        # Primero, intentar con OCR simple
        from app.services.ocr_service import extract_receipt_data_simple
        simple_result = extract_receipt_data_simple(image_path)
        
        # Luego, intentar con Llama visión si está disponible
        try:
            # Verificar si llava está disponible
            response = client.chat(
                model='llava:7b',  # Modelo de visión
                messages=[{
                    'role': 'user',
                    'content': 'Analiza esta boleta. Extrae: monto total, fecha, nombre del pagador. Responde SOLO en JSON.'
                }],
                images=[image_path],
                options={'temperature': 0.1}
            )
            
            vision_result = response['message']['content']
            logger.info(f"Vision analysis: {vision_result[:100]}")
            
            # Combinar resultados
            return {
                'status': 'success',
                'ocr_data': simple_result,
                'vision_analysis': vision_result,
                'extraction_method': 'ocr_+_vision'
            }
        except:
            # Fallback si llava no está disponible
            logger.warning("Llava not available, using OCR only")
            return {
                'status': 'success',
                'ocr_data': simple_result,
                'vision_analysis': None,
                'extraction_method': 'ocr_only'
            }
    except Exception as e:
        logger.error(f"Error analyzing voucher: {e}")
        return {'status': 'error', 'error': str(e)}
