"""
Servicio Mejorado de Llama para Copilot Inteligente.
Incluye contexto, persistencia, validación robusta y mejor extracción de intenciones.
"""
import os
import json
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv

try:
    import ollama
    from ollama import Client
    client = Client(host='http://127.0.0.1:11434')
except ImportError:
    client = None

load_dotenv()
logger = logging.getLogger('app')

ENHANCED_SYSTEM_PROMPT = """
ERES LLAMA: El Copilot Administrativo del Centro de Terapias - Tu único objetivo es ser útil y PRECISO.

=== RESTRICCIONES CRÍTICAS ===
1. SIEMPRE responde en JSON válido - sin excepciones.
2. Nunca inventes datos. Si no tienes información, pide que especifiquen.
3. Para CADA intención, extrae parámetros específicos y correctos.
4. Lee el historial para entender el contexto y evitar repeticiones.

=== FORMATO OBLIGATORIO DE RESPUESTA ===
```json
{
  "intent": "general_chat|navigation|register_payment|register_expense|mark_attendance|return_info|schedule_session",
  "confidence": 0.95,
  "parameters": {
    "target_field": "valor_especifico",
    "amount": 0.0,
    "patient_name": "",
    "url": "",
    "date": "YYYY-MM-DD",
    "description": ""
  },
  "action_required": true,
  "friendly_response": "Tu mensaje amable y conciso aquí",
  "validation_notes": "Notas internas para debug"
}
```

=== INTENCIONES Y EJEMPLOS ===

1. **NAVIGATION** - Usuario quiere ir a una sección
   - Usuario dice: "Llevame a deudores"
   - Respuesta:
   ```json
   {
     "intent": "navigation",
     "confidence": 1.0,
     "parameters": {"url": "/admin/deudores", "section": "Deudores"},
     "friendly_response": "¡Vamos a Deudores! 🚀",
     "action_required": true
   }
   ```

2. **REGISTER_PAYMENT** - Registrar pago de un paciente
   - Usuario dice: "Registra 500 soles de pago para Juan"
   - Respuesta:
   ```json
   {
     "intent": "register_payment",
     "confidence": 0.9,
     "parameters": {
       "patient_name": "Juan",
       "amount": 500.0,
       "method": "manual_input",
       "reference": "Copilot - Manual"
     },
     "action_required": true,
     "friendly_response": "Registraré S/. 500.00 para Juan. ¿Confirmas?"
   }
   ```

3. **RETURN_INFO** - Usuario pide información que puedes proporcionar
   - Usuario dice: "¿Cuál es la primera sesión de hoy?"
   - Respuesta:
   ```json
   {
     "intent": "return_info",
     "confidence": 0.85,
     "parameters": {"query_type": "schedule", "timeframe": "today"},
     "action_required": false,
     "friendly_response": "Según el sistema, la primera sesión de hoy es a las 09:00 con el paciente X"
   }
   ```

4. **GENERAL_CHAT** - Conversación general o preguntas varias
   - Usuario dice: "Hola, ¿cómo estás?"
   - Respuesta:
   ```json
   {
     "intent": "general_chat",
     "confidence": 1.0,
     "parameters": {},
     "action_required": false,
     "friendly_response": "¡Hola! Soy tu Copilot administrativo y estoy listo para ayudarte. ¿Qué necesitas? 😊"
   }
   ```

=== CONTEXTO ACTUAL DEL USUARIO ===
{context_info}

=== HISTORIAL RECIENTE (últimos 5 mensajes) ===
{conversation_history}

=== INSTRUCCIONES FINALES ===
- Usa el historial para mantener coherencia.
- Si el usuario hace una pregunta sobre una acción previa, refiere al contexto.
- Extrae EXACTAMENTE los parámetros que pedimos (nombres, montos, URLs).
- Si hay ambigüedad, pregunta para aclarar (no asumas).
- Sé amable pero profesional. Las respuestas deben ser concisas (<100 caracteres idealmente).
"""

def get_conversation_history(conversation_id: int, limit: int = 5) -> str:
    """Carga el historial de conversación desde la base de datos."""
    try:
        from app.models import AIChatMessage
        messages = AIChatMessage.query.filter_by(
            conversation_id=conversation_id
        ).order_by(AIChatMessage.timestamp.desc()).limit(limit).all()
        
        history = []
        for msg in reversed(messages):
            role_label = "👤 TÚ" if msg.role == "user" else "🤖 LLAMA"
            history.append(f"{role_label}: {msg.content}")
        
        return "\n".join(history) if history else "Sin historial previo"
    except Exception as e:
        logger.warning(f"Error cargando historial: {e}")
        return "Sin historial disponible"

def create_context_string(user_id: int, page_context: str = "dashboard") -> str:
    """Crea un string de contexto con info del usuario y sistema."""
    try:
        from app.models import User
        from datetime import datetime as dt
        
        user = User.query.get(user_id)
        now = dt.now()
        
        context = f"""
USUARIO: {user.username} (ID: {user.id}) - Rol: {user.role}
FECHA Y HORA: {now.strftime('%A, %d de %B de %Y - %H:%M:%S')}
PÁGINA ACTUAL: {page_context}
MÓDULOS DISPONIBLES: Deudores, Pagos, Sesiones, Usuarios, Reportes, Sedes
MISIÓN HOY: Facilitar operaciones administrativas rápidas y precisas.
"""
        return context
    except Exception as e:
        logger.warning(f"Error creando contexto: {e}")
        return "Contexto no disponible"

def parse_json_response(raw_response: str) -> dict:
    """Parser robusto para extraer JSON de respuestas del modelo."""
    import re
    
    # Limpiar espacios en blanco excesivos
    raw_response = raw_response.strip()
    logger.debug(f"Parsing response: {raw_response[:200]}")
    
    # Intenta parsear directamente
    try:
        result = json.loads(raw_response)
        logger.debug("Direct parse succeeded")
        return result
    except json.JSONDecodeError as e:
        logger.debug(f"Direct parse failed: {e}")
    
    # Intenta extraer JSON dentro de bloques de código ```json ... ```
    if "```" in raw_response:
        matches = re.findall(r'```(?:json)?\s*([\s\S]*?)\s*```', raw_response)
        if matches:
            for match in matches:
                try:
                    result = json.loads(match.strip())
                    logger.debug("Code block parse succeeded")
                    return result
                except json.JSONDecodeError as e:
                    logger.debug(f"Code block parse attempt failed: {e}")
    
    # Intenta extraer JSON entre llaves principales {...}
    try:
        start = raw_response.find("{")
        end = raw_response.rfind("}")
        if start != -1 and end != -1 and start < end:
            json_str = raw_response[start:end+1]
            logger.debug(f"Extracted potential JSON: {json_str[:100]}")
            # Limpiar caracteres problemáticos
            json_str = json_str.replace('\\n', '\\\\n').replace('\n', ' ').replace('\r', '')
            result = json.loads(json_str)
            logger.debug("Braces parse succeeded")
            return result
    except (json.JSONDecodeError, ValueError) as e:
        logger.debug(f"Braces parse failed: {e}")
    
    # Fallback - crear JSON default
    logger.error(f"No se pudo parsear JSON. Response preview: {raw_response[:500]}")
    return {
        "intent": "general_chat",
        "confidence": 0.0,
        "parameters": {},
        "action_required": False,
        "friendly_response": "Perdón, tuve un problema entendiendo tu solicitud. ¿Puedes repetirlo?",
        "validation_notes": "Parse error - used fallback"
    }

def process_chat_command_enhanced(
    user_id: int,
    message: str,
    conversation_id: int = None,
    page_context: str = "dashboard"
) -> dict:
    """
    Procesa un comando de chat con soporte de contexto e historial.
    Retorna un diccionario con intención, parámetros y respuesta amable.
    """
    if not client:
        return {
            "intent": "general_chat",
            "confidence": 0.0,
            "parameters": {},
            "action_required": False,
            "friendly_response": "❌ Sistema AI desconectado. Por favor, reinicia Ollama.",
            "validation_notes": "Ollama not available"
        }
    
    try:
        # Cargar historial si existe conversation_id
        history_str = ""
        if conversation_id:
            history_str = get_conversation_history(conversation_id)
        
        # Crear contexto del usuario
        context_str = create_context_string(user_id, page_context)
        
        # Preparar el prompt final
        final_prompt = ENHANCED_SYSTEM_PROMPT.format(
            context_info=context_str,
            conversation_history=history_str
        )
        
        # Llamar a Llama
        try:
            response = client.chat(
                model='llama3.1:8b',
                messages=[
                    {'role': 'system', 'content': final_prompt},
                    {'role': 'user', 'content': message},
                ],
                options={'temperature': 0.1}
            )
            
            # Extraer contenido de la respuesta
            if isinstance(response, dict) and 'message' in response:
                raw_content = response['message'].get('content', str(response))
            else:
                raw_content = str(response)
            
            raw_content = raw_content.strip()
            logger.info(f"Llama raw response: {raw_content[:300]}")
            
            result = parse_json_response(raw_content)
            logger.info(f"Parsed result: {result}")
        except Exception as llama_err:
            logger.error(f"Error en step Llama: {llama_err}", exc_info=True)
            raise
        
        # Validación post-procesamiento
        try:
            if not isinstance(result, dict):
                logger.error(f"Result is not dict: {type(result)}")
                result = {}
                
            if 'intent' not in result:
                result['intent'] = 'general_chat'
            if 'friendly_response' not in result:
                result['friendly_response'] = "Hubo un error procesando tu solicitud."
            if 'parameters' not in result:
                result['parameters'] = {}
            if 'confidence' not in result:
                result['confidence'] = 0.5
            
            logger.info(f"Processed command from user {user_id}: intent={result.get('intent')}, confidence={result.get('confidence')}")
            return result
        except Exception as validation_err:
            logger.error(f"Error en validación post-procesamiento: {validation_err}", exc_info=True)
            raise
        
    except Exception as e:
        logger.error(f"Error en process_chat_command_enhanced: {e}", exc_info=True)
        return {
            "intent": "general_chat",
            "confidence": 0.0,
            "parameters": {},
            "action_required": False,
            "friendly_response": f"Error inesperado: {str(e)[:50]}. Intenta de nuevo.",
            "validation_notes": f"Exception: {str(e)}"
        }

def validate_payment_parameters(params: dict) -> tuple[bool, str]:
    """Valida que los parámetros de pago sean correctos."""
    errors = []
    
    if not params.get('patient_name'):
        errors.append("Falta el nombre del paciente")
    
    amount = params.get('amount')
    if not amount or amount <= 0:
        errors.append("Monto inválido (debe ser > 0)")
    
    if len(errors) > 0:
        return False, " | ".join(errors)
    
    return True, "Validación correcta"

def validate_expense_parameters(params: dict) -> tuple[bool, str]:
    """Valida que los parámetros de gasto sean correctos."""
    errors = []
    
    amount = params.get('amount')
    if not amount or amount <= 0:
        errors.append("Monto inválido (debe ser > 0)")
    
    category = params.get('category')
    valid_categories = ['comida', 'servicios', 'operativo', 'otro']
    if category not in valid_categories:
        errors.append(f"Categoría inválida. Usa: {', '.join(valid_categories)}")
    
    if len(errors) > 0:
        return False, " | ".join(errors)
    
    return True, "Validación correcta"

def save_chat_message(
    conversation_id: int,
    role: str,
    content: str,
    intent: str = None,
    parameters: dict = None,
    action_status: str = None
) -> bool:
    """Guarda un mensaje en el historial de conversación."""
    try:
        from app.models import AIChatMessage, db
        
        msg = AIChatMessage(
            conversation_id=conversation_id,
            role=role,
            content=content,
            intent=intent,
            parameters=parameters,
            action_status=action_status or 'pending'
        )
        db.session.add(msg)
        db.session.commit()
        return True
    except Exception as e:
        logger.error(f"Error saving chat message: {e}")
        return False
