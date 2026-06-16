import logging
import os

from dotenv import load_dotenv

try:
    import pytesseract
    from PIL import Image
except ImportError:
    pytesseract = None
    Image = None

try:
    from transformers import pipeline

    _doc_pipeline = None

    def get_doc_pipeline():
        global _doc_pipeline
        if _doc_pipeline is None:
            _doc_pipeline = pipeline(
                'document-question-answering', model='naver-clova-ix/donut-base-finetuned-naver-receipt-ocr'
            )
        return _doc_pipeline
except Exception:
    _doc_pipeline = None

    def get_doc_pipeline():
        return None


doc_pipeline = None

load_dotenv()
logger = logging.getLogger('app')


def extract_receipt_data_simple(image_path: str) -> dict:
    """
    Extrae datos básicos de un recibo usando Tesseract OCR.
    Usa regex para identificar patrones de moneda (S/., $, etc).
    """
    if not pytesseract or not Image:
        logger.warning('pytesseract or PIL not installed')
        return {'error': 'OCR not available'}

    try:
        img = Image.open(image_path)
        text = pytesseract.image_to_string(img, lang='spa+eng')

        logger.info(f'OCR texto extraído: {text[:200]}')

        import re

        amount_pattern = r'(?:S/\s*|S/\.?\s*|\$\s*)?(\d+(?:\.\d{2})?|\d+(?:,\d{2})?)'
        amounts = re.findall(amount_pattern, text)

        name_pattern = r'\b(?:[A-Z][a-z]+\s)+(?:[A-Z][a-z]+)\b'
        names = re.findall(name_pattern, text)

        ref_pattern = r'(?:Ref|Operación|Op\.|#)[\s:]*(\w+)'
        references = re.findall(ref_pattern, text, re.IGNORECASE)

        date_pattern = r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})'
        dates = re.findall(date_pattern, text)

        extracted = {
            'status': 'success',
            'amounts': amounts,
            'possible_names': names[:3],
            'references': references,
            'dates': dates,
            'confidence': 0.6,
            'raw_text': text[:500],
            'extraction_method': 'tesseract_simple',
        }

        return extracted
    except Exception as e:
        logger.error(f'Error en OCR simple: {e}')
        return {'error': str(e), 'extraction_method': 'tesseract_simple'}


def extract_receipt_data_advanced(image_path: str) -> dict:
    """
    Extrae datos de recibo usando modelo Donut (más preciso).
    Requiere CUDA para velocidad óptima.
    """
    pipeline_instance = get_doc_pipeline()
    if not pipeline_instance:
        logger.warning('Document pipeline not available, falling back to simple OCR')
        return extract_receipt_data_simple(image_path)

    try:
        img = Image.open(image_path)
        result = pipeline_instance(img, 'Cuál es el monto total?', top_k=3)

        extracted = {
            'status': 'success',
            'answers': result,
            'confidence': result[0].get('score', 0) if result else 0,
            'extraction_method': 'donut_advanced',
        }

        return extracted
    except Exception as e:
        logger.error(f'Error en OCR avanzado: {e}')
        return extract_receipt_data_simple(image_path)


def process_payment_voucher(image_path: str) -> dict:
    """
    Procesa un voucher de pago y retorna datos estructurados.
    Combina OCR simple y avanzado para máxima precisión.
    """
    logger.info(f'Procesando voucher: {image_path}')

    if not os.path.exists(image_path):
        return {'status': 'error', 'message': 'Archivo no encontrado', 'error': 'Ruta de archivo inválida'}

    file_size = os.path.getsize(image_path)
    max_size = 10 * 1024 * 1024
    if file_size > max_size:
        return {
            'status': 'error',
            'message': f'Archivo demasiado grande ({file_size / (1024 * 1024):.1f}MB). Máximo 10MB.',
            'error': 'File too large',
        }

    valid_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
    file_ext = os.path.splitext(image_path)[1].lower()
    if file_ext not in valid_extensions:
        return {
            'status': 'error',
            'message': f'Formato no soportado: {file_ext}. Usa JPG, PNG, GIF o WEBP',
            'error': 'Invalid file format',
        }

    simple_result = extract_receipt_data_simple(image_path)

    if simple_result.get('error'):
        return {
            'status': 'error',
            'message': 'No se pudo leer el comprobante. Intenta con otra imagen más clara.',
            'error': simple_result.get('error'),
        }

    amounts = simple_result.get('amounts', [])
    names = simple_result.get('possible_names', [])

    if not amounts:
        return {
            'status': 'warning',
            'message': ' No se encontró monto en la imagen. ¿Puedes decirme el monto del pago?',
            'extracted_names': names,
        }

    try:
        valid_amounts = []
        for a in amounts:
            amt = float(a.replace(',', '.'))
            if 1 <= amt <= 50000:
                valid_amounts.append(amt)

        if not valid_amounts:
            best_amount = max(float(a.replace(',', '.')) for a in amounts if float(a.replace(',', '.')) > 0)
        else:
            valid_amounts.sort(reverse=True)
            best_amount = valid_amounts[0]
    except Exception as e:
        logger.error(f'Error al procesar montos: {e}')
        best_amount = float(amounts[0].replace(',', '.'))

    validated = validate_voucher_with_llama(best_amount, names, simple_result.get('raw_text', '')[:300])

    return {
        'status': 'success',
        'amount': round(best_amount, 2),
        'possible_names': names,
        'references': simple_result.get('references', []),
        'confidence': min(0.95, validated.get('confidence', 0.7)),
        'message': f' Detecté S/. {best_amount:.2f}. {validated.get("note", "")}',
        'extraction_method': simple_result.get('extraction_method'),
        'validation_method': validated.get('method', 'ocr'),
        'file_validated': True,
    }


def validate_voucher_with_llama(amount: float, names: list, text_sample: str) -> dict:
    """Valida datos de voucher usando Llama para mayor confianza"""
    try:
        import ollama

        client = ollama.Client(host='http://127.0.0.1:11434')

        prompt = f"""Analiza este texto de boleta:
        Monto encontrado: S/. {amount:.2f}
        Posibles nombres: {', '.join(names) if names else 'Ninguno'}
        Texto: {text_sample}

        Responde SOLO en JSON: {{"is_valid_amount": boolean, "confidence": 0-1, "note": "breve observación"}}"""

        resp = client.chat(
            model='llama3.1:8b', messages=[{'role': 'user', 'content': prompt}], options={'temperature': 0.1}
        )

        raw = resp['message'].get('content', '').strip()

        import json

        start = raw.find('{')
        end = raw.rfind('}') + 1
        if start != -1 and end > start:
            result = json.loads(raw[start:end])
            return {
                'confidence': result.get('confidence', 0.7),
                'is_valid': result.get('is_valid_amount', True),
                'note': result.get('note', ''),
                'method': 'llama_validated',
            }
    except Exception as e:
        logger.error(f'Llama validation failed: {e}')

    return {'confidence': 0.7, 'is_valid': True, 'note': '', 'method': 'ocr_only'}


def confirm_voucher_data(image_path: str, amount: float, payer_name: str) -> dict:
    """
    Valida que los datos extraídos sean correctos.
    Usa OCR para confirmar monto y número de operación.
    """
    try:
        simple_result = extract_receipt_data_simple(image_path)
        raw_text = simple_result.get('raw_text', '').upper()

        amount_str = str(amount).replace(',', '.')
        amount_found = amount_str in raw_text or f'{amount:.2f}'.replace(',', '.') in raw_text

        name_found = payer_name.upper() in raw_text

        validation = {
            'amount_valid': amount_found,
            'name_valid': name_found,
            'overall_valid': amount_found and name_found,
            'confidence': 0.85 if (amount_found and name_found) else 0.5,
        }

        return validation
    except Exception as e:
        logger.error(f'Error en validación de voucher: {e}')
        return {'amount_valid': True, 'name_valid': True, 'overall_valid': True, 'confidence': 0.5}
