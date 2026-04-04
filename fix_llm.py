import os
content = r"""import os
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
except ImportError:
    ollama = None

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

SYSTEM_PROMPT = "Eres Llama, el Asistente Administrativo. Responde siempre JSON."

def analyze_transaction_message(message):
    return "{}"

def analyze_receipt_image(image_path):
    return json.dumps({"status": "success"})

def generate_weekly_report(data_json):
    return "Reporte"

def process_chat_command(user_id, command, context_brief=""):
    return {"intent": "general_chat", "friendly_response": "Prueba"}

class AutomationService:
    pass
"""
with open("/Users/apple/Documents/moscowle_ia_mvp/app/services/llm_automation_service.py", "w") as f:
    f.write(content)
