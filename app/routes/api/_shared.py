import json
import os
import time
import warnings

from app.services.admin_service import AdminService
from app.services.appointment_service import AppointmentService
from app.services.dashboard_service import DashboardService
from app.services.game_service import GameService
from app.services.notification_service import NotificationService
from app.services.patient_service import PatientService
from app.services.report_service import ReportService
from app.utils import parse_datetime
from app.utils.sanitizer import sanitize_for_prompt

warnings.filterwarnings('ignore', message='.*google.generativeai.*ended.*')
try:
    import google.generativeai as genai
except ImportError:
    genai = None
try:
    from groq import Groq
except ImportError:
    Groq = None
try:
    import ollama

    _ollama_client = ollama.Client(host=os.environ.get('OLLAMA_HOST', 'http://127.0.0.1:11434'))
    _ollama_client.list()
except Exception:
    _ollama_client = None
try:
    from openai import OpenAI as _OpenAI

    _glm_client = None
    if os.environ.get('GLM_API_KEY'):
        _glm_client = _OpenAI(
            base_url='https://integrate.api.nvidia.com/v1',
            api_key=os.environ['GLM_API_KEY'],
        )
except Exception:
    _glm_client = None

from app.services.financial_service import FinancialService

try:
    from app.services.ai_service import predict_level, start_async_training
except ImportError:
    predict_level = None
    start_async_training = None

appointment_service = AppointmentService()
game_service = GameService()
admin_service = AdminService()
notification_service = NotificationService()
patient_service = PatientService()
dashboard_service = DashboardService()
report_service = ReportService()
fs = FinancialService()

_drive_service = None


def _get_drive_service():
    global _drive_service
    if _drive_service is None:
        from app.services.google_drive_service import GoogleDriveService

        _drive_service = GoogleDriveService()
    return _drive_service


class _DriveProxy:
    def __getattr__(self, name):
        return getattr(_get_drive_service(), name)


drive_service = _DriveProxy()


def _parse_json(raw):
    if '```json' in raw:
        raw = raw.split('```json')[1].split('```')[0]
    elif '```' in raw:
        raw = raw.split('```')[1].split('```')[0]
    start = raw.find('{')
    end = raw.rfind('}')
    if start != -1 and end != -1:
        raw = raw[start : end + 1]
    try:
        return json.loads(raw)
    except Exception:
        return None


_parse_datetime = parse_datetime


def analyze_contact_message_ai(name, email, message, service_interest):
    result = {
        'sentiment': 'neutral',
        'detected_intent': 'consulta',
        'suggested_response': '',
        'confidence': 'media',
        'provider': None,
    }
    prompt = f"""Analiza este mensaje de contacto de un cliente potencial y responde SOLO con JSON válido:
Nombre: {sanitize_for_prompt(name)}
Email: {sanitize_for_prompt(email)}
Mensaje: {sanitize_for_prompt(message)}
Servicio de interés: {sanitize_for_prompt(service_interest or 'No especificado')}
Responde con este JSON exacto (sin markdown):
{{"sentiment": "positivo"|"neutral"|"negativo", "detected_intent": "agendar_cita"|"informacion"|"consulta"|"queja"|"seguimiento", "suggested_response": "texto cortés de respuesta sugerida", "confidence": "alta"|"media"|"baja"}}"""
    providers = []
    if _glm_client:
        providers.append(
            (
                'glm',
                lambda: (
                    _glm_client.chat.completions.create(
                        model='z-ai/glm-5.2',
                        messages=[{'role': 'user', 'content': prompt}],
                        temperature=0.0,
                        max_tokens=300,
                    )
                    .choices[0]
                    .message.content
                ),
            )
        )
    if _ollama_client:
        providers.append(
            (
                'ollama',
                lambda: _ollama_client.chat(
                    model='llama3.2', messages=[{'role': 'user', 'content': prompt}], options={'temperature': 0.0}
                )['message']['content'],
            )
        )
    if genai and os.environ.get('GEMINI_API_KEY'):
        providers.append(
            (
                'gemini',
                lambda: (
                    genai.configure(api_key=os.environ['GEMINI_API_KEY']),
                    genai.GenerativeModel('gemini-1.5-flash').generate_content(prompt).text,
                )[1],
            )
        )
    if Groq and os.environ.get('GROQ_API_KEY'):
        providers.append(
            (
                'groq',
                lambda: (
                    Groq(api_key=os.environ['GROQ_API_KEY'])
                    .chat.completions.create(
                        model='llama-3.2-3b-preview',
                        messages=[{'role': 'user', 'content': prompt}],
                        temperature=0.0,
                        max_tokens=300,
                    )
                    .choices[0]
                    .message.content
                ),
            )
        )
    for name, fn in providers:
        try:
            t0 = time.time()
            raw = fn()
            parsed = _parse_json(raw)
            if parsed:
                parsed['provider'] = name
                parsed['response_time'] = round(time.time() - t0, 2)
                result.update(parsed)
                break
        except Exception:
            continue
    return json.dumps(result, ensure_ascii=False)
