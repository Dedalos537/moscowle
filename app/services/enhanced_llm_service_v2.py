"""Servicio simplificado de Llama"""
import json, logging
from dotenv import load_dotenv

try:
    import ollama
    client = ollama.Client(host='http://127.0.0.1:11434')
except:
    client = None

load_dotenv()
logger = logging.getLogger('app')

PROMPT = """Eres Llama, asistente administrativo. RESPONDE SOLO EN JSON.
Estructura: {{"intent": "tipo", "response": "msg", "parameters": {{}}}}
Intenciones: general_chat|navigation|register_payment|return_info
Usuario: {context_info}
Historial: {conversation_history}
SOLO JSON."""

def get_conversation_history(cid, limit=5):
    try:
        from app.models import AIChatMessage
        msgs = AIChatMessage.query.filter_by(conversation_id=cid).order_by(AIChatMessage.timestamp.desc()).limit(limit).all()
        return "\\n".join([f"{'USER' if m.role=='user' else 'LLAMA'}: {m.content}" for m in reversed(msgs)]) if msgs else "Sin historial"
    except:
        return "Sin historial"

def create_context_string(uid, pg="dashboard"):
    try:
        from app.models import User
        return User.query.get(uid).username
    except:
        return "unknown"

def parse_json_response(raw):
    """Parse JSON response, with fallback strategy"""
    if not raw:
        return {"intent": "general_chat", "response": "Sin respuesta", "parameters": {}}
    
    raw = str(raw).strip()
    logger.debug(f"Parse: {raw[:100]}")
    
    # Try 1: Direct parse
    try:
        return json.loads(raw)
    except Exception as e1:
        logger.debug(f"Direct parse failed: {e1}")
    
    # Try 2: Extract JSON from text
    try:
        start, end = raw.find("{"), raw.rfind("}")
        if start != -1 and end != -1:
            return json.loads(raw[start:end+1])
    except Exception as e2:
        logger.debug(f"Extract parse failed: {e2}")
    
    # Fallback: Return safe default
    logger.error(f"JSON parse failed: {raw[:200]}")
    return {"intent": "general_chat", "response": "Intenta de nuevo.", "parameters": {}}

def process_chat_command_enhanced(uid, msg, cid=None, pg="dashboard"):
    if not client:
        return {"intent": "general_chat", "response": "AI offline", "parameters": {}}
    try:
        hist = get_conversation_history(cid) if cid else ""
        ctx = create_context_string(uid, pg)
        prompt = PROMPT.format(context_info=ctx, conversation_history=hist)
        logger.info(f"Send: {msg[:50]}")
        resp = client.chat(model='llama3.1:8b', messages=[{'role': 'system', 'content': prompt}, {'role': 'user', 'content': msg}], options={'temperature': 0.1})
        raw = resp['message'].get('content', '')
        logger.info(f"Resp: {raw[:100]}")
        result = parse_json_response(raw)
        
        # Ensure result is a dict
        if not isinstance(result, dict):
            logger.error(f"parse_json_response returned non-dict: {type(result)}")
            result = {"intent": "general_chat", "response": str(result), "parameters": {}}
        
        result.setdefault('intent', 'general_chat')
        result.setdefault('response', 'OK')
        result.setdefault('parameters', {})
        result['confidence'] = 0.9
        return result
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return {"intent": "general_chat", "response": f"Error: {str(e)[:40]}", "parameters": {}}

def validate_payment_parameters(p):
    name = p.get('patient_name', '').strip()
    if not name: return False, "Falta nombre"
    try:
        amt = float(p.get('amount', 0))
        return (True, "OK") if amt > 0 else (False, "Monto > 0")
    except:
        return False, "Monto inválido"

def validate_expense_parameters(p):
    cat = p.get('category', '').strip()
    if not cat: return False, "Falta categoría"
    try:
        amt = float(p.get('amount', 0))
        return (True, "OK") if amt > 0 else (False, "Monto > 0")
    except:
        return False, "Monto inválido"

def save_chat_message(cid, role, content, intent=None, parameters=None, action_status='pending'):
    try:
        from app.extensions import db
        from app.models import AIChatMessage
        msg = AIChatMessage(conversation_id=cid, role=role, content=content, intent=intent, parameters=json.dumps(parameters or {}), action_status=action_status)
        db.session.add(msg)
        db.session.commit()
        logger.info(f"Saved: {role} - {content[:30]}")
    except Exception as e:
        logger.error(f"Save error: {e}")
