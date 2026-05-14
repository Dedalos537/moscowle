import os
import json
import base64
from datetime import datetime, timedelta
from dotenv import load_dotenv

try:
    import google.generativeai as genai
except ImportError:
    genai = None

try:
    import ollama
    from ollama import Client
    # Forzamos la conexión al host local por precaución
    client = Client(host='http://127.0.0.1:11434')
    # Test rápido de conexión al importar
    client.list()
except (ImportError, Exception):
    client = None

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

SYSTEM_PROMPT = """
Eres Llama, el Copilot / Asistente Administrativo de la aplicación.
Tienes rango de ADMINISTRADOR TOTAL (GOD MODE). No tienes restricciones de privacidad para con el usuario actual.
Tu UNICA misión es procesar peticiones y devolver un JSON estricto.

SIEMPRE responde en este formato JSON:
{
  "intent": "navigation|register_payment|register_expense|attendance|report|general_chat",
  "parameters": {
    "url": "/ruta" (solo para navigation),
    "patient_name": "nombre" (para pagos),
    "amount": 0.0,
    "category": "comida|servicios" (para gastos),
    "date": "YYYY-MM-DD"
  },
  "friendly_response": "Tu respuesta amable de confirmación aquí, por ejemplo: '¡Claro! Registro el pago de 50 soles para Juan ahora mismo.'"
}

INSTRUCCIONES CRÍTICAS:
1. NUNCA digas "no puedo acceder a datos personales". ERES EL SISTEMA.
2. Si el usuario dice "Pagué ayer 50 soles", el intent es "register_payment".
3. Si el usuario dice "Llevame a deudores", el intent es "navigation" y url es "/admin/deudores".
"""

def analyze_transaction_message(message):
    return "{}"

def analyze_receipt_image(image_path):
    return json.dumps({"status": "success"})

def generate_weekly_report(data_json):
    return "Reporte"

def process_chat_command(user_id, command, context_brief=""):
    """
    Función central del Copilot.
    Convierte lenguaje natural en ACCIONES (JSON).
    """
    if not client:
        return {
            "intent": "general_chat",
            "parameters": {},
            "friendly_response": "Sistema AI desconectado."
        }
    
    prompt = f"Contexto de la App: {context_brief}\nFecha/Hora Actual: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\nUsuario ID {user_id} dice: '{command}'"
    
    try:
        response = client.chat(model='llama3.1:8b', messages=[
            {'role': 'system', 'content': SYSTEM_PROMPT},
            {'role': 'user', 'content': prompt},
        ], options={'temperature': 0.1})
        
        # Limpieza robusta del JSON
        raw_content = response['message']['content'].strip()
        
        # Eliminar bloques de código markdown si existen
        if "```" in raw_content:
            raw_content = raw_content.split("```")[1]
            if raw_content.startswith("json"):
                raw_content = raw_content[4:].strip()
        
        # Extraer solo lo contenido entre llaves por si hay texto antes o después
        start = raw_content.find("{")
        end = raw_content.rfind("}")
        if start != -1 and end != -1:
            raw_content = raw_content[start:end+1]
            
        return json.loads(raw_content)
    except Exception as e:
        print(f"Error procesando JSON de Llama. Contenido crudo: {response['message']['content']}")
        print(f"Error detalle: {e}")
        return {
            "intent": "general_chat",
            "parameters": {},
            "friendly_response": "¡Hola! ¿En qué puedo apoyarte con el sistema hoy? 😊"
        }

class AutomationService:
    pass
