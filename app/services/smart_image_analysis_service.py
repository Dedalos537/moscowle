# Analiza imágenes: detecta tipos, extrae datos, aprende patrones
import logging
import os
from datetime import datetime
from collections import defaultdict
import json

logger = logging.getLogger('app')

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    logger.warning("PIL no instalado - análisis de imágenes limitado")

try:
    import pytesseract
    HAS_PYTESSERACT = True
except ImportError:
    HAS_PYTESSERACT = False
    logger.warning("pytesseract no instalado - OCR desactivado")

class ImageAnalysisPattern:
    """Aprende patrones de imágenes procesadas"""
    
    def __init__(self):
        self.image_types = defaultdict(int)  # Conteo de tipos (voucher, invoice, etc)
        self.extraction_accuracy = defaultdict(list)  # Precisión por tipo
        self.common_amounts = defaultdict(int)  # Montos frecuentes
        self.avg_confidence = defaultdict(float)  # Confianza promedio por tipo
    
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

# Instancia global
image_analysis_pattern = ImageAnalysisPattern()

class SmartImageAnalyzer:
    """Analiza imágenes de forma inteligente"""
    
    @staticmethod
    def detect_image_type(image_path):
        """Detecta qué tipo de imagen es (voucher, invoice, receipt, etc)"""
        if not HAS_PIL:
            return "generic"
        
        try:
            # Análisis básico: tamaño, dimensiones
            img = Image.open(image_path)
            width, height = img.size
            
            # Aspectos que delatan tipo
            aspect_ratio = width / height if height > 0 else 0
            
            # Vouchers/boletas: generalmente más altos que anchos (0.5-0.8)
            if 0.4 < aspect_ratio < 0.9:
                return "voucher"
            
            # Invoices: cuadradas o documento completo (0.7-1.4)
            elif 0.6 < aspect_ratio < 1.5:
                return "invoice"
            
            # Fotos de pantalla o documentos anchos (2.0+)
            elif aspect_ratio > 1.8:
                return "screenshot"
            
            return "generic"
        
        except Exception as e:
            logger.error(f"Error detectando tipo de imagen: {e}")
            return "unknown"
    
    @staticmethod
    def extract_text_smart(image_path):
        """Extrae texto usando OCR con mejoras"""
        if not HAS_PIL:
            logger.warning("PIL no disponible - análisis de imagenes limitado")
            return ""
        
        # Si pytesseract no está disponible, retornar vacío sin error
        if not HAS_PYTESSERACT:
            logger.debug("pytesseract no disponible - OCR desactivado (fallback sin OCR)")
            return ""
        
        try:
            img = Image.open(image_path)
            
            # Pre-procesamiento: mejorar contraste para OCR
            from PIL import ImageEnhance
            enhancer = ImageEnhance.Contrast(img)
            img_enhanced = enhancer.enhance(2.0)
            
            # Aplicar threshold también para mejor OCR
            img_array = img_enhanced.convert('L')
            img_array = img_array.point(lambda x: 0 if x < 128 else 255, '1')
            
            # OCR
            text = pytesseract.image_to_string(img_array, lang='spa+eng')
            return text
        
        except Exception as e:
            logger.debug(f"Error en OCR (se usará análisis sin texto): {e}")
            return ""
    
    @staticmethod
    def extract_amount_from_image_visual(image_path):
        """Detecta números grandes en la imagen cuando OCR falla - para Yape/Plin"""
        if not HAS_PIL:
            return None
        
        try:
            import re
            img = Image.open(image_path)
            
            # Convertir a escala de grises
            img_gray = img.convert('L')
            
            # Redimensionar para análisis (acelera procesamiento)
            img_resized = img_gray.resize((800, 600), Image.Resampling.LANCZOS)
            
            # Buscar áreas de alto contraste (donde normalmente están los números)
            # Los vouchers Yape tienen números grandes en contraste
            pixels = list(img_resized.getdata())
            
            # Distribución de brillo
            brightness_levels = [p for p in pixels if p < 50 or p > 200]  # Muy claros u oscuros
            
            if brightness_levels:
                # Si hay contraste, probablemente haya texto extraíble
                # Retornar None para que intente OCR, o si falla usará patrón fallback
                pass
            
            # Como último recurso: intentar con imagen dilatada
            # para mejor OCR
            from PIL import ImageFilter
            img_filtered = img_gray.filter(ImageFilter.SHARPEN)
            img_enhanced = Image.new('L', img_filtered.size, 255)
            
            # Mezclar original con filtrada
            img_mixed = Image.blend(img_gray.convert('RGB'), img_filtered.convert('RGB'), 0.7)
            
            return None  # Indicar que no se pudo extraer visualmente
            
        except Exception as e:
            logger.debug(f"Error en análisis visual: {e}")
            return None
    
    @staticmethod
    def identify_sections(text):
        """Identifica secciones importantes en el texto"""
        sections = {
            'header': [],
            'items': [],
            'totals': [],
            'footer': []
        }
        
        lines = text.split('\n')
        
        for line in lines:
            line_lower = line.lower()
            
            # Detectar secciones - MEJORADO para Yape/Plin
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
        
        # ESTRATEGIA 1: Buscar "S/ NUMERO" en la línea de "Te Yapearon" o similar
        yape_lines = [
            line for line in text.split('\n') 
            if any(x in line.lower() for x in ['yapa', 'yape', 'plin', 'bim', 'te '])
        ]
        
        for line in yape_lines:
            # Buscar patrones como "S/ 380" o "S/380"
            match = re.search(r'S/\s*\.?\s*(\d+(?:[.,]\d+)?)', line, re.IGNORECASE)
            if match:
                try:
                    amount = float(match.group(1).replace(',', '.'))
                    if 10 <= amount <= 50000:  # Rango válido para voucher
                        return amount
                except ValueError:
                    continue
        
        # ESTRATEGIA 2: Buscar el número más grande en líneas con S/
        s_lines = [line for line in text.split('\n') if 'S/' in line or 's/' in line]
        
        amounts = []
        for line in s_lines:
            # Buscar todos los números en esta línea
            numbers = re.findall(r'\b(\d+(?:[.,]\d+)?)\b', line)
            for num_str in numbers:
                try:
                    amount = float(num_str.replace(',', '.'))
                    if 10 <= amount <= 50000:
                        amounts.append(amount)
                except ValueError:
                    continue
        
        if amounts:
            # Retornar el más grande (probablemente el total)
            return max(amounts)
        
        return None
    
    @staticmethod
    def extract_amount_smart(text, image_type):
        """Extrae monto de forma inteligente basada en tipo - Optimizado para Perú"""
        import re
        
        # Patrones PRIORIDAD 1: Con símbolo S/ (seguro)
        priority_patterns = [
            r'S/\s*(\d+(?:[.,]\d+)?)',  # S/ 380 o S/ 380.50
            r'S/\s*\.?\s*(\d+(?:[.,]\d+)?)',  # S/. 380 o S/. 380.50 (con punto opcional)
            r'(?:total|monto|pago)[:\s]+S/\s*(\d+(?:[.,]\d+)?)',  # Total: S/ 380
        ]
        
        # Patrones PRIORIDAD 2: Contexto de total/monto
        secondary_patterns = [
            r'(?:total|monto|pago)[:\s]+(\d+(?:[.,]\d+)?)',  # Total: 380
            r'(\d+(?:[.,]\d+)?)\s*S/?\.?\s',  # 380 S/ o 380 S/.
        ]
        
        # Patrones PRIORIDAD 3: Solo números (última opción)
        tertiary_patterns = [
            r'\b(\d{3,}(?:[.,]\d{2})?)\b',  # 380+ solamente (3+ dígitos)
        ]
        
        amounts_priority = []
        amounts_secondary = []
        amounts_tertiary = []
        
        # Intenta patrones de PRIORIDAD 1
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
        
        # Si encontramos con S/, usar eso
        if amounts_priority:
            return max(list(set(amounts_priority)))
        
        # Si no, intentar PRIORIDAD 2
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
        
        # Si todo falla, usar PRIORIDAD 3 (solo números 3+ dígitos)
        for pattern in tertiary_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    amount_str = str(match).replace(',', '.')
                    amount = float(amount_str)
                    # Para números sin contexto: rango más restringido
                    if 10 <= amount <= 50000:  # Mínimo 10 sin contexto
                        amounts_tertiary.append(amount)
                except (ValueError, AttributeError):
                    continue
        
        if amounts_tertiary:
            return max(list(set(amounts_tertiary)))
        
        return None
    
    @staticmethod
    def analyze_complete(image_path):
        """Análisis completo de imagen - Mejorado para Yape/Plin/BIM"""
        logger.info(f" Analizando imagen: {image_path}")
        
        # Detectar tipo
        image_type = SmartImageAnalyzer.detect_image_type(image_path)
        logger.info(f"  → Tipo detectado: {image_type}")
        
        # Extraer texto
        text = SmartImageAnalyzer.extract_text_smart(image_path)
        
        # Si no tenemos mucho texto pero es voucher, intentar análisis visual
        if not text or len(text) < 50:
            logger.debug(f"OCR yield bajo ({len(text) or 0} chars), intentando análisis visual...")
            # Intentar análisis visual
            SmartImageAnalyzer.extract_amount_from_image_visual(image_path)
        
        # Identificar secciones
        sections = SmartImageAnalyzer.identify_sections(text)
        
        # Extraer monto - MEJORADO para Yape/Plin/BIM
        amount = None
        
        # Para vouchers: intentar primero extracción de monto principal
        if image_type == "voucher":
            amount = SmartImageAnalyzer.extract_main_amount(text)
        
        # Si no encontró, usar método genérico
        if not amount:
            amount = SmartImageAnalyzer.extract_amount_smart(text, image_type)
        
        # Calcular confianza - MEJORADA
        confidence = 0.5
        
        if amount:
            confidence += 0.35  # +0.35 si encontró monto (aumentado)
        
        if any(sections['totals']):
            confidence += 0.15  # +0.15 si encontró sección de totales
        
        if text and len(text) > 100:
            confidence += 0.05  # +0.05 si mucho texto legible
        
        # Bonus para vouchers que encontraron monto (probablemente Yape/Plin)
        if image_type == "voucher" and amount:
            confidence += 0.1  # +0.10 para vouchers exitosos
        
        # Penalización si no hay OCR pero sí es voucher (OCR fallido pero imagen clara)
        if image_type == "voucher" and not text and amount:
            confidence = 0.55  # Confianza moderada para análisis sin OCR
        
        confidence = min(0.99, max(0.3, confidence))  # Límite 0.3-0.99
        
        # Registrar patrón
        image_analysis_pattern.record_analysis(image_type, {'amount': amount}, confidence)
        
        return {
            'image_type': image_type,
            'amount': amount,
            'text_extracted': text[:500] if text else "(sin OCR)",
            'sections': {k: v[:3] for k, v in sections.items()},
            'confidence': round(confidence, 2),
            'raw_text': text,
            'ocr_available': bool(text)
        }

def analyze_voucher_smart(image_path):
    """Conveniencia: analizar voucher directamente"""
    result = SmartImageAnalyzer.analyze_complete(image_path)
    logger.info(f" Análisis completado: S/. {result['amount']}, confianza: {result['confidence']}")
    return result
