## pywhatkit - Guía de Uso

**Estado**: ✅ Instalado y configurado (completamente GRATUITO)

### ¿Qué es pywhatkit?

pywhatkit es una librería Python que automatiza el envío de mensajes a través de WhatsApp Web. **No requiere credenciales de Twilio** ni ningún pago.

**Características**:
- ✅ **COMPLETAMENTE GRATIS**
- ✅ Envía mensajes de WhatsApp automáticamente
- ✅ Abre Chrome/Chromium automáticamente
- ✅ Accede a WhatsApp Web sin intervención manual
- ✅ No requiere configuración de credenciales

### Cómo Funciona

1. **Al enviar un mensaje via WhatsApp**, la aplicación:
   - Abre automáticamente Chrome con WhatsApp Web
   - Busca el contacto por número de teléfono
   - Envía el mensaje automáticamente
   - Cierra la pestaña después del envío

2. **Tiempo de envío**:
   - Se programa el envío para 1 minuto en el futuro (configurable)
   - Esto da tiempo para que WhatsApp Web inicie

### Ventajas vs Twilio

| Aspecto | pywhatkit | Twilio |
|---------|-----------|--------|
| **Costo** | 🟢 GRATIS | 🔴 De pago ($) |
| **Configuración** | 🟢 Automática | 🔴 Requiere credenciales API |
| **Números de prueba** | 🟢 Cualquier número real | 🔴 Sandbox limitado |
| **Instalación** | 🟢 pip install pywhatkit | 🔴 pip install twilio |
| **Mantenimiento** | 🟢 Ninguno | 🔴 Requiere actualizar credenciales |

### Limitaciones

⚠️ **Importante**: pywhatkit tiene algunas limitaciones:

1. **Requiere navegador Chrome/Chromium** 
   - En servidor sin UI, esto puede ser problemático
   - Funciona perfectamente en desktop/laptop

2. **Corre en background thread**
   - Los mensajes se envían de forma asincrónica
   - No bloquea las peticiones HTTP

3. **No funciona en máquinas headless**
   - Si corres el servidor sin monitor/display, necesitarás Xvfb (virtual display)
   - O usar solo en desarrollo local

### Configuración en macOS

✅ Ya está listo. En macOS, pywhatkit detecta Chrome automáticamente.

### Prueba Manual

Para probar que funciona:

```bash
python3 -c "
import pywhatkit
from datetime import datetime

# Programa un mensaje para ahora + 1 minuto
now = datetime.now()
hour = now.hour
minute = now.minute + 1

if minute >= 60:
    minute -= 60
    hour += 1

pywhatkit.sendwhatmsg(
    '+51921507470',  # Tu número Perú
    'Hola! Este es un mensaje de prueba',
    hour,
    minute
)
print('✅ Mensaje programado. Se abrirá Chrome automáticamente')
"
```

**Resultado esperado**:
1. Chrome se abre con WhatsApp Web
2. Se busca el contacto "+51 921 507 470"
3. Se escribe el mensaje
4. Se envía automáticamente
5. La pestaña se cierra

### Cómo está integrado en moscowle

En `/app/services/sms_whatsapp_service.py`:

**Cuando el usuario hace clic en "Enviar recordatorio" → WhatsApp**:
1. Se crea un thread de background
2. Se ejecuta `_send_whatsapp_pywhatkit()`
3. Se programa el envío para 1 minuto después
4. El usuario ve: "📱 WhatsApp via pywhatkit scheduled"
5. Chrome se abre automáticamente en segundo plano
6. El mensaje se envía sin afectar la aplicación

### Flujo Actual

```
Usuario hace click en "WhatsApp" 
         ↓
Backend busca pywhatkit disponible
         ↓
SI hay pywhatkit → Envía via pywhatkit (GRATIS) ✅
NO hay pywhatkit → Intenta Twilio (de pago)
         ↓
Respuesta: "Mensaje programado/enviado"
```

### Próximos Pasos

1. **Reinicia el servidor Flask** (ya está listo):
   ```bash
   PORT=8000 python3 run.py
   ```

2. **Ve a `/admin/deudores`**

3. **Haz clic en el ícono de campana** (reminder) en cualquier deudor

4. **Selecciona "WhatsApp"**

5. **¡Debería funcionar! Chrome se abrirá automáticamente**

### Si hay problemas

**Problema**: "Chrome no se abre"
- **Solución**: Asegúrate que Chrome esté instalado: `/Applications/Google Chrome.app`

**Problema**: "No se abre WhatsApp Web"
- **Solución**: Abre WhatsApp Web manualmente en `web.whatsapp.com` uma vez

**Problema**: "El número no existe en WhatsApp"
- **Solución**: El número destino debe tener WhatsApp activo

**Problema**: "Mensaje no se envía"
- **Solución**: Verifica que hayas aceptado la confirmación manual la primera vez

### Alternativa: Si pywhatkit no funciona bien

Vuelve a Twilio siguiendo estos pasos:

1. Crea cuenta en https://www.twilio.com
2. Obtén credenciales (Account SID, Auth Token)
3. Agrega a `.env`:
   ```
   TWILIO_ACCOUNT_SID=your_sid
   TWILIO_AUTH_TOKEN=your_token
   TWILIO_PHONE_NUMBER=+15551234567
   TWILIO_WHATSAPP_NUMBER=whatsapp:+14155552671
   ```
4. Reinicia: `PORT=8000 python3 run.py`

**El código ya está preparado** para cambiar automáticamente a Twilio si pywhatkit no funciona o no está disponible.

---

**Conclusión**: pywhatkit es la opción más práctica ahora porque es GRATIS y funciona sin configuración. Si tiene problemas en producción, siempre puedes cambiar a Twilio.
