from flask import Blueprint, request, jsonify, current_app, url_for
from flask_login import login_required, current_user
from app.models import db, User, Notification, Appointment, Message, Game, SessionMetrics, SessionImage, ContactMessage, Sede, Payment
from app.services.appointment_service import AppointmentService
from app.services.game_service import GameService
from app.services.admin_service import AdminService
from app.services.notification_service import NotificationService
from app.services.patient_service import PatientService
from app.services.dashboard_service import DashboardService
from app.services.report_service import ReportService
import json, os, time, warnings
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
    _ollama_client = ollama.Client(host='http://127.0.0.1:11434')
    _ollama_client.list()
except Exception:
    _ollama_client = None
from app.services.google_drive_service import GoogleDriveService
from app.services.ai_service import predict_level, start_async_training
from app.utils import get_user_today_utc_range, get_user_now, localize_datetime_for_display, get_user_timezone
from app.schemas import AssignTherapistSchema, UpdateUserSchema, SendMessageSchema
from app.extensions import bcrypt, limiter, csrf
from app.services.email_service import EmailService
from app.services.financial_service import FinancialService
from app.utils.api_helpers import api_response
from app.services.availability_service import AvailabilityService
from datetime import datetime, timedelta, timezone
import uuid
from werkzeug.utils import secure_filename
import requests
from sqlalchemy import or_, func

appointment_service = AppointmentService()
game_service = GameService()
admin_service = AdminService()
notification_service = NotificationService()
patient_service = PatientService()
dashboard_service = DashboardService()
report_service = ReportService()
drive_service = GoogleDriveService()
fs = FinancialService()

LIMA_TZ = timezone(timedelta(hours=-5))


def _parse_json(raw):
    if '```json' in raw: raw = raw.split('```json')[1].split('```')[0]
    elif '```' in raw: raw = raw.split('```')[1].split('```')[0]
    start = raw.find('{'); end = raw.rfind('}')
    if start != -1 and end != -1: raw = raw[start:end+1]
    try: return json.loads(raw)
    except Exception: return None


def _parse_datetime(value):
    if not value:
        return None
    try:
        if value.endswith('Z'):
            value = value[:-1] + '+00:00'
        dt = datetime.fromisoformat(value)
        if dt.tzinfo:
            return dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt.replace(tzinfo=LIMA_TZ).astimezone(timezone.utc).replace(tzinfo=None)
    except Exception:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(value, fmt)
                return dt.replace(tzinfo=LIMA_TZ).astimezone(timezone.utc).replace(tzinfo=None)
            except Exception:
                continue
    return None


def analyze_contact_message_ai(name, email, message, service_interest):
    result = {'sentiment': 'neutral', 'detected_intent': 'consulta', 'suggested_response': '', 'confidence': 'media', 'provider': None}
    prompt = f"""Analiza este mensaje de contacto de un cliente potencial y responde SOLO con JSON válido:
Nombre: {name}
Email: {email}
Mensaje: {message}
Servicio de interés: {service_interest or 'No especificado'}
Responde con este JSON exacto (sin markdown):
{{"sentiment": "positivo"|"neutral"|"negativo", "detected_intent": "agendar_cita"|"informacion"|"consulta"|"queja"|"seguimiento", "suggested_response": "texto cortés de respuesta sugerida", "confidence": "alta"|"media"|"baja"}}"""
    providers = []
    if _ollama_client:
        providers.append(('ollama', lambda: _ollama_client.chat(model='llama3.2', messages=[{'role': 'user', 'content': prompt}], options={'temperature': 0.0})['message']['content']))
    if genai and os.environ.get('GEMINI_API_KEY'):
        providers.append(('gemini', lambda: (genai.configure(api_key=os.environ['GEMINI_API_KEY']), genai.GenerativeModel('gemini-1.5-flash').generate_content(prompt).text)[1]))
    if Groq and os.environ.get('GROQ_API_KEY'):
        providers.append(('groq', lambda: Groq(api_key=os.environ['GROQ_API_KEY']).chat.completions.create(model='llama-3.2-3b-preview', messages=[{'role': 'user', 'content': prompt}], temperature=0.0, max_tokens=300).choices[0].message.content))
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
