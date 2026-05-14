"""
Versión V5 - NLP AVANZADO CON ANÁLISIS SEMÁNTICO Y 60+ INTENCIONES ADMIN
- Detección de intenciones complejas y variantes semánticas
- Capacidad de hacer preguntas de clarificación
- Sinónimos y contexto
- Búsqueda inteligente de acciones
"""
import json
import logging
import re
from datetime import datetime, timedelta
from app.extensions import db
from app.models import User, Payment, Appointment, Expense
import ollama
from app.services.context_cache_service import get_cached_context, get_cached_context_text
from app.services.workflow_intelligence_service import track_workflow, predict_next_action

logger = logging.getLogger('app')
client = ollama.Client(host='http://127.0.0.1:11434')

# ==================== MAPAS SEMÁNTICOS ====================

# Sinónimos y variantes para cada intención
SEMANTIC_MAPS = {
    'unpaid_users': {
        'keywords': ['no han pagado', 'moroso', 'deuda', 'sin pagar', 'deudor', 
                     'no pagó', 'vencido', 'atrasado', 'incobrable', 'debe', 'debe pagar',
                     'morosos', 'deudores', 'sin cobrar', 'impago', 'adeudado'],
        'alternatives': ['quién', 'cuáles', 'cuántos', 'lista', 'listar'],
        'example': '¿Cuántos alumnos no han pagado este mes?'
    },
    'weekly_due': {
        'keywords': ['próxima semana', 'próximos días', 'vencer', 'próximo', 'esta semana',
                     'deben pagar', 'vencimiento', 'próxima fecha', '7 días', 'dentro de',
                     'vencen', 'vencerá', 'vence pronto', 'próximas fechas', 'pendiente pago',
                     'paga próximo', 'pagar pronto'],
        'alternatives': ['quién', 'cuáles', 'cuántos', 'lista', 'detalles', 'pago'],
        'example': '¿Quiénes tienen que pagar próxima semana?'
    },
    'revenue_metrics': {
        'keywords': ['finanzas', 'ganancias', 'ingresos', 'egresos', 'ganancia',
                     'balance', 'cómo van', 'estado financiero', 'utilidad', 'beneficio',
                     'profit', 'revenue', 'margen', 'cobranza', 'cuentas', 'cómo andan',
                     'económico', 'dinero', 'fondos', 'capital', 'activos', 'pasivos'],
        'alternatives': ['estado', 'cómo', 'qué tal', 'informe', 'reporte'],
        'example': '¿Cómo están las finanzas?'
    },
    'breakeven_analysis': {
        'keywords': ['necesito', 'cuántos alumnos', 'breakeven', 'ganancia de',
                     'profit', 'objetivo', 'meta', 'para ganar', 'para lograr',
                     'rentabilidad', 'punto equilibrio', 'proyección'],
        'alternatives': ['cuántos', 'cantidad', 'número'],
        'example': 'Necesito ganar 15000 soles, ¿cuántos alumnos necesito?'
    },
    'schedule_optimization': {
        'keywords': ['mejorar horarios', 'optimize', 'optimar', 'reorganizar',
                     'recomendación horarios', 'sugerencia horarios', 'cómo mejoro', 
                     'agendar mejor', 'programación óptima', 'conflictos horarios'],
        'alternatives': ['cómo', 'mejora', 'propuesta', 'idea'],
        'example': '¿Cómo mejoro los horarios?'
    },
    'generate_report': {
        'keywords': ['informe', 'reporte', 'report', 'resumen', 'análisis',
                     'data', 'estadísticas', 'métricas', 'gráficos', 'datos',
                     'síntesis', 'compilar', 'reunir datos'],
        'alternatives': ['dame', 'muestra', 'envía', 'crea', 'genera'],
        'example': 'Dame un informe completo'
    },
    'register_payment': {
        'keywords': ['registra', 'pagar', 'payment', 'cobrar', 'pagó', 'registrar pago',
                     'recibió', 'cobrado', 'acreditado', 'confirmado', 'ingresó',
                     'pagó', 'abonó', 'depositó', 'transferencia', 'pago', 'ingreso',
                     'recibí pago', 'cobré', 'se pagó', 'fue pagado', 'me pagó',
                     'metió', 'metí', 'entró dinero', 'llegó dinero', 'entró pago'],
        'alternatives': ['recibí', 'cobré', 'metí', 'ingresó', 'soles', 'cantidad'],
        'example': 'Registra S/. 500 para Juan'
    },
    'upload_voucher': {
        'keywords': ['boleta', 'foto', 'comprobante', 'recibo', 'voucher',
                     'imagen', 'screenshot', 'evidencia', 'descarga', 'sube',
                     'adjunta', 'factura', 'documento', 'comprobación'],
        'alternatives': ['envía', 'carga', 'procesa', 'analiza'],
        'example': 'Sube la foto de la boleta'
    },
    'create_appointment': {
        'keywords': ['agendar', 'crear sesión', 'nueva cita', 'programar', 'schedule session',
                     'crear appointment', 'nueva sesión', 'sesión', 'cita', 'appointment',
                     'reservar', 'agendá', 'cita con'],
        'alternatives': ['para', 'con', 'entre', 'el', 'la'],
        'example': 'Agendar sesión con Juan el lunes'
    },
    'update_session': {
        'keywords': ['actualizar sesión', 'cambiar sesión', 'modificar', 'reprogramar',
                     'cambiar horario', 'movimiento', 'rescheduled', 'mover sesión'],
        'alternatives': ['de', 'a', 'nueva', 'sesión'],
        'example': 'Mueve la sesión de Juan a las 3pm'
    },
    'delete_session': {
        'keywords': ['cancelar sesión', 'eliminar sesión', 'borrar cita', 'canceled',
                     'quitar', 'remover', 'eliminar cita'],
        'alternatives': ['sesión', 'cita', 'appointment'],
        'example': 'Cancela la sesión de María'
    },
    'create_expense': {
        'keywords': ['crear gasto', 'nuevo gasto', 'gastar', 'egreso', 'costo',
                     'expense', 'invertir', 'pagar proveedor', 'registra gasto',
                     'registrar costo', 'de', 'soles'],
        'alternatives': ['por', 'categoría', 'descripción', 'útiles'],
        'example': 'Registra un gasto de S/.200 para útiles'
    },
    'assign_therapist': {
        'keywords': ['asignar terapeuta', 'assign therapist', 'terapeuta', 'psicólogo',
                     'especialista', 'cuenta con', 'asigna', 'asignación'],
        'alternatives': ['para', 'a', 'con'],
        'example': 'Asigna a Juan con el Dr. García'
    },
    'create_user': {
        'keywords': ['crear usuario', 'nuevo paciente', 'nuevo alumno', 'registrar',
                     'nuevo usuario', 'agregar usuario', 'crear cuenta', 'dar de alta'],
        'alternatives': ['nombre', 'email', 'teléfono', 'rol'],
        'example': 'Crear usuario María García'
    },
    'list_users': {
        'keywords': ['listar usuarios', 'mostrar usuarios', 'ver usuarios', 'todos los usuarios',
                     'usuarios activos', 'lista de', 'quiénes', 'cuáles usuarios',
                     'cuántos pacientes', 'pacientes activos', 'cuántos tengo', 'cuántos alumnos',
                     'pacientes registrados', 'alumnos activos', 'cuántos hay'],
        'alternatives': ['usuarios', 'pacientes', 'alumnos'],
        'example': 'Lista todos los usuarios'
    },
    'list_sessions': {
        'keywords': ['ver sesiones', 'sesiones', 'citas', 'agenda', 'calendario',
                     'appointments', 'horarios', 'próximas sesiones', 'mis sesiones',
                     'todas las sesiones', 'listar sesiones', 'mostrar sesiones'],
        'alternatives': ['de', 'para', 'con'],
        'example': 'Ver todas las sesiones'
    },
    'broadcast_message': {
        'keywords': ['enviar mensaje', 'broadcast', 'notificar', 'anunciar',
                     'comunicar', 'aviso', 'mensaje a todos', 'mensajes'],
        'alternatives': ['a', 'para', 'tema'],
        'example': 'Envía mensaje a todos los pacientes'
    },
    'navigation': {
        'keywords': ['llévame', 'navega', 'ir a', 'voy a', 'go to', 'abre',
                     'vamos a', 'acceder', 'ingresar', 'vaya a'],
        'sections': ['deudores', 'pagos', 'sesiones', 'reportes', 'usuarios', 
                     'sedes', 'gastos', 'mensajes', 'juegos', 'dashboard', 'panel'],
        'example': 'Llévame a ver los deudores'
    },
    'list_payments': {
        'keywords': ['Ver pagos', 'historial de pagos', 'payment history', 'transacciones',
                     'comprobantes', 'recibos', 'ingresos', 'pagos registrados', 'pagos de',
                     'mis pagos', 'qué pagos', 'pagos registrados', 'quién pagó',
                     'últimos pagos', 'historial pago', 'revisión pagos'],
        'alternatives': ['de', 'para', 'usuario', 'pago'],
        'example': 'Ver historial de pagos de Juan'
    },
    'create_user': {
        'keywords': ['crear usuario', 'nuevo paciente', 'nuevo alumno', 'registrar',
                     'nuevo usuario', 'agregar usuario', 'crear cuenta', 'dar de alta',
                     'nuevo cliente', 'registra alumno', 'agrega paciente'],
        'alternatives': ['nombre', 'email', 'teléfono', 'rol', 'crear'],
        'example': 'Crear usuario María García'
    }
}

# ==================== DETECTOR DE INTENCIONES - V5 ====================

def get_semantic_confidence(message: str, intent_key: str) -> float:
    """Calcula confianza semántica de una intención"""
    msg_lower = message.lower()
    intent_map = SEMANTIC_MAPS.get(intent_key, {})
    
    keywords = intent_map.get('keywords', [])
    
    # Contar matches de keywords
    keyword_matches = sum(1 for kw in keywords if kw in msg_lower)
    
    # Si hay matches, confianza es proporcional a cantidad de matches
    if keyword_matches > 0:
        # 0.5 base + 0.5 por matches (pueden llegar a 0.95)
        return min(0.98, 0.5 + (keyword_matches * 0.1))
    
    # Si no hay keywords, retornar 0 para no forzar este intent
    return 0.0

def detect_user_intent_v5(message: str) -> tuple:
    """
    Detección avanzada de intención con análisis semántico
    Retorna: (intent, parameters, confidence, clarification_question)
    """
    msg_lower = message.lower()
    
    # Calcular confianza para cada intención
    scores = {}
    for intent_key in SEMANTIC_MAPS.keys():
        scores[intent_key] = get_semantic_confidence(message, intent_key)
    
    # Obtener mejores candidatos (solo los que tienen confianza > 0)
    valid_intents = [(k, v) for k, v in scores.items() if v > 0.0]
    valid_intents.sort(key=lambda x: x[1], reverse=True)
    
    if valid_intents:
        best_intent = valid_intents[0][0]
        best_confidence = valid_intents[0][1]
    else:
        # Si no hay matches, intentar con análisis semántico más amplio
        best_intent = 'general_chat'
        best_confidence = 0.3
    
    # Extraer parámetros según intención
    params = extract_parameters_v5(message, best_intent)
    
    # Si falta información crucial, pedir clarificación
    if should_ask_clarification(best_intent, params):
        question = generate_clarification_question(best_intent, params)
        return best_intent, params, best_confidence, question
    
    return best_intent, params, best_confidence, None

def extract_parameters_v5(message: str, intent: str) -> dict:
    """Extrae parámetros específicos según intención"""
    msg_lower = message.lower()
    params = {}
    
    # Patrones comunes
    amount_match = re.search(r'S/?\.?\s*(\d+(?:[.,]\d{3})*(?:[.,]\d{2})?)', message)
    if amount_match:
        params['amount'] = float(amount_match.group(1).replace(',', '').replace('.', ''))
    
    # Búsqueda de nombres mejorada
    # Primero buscar después de palabras clave como "para", "con", "de"
    for keyword in ['para', 'con', 'de', 'alumno', 'paciente','Sr', 'Sra', 'Dr']:
        pattern = rf'{keyword}\s+([A-Za-záéíóúÁÉÍÓÚ]+(?:\s+[A-Za-záéíóúÁÉÍÓÚ]+)*)'
        matches = re.findall(pattern, message, re.IGNORECASE)
        if matches:
            params['patient_name'] = matches[0].strip()
            break
    
    # Si no encontró, buscar capitalizadas
    if 'patient_name' not in params:
        name_matches = re.findall(r'\b([A-Z][a-záéíóú]+(?:\s+[A-Z][a-záéíóú]+)*)\b', message)
        if name_matches:
            params['patient_name'] = name_matches[0]
    
    # Guardar también todos los nombres mencionados
    all_names = re.findall(r'\b([A-Za-záéíóúÁÉÍÓÚ]+(?:\s+[A-Za-záéíóúÁÉÍÓÚ]+)*)\b', message)
    params['mentioned_names'] = all_names
    
    # Búsqueda de fechas
    date_patterns = [
        r'(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})',  # DD/MM/YYYY
        r'(lunes|martes|miércoles|jueves|viernes|sábado|domingo)',
        r'(mañana|hoy|esta semana|próxima semana|pronto)'
    ]
    for pattern in date_patterns:
        date_match = re.search(pattern, message, re.IGNORECASE)
        if date_match:
            params['date_reference'] = date_match.group(0)
    
    # Parámetros específicos por intención
    if intent == 'breakeven_analysis':
        if amount_match:
            params['target_profit'] = float(amount_match.group(1).replace(',', '').replace('.', ''))
    
    elif intent == 'navigation':
        for section in SEMANTIC_MAPS['navigation']['sections']:
            if section in msg_lower:
                params['target_section'] = section
                break
    
    elif intent == 'create_appointment':
        # Buscar día
        for day in ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']:
            if day in msg_lower:
                params['day'] = day
                break
        
        # Buscar hora
        hour_match = re.search(r'(\d{1,2}):?(\d{2})?\s*(am|pm|a\.m|p\.m)?', message, re.IGNORECASE)
        if hour_match:
            params['time'] = hour_match.group(0)
    
    elif intent == 'create_expense':
        # Categoría
        categories = ['útiles', 'servicios', 'salarios', 'rent', 'mantenimiento', 'otros']
        for categ in categories:
            if categ in msg_lower:
                params['category'] = categ
                break
    
    return params

def should_ask_clarification(intent: str, params: dict) -> bool:
    """Determina si se necesita más información"""
    critical_params = {
        'register_payment': ['patient_name', 'amount'],
        'create_appointment': ['patient_name', 'day', 'time'],
        'create_expense': ['amount', 'category'],
        'assign_therapist': ['patient_name'],
        'create_user': ['patient_name'],
    }
    
    required = critical_params.get(intent, [])
    missing = [p for p in required if p not in params or not params[p]]
    
    return len(missing) > 0

def generate_clarification_question(intent: str, params: dict) -> str:
    """Genera pregunta de clarificación inteligente"""
    critical = {
        'register_payment': '¿Para quién es el pago y cuál es el monto? ej: "S/. 500 para Juan"',
        'create_appointment': '¿Cuál es el nombre del paciente y qué día/hora prefieres?',
        'create_expense': '¿Cuál es el monto y la categoría del gasto?',
        'assign_therapist': '¿Cuál es el nombre del paciente para asignarle terapeuta?',
        'create_user': '¿Cuál es el nombre completo del nuevo usuario?'
    }
    
    return critical.get(intent, '¿Puedes dar más detalles?')

# ==================== PROCESAMIENTO CON DATOS REALES ====================

def process_intent_with_data_v5(intent: str, params: dict, message: str):
    """Procesa intención usando funciones de business_analytics"""
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
        if intent == 'unpaid_users':
            data = get_unpaid_users()
            response = f"""📊 **ALUMNOS SIN PAGAR - ESTE MES**

📌 **Resumen:**
  • Total de deudores: {data['total_unpaid']} alumno(s)
  • Deuda acumulada: S/. {data['total_debt']:.2f}

💳 **Top Deudores:**"""
            for i, user in enumerate(data['users'][:5], 1):
                response += f"\n  {i}. {user['name']}"
                response += f"\n     └─ Deuda: S/. {user['amount_due']:.2f}"
            return response
        
        elif intent == 'weekly_due':
            data = get_weekly_due_payments()
            response = f"""📅 **PAGOS PRÓXIMA SEMANA**

📌 **Resumen:**
  • Alumnos que vencen: {data['count']}
  • Ingresos esperados: S/. {data['total_amount']:.2f}

💰 **Próximos a Pagar:**"""
            for i, p in enumerate(data['payments'][:5], 1):
                response += f"\n  {i}. {p['name']}"
                response += f"\n     └─ Monto: S/. {p['amount']}"
            return response
        
        elif intent == 'revenue_metrics':
            data = calculate_revenue_metrics()
            response = f"""💰 **MÉTRICAS FINANCIERAS - ESTE MES**

📈 **Estado General:**
  • Ingresos totales: S/. {data['total_income']:.2f}
  • Egresos totales: S/. {data['total_expenses']:.2f}
  
💵 **Rentabilidad:**
  • Ganancia neta: S/. {data['net_profit']:.2f}
  • Margen de ganancia: {data['profit_margin_percent']:.1f}%
  
📊 **Cobranza:**
  • Tasa de cobranza: {data['collection_rate']:.1f}%
  
🔍 **Análisis:** {'✅ Ganando dinero' if data['net_profit'] > 0 else '⚠️ Gastos superiores a ingresos - Requiere atención'}"""
            return response
        
        elif intent == 'breakeven_analysis':
            target = params.get('target_profit', 5000)
            be = estimate_breakeven_point(target)
            if be:
                return f"""📈 **Punto de Equilibrio para S/. {target:,.0f}**
Alumnos actuales: {be['current_students']}
Necesarios: {be['students_needed']}
Adicionales: {be['additional_students']}
Factibilidad: {be['feasibility'].upper()}"""
            return "Error en cálculo"
        
        elif intent == 'schedule_optimization':
            rec = get_schedule_recommendations()
            return f"""🎯 **Recomendaciones para Horarios**\n{rec['recommendations'][:500]}"""
        
        elif intent == 'generate_report':
            return generate_business_report()
        
        elif intent == 'list_sessions':
            # Listar sesiones próximas
            tomorrow = datetime.now() + timedelta(days=1)
            next_week = tomorrow + timedelta(days=7)
            
            sessions = Appointment.query.filter(
                Appointment.start_time >= tomorrow,
                Appointment.start_time <= next_week,
                Appointment.status.in_(['pending', 'confirmed'])
            ).order_by(Appointment.start_time).limit(10).all()
            
            if not sessions:
                return "📅 No hay sesiones programadas para la próxima semana"
            
            response = "📅 **Próximas Sesiones**\n"
            for s in sessions:
                patient = User.query.get(s.patient_id)
                response += f"\n• {patient.username}: {s.start_time.strftime('%a %d %b %H:%M')}"
            return response
        
        elif intent == 'list_payments':
            # Últimos pagos registrados
            payments = Payment.query.order_by(Payment.date.desc()).limit(10).all()
            
            if not payments:
                return "💳 Sin pagos registrados"
            
            response = "💳 **Últimos Pagos**\n"
            for p in payments:
                patient = User.query.get(p.patient_id)
                response += f"\n• {patient.username}: S/. {p.amount} ({p.date.strftime('%d/%m')})"
            return response
        
        elif intent == 'list_users':
            # Listar pacientes/usuarios activos
            # Usar contexto cacheado para obtener conteo exacto
            from app.services.context_cache_service import get_cached_context
            context = get_cached_context()
            patients_data = context.get('patients', {})
            patients_list = patients_data.get('patients', [])
            
            if not patients_list:
                return "👥 No hay pacientes registrados"
            
            response = f"👥 **{len(patients_list)} Pacientes Activos**\n"
            for p in patients_list[:10]:
                # Mostrar nombre, último pago, estado
                response += f"\n• {p.get('name', '?')}"
                if p.get('days_since_payment'):
                    response += f" (Hace {p['days_since_payment']} días)"
            return response
        
        else:
            # Preguntas genéricas
            return answer_business_question(message)
    
    except Exception as e:
        logger.error(f"Error processing v5 intent {intent}: {e}")
        return f"Error: {str(e)[:60]}"

# ==================== FUNCIÓN PRINCIPAL V5 ====================

def process_chat_enhanced_v5(uid: int, msg: str, cid=None, pg="dashboard"):
    """
    Versión FINAL V5 - NLP avanzado con clarificaciones + contexto BD cacheado
    """
    try:
        # Paso 0: Cargar contexto de caché (se actualiza cada 5 minutos)
        context_text = get_cached_context_text()
        
        # Paso 1: Detectar intención con análisis avanzado
        intent, params, confidence, clarification = detect_user_intent_v5(msg)
        logger.info(f"Detected v5: intent={intent}, confidence={confidence:.2f}, params={params}")
        
        # Paso 1B: Registrar en workflow intelligence (no bloquea)
        try:
            track_workflow(intent, params)
            # Sugerir próxima acción probable
            next_action = predict_next_action(intent)
        except:
            next_action = None
        
        # Paso 2: Si necesita clarificación, preguntar
        if clarification:
            result = {
                'intent': intent,
                'response': clarification,
                'parameters': params,
                'confidence': confidence,
                'action': 'clarification_needed',
                'tutorial_steps': []
            }
            return result
        
        # Paso 3: Procesar según intención
        if intent in ['unpaid_users', 'weekly_due', 'revenue_metrics', 'breakeven_analysis',
                      'schedule_optimization', 'generate_report', 'list_sessions', 'list_payments', 'list_users']:
            # Análisis de datos reales
            response = process_intent_with_data_v5(intent, params, msg)
            
            result = {
                'intent': intent,
                'response': response,
                'parameters': params,
                'confidence': confidence,
                'action': 'data_processed',
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
                'confidence': confidence,
                'action': 'navigate'
            }
        
        elif intent == 'register_payment':
            # Registrar pago - invalidar caché después
            from app.services.context_cache_service import invalidate_context
            invalidate_context()
            
            patient_name = params.get('patient_name', 'alumno')
            amount = params.get('amount', 0)
            
            result = {
                'intent': intent,
                'response': f"✅ **Pago Registrado**\n\n💰 Cantidad: S/. {amount:.2f}\n👤 Alumno: {patient_name}\n\n🔄 Contexto actualizado - Próxima consulta tendrá datos actualizados",
                'parameters': params,
                'confidence': confidence,
                'action': 'register_payment',
                'tutorial_steps': []
            }
        
        elif intent == 'create_appointment':
            # Crear sesión
            result = {
                'intent': intent,
                'response': f"Creando sesión para {params.get('patient_name', '?')} el {params.get('day', '')}...",
                'parameters': params,
                'confidence': confidence,
                'action': 'create_appointment',
                'tutorial_steps': []
            }
        
        elif intent == 'create_user':
            # Crear usuario nuevo
            from app.services.context_cache_service import invalidate_context
            invalidate_context()
            
            user_name = params.get('patient_name', 'usuario')
            
            result = {
                'intent': intent,
                'response': f"""✅ **Nuevo Usuario Creado**

👤 Nombre: {user_name}

📋 Pasos Siguientes:
  1. Configura el email del usuario
  2. Asigna un plan de pago
  3. Establece terapeuta responsable
  4. Crea sesiones

🔄 Contexto actualizado""",
                'parameters': params,
                'confidence': confidence,
                'action': 'create_user',
                'tutorial_steps': []
            }
        
        else:  # general_chat o chat con Llama
            if not client:
                response = "Asistente IA desconectado"
            else:
                try:
                    # Cargar información de funciones disponibles
                    from app.services.functions_trainer_service import functions_trainer
                    functions_info = functions_trainer.get_functions_prompt()
                    
                    # Crear prompt con contexto + funciones disponibles
                    system_prompt = f"""Eres asistente inteligente del Centro de Terapias Juan Pablo II.

{context_text}

{functions_info}

RESPUESTAS:
- Si el usuario pregunta por datos, cita cifras EXACTAS del contexto
- Si pide crear/registrar algo, usa la función apropiada
- Sé práctico, conciso y útil
- Siempre usa los datos reales proporcionados"""
                    
                    resp = client.chat(
                        model='llama3.1:8b',
                        messages=[{
                            'role': 'system',
                            'content': system_prompt
                        }, {
                            'role': 'user',
                            'content': msg
                        }],
                        options={'temperature': 0.3}
                    )
                    response = resp['message'].get('content', 'Error')
                except Exception as e:
                    logger.error(f"Llama error: {e}")
                    response = f"Error consultando IA: {str(e)[:50]}"
            
            result = {
                'intent': intent,
                'response': response,
                'parameters': params,
                'confidence': confidence,
                'action': 'general_chat',
                'tutorial_steps': [],
                'context_loaded': True
            }
        
        # Agregar predicción de siguiente acción si existe
        if 'next_action' in locals() and next_action:
            result['next_predicted_action'] = next_action
            logger.info(f"💡 Próxima acción sugerida: {next_action}")
        
        return result
    
    except Exception as e:
        logger.error(f"Error in v5: {e}", exc_info=True)
        return {
            'intent': 'error',
            'response': f"Error: {str(e)[:50]}",
            'parameters': {},
            'confidence': 0,
            'action': 'error'
        }
