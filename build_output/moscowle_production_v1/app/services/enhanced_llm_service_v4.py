"""Versión FINAL de Llama v4 - Detecta intenciones y procesa análisis"""
import json
import logging
import re
from datetime import datetime, timedelta
from app.extensions import db
from app.models import User, Payment
import ollama

logger = logging.getLogger('app')
client = ollama.Client(host='http://127.0.0.1:11434')

# ==================== DETECTOR DE INTENCIONES ====================

def detect_user_intent(message: str):
    """Detecta intención del usuario por palabras clave"""
    msg_lower = message.lower()
    
    # Business Analysis
    if any(word in msg_lower for word in ['no han pagado', 'moroso', 'deuda', 'unpaid', 'sin pagar']):
        return 'business_analysis', {'analysis_type': 'unpaid_users'}
    
    if any(word in msg_lower for word in ['próxima semana', 'próximos días', 'vencer', 'deben pagar', 'weekly']):
        return 'business_analysis', {'analysis_type': 'weekly_due'}
    
    if any(word in msg_lower for word in ['finanzas', 'ganancias', 'ingresos', 'egresos', 'revenue', 'profit']):
        return 'business_analysis', {'analysis_type': 'revenue_metrics'}
    
    if any(word in msg_lower for word in ['necesito', 'cuántos alumnos', 'breakeven', 'ganancia de', 'profit']):
        match = re.search(r'\d+(?:,\d{3})*(?:\.\d{2})?', message)
        target = float(match.group(0).replace(',', '')) if match else 5000
        return 'breakeven_analysis', {'target_profit': target}
    
    # Schedule & Optimization
    if any(word in msg_lower for word in ['mejorar horarios', 'scheduling', 'horario', 'optimize']):
        return 'schedule_optimization', {}
    
    # Reports
    if any(word in msg_lower for word in ['informe', 'reporte', 'report', 'resumen']):
        return 'generate_report', {}
    
    # Navigation
    if any(word in msg_lower for word in ['llévame', 'navega', 'ir a', 'voy a', 'go to']):
        for section in ['deudores', 'pagos', 'sesiones', 'reportes', 'usuarios', 'sedes', 'gastos', 'mensajes']:
            if section in msg_lower:
                return 'navigation', {'target_section': section}
    
    # Payment Registration
    if any(word in msg_lower for word in ['registra', 'pagar', 'payment', 'cobrar']):
        # Extraer monto y nombre
        amount_match = re.search(r'(\d+(?:[.,]\d{2})?)', message)
        name_match = re.search(r'para\s+([a-záéíóúñ\s]+?)(?:\s+(?:de|por|monto)|\.|$)', message, re.IGNORECASE)
        
        params = {}
        if amount_match:
            params['amount'] = float(amount_match.group(1).replace(',', '.'))
        if name_match:
            params['patient_name'] = name_match.group(1).strip()
        
        return 'register_payment', params
    
    # Upload Voucher
    if any(word in msg_lower for word in ['boleta', 'voucher', 'foto', 'comprobante', 'upload']):
        return 'upload_voucher', {}
    
    # Default: General chat
    return 'general_chat', {}

# ==================== PROCESAMIENTO ====================

def process_intent_with_data(intent: str, params: dict, user_message: str):
    """Procesa intención con datos reales desde BD"""
    from app.services.business_analytics_service import (
        get_unpaid_users,
        get_weekly_due_payments,
        calculate_revenue_metrics,
        get_schedule_recommendations,
        generate_business_report,
        estimate_breakeven_point,
        answer_business_question
    )
    
    try:
        if intent == 'business_analysis':
            analysis_type = params.get('analysis_type', 'revenue_metrics')
            
            if analysis_type == 'unpaid_users':
                data = get_unpaid_users()
                response = f"""📊 **Alumnos Sin Pagar Este Mes**
Total morosos: {data['total_unpaid']}
Deuda acumulada: S/. {data['total_debt']:.2f}
Días promedio de retraso: {sum(u['days_overdue'] for u in data['users']) // max(1, len(data['users']))} días

Top morosos:"""
                for user in data['users'][:3]:
                    response += f"\n• {user['name']}: S/. {user['amount_due']:.2f} ({user['days_overdue']} días)"
                return response
            
            elif analysis_type == 'weekly_due':
                data = get_weekly_due_payments()
                response = f"""📅 **Pagos Próxima Semana**
Pendientes de pago: {data['count']} alumnos
Ingresos esperados: S/. {data['total_amount']:.2f}

Detalle:"""
                for p in data['payments'][:5]:
                    response += f"\n• {p['name']}: S/. {p['amount']} (vence en {p['days_until_due']} días)"
                return response
            
            elif analysis_type == 'revenue_metrics':
                data = calculate_revenue_metrics()
                response = f"""💰 **Métricas Financieras (Este mes)**
Ingresos: S/. {data['total_income']:.2f}
Egresos: S/. {data['total_expenses']:.2f}
Ganancia Neta: S/. {data['net_profit']:.2f}
Margen de Ganancia: {data['profit_margin_percent']:.1f}%

Cobranza:
Alumnos que pagaron: {data['paid_patients']}/{data['total_patients']} ({data['collection_rate']:.1f}%)
Promedio por alumno: S/. {data['avg_income_per_paid_patient']:.2f}"""
                return response
        
        elif intent == 'schedule_optimization':
            rec = get_schedule_recommendations()
            return f"""📍 **Recomendaciones para Mejorar Horarios**\n{rec['recommendations']}"""
        
        elif intent == 'generate_report':
            report = generate_business_report()
            return report  # Devuelve el reporte completo
        
        elif intent == 'breakeven_analysis':
            target = params.get('target_profit', 5000)
            be = estimate_breakeven_point(target)
            if be:
                return f"""📈 **Análisis de Rentabilidad**
Objetivo: S/. {target:.0f} de ganancia
Alumnos actuales: {be['current_students']}
Alumnos necesarios: {be['students_needed']} 
Alumnos adicionales: {be['additional_students']}
Factibilidad: {be['feasibility'].upper()}"""
            return "Error en cálculo de punto de equilibrio"
        
        # Preguntas genéricas de negocio
        else:
            analysis = answer_business_question(user_message)
            return analysis['answer']
    
    except Exception as e:
        logger.error(f"Error processing intent {intent}: {e}")
        return f"Error procesando {intent}: {str(e)[:50]}"

# ==================== FUNCIÓN PRINCIPAL ====================

def process_chat_enhanced_v4(uid: int, msg: str, cid=None, pg="dashboard"):
    """
    Versión FINAL - Detecta intención + Procesa con datos reales
    """
    try:
        # Paso 1: Detectar intención
        intent, params = detect_user_intent(msg)
        logger.info(f"Detected intent: {intent}, params: {params}")
        
        # Paso 2: Procesar según intención
        if intent in ['business_analysis', 'schedule_optimization', 'generate_report', 'breakeven_analysis']:
            # Análisis de datos reales
            response = process_intent_with_data(intent, params, msg)
            
            # Construir respuesta JSON
            result = {
                'intent': intent,
                'response': response,
                'parameters': params,
                'confidence': 0.95,
                'tutorial_steps': []
            }
        
        elif intent == 'navigation':
            # Navegar a sección
            from app.services.enhanced_llm_service_v3 import get_navigation_url, get_tutorial_steps
            target_section = params.get('target_section', 'dashboard')
            redirect_url = get_navigation_url(target_section, uid)
            
            result = {
                'intent': intent,
                'response': f"🚀 Llevándote a {target_section}...",
                'parameters': params,
                'redirect': redirect_url,
                'tutorial_steps': get_tutorial_steps('navigation', target_section),
                'confidence': 0.95
            }
        
        elif intent == 'register_payment':
            # Registrar pago
            result = {
                'intent': intent,
                'response': f"Entiendo que quieres registrar S/. {params.get('amount', 0):.2f} para {params.get('patient_name', '?')}",
                'parameters': params,
                'confidence': 0.90,
                'tutorial_steps': []
            }
        
        elif intent == 'upload_voucher':
            result = {
                'intent': intent,
                'response': "📸 Sube la foto de la boleta para que la analice",
                'parameters': params,
                'confidence': 0.95,
                'tutorial_steps': []
            }
        
        else:  # general_chat
            # Pregunta general con IA
            if not client:
                response = "Asistente IA desconectado"
            else:
                try:
                    resp = client.chat(
                        model='llama3.1:8b',
                        messages=[{
                            'role': 'user',
                            'content': f"Eres asistente de Centro de Terapias. Responde brevemente: {msg}"
                        }],
                        options={'temperature': 0.3}
                    )
                    response = resp['message'].get('content', 'No hay respuesta')
                except:
                    response = "Error consultando IA"
            
            result = {
                'intent': intent,
                'response': response,
                'parameters': params,
                'confidence': 0.8,
                'tutorial_steps': []
            }
        
        return result
    
    except Exception as e:
        logger.error(f"Error in v4: {e}", exc_info=True)
        return {
            'intent': 'error',
            'response': f"Error: {str(e)[:50]}",
            'parameters': {},
            'confidence': 0
        }
