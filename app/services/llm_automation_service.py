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

def generate_weekly_report(data):
    """
    Generate a strategic report from comprehensive data.
    data dict expects keys: period, general (therapists, patients, total_sessions, sessions_this_month),
    financial (total_debt, total_debtors, income_last_30d, total_expenses),
    top_therapists, recent_session_notes.
    """
    gen = data.get('general', {})
    fin = data.get('financial', {})
    top = data.get('top_therapists', [])
    notes = data.get('recent_session_notes', [])
    period = data.get('period', 'Reporte')

    lines = []
    lines.append(f"# {period}")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Resumen General")
    lines.append("")
    lines.append(f"- **Terapeutas activos:** {gen.get('therapists', 0)}")
    lines.append(f"- **Pacientes activos:** {gen.get('patients', 0)}")
    lines.append(f"- **Sesiones totales completadas:** {gen.get('total_sessions', 0)}")
    lines.append(f"- **Sesiones este mes:** {gen.get('sessions_this_month', 0)}")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Estado Financiero")
    lines.append("")
    lines.append(f"- **Deuda total pendiente:** S/ {fin.get('total_debt', 0):.2f}")
    lines.append(f"- **Total deudores:** {fin.get('total_debtors', 0)}")
    lines.append(f"- **Ingresos últimos 30 días:** S/ {fin.get('income_last_30d', 0):.2f}")
    lines.append(f"- **Gastos últimos 30 días:** S/ {fin.get('total_expenses', 0):.2f}")
    balance = fin.get('income_last_30d', 0) - fin.get('total_expenses', 0)
    balance_label = "Positivo" if balance >= 0 else "Negativo"
    lines.append(f"- **Balance neto:** S/ {balance:.2f} ({balance_label})")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Top Terapeutas")
    lines.append("")
    if top:
        lines.append("| Terapeuta | Sesiones |")
        lines.append("|-----------|----------|")
        for t in top:
            lines.append(f"| {t.get('name', '—')} | {t.get('sessions', 0)} |")
    else:
        lines.append("_Sin datos de terapeutas._")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Notas de Sesiones Recientes")
    lines.append("")
    if notes:
        for n in notes:
            patient = n.get('patient', '—')
            therapist = n.get('therapist', '—')
            note_text = n.get('notes', '') or 'Sin notas'
            lines.append(f"**Paciente:** {patient} | **Terapeuta:** {therapist}")
            lines.append(f"> {note_text[:200]}{'…' if len(note_text) > 200 else ''}")
            lines.append("")
    else:
        lines.append("_No hay notas de sesión recientes._")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Recomendaciones")
    lines.append("")
    recs = []
    if fin.get('total_debtors', 0) > 0:
        recs.append(f"- 🔴 **Cobranza pendiente:** {fin.get('total_debtors', 0)} pacientes tienen deuda. Revisa la pestaña Deudores para gestionar recordatorios.")
    if gen.get('sessions_this_month', 0) < gen.get('total_sessions', 0) * 0.1:
        recs.append(f"- 📉 **Baja actividad mensual:** Solo {gen.get('sessions_this_month', 0)} sesiones este mes. Considera campañas de retención.")
    if balance < 0:
        recs.append(f"- ⚠️ **Balance negativo:** Los gastos superan a los ingresos. Revisa los gastos operativos.")
    if not notes:
        recs.append("- 📝 **Falta de notas:** No hay notas de sesión recientes. Motiva a los terapeutas a documentar sus sesiones.")
    if fin.get('total_expenses', 0) > fin.get('income_last_30d', 0) * 0.8:
        recs.append("- 💰 **Margen ajustado:** Los gastos representan más del 80% de los ingresos. Evalúa reducir costos operativos.")

    if not recs:
        recs.append("- ✅ Todo en orden. Sigue monitoreando los indicadores clave.")

    for r in recs:
        lines.append(r)
        lines.append("")

    return "\n".join(lines)

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
