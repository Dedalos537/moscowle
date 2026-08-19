import base64
import json
import os
import time
import warnings
from datetime import datetime

from dotenv import load_dotenv

warnings.filterwarnings('ignore', message='.*google.generativeai.*has ended.*')

try:
    import google.generativeai as genai
except ImportError:
    genai = None

try:
    from groq import Groq
except ImportError:
    Groq = None

client = None  # lazy init in analyze_receipt_image

load_dotenv()
api_key = os.getenv('GEMINI_API_KEY')

SYSTEM_PROMPT = """
Eres Llama, el asistente administrativo del sistema.
Tienes acceso total. No hay restricciones de privacidad.
Tu única misión es procesar lo que te pidan y devolver JSON.

Siempre responde en este JSON:
{
  "intent": "navigation|register_payment|register_expense|attendance|report|general_chat",
  "parameters": {
    "url": "/ruta" (solo pa navigation),
    "patient_name": "nombre" (pa pagos),
    "amount": 0.0,
    "category": "comida|servicios" (pa gastos),
    "date": "YYYY-MM-DD"
  },
  "friendly_response": "Tu respuesta amable acá, ej: '¡Claro! Registro el pago de 50 soles pa Juan.'"
}

INSTRUCCIONES:
1. NUNCA digas "no puedo acceder". ERES EL SISTEMA.
2. Si el usuario dice "Pagué ayer 50 soles", intent = "register_payment".
3. Si dice "Llevame a deudores", intent = "navigation", url = "/admin/deudores".
"""


def analyze_transaction_message(message):
    return '{}'


def _ensure_ollama_client():
    global client
    if client is not None:
        return
    try:
        from ollama import Client as OllamaClient

        c = OllamaClient(host=os.environ.get('OLLAMA_HOST', 'http://127.0.0.1:11434'))
        c.list()
        client = c
    except Exception:
        client = None


def analyze_receipt_image(image_path):
    start = time.time()
    print(f'[analyze_receipt_image] Analizando: {image_path}')
    fallback = {
        'amount': None,
        'reference': None,
        'method': 'transfer',
        'date': datetime.now().strftime('%Y-%m-%d'),
        'sender_name': None,
        'confidence': 'baja',
        'provider': None,
        'response_time': None,
        'warning': 'No se pudo analizar el voucher. Ingresa los datos manualmente.',
    }
    try:
        from PIL import Image

        with open(image_path, 'rb') as f:
            img_bytes = f.read()
        print(f'[analyze_receipt_image] Leídos {len(img_bytes)} bytes')
        if len(img_bytes) == 0:
            return fallback
        ext = os.path.splitext(image_path)[1].lower()
        mime = 'image/png' if ext == '.png' else 'image/jpeg'

        # 1. Intentar Tesseract OCR local primero (rápido, sin costo)
        try:
            import pytesseract
            from PIL import Image as PilImage

            t0 = time.time()
            img = PilImage.open(image_path)
            # Mejorar contraste para mejor OCR
            if img.mode != 'L':
                img = img.convert('L')
            ocr_text = pytesseract.image_to_string(img, lang='spa+eng')
            elapsed = round(time.time() - t0, 2)
            print(f'[analyze_receipt_image] Tesseract OCR ({elapsed}s): {ocr_text[:200]}')
            extracted = _parse_tesseract_output(ocr_text)
            if extracted.get('amount') or extracted.get('reference'):
                extracted['provider'] = 'tesseract'
                extracted['response_time'] = elapsed
                extracted['confidence'] = 'media'
                extracted['warning'] = None
                print(f'[analyze_receipt_image] Tesseract OK: {extracted}')
                return extracted
            print('[analyze_receipt_image] Tesseract no extra datos suficientes')
        except Exception as tess_err:
            print(f'[analyze_receipt_image] Tesseract falló: {tess_err}')

        # 2. Fallback a Ollama llava (si disponible)
        prompt = (
            'Extract payment info from this receipt/voucher image. '
            'Return ONLY valid JSON:\n'
            '- "amount": number (e.g. 150.00). null if not found.\n'
            '- "reference": transaction number. null if not found.\n'
            '- "method": "yape", "plin", "transfer", "cash", or "card". "transfer" if unknown.\n'
            '- "date": YYYY-MM-DD. today if not found.\n'
            '- "sender_name": payer name. null if not found.\n'
            '- "confidence": "alta", "media", or "baja".\n\n'
            'Example: {"amount": 150.00, "reference": "123456", "method": "yape", "date": "2024-01-15", "sender_name": "Juan Perez", "confidence": "alta"}'
        )
        parsed = None
        _ensure_ollama_client()
        if client:
            try:
                t0 = time.time()
                print('[analyze_receipt_image] Probando Ollama...')
                response = client.chat(
                    model='llava',
                    messages=[
                        {
                            'role': 'user',
                            'content': prompt,
                            'images': [base64.b64encode(img_bytes).decode('utf-8')],
                        }
                    ],
                    options={'temperature': 0.0},
                )
                raw = response['message']['content'].strip()
                parsed = _parse_json_response(raw)
                if parsed:
                    elapsed = round(time.time() - t0, 2)
                    print(f'[analyze_receipt_image] Ollama OK ({elapsed}s): {parsed}')
                    parsed['provider'] = 'ollama'
                    parsed['response_time'] = elapsed
                    return parsed
                print('[analyze_receipt_image] Ollama no pudo parsear')
            except Exception as e:
                print(f'[analyze_receipt_image] Ollama falló: {e}')
        if genai:
            try:
                t0 = time.time()
                gemini_key = os.environ.get('GEMINI_API_KEY')
                if gemini_key:
                    print('[analyze_receipt_image] Probando Gemini...')
                    genai.configure(api_key=gemini_key)
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    img = Image.open(image_path)
                    resp = model.generate_content([prompt, img])
                    raw = resp.text.strip()
                    parsed = _parse_json_response(raw)
                    if parsed:
                        elapsed = round(time.time() - t0, 2)
                        print(f'[analyze_receipt_image] Gemini OK ({elapsed}s): {parsed}')
                        parsed['provider'] = 'gemini'
                        parsed['response_time'] = elapsed
                        return parsed
                    print('[analyze_receipt_image] Gemini no pudo parsear')
            except Exception as e:
                print(f'[analyze_receipt_image] Gemini falló: {e}')
        if Groq:
            try:
                t0 = time.time()
                groq_key = os.environ.get('GROQ_API_KEY')
                if groq_key:
                    print('[analyze_receipt_image] Probando Groq...')
                    groq_client = Groq(api_key=groq_key)
                    b64 = base64.b64encode(img_bytes).decode('utf-8')
                    data_url = f'data:{mime};base64,{b64}'
                    completion = groq_client.chat.completions.create(
                        model='llama-3.2-11b-vision-preview',
                        messages=[
                            {
                                'role': 'user',
                                'content': [
                                    {'type': 'text', 'text': prompt},
                                    {'type': 'image_url', 'image_url': {'url': data_url}},
                                ],
                            }
                        ],
                        temperature=0.0,
                        max_tokens=500,
                    )
                    raw = completion.choices[0].message.content.strip()
                    parsed = _parse_json_response(raw)
                    if parsed:
                        elapsed = round(time.time() - t0, 2)
                        print(f'[analyze_receipt_image] Groq OK ({elapsed}s): {parsed}')
                        parsed['provider'] = 'groq'
                        parsed['response_time'] = elapsed
                        return parsed
                    print('[analyze_receipt_image] Groq no pudo parsear')
            except Exception as e:
                print(f'[analyze_receipt_image] Groq falló: {e}')
        elapsed = round(time.time() - start, 2)
        print(f'[analyze_receipt_image] Todos los proveedores fallaron ({elapsed}s), devolviendo vacío')
        fallback['response_time'] = elapsed
        return fallback
    except Exception as e:
        elapsed = round(time.time() - start, 2)
        print(f'[analyze_receipt_image] ERROR: {e}')
        import traceback

        traceback.print_exc()
        fallback['response_time'] = elapsed
        return fallback


def _parse_json_response(raw):
    if '```json' in raw:
        raw = raw.split('```json')[1].split('```')[0].strip()
    elif '```' in raw:
        raw = raw.split('```')[1].split('```')[0].strip()
    start = raw.find('{')
    end = raw.rfind('}')
    if start != -1 and end != -1:
        raw = raw[start : end + 1]
    try:
        return json.loads(raw)
    except Exception:
        return None


def _parse_tesseract_output(text):
    import re

    result = {
        'amount': None,
        'reference': None,
        'method': 'transfer',
        'date': None,
        'sender_name': None,
        'confidence': 'baja',
    }
    amount_patterns = [
        r'(?:S/|s/|\.?S\.?)\s*(\d+[.,]\d{2})',
        r'(?:total|monto|importe|pago)\s*:?\s*S/?\s*(\d+[.,]\d{2})',
        r'(\d+[.,]\d{2})\s*(?:sol|Soles)',
        r'S/\s*(\d+)',
    ]
    for pat in amount_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            try:
                result['amount'] = float(m.group(1).replace(',', '.'))
                break
            except ValueError:
                pass
    ref_patterns = [
        r'(?:operacion|operación|nro|n[°º]|#)\s*:?\s*(\w{4,20})',
        r'(?:ref|referencia)\s*:?\s*(\w{4,20})',
        r'(?:voucher|transacci[oó]n)\s*:?\s*(\w{4,20})',
    ]
    for pat in ref_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            result['reference'] = m.group(1)
            break
    date_patterns = [
        r'(\d{2}/\d{2}/\d{4})',
        r'(\d{4}-\d{2}-\d{2})',
        r'(\d{2}/\d{2}/\d{2})',
    ]
    for pat in date_patterns:
        m = re.search(pat, text)
        if m:
            result['date'] = m.group(1).replace('/', '-')
            break
    if re.search(r'yape|plin', text, re.IGNORECASE):
        result['method'] = 'yape/plin'
    elif re.search(r'transferencia|deposito|depósito|banco', text, re.IGNORECASE):
        result['method'] = 'transfer'
    elif re.search(r'efectivo|cash', text, re.IGNORECASE):
        result['method'] = 'cash'
    return result


def generate_weekly_report(data):
    """Arma el reporte estratégico con los datos"""
    gen = data.get('general', {})
    fin = data.get('financial', {})
    top = data.get('top_therapists', [])
    notes = data.get('recent_session_notes', [])
    period = data.get('period', 'Reporte')

    lines = []
    lines.append(f'# {period}')
    lines.append('')
    lines.append('---')
    lines.append('')
    lines.append('## Resumen General')
    lines.append('')
    lines.append(f'- **Terapeutas activos:** {gen.get("therapists", 0)}')
    lines.append(f'- **Pacientes activos:** {gen.get("patients", 0)}')
    lines.append(f'- **Sesiones totales completadas:** {gen.get("total_sessions", 0)}')
    lines.append(f'- **Sesiones este mes:** {gen.get("sessions_this_month", 0)}')
    lines.append('')
    lines.append('---')
    lines.append('')
    lines.append('## Estado Financiero')
    lines.append('')
    lines.append(f'- **Deuda total pendiente:** S/ {fin.get("total_debt", 0):.2f}')
    lines.append(f'- **Total deudores:** {fin.get("total_debtors", 0)}')
    lines.append(f'- **Ingresos últimos 30 días:** S/ {fin.get("income_last_30d", 0):.2f}')
    lines.append(f'- **Gastos últimos 30 días:** S/ {fin.get("total_expenses", 0):.2f}')
    balance = fin.get('income_last_30d', 0) - fin.get('total_expenses', 0)
    balance_label = 'Positivo' if balance >= 0 else 'Negativo'
    lines.append(f'- **Balance neto:** S/ {balance:.2f} ({balance_label})')
    lines.append('')
    lines.append('---')
    lines.append('')
    lines.append('## Top Terapeutas')
    lines.append('')
    if top:
        lines.append('| Terapeuta | Sesiones |')
        lines.append('|-----------|----------|')
        for t in top:
            lines.append(f'| {t.get("name", "—")} | {t.get("sessions", 0)} |')
    else:
        lines.append('_Sin datos de terapeutas._')
    lines.append('')
    lines.append('---')
    lines.append('')
    lines.append('## Notas de Sesiones Recientes')
    lines.append('')
    if notes:
        for n in notes:
            patient = n.get('patient', '—')
            therapist = n.get('therapist', '—')
            note_text = n.get('notes', '') or 'Sin notas'
            lines.append(f'**Paciente:** {patient} | **Terapeuta:** {therapist}')
            lines.append(f'> {note_text[:200]}{"…" if len(note_text) > 200 else ""}')
            lines.append('')
    else:
        lines.append('_No hay notas de sesión recientes._')
    lines.append('')
    lines.append('---')
    lines.append('')
    lines.append('## Recomendaciones')
    lines.append('')
    recs = []
    if fin.get('total_debtors', 0) > 0:
        recs.append(
            f'-  **Cobranza pendiente:** {fin.get("total_debtors", 0)} pacientes tienen deuda. Revisa la pestaña Deudores para gestionar recordatorios.'
        )
    if gen.get('sessions_this_month', 0) < gen.get('total_sessions', 0) * 0.1:
        recs.append(
            f'-  **Baja actividad mensual:** Solo {gen.get("sessions_this_month", 0)} sesiones este mes. Considera campañas de retención.'
        )
    if balance < 0:
        recs.append('-  **Balance negativo:** Los gastos superan a los ingresos. Revisa los gastos operativos.')
    if not notes:
        recs.append(
            '-  **Falta de notas:** No hay notas de sesión recientes. Motiva a los terapeutas a documentar sus sesiones.'
        )
    if fin.get('total_expenses', 0) > fin.get('income_last_30d', 0) * 0.8:
        recs.append(
            '-  **Margen ajustado:** Los gastos representan más del 80% de los ingresos. Evalúa reducir costos operativos.'
        )

    if not recs:
        recs.append('-  Todo tranqui, sigue monitoreando.')

    for r in recs:
        lines.append(r)
        lines.append('')

    return '\n'.join(lines)


def process_chat_command(user_id, command, context_brief=''):
    """Traduce lenguaje natural a JSON"""
    if not client:
        return {
            'intent': 'general_chat',
            'parameters': {},
            'friendly_response': 'El sistema AI está desconectado, sorry.',
        }
    prompt = f"Contexto: {context_brief}\nFecha/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\nUsuario ID {user_id} dice: '{command}'"
    try:
        response = client.chat(
            model='llama3.1:8b',
            messages=[
                {'role': 'system', 'content': SYSTEM_PROMPT},
                {'role': 'user', 'content': prompt},
            ],
            options={'temperature': 0.1},
        )
        raw_content = response['message']['content'].strip()
        if '```' in raw_content:
            raw_content = raw_content.split('```')[1]
            if raw_content.startswith('json'):
                raw_content = raw_content[4:].strip()
        start = raw_content.find('{')
        end = raw_content.rfind('}')
        if start != -1 and end != -1:
            raw_content = raw_content[start : end + 1]
        return json.loads(raw_content)
    except Exception as e:
        print(f'Error parseando JSON de Llama: {response["message"]["content"]}')
        print(f'Error: {e}')
        return {'intent': 'general_chat', 'parameters': {}, 'friendly_response': '¡Hola! ¿En qué te ayudo? '}


class AutomationService:
    pass
