# Configuración de Email para Moscowle

## Problema Actual
El sistema no puede enviar correos electrónicos a los pacientes nuevos porque Gmail requiere una "Contraseña de Aplicación" en lugar de la contraseña normal de la cuenta.

## Solución: Configurar Contraseña de Aplicación de Gmail

### Paso 1: Habilitar la Verificación en Dos Pasos
1. Ve a tu cuenta de Google: https://myaccount.google.com/
2. En el menú izquierdo, selecciona **Seguridad**
3. En "Cómo inicias sesión en Google", selecciona **Verificación en dos pasos**
4. Sigue los pasos para habilitarla (necesitarás tu teléfono)

### Paso 2: Generar una Contraseña de Aplicación
1. Una vez habilitada la verificación en dos pasos, regresa a **Seguridad**
2. En "Cómo inicias sesión en Google", selecciona **Contraseñas de aplicaciones**
3. En "Seleccionar app", elige **Correo**
4. En "Seleccionar dispositivo", elige **Otro** y escribe "Moscowle"
5. Haz clic en **Generar**
6. Google te mostrará una contraseña de 16 caracteres (ejemplo: `abcd efgh ijkl mnop`)
7. **COPIA ESTA CONTRASEÑA** (sin espacios)

### Paso 3: Actualizar el archivo .env
1. Abre el archivo `.env` en la raíz del proyecto
2. Reemplaza la línea `MAIL_PASSWORD` con tu nueva contraseña de aplicación:
   ```
   MAIL_PASSWORD=abcdefghijklmnop
   ```
   (sin espacios, solo los 16 caracteres)

### Paso 4: Reiniciar el Servidor
```bash
# Detén el servidor (Ctrl+C)
# Inicia nuevamente
python app.py
```

## Verificación
Después de configurar:
1. Ve a **Pacientes** en el dashboard
2. Agrega un nuevo paciente con un correo real (puede ser el tuyo para probar)
3. Deberías ver un mensaje de éxito y el paciente debería recibir un correo con sus credenciales
4. Si no se puede enviar el correo, el sistema mostrará las credenciales directamente en el mensaje de alerta

## Alternativa: Usar Otro Proveedor de Email
Si no quieres usar Gmail, puedes configurar otro proveedor en `.env`:

### Ejemplo con Outlook/Hotmail:
```env
MAIL_SERVER=smtp-mail.outlook.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=tu_correo@outlook.com
MAIL_PASSWORD=tu_contraseña
MAIL_DEFAULT_SENDER=tu_correo@outlook.com
```

### Ejemplo con SendGrid (recomendado para producción):
```env
MAIL_SERVER=smtp.sendgrid.net
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=apikey
MAIL_PASSWORD=tu_api_key_de_sendgrid
MAIL_DEFAULT_SENDER=noreply@tudominio.com
```

## Comportamiento Actual del Sistema
- ✅ Si el email se configura correctamente: Se envía un correo con las credenciales
- ⚠️ Si el email no se puede enviar: Se muestra un mensaje de advertencia con las credenciales visibles para que el terapeuta las copie manualmente
- ✅ El paciente siempre se crea en el sistema, independientemente del estado del email
- ✅ Se crea una notificación para el terapeuta cuando se agrega un paciente

## Notas de Seguridad
- ⚠️ Las contraseñas de aplicación son sensibles, no las compartas
- ✅ Las contraseñas temporales de pacientes son generadas aleatoriamente
- ✅ Los pacientes deben cambiar su contraseña después del primer inicio de sesión
- ⚠️ No subas el archivo `.env` a repositorios públicos (ya está en `.gitignore`)
