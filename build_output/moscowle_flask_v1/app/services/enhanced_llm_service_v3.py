"""Servicio mejorado de Llama v3 con datos reales y redirecciones"""
import json, logging, re
from dotenv import load_dotenv
from flask import url_for
from datetime import datetime

try:
    import ollama
    client = ollama.Client(host='http://127.0.0.1:11434')
except:
    client = None

load_dotenv()
logger = logging.getLogger('app')

# PROMPT MEJORADO CON ANÁLISIS DE NEGOCIO
PROMPT = """Eres Llama, asistente administrativo experto en Centro de Terapias. Expertise:
- Finanzas y cobranza
- Análisis de rentabilidad
- Horarios y scheduling
- Reportes y métricas
- Análisis de imágenes/boletas

INSTRUCCIONES CRÍTICAS:
1. SIEMPRE responde SOLO en JSON válido
2. Estructura: {{"intent": "tipo", "response": "amistoso", "parameters": {{}}, "tutorial_steps": []}}
3. Intenciones válidas: 
   - general_chat (preguntas generales)
   - navigation (llevar a sección)
   - register_payment (registrar pago)
   - business_analysis (análisis de negocio)
   - generate_report (crear informe)
   - schedule_optimization (recomendar horarios)
   - breakeven_analysis (análisis de rentabilidad)
   - upload_voucher (procesar foto de boleta)
   - tutorial (modo tutorial paso a paso)

4. Para business_analysis, incluye en parameters:
   - analysis_type: unpaid_users|weekly_due|revenue_metrics|breakeven|recommendations
   - target_profit: (si es breakeven)

CONTEXTO DEL SISTEMA:
- Total de alumnos: {total_students}
- Ingresos este mes: S/. {current_income}
- Egresos este mes: S/. {current_expenses}
- Ganancia neta: S/. {net_profit}
- Tasa de cobranza: {collection_rate}%
- Alumnos morosos: {unpaid_count}
- Ingresos esperados próxima semana: S/. {weekly_income}

PREGUNTAS COMUNES A DETECTAR:
- "cuántos no han pagado" → intent: business_analysis, analysis_type: unpaid_users
- "quiénes deben pagar" → intent: business_analysis, analysis_type: weekly_due
- "ganancias de {{número}}" → intent: breakeven_analysis, target_profit: {{número}}
- "mejorar horarios" → intent: schedule_optimization
- "hacer informe" → intent: generate_report
- "foto/boleta/comprobante" → intent: upload_voucher
- "cómo va el negocio" → intent: generate_report

Historial reciente:
{conversation_history}

RESPONDE ÚNICAMENTE EN JSON VÁLIDO. No incluyas explicaciones fuera del JSON."""

def get_conversation_history(cid, limit=3):
    try:
        from app.models import AIChatMessage
        msgs = AIChatMessage.query.filter_by(conversation_id=cid).order_by(
            AIChatMessage.timestamp.desc()).limit(limit).all()
        return "\n".join([f"{'USER' if m.role=='user' else 'IA'}: {m.content}" 
                         for m in reversed(msgs)]) if msgs else "Sin historial"
    except:
        return "Sin historial"

def get_system_metrics():
    """Obtiene métricas reales del sistema incluyendo análisis de negocio"""
    try:
        from app.models import User, Payment, Expense
        from app.services.business_analytics_service import (
            get_unpaid_users,
            get_weekly_due_payments,
            calculate_revenue_metrics
        )
        from app.extensions import db
        from datetime import datetime
        
        # Métricas financieras
        revenue = calculate_revenue_metrics()
        unpaid = get_unpaid_users()
        weekly = get_weekly_due_payments()
        
        return {
            'total_students': str(revenue.get('total_patients', 0)),
            'current_income': f"{revenue.get('total_income', 0):.2f}",
            'current_expenses': f"{revenue.get('total_expenses', 0):.2f}",
            'net_profit': f"{revenue.get('net_profit', 0):.2f}",
            'collection_rate': f"{revenue.get('collection_rate', 0):.1f}",
            'unpaid_count': str(unpaid.get('total_unpaid', 0)),
            'weekly_income': f"{weekly.get('total_amount', 0):.2f}"
        }
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        return {
            'total_students': '0',
            'current_income': '0',
            'current_expenses': '0',
            'net_profit': '0',
            'collection_rate': '0',
            'unpaid_count': '0',
            'weekly_income': '0'
        }

def parse_json_response(raw):
    """Parse JSON con fallbacks"""
    if not raw:
        return None
    
    raw = str(raw).strip()
    logger.debug(f"Parse attempt: {raw[:150]}")
    
    # Try 1: Direct JSON
    try:
        result = json.loads(raw)
        if isinstance(result, dict):
            return result
    except Exception as e1:
        logger.debug(f"Direct parse failed: {e1}")
    
    # Try 2: Extract JSON
    try:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start != -1 and end > start:
            extracted = raw[start:end]
            result = json.loads(extracted)
            if isinstance(result, dict):
                return result
    except Exception as e2:
        logger.debug(f"Extract failed: {e2}")
    
    # Try 3: Remove markdown code blocks
    try:
        cleaned = raw.replace("```json", "").replace("```", "").strip()
        start = cleaned.find("{")
        end = cleaned.rfind("}") + 1
        if start != -1 and end > start:
            result = json.loads(cleaned[start:end])
            if isinstance(result, dict):
                return result
    except Exception as e3:
        logger.debug(f"Markdown cleanup failed: {e3}")
    
    logger.error(f"JSON parse completely failed: {raw[:300]}")
    return None

def process_chat_command_enhanced_v3(uid, msg, cid=None, pg="dashboard"):
    """Procesa comando con datos reales y redirecciones"""
    if not client:
        return {
            "intent": "general_chat",
            "response": "El asistente IA está desconectado. Intenta más tarde.",
            "parameters": {}
        }
    
    try:
        hist = get_conversation_history(cid) if cid else ""
        metrics = get_system_metrics()
        
        prompt = PROMPT.format(
            conversation_history=hist,
            total_students=metrics.get('total_students', '0'),
            current_income=metrics.get('current_income', '0'),
            current_expenses=metrics.get('current_expenses', '0'),
            net_profit=metrics.get('net_profit', '0'),
            collection_rate=metrics.get('collection_rate', '0'),
            unpaid_count=metrics.get('unpaid_count', '0'),
            weekly_income=metrics.get('weekly_income', '0')
        )
        
        logger.info(f"Sending to Llama: {msg[:50]}")
        
        resp = client.chat(
            model='llama3.1:8b',
            messages=[
                {'role': 'system', 'content': prompt},
                {'role': 'user', 'content': msg}
            ],
            options={'temperature': 0.2}  # Más determinista
        )
        
        raw = resp['message'].get('content', '')
        logger.info(f"Llama response: {raw[:150]}")
        
        result = parse_json_response(raw)
        
        if not result or not isinstance(result, dict):
            logger.error(f"Failed to parse response, raw: {raw[:200]}")
            return {
                "intent": "general_chat",
                "response": "No entendí bien. ¿Puedes repetir?",
                "parameters": {}
            }
        
        # Asegurar campos obligatorios
        result.setdefault('intent', 'general_chat')
        result.setdefault('response', 'OK')
        result.setdefault('parameters', {})
        result.setdefault('tutorial_steps', [])
        result['confidence'] = min(0.95, result.get('confidence', 0.8))
        
        logger.info(f"Parsed result: intent={result.get('intent')}, params={result.get('parameters')}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error in v3 service: {e}", exc_info=True)
        return {
            "intent": "general_chat",
            "response": f"Error al procesar: {str(e)[:30]}",
            "parameters": {}
        }

def extract_payment_details(msg):
    """Extrae detalles de pago del mensaje usando regex"""
    # Busca patrones como "500 para Juan" o "Juan García 500"
    patterns = [
        r'(?:registra|pago|pagar|s/\.?\s*)(\d+(?:[.,]\d{2})?)\s+(?:para|a)\s+([a-záéíóúñ\s]+)',
        r'([a-záéíóúñ\s]+)\s+(?:de|por|pago|monto|s/\.?)\s*(\d+(?:[.,]\d{2})?)',
    ]
    
    msg_lower = msg.lower()
    for pattern in patterns:
        match = re.search(pattern, msg_lower, re.IGNORECASE)
        if match:
            if 'para' in pattern or 'a' in pattern:
                amount, name = match.groups()
            else:
                name, amount = match.groups()
            
            try:
                amount = float(amount.replace(',', '.'))
                return {'patient_name': name.strip(), 'amount': amount}
            except:
                pass
    
    return {}

def validate_payment_parameters(p):
    name = p.get('patient_name', '').strip()
    if not name:
        return False, "Falta nombre del paciente"
    try:
        amt = float(p.get('amount', 0))
        if amt <= 0:
            return False, "El monto debe ser mayor a 0"
        return True, "OK"
    except:
        return False, "Monto inválido"

def validate_expense_parameters(p):
    cat = p.get('category', '').strip()
    if not cat:
        return False, "Falta categoría"
    try:
        amt = float(p.get('amount', 0))
        if amt <= 0:
            return False, "El monto debe ser mayor a 0"
        return True, "OK"
    except:
        return False, "Monto inválido"

def save_chat_message(cid, role, content, intent=None, parameters=None, action_status='pending'):
    """Guarda mensaje en BD"""
    try:
        from app.extensions import db
        from app.models import AIChatMessage
        msg = AIChatMessage(
            conversation_id=cid,
            role=role,
            content=content,
            intent=intent,
            parameters=json.dumps(parameters or {}),
            action_status=action_status
        )
        db.session.add(msg)
        db.session.commit()
        logger.info(f"Saved: {role} - {content[:40]}")
    except Exception as e:
        logger.error(f"Save error: {e}")

def get_navigation_url(target_section, uid=None):
    """Genera URL correcta para navegación"""
    section_map = {
        'deudores': 'admin.deudores_list',
        'pagos': 'admin.payments',
        'sesiones': 'admin.sesiones',
        'reportes': 'admin.reports',
        'usuarios': 'admin.users_list',
        'sedes': 'admin.sedes',
        'gastos': 'admin.expenses',
        'mensajes': 'admin.messages',
        'dashboard': 'admin.dashboard',
    }
    
    endpoint = section_map.get(target_section.lower(), 'admin.dashboard')
    try:
        if uid and 'user' in endpoint:
            return url_for(endpoint, user_id=uid)
        return url_for(endpoint)
    except:
        return f"/admin/{target_section}"

def get_tutorial_steps(intent, target_section=None):
    """Genera pasos de tutorial según intención"""
    tutorials = {
        'navigation': [
            {"step": 1, "title": "Mirando datos...", "message": "Una momento, cargaré la información..."},
            {"step": 2, "title": "Navegando...", "message": f"Te llevaré a la sección de {target_section or 'módulo'}..."},
            {"step": 3, "title": "¡Listo!", "message": "Aquí está la información que buscabas."},
        ],
        'register_payment': [
            {"step": 1, "title": "Validando datos...", "message": "Verificando nombre del paciente..."},
            {"step": 2, "title": "Buscando paciente...", "message": "Consultando base de datos..."},
            {"step": 3, "title": "Registrando pago...", "message": "Procesando transacción..."},
            {"step": 4, "title": "¡Completado!", "message": "Pago registrado exitosamente."},
        ],
        'upload_voucher': [
            {"step": 1, "title": "Preparado para recibir...", "message": "Sube la imagen del comprobante."},
            {"step": 2, "title": "Analizando boleta...", "message": "Extrayendo información del documento..."},
            {"step": 3, "title": "Validando datos...", "message": "Verificando monto y datos..."},
            {"step": 4, "title": "¡Listo!", "message": "Boleta procesada correctamente."},
        ],
    }
    
    return tutorials.get(intent, [])
