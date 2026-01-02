# Moscowle AI - Centro de Terapias Juan Pablo II

Sistema de terapia digital con inteligencia artificial para seguimiento de pacientes.

## 🚀 Funcionalidades Implementadas

### ✅ Seguridad y Autenticación
- **Encriptación de contraseñas** con bcrypt
- **Autenticación OAuth2** con Google y Microsoft
- **Validación de emails** con email-validator
- **Gestión de sesiones** con Flask-Login
- **Variables de entorno** protegidas con python-dotenv

### ✅ Gestión de Usuarios
- Solo el terapeuta administrador puede agregar pacientes
- Generación automática de contraseñas seguras
- Envío de credenciales por correo electrónico
- Activar/desactivar cuentas de pacientes
- Eliminación de pacientes

### ✅ Sistema de Emails
- Envío automático de credenciales a nuevos pacientes
- Configuración SMTP con Gmail
- Plantillas HTML personalizadas

### ✅ Panel de Control
- Dashboard con estadísticas en tiempo real
- Visualización de rendimiento de pacientes
- Sistema de alertas basado en IA
- Gestión completa de pacientes

## 📋 Requisitos Previos

- Python 3.8+
- Cuenta de Gmail para envío de emails
- (Opcional) Credenciales OAuth2 de Google y Microsoft

## 🔧 Instalación

1. **Clonar el repositorio**
```bash
cd /Users/apple/Documents/moscowle_ia_mvp
```

2. **Crear entorno virtual**
```bash
python -m venv venv
source venv/bin/activate  # En macOS/Linux
```

3. **Instalar dependencias**
```bash
pip install -r requirements.txt
```

4. **Configurar variables de entorno**

Edita el archivo `.env` con tus credenciales:

```env
# Flask Configuration
SECRET_KEY=moscowle_secret_key_production_2024

# Email Configuration (Gmail SMTP)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=info@centrojuanpabloii.com
MAIL_PASSWORD=tu_contraseña_de_aplicacion_aqui
MAIL_DEFAULT_SENDER=info@centrojuanpabloii.com

# OAuth2 Google (opcional)
GOOGLE_CLIENT_ID=tu_google_client_id
GOOGLE_CLIENT_SECRET=tu_google_client_secret

# OAuth2 Microsoft (opcional)
MICROSOFT_CLIENT_ID=tu_microsoft_client_id
MICROSOFT_CLIENT_SECRET=tu_microsoft_client_secret

# Admin Configuration
ADMIN_EMAIL=diegocenteno537@gmail.com
ADMIN_PASSWORD=Rucula_530

### 📧 Configurar Gmail para envío de emails

1. Ve a tu cuenta de Google: https://myaccount.google.com/
2. Activa la verificación en 2 pasos
3. Ve a "Contraseñas de aplicaciones": https://myaccount.google.com/apppasswords
4. Genera una contraseña de aplicación para "Correo"
5. Copia la contraseña generada en `MAIL_PASSWORD` del archivo `.env`

### 🔐 Configurar OAuth2 (Opcional)

**Google OAuth2:**
1. Ve a https://console.cloud.google.com/
2. Crea un nuevo proyecto o selecciona uno existente
3. Habilita "Google+ API"
4. Ve a "Credenciales" → "Crear credenciales" → "ID de cliente de OAuth"
5. Configura la pantalla de consentimiento
6. Agrega URI de redirección: `http://127.0.0.1:5000/authorize/google`
7. Copia Client ID y Client Secret al `.env`

**Microsoft OAuth2:**
1. Ve a https://portal.azure.com/
2. Registra una nueva aplicación en Azure AD
3. Configura permisos: `openid`, `email`, `profile`
4. Agrega URI de redirección: `http://127.0.0.1:5000/authorize/microsoft`
5. Copia Client ID y Client Secret al `.env`

## 🚀 Ejecutar la Aplicación

```bash
python app.py
```

La aplicación estará disponible en: http://127.0.0.1:5000

## 👤 Credenciales de Acceso

**Terapeuta (Administrador):**
- Email: `mamiebamos2@gmail.com`
- Contraseña: `@dm1n_123!`

## 📱 Uso del Sistema

### Para el Terapeuta:

1. **Iniciar sesión** con las credenciales de administrador
2. **Agregar pacientes:**
   - Ir a "Pacientes" en el menú lateral
   - Completar nombre y email del paciente
   - El sistema generará una contraseña automática
   - Se enviará un email al paciente con sus credenciales
3. **Ver estadísticas** en el Dashboard
4. **Gestionar pacientes:**
   - Activar/desactivar cuentas
   - Eliminar pacientes
   - Ver rendimiento individual

### Para el Paciente:

1. Recibir email con credenciales
2. Iniciar sesión con email y contraseña
3. Acceder al juego de entrenamiento cognitivo
4. Ver recomendaciones de la IA

## 🛡️ Seguridad Implementada

- ✅ Contraseñas encriptadas con bcrypt
- ✅ Validación de formato de emails
- ✅ Tokens de sesión seguros
- ✅ Variables de entorno protegidas
- ✅ Verificación de usuarios existentes
- ✅ Control de acceso por roles (terapeuta/jugador)
- ✅ Solo el admin puede gestionar usuarios

## 📁 Estructura del Proyecto

```
moscowle_ia_mvp/
├── app.py                    # Aplicación principal con todas las rutas
├── models.py                 # Modelos de base de datos
├── ai_service.py            # Servicio de IA para predicciones
├── .env                     # Variables de entorno (NO SUBIR A GIT)
├── requirements.txt         # Dependencias de Python
├── templates/
│   ├── base.html           # Plantilla base
│   ├── login.html          # Página de login con OAuth
│   ├── dashboard.html      # Dashboard principal
│   ├── manage_patients.html # Gestión de pacientes
│   └── game.html           # Juego de entrenamiento
├── static/
│   ├── style.css           # Estilos CSS
│   └── game.js             # Lógica del juego
└── instance/
    └── moscowle.db         # Base de datos SQLite
```

## 🔄 Base de Datos

El sistema usa SQLite con las siguientes tablas:

**User:**
- id, username, email, password (encriptada), role, oauth_provider, oauth_id, created_at, is_active

**SessionMetrics:**
- id, user_id, game_name, accurracy, avg_time, prediction, date

## 📝 Notas Importantes

1. **NO compartir el archivo `.env`** - Contiene información sensible
2. **Cambiar SECRET_KEY** en producción
3. **Usar HTTPS** en producción
4. **Configurar Gmail App Password** para envío de emails
5. **El único terapeuta** por defecto es: mamiebamos2@gmail.com

## 🐛 Solución de Problemas

**Error al enviar emails:**
- Verifica que hayas configurado la contraseña de aplicación de Gmail
- Asegúrate de tener verificación en 2 pasos activada
- Revisa que `MAIL_USERNAME` y `MAIL_PASSWORD` estén correctos en `.env`

**OAuth no funciona:**
- Verifica que las URIs de redirección estén configuradas correctamente
- Asegúrate de haber habilitado las APIs necesarias
- Revisa que los Client IDs y Secrets estén correctos

**Error de base de datos:**
- Elimina el archivo `instance/moscowle.db` y reinicia la app
- El sistema recreará la base de datos automáticamente

## 📧 Contacto

Para soporte técnico: info@centrojuanpabloii.com

## 📄 Licencia

Este proyecto es privado y confidencial del Centro de Terapias Juan Pablo II.
