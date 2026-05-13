# 📧 Configuración de Email para Moscowle - GUÍA RÁPIDA

## ⚡ Opción más rápida: Mailtrap (2 minutos)

### Paso 1: Crear cuenta en Mailtrap
1. Ve a **https://mailtrap.io**
2. Haz clic en "Sign Up" (es GRATIS)
3. Regístrate con Google o email

### Paso 2: Obtener credenciales
1. Una vez dentro, ve a **"Email Testing"** → **"Inboxes"** → **"My Inbox"**
2. En la pestaña **"SMTP Settings"**, selecciona **"Show Credentials"**
3. Verás algo como:
   ```
   Host: sandbox.smtp.mailtrap.io
   Port: 2525
   Username: 1a2b3c4d5e6f7g
   Password: 9h8i7j6k5l4m3n
   ```

### Paso 3: Actualizar tu archivo .env
Abre el archivo `.env` en tu proyecto y cambia estas líneas:

```env
MAIL_SERVER=sandbox.smtp.mailtrap.io
MAIL_PORT=2525
MAIL_USE_TLS=True
MAIL_USERNAME=1a2b3c4d5e6f7g        ← Pon tu username de Mailtrap aquí
MAIL_PASSWORD=9h8i7j6k5l4m3n        ← Pon tu password de Mailtrap aquí
MAIL_DEFAULT_SENDER=mamiebamos2@gmail.com
```

### Paso 4: Probar la configuración
```bash
python test_email.py
```

### Paso 5: Crear paciente
1. Inicia tu servidor: `python app.py`
2. Ve a **Pacientes** → **Nuevo Paciente**
3. Llena el formulario y envía
4. ✅ Verás las credenciales en pantalla
5. 📬 Ve a Mailtrap.io → My Inbox para ver el email

---

## 📮 Opción Gmail (para emails REALES)

Si prefieres usar tu Gmail personal para enviar emails reales:

### Paso 1: Habilitar verificación en dos pasos
1. Ve a https://myaccount.google.com/security
2. Busca **"Verificación en dos pasos"**
3. Actívala (necesitarás tu teléfono)

### Paso 2: Generar App Password
1. En la misma página de seguridad, busca **"Contraseñas de aplicaciones"**
2. Si no aparece, es porque no has activado la verificación en dos pasos
3. Selecciona:
   - App: **Correo**
   - Dispositivo: **Otro** → Escribe "Moscowle"
4. Haz clic en **Generar**
5. Google te dará una contraseña de 16 caracteres como: `abcd efgh ijkl mnop`
6. **COPIA esta contraseña** (sin los espacios)

### Paso 3: Actualizar .env
```env
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=mamiebamos2@gmail.com
MAIL_PASSWORD=abcdefghijklmnop     ← Pon tu App Password aquí (sin espacios)
MAIL_DEFAULT_SENDER=mamiebamos2@gmail.com
```

### Paso 4: Probar
```bash
python test_email.py
```

---

## 🎯 ¿Qué opción elegir?

| Opción | Ventajas | Desventajas |
|--------|----------|-------------|
| **Mailtrap** | • Gratis<br>• Configuración en 2 minutos<br>• No necesita verificación<br>• Perfecto para desarrollo | • Los emails NO se envían realmente<br>• Solo los ves en Mailtrap.io |
| **Gmail** | • Envía emails REALES<br>• Los pacientes reciben sus credenciales | • Requiere App Password<br>• Límite de 500 emails/día<br>• Más configuración |

**Recomendación:** 
- 🧪 Para **testing/desarrollo**: Usa **Mailtrap**
- 🚀 Para **producción**: Usa **Gmail** (o mejor, SendGrid/Mailgun)

---

## 🔍 Troubleshooting

### Error: "MAIL_USERNAME o MAIL_PASSWORD no configurados"
- ✅ Verifica que tu `.env` tenga estas líneas sin comentar
- ✅ Asegúrate de reiniciar el servidor después de cambiar `.env`

### Error: "Authentication failed"
- ✅ Si usas Gmail: asegúrate de usar **App Password**, no tu contraseña normal
- ✅ Si usas Mailtrap: verifica que copiaste bien las credenciales

### El email no llega
- ✅ Si usas Mailtrap: los emails NO llegan a la bandeja real, revisa en mailtrap.io
- ✅ Si usas Gmail: revisa spam/correo no deseado

---

## ✅ Verificación Final

Después de configurar, ejecuta:

```bash
# 1. Probar configuración de email
python test_email.py

# 2. Si el test pasa, inicia el servidor
python app.py

# 3. Ve al navegador y crea un paciente
# http://127.0.0.1:5000/patients
```

Deberías ver:
- ✅ Mensaje de éxito con las credenciales en pantalla
- ✅ Email enviado (visible en Mailtrap o en inbox real según tu configuración)
- ✅ Notificación con las credenciales

---

## 📝 Notas Importantes

1. **Las credenciales siempre se muestran en pantalla** después de crear un paciente, independientemente de si el email se envía o no.

2. **Las credenciales también se guardan en las notificaciones** del terapeuta.

3. **Formato del mensaje:**
   ```
   ✅ Paciente Juan Pérez agregado exitosamente.
   📧 Email enviado a: juan@ejemplo.com
   🔑 Contraseña temporal: Abc123!@#
   ```

4. **El email que recibe el paciente contiene:**
   - Saludo personalizado
   - Email de acceso
   - Contraseña temporal
   - Instrucciones para cambiarla

---

¿Tienes dudas? Ejecuta `python test_email.py` y te guiará paso a paso.
