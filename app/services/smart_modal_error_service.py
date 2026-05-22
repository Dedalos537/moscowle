# Errores como modales, sin logs feos
import logging
import traceback
from enum import Enum

logger = logging.getLogger('app')

class ErrorSeverity(Enum):
    """Nivel de severidad del error"""
    INFO = "info"          # Información importante pero no error
    WARNING = "warning"    # Advertencia, proceder con cuidado
    ERROR = "error"        # Error que requiere acción del usuario
    CRITICAL = "critical"  # Error crítico, detener operación

class SmartModalError:
    """Estructura de error formateada para modales"""
    
    def __init__(self, title, message, severity=ErrorSeverity.ERROR, 
                 action_button=None, details=None, error_code=None):
        """
        title: Título del modal (ej: "Error de Validación")
        message: Mensaje amigable para el usuario
        severity: INFO, WARNING, ERROR, CRITICAL
        action_button: {"text": "Reintentar", "action": "retry"} o {"text": "Continuar", "action": "continue"}
        details: Información técnica adicional (para developers)
        error_code: Código de error para tracking (ej: "FILE_NOT_FOUND_001")
        """
        self.title = title
        self.message = message
        self.severity = severity.value if isinstance(severity, ErrorSeverity) else severity
        self.action_button = action_button
        self.details = details
        self.error_code = error_code or f"ERR_{severity.value.upper()}"
        self.timestamp = None
    
    def to_dict(self):
        """Convertir a dict para JSON response"""
        return {
            'error_modal': {
                'title': self.title,
                'message': self.message,
                'severity': self.severity,
                'action_button': self.action_button,
                'details': self.details,
                'error_code': self.error_code,
                'timestamp': self.timestamp or datetime.now().isoformat()
            }
        }
    
    def log(self):
        """Registrar en logs pero sin gritar"""
        if self.severity == 'critical':
            logger.critical(f"[{self.error_code}] {self.title}: {self.message}")
        elif self.severity == 'error':
            logger.error(f"[{self.error_code}] {self.title}: {self.message}")
        elif self.severity == 'warning':
            logger.warning(f"[{self.error_code}] {self.title}: {self.message}")
        else:
            logger.info(f"[{self.error_code}] {self.title}: {self.message}")

# Errores predefinidos comunes
class CommonErrors:
    """Errores estándar del sistema"""
    
    @staticmethod
    def file_not_found(filename):
        return SmartModalError(
            title=" Archivo No Encontrado",
            message=f"No se pudo encontrar el archivo '{filename}'. ¿Fue eliminado?",
            severity=ErrorSeverity.WARNING,
            action_button={"text": "Buscar Archivo", "action": "browse_file"},
            details=f"File not found: {filename}",
            error_code="FILE_NOT_FOUND"
        )
    
    @staticmethod
    def validation_error(field, reason):
        return SmartModalError(
            title=" Validación Fallida",
            message=f"El campo '{field}' no es válido: {reason}",
            severity=ErrorSeverity.WARNING,
            action_button={"text": "Corregir", "action": "focus_field"},
            details=f"Validation failed for {field}",
            error_code="VALIDATION_ERROR"
        )
    
    @staticmethod
    def insufficient_data(missing_fields):
        fields_str = ", ".join(missing_fields)
        return SmartModalError(
            title=" Información Incompleta",
            message=f"Necesitamos: {fields_str}",
            severity=ErrorSeverity.INFO,
            action_button={"text": "Completar", "action": "complete_form"},
            details=f"Missing fields: {missing_fields}",
            error_code="MISSING_DATA"
        )
    
    @staticmethod
    def database_error():
        return SmartModalError(
            title=" Error de Base de Datos",
            message="No se pudo conectar a la base de datos. Intenta nuevamente en unos momentos.",
            severity=ErrorSeverity.CRITICAL,
            action_button={"text": "Reintentar", "action": "retry"},
            error_code="DB_ERROR"
        )
    
    @staticmethod
    def access_denied(resource):
        return SmartModalError(
            title=" Acceso Denegado",
            message=f"No tienes permisos para acceder a '{resource}'.",
            severity=ErrorSeverity.ERROR,
            action_button={"text": "Solicitar Acceso", "action": "request_access"},
            error_code="ACCESS_DENIED"
        )
    
    @staticmethod
    def file_too_large(max_size_mb):
        return SmartModalError(
            title=" Archivo Demasiado Grande",
            message=f"El archivo supera el límite de {max_size_mb}MB. Comprime la imagen.",
            severity=ErrorSeverity.WARNING,
            action_button={"text": "Comprimir", "action": "compress_image"},
            error_code="FILE_TOO_LARGE"
        )
    
    @staticmethod
    def invalid_image_format():
        return SmartModalError(
            title=" Formato No Soportado",
            message="Solo soportamos JPG, PNG, GIF y WEBP.",
            severity=ErrorSeverity.WARNING,
            action_button={"text": "Cambiar Formato", "action": "convert_image"},
            error_code="INVALID_IMAGE_FORMAT"
        )

def create_error_response(error_obj, status_code=400):
    """Crea respuesta JSON estructurada para errores"""
    error_obj.log()
    return {
        'success': False,
        **error_obj.to_dict()
    }, status_code

from datetime import datetime
