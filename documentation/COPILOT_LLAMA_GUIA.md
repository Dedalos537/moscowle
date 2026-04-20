# 🤖 GUÍA COMPLETA: Copilot Llama Mejorado V3

## ✨ Lo que hemos implementado

### **FASE 1: Base de Datos & Chat Persistente** ✅
- ✅ Modelo `AIConversation` - Agrupa conversaciones por usuario y sesión
- ✅ Modelo `AIChatMessage` - Guarda cada mensaje con metadata (intención, parámetros, estado)
- ✅ Historial automático de chat que persiste entre sesiones

### **FASE 2: Inteligencia Mejorada** ✅
- ✅ `enhanced_llm_service.py` - Servicio con:
  - Prompt del sistema ultra-específico con ejemplos
  - Contexto de usuario y página actual inyectado
  - Parser robusto de JSON desde Llama
  - Validación de respuestas
  - Historial de conversación como contexto
  
### **FASE 3: OCR Mejorado** ✅
- ✅ `ocr_service.py` - Soporte para:
  - OCR simple con Tesseract (rápido, bajo resources)
  - OCR avanzado con Donut (más preciso, requiere CUDA)
  - Extracción de montos, nombres, referencias y fechas
  - Validación de datos vs voucher
  - Confianza de extracción

### **FASE 4: Registro de Operaciones** ✅
- ✅ Validación en 2 pasos antes de registrar
- ✅ Audit trail en la BD (qué hizo la IA, cuándo, con qué confianza)
- ✅ Notificaciones automáticas de acciones ejecutadas

### **FASE 5: Navegación Inteligente** ✅
- ✅ Detección automática de intención de navegación
- ✅ Validación de URLs antes de redirigir
- ✅ Contexto de página actual en prompts

### **FASE 6: UI/UX Mejorada** ✅
- ✅ Chat con historial persistente
- ✅ Acciones rápidas contextuales
- ✅ Confirmaciones visuales antes de ejecutar
- ✅ Contraste mejorado (Verde primary color)

---

## 🚀 CÓMO USAR

### **1. Crear las Tablas de BD**
```bash
# Entra a Flask shell
flask shell

# Ejecuta
from app.utils.migrate_ia import create_ia_tables, check_ia_tables
create_ia_tables()
check_ia_tables()
```

### **2. Iniciar la App**
```bash
python -m flask run
# La IA se iniciará automáticamente junto con Ollama
```

### **3. Usar el Copilot**

**Ejemplos de comandos:**

```
💰 Pago:
  "Registra 500 soles para Juan"
  "Marca 1000 de pago a María"

📊 Gastos:
  "Registra gasto de 250 en servicios"
  "Crea egreso de 100 para comida"

🔀 Navegación:
  "Llevame a deudores"
  "Ve a pagos"
  "Abre usuarios"

❓ Información:
  "¿Cuántas sesiones hoy?"
  "¿Cuál es la primera cita?"
  
🧾 Voucher:
  "Sube este voucher" (+ imagen)
```

---

## 📁 Archivos Creados/Modificados

### **Nuevos Archivos**
- `app/models.py` - Agregados modelos `AIConversation`, `AIChatMessage`
- `app/services/enhanced_llm_service.py` - Servicio mejorado de IA
- `app/services/ocr_service.py` - Servicio OCR para vouchers
- `app/routes/llama_routes.py` - Rutas del Copilot
- `app/utils/migrate_ia.py` - Script de migración

### **Modificados**
- `app/__init__.py` - Registrado nuevo blueprint llama_routes
- `app/templates/therapist/base.html` - Actualizado JavaScript del chat

---

## 🔧 ENDPOINTS DISPONIBLES

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/llama/chat/send` | POST | Enviar mensaje al Copilot |
| `/llama/chat/history` | GET | Obtener historial de chat |
| `/llama/chat/upload-voucher` | POST | Subir y procesar voucher |
| `/llama/chat/confirm-payment` | POST | Confirmar pago luego de OCR |

---

## 📊 Flujo de Registro de Pago (Mejorado)

```
1. Usuario: "Registra 500 para Juan"
   ↓
2. Copilot: Extrae parámetros (patient_name, amount, method)
   ↓
3. Validación: Verifica que datos sean correctos
   ↓
4. Búsqueda: Encuentra el paciente en BD
   ↓
5. Registro: Inserta en tabla Payment
   ↓
6. Notificación: Crea notificación + audit trail
   ↓
7. Respuesta: "✅ Registré S/. 500 para Juan"
   ↓
8. Historial: Guarda mensaje + intención + parámetros + resultado en BD
```

---

## 🧠 Contexto Inteligente

Cada mensaje incluye:
```
- Usuario actual (ID, nombre, rol)
- Fecha y hora actual del servidor
- Página donde está el usuario
- Últimos 5 mensajes de conversación
- Módulos disponibles
```

Esto permite que la IA entienda mejor y sea coherente.

---

## ⚙️ Configuración

### OCR
```python
# Cambiar de Tesseract a Donut:
# En `ocr_service.py`, la función `process_payment_voucher` 
# intenta Donut primero, luego fallback a Tesseract

# Instalar dependencias (opcional):
pip install pytesseract pillow transformers torch
```

### Prompt del Sistema
- Ubicado en: `app/services/enhanced_llm_service.py`
- Línea: `ENHANCED_SYSTEM_PROMPT`
- Editable en tiempo real

---

## 🚨 Troubleshooting

### "Sistema AI desconectado"
```
✅ Solución: Las tablas de IA no existen
- Ejecutar: `flask shell`
- Luego: `from app.utils.migrate_ia import create_ia_tables; create_ia_tables()`
```

### OCR no funciona
```
✅ Verificar pytesseract está instalado:
pip install pytesseract pillow

✅ En MacOS, también instalar tesseract:
brew install tesseract
```

### Pago no registra
```
✅ Verificar:
- El nombre del paciente es correcto (búsqueda fuzzy helps)
- El monto es > 0
- Revisar logs: `flask run` mostrará errores
```

---

## 📈 Próximas Mejoras

- [ ] Análisis de múltiples vouchers en un mensaje
- [ ] Multiidioma (español, inglés, quechua)
- [ ] Integración with WhatsApp Business API
- [ ] Análisis predictivo de pagos con IA
- [ ] Copilot puede generar reportes automáticos

---

## 📞 Soporte

Si encuentras problemas:
1. Revisa `flask run` logs
2. Excepta desde bash: `flask shell`
3. Debugging: Activa `app.logger.info()` en rutas

¡El Copilot está listo para trabajar! 🚀
