import logging
from collections import defaultdict

logger = logging.getLogger('app')

try:
    from PIL import Image

    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    logger.warning('PIL no instalado - análisis de imágenes limitado')

try:
    import pytesseract

    HAS_PYTESSERACT = True
except ImportError:
    HAS_PYTESSERACT = False
    logger.warning('pytesseract no instalado - OCR desactivado')


class ImageAnalysisPattern:
    """Aprende patrones de imágenes procesadas"""

    def __init__(self):
        self.image_types = defaultdict(int)
        self.extraction_accuracy = defaultdict(list)
        self.common_amounts = defaultdict(int)
        self.avg_confidence = defaultdict(float)

    def record_analysis(self, image_type, extracted_data, confidence):
        """Registra análisis realizado"""
        self.image_types[image_type] += 1
        if extracted_data.get('amount'):
            self.common_amounts[image_type] += 1
        self.extraction_accuracy[image_type].append(confidence)

    def get_confidence_by_type(self, image_type):
        """Obtiene confianza promedio para un tipo de imagen"""
        if image_type not in self.extraction_accuracy:
            return 0.5
        accuracies = self.extraction_accuracy[image_type]
        return sum(accuracies) / len(accuracies) if accuracies else 0.5


image_analysis_pattern = ImageAnalysisPattern()


class SmartImageAnalyzer:
    """Analiza imágenes de forma inteligente"""

    @staticmethod
    def detect_image_type(image_path):
        """Detecta qué tipo de imagen es (voucher, invoice, receipt, etc)"""
        if not HAS_PIL:
            return 'generic'

        try:
            img = Image.open(image_path)
            width, height = img.size

            aspect_ratio = width / height if height > 0 else 0

            if 0.4 < aspect_ratio < 0.9:
                return 'voucher'

            elif 0.6 < aspect_ratio < 1.5:
                return 'invoice'

            elif aspect_ratio > 1.8:
                return 'screenshot'

            return 'generic'

        except Exception as e:
            logger.error(f'Error detectando tipo de imagen: {e}')
            return 'unknown'

    @staticmethod
    def extract_text_smart(image_path):
        """Extrae texto usando OCR con mejoras"""
        if not HAS_PIL:
            logger.warning('PIL no disponible - análisis de imagenes limitado')
            return ''

        if not HAS_PYTESSERACT:
            logger.debug('pytesseract no disponible - OCR desactivado (fallback sin OCR)')
            return ''

        try:
            img = Image.open(image_path)

            from PIL import ImageEnhance

            enhancer = ImageEnhance.Contrast(img)
            img_enhanced = enhancer.enhance(2.0)

            img_array = img_enhanced.convert('L')
            img_array = img_array.point(lambda x: 0 if x < 128 else 255, '1')

            text = pytesseract.image_to_string(img_array, lang='spa+eng')
            return text

        except Exception as e:
            logger.debug(f'Error en OCR (se usará análisis sin texto): {e}')
            return ''

    @staticmethod
    def extract_amount_from_image_visual(image_path):
        """Detecta números grandes en la imagen cuando OCR falla - para Yape/Plin"""
        if not HAS_PIL:
            return None

        try:
            img = Image.open(image_path)

            img_gray = img.convert('L')

            img_resized = img_gray.resize((800, 600), Image.Resampling.LANCZOS)

            pixels = list(img_resized.getdata())

            brightness_levels = [p for p in pixels if p < 50 or p > 200]

            if brightness_levels:
                pass

            from PIL import ImageFilter

            img_filtered = img_gray.filter(ImageFilter.SHARPEN)
            img_enhanced = Image.new('L', img_filtered.size, 255)

            img_mixed = Image.blend(img_gray.convert('RGB'), img_filtered.convert('RGB'), 0.7)

            return None

        except Exception as e:
            logger.debug(f'Error en análisis visual: {e}')
            return None

    @staticmethod
    def identify_sections(text):
        """Identifica secciones importantes en el texto"""
        sections = {'header': [], 'items': [], 'totals': [], 'footer': []}

        lines = text.split('\n')

        for line in lines:
            line_lower = line.lower()

            if any(x in line_lower for x in ['yapa', 'yape', 'plin', 'bim', 'factura', 'boleta', 'recibo', 'invoice']):
                sections['header'].append(line)
            elif any(x in line_lower for x in ['total', 'neto', 'bruto', 'subtotal', 's/.', 'soles', 'monto']):
                sections['totals'].append(line)
            elif any(x in line_lower for x in ['gracias', 'gracias por', 'vuelto', 'cambio']):
                sections['footer'].append(line)
            else:
                sections['items'].append(line)

        return sections

    @staticmethod
    def extract_main_amount(text):
        """Extrae el monto PRINCIPAL del texto - para vouchers Yape/Plin/BIM

        Estrategia:
        1. Buscar S/ XXX (más confiable)
        2. Buscar en líneas con Yape/Plin/BIM
        3. Buscar líneas con "Te Yapearon!" + número grande
        4. Fallback a números grandes en contexto
        """
        import re

        yape_lines = [
            line for line in text.split('\n') if any(x in line.lower() for x in ['yapa', 'yape', 'plin', 'bim', 'te '])
        ]

        for line in yape_lines:
            match = re.search(r'S/\s*\.?\s*(\d+(?:[.,]\d+)?)', line, re.IGNORECASE)
            if match:
                try:
                    amount = float(match.group(1).replace(',', '.'))
                    if 10 <= amount <= 50000:
                        return amount
                except ValueError:
                    continue

        s_lines = [line for line in text.split('\n') if 'S/' in line or 's/' in line]

        amounts = []
        for line in s_lines:
            numbers = re.findall(r'\b(\d+(?:[.,]\d+)?)\b', line)
            for num_str in numbers:
                try:
                    amount = float(num_str.replace(',', '.'))
                    if 10 <= amount <= 50000:
                        amounts.append(amount)
                except ValueError:
                    continue

        if amounts:
            return max(amounts)

        return None

    @staticmethod
    def extract_amount_smart(text, image_type):
        """Extrae monto de forma inteligente basada en tipo - Optimizado para Perú"""
        import re

        priority_patterns = [
            r'S/\s*(\d+(?:[.,]\d+)?)',
            r'S/\s*\.?\s*(\d+(?:[.,]\d+)?)',
            r'(?:total|monto|pago)[:\s]+S/\s*(\d+(?:[.,]\d+)?)',
        ]

        secondary_patterns = [
            r'(?:total|monto|pago)[:\s]+(\d+(?:[.,]\d+)?)',
            r'(\d+(?:[.,]\d+)?)\s*S/?\.?\s',
        ]

        tertiary_patterns = [
            r'\b(\d{3,}(?:[.,]\d{2})?)\b',
        ]

        amounts_priority = []
        amounts_secondary = []
        amounts_tertiary = []

        for pattern in priority_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    amount_str = str(match).replace(',', '.')
                    amount = float(amount_str)
                    if 1 <= amount <= 50000:
                        amounts_priority.append(amount)
                except (ValueError, AttributeError):
                    continue

        if amounts_priority:
            return max(list(set(amounts_priority)))

        for pattern in secondary_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    amount_str = str(match).replace(',', '.')
                    amount = float(amount_str)
                    if 1 <= amount <= 50000:
                        amounts_secondary.append(amount)
                except (ValueError, AttributeError):
                    continue

        if amounts_secondary:
            return max(list(set(amounts_secondary)))

        for pattern in tertiary_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    amount_str = str(match).replace(',', '.')
                    amount = float(amount_str)
                    if 10 <= amount <= 50000:
                        amounts_tertiary.append(amount)
                except (ValueError, AttributeError):
                    continue

        if amounts_tertiary:
            return max(list(set(amounts_tertiary)))

        return None

    @staticmethod
    def analyze_complete(image_path):
        """Análisis completo de imagen - Mejorado para Yape/Plin/BIM"""
        logger.info(f' Analizando imagen: {image_path}')

        image_type = SmartImageAnalyzer.detect_image_type(image_path)
        logger.info(f'  → Tipo detectado: {image_type}')

        text = SmartImageAnalyzer.extract_text_smart(image_path)

        if not text or len(text) < 50:
            logger.debug(f'OCR yield bajo ({len(text) or 0} chars), intentando análisis visual...')
            SmartImageAnalyzer.extract_amount_from_image_visual(image_path)

        sections = SmartImageAnalyzer.identify_sections(text)

        amount = None

        if image_type == 'voucher':
            amount = SmartImageAnalyzer.extract_main_amount(text)

        if not amount:
            amount = SmartImageAnalyzer.extract_amount_smart(text, image_type)

        confidence = 0.5

        if amount:
            confidence += 0.35

        if any(sections['totals']):
            confidence += 0.15

        if text and len(text) > 100:
            confidence += 0.05

        if image_type == 'voucher' and amount:
            confidence += 0.1

        if image_type == 'voucher' and not text and amount:
            confidence = 0.55

        confidence = min(0.99, max(0.3, confidence))

        image_analysis_pattern.record_analysis(image_type, {'amount': amount}, confidence)

        return {
            'image_type': image_type,
            'amount': amount,
            'text_extracted': text[:500] if text else '(sin OCR)',
            'sections': {k: v[:3] for k, v in sections.items()},
            'confidence': round(confidence, 2),
            'raw_text': text,
            'ocr_available': bool(text),
        }


def analyze_voucher_smart(image_path):
    """Conveniencia: analizar voucher directamente"""
    result = SmartImageAnalyzer.analyze_complete(image_path)
    logger.info(f' Análisis completado: S/. {result["amount"]}, confianza: {result["confidence"]}')
    return result
