# 🎮 Moscowle IA - Sistema de Terapia Digital Asistido por IA

**Centro de Terapias Juan Pablo II**

Plataforma integral de terapia digital con juegos terapéuticos e inteligencia artificial para seguimiento, evaluación y adaptación del tratamiento de pacientes.

---

## 📋 Descripción General del Proyecto

Moscowle IA es una solución web full-stack (Flask + SQLite) que integra:

- 🎮 **Juegos terapéuticos interactivos** para pacientes (enfoque en menores de edad)
- 📊 **Dashboard para terapeutas** con análisis de progreso y métricas detalladas
- 🔧 **Panel administrativo** para gestión de usuarios, pagos y configuración
- 🤖 **Sistema de IA/ML (SVM)** para adaptación automática de dificultad
- 📅 **Gestión de citas y sesiones** con validación de asistencia
- 💳 **Sistema de pagos** con múltiples métodos y seguimiento automático
- 🔔 **Notificaciones y recordatorios** automatizados (APScheduler)
- 💬 **Sistema de mensajería** entre terapeutas y pacientes
- 🔐 **Autenticación avanzada** con OAuth2 (Google/Microsoft) y local

---

## 🎯 Características Principales

### 🔐 Seguridad y Autenticación

| Característica | Implementación |
|---|---|
| **Encriptación de contraseñas** | Bcrypt (BCRYPT algorithm) |
| **Autenticación OAuth2** | Google y Microsoft (configurables) |
| **Validación de emails** | email-validator con RFC 5322 |
| **Gestión de sesiones** | Flask-Login con session tokens |
| **Variables de entorno** | python-dotenv para credenciales |
| **Control de acceso (RBAC)** | Roles: admin, terapista, jugador |

### 👥 Gestión de Usuarios Multi-Rol

#### **Administrador (Admin)**
- Crear y gestionar terapeutas
- Agregar pacientes (solo a través del terapeuta asignado)
- Gestionar pagos y visualizar historial
- Visualizar reportes y estadísticas globales
- Configurar juegos y su disponibilidad

#### **Terapeutas (Profesionales)**
- Crear y gestionar sus citas
- Asignar juegos a pacientes específicos
- Visualizar métricas y progreso de pacientes asignados
- Enviar y recibir mensajes de pacientes
- Validar asistencia a sesiones
- Ver análisis de desempeño

#### **Pacientes (Jugadores)**
- Jugar con los juegos asignados
- Ver su progreso y métricas
- Recibir recomendaciones de la IA
- Ver próximas citas
- Comunicarse con su terapeuta
- Actualizar información de perfil

### 📧 Sistema de Emails

- ✅ Envío automático de credenciales a nuevos pacientes
- ✅ Configuración SMTP con Gmail (Gmail App Password)
- ✅ Plantillas HTML personalizadas
- ✅ Notificaciones de citas próximas
- ✅ Recordatorios automáticos de pago vencido
- ✅ Correos de bienvenida con instrucciones

### 🎮 Juegos Terapéuticos

**Base de datos de juegos** con:
- Configuración por dificultad escalable
- Asignación inteligente por terapeuta
- Seguimiento de métricas de desempeño
- Captura de: precisión, tiempo promedio, predicción de progreso

**Juegos implementados:**
1. **Aprender a mover las flechas** - Entrenamiento de motricidad fina
2. **Cuento: Cenicienta** - Lectura interactiva y comprensión
3. (Arquitectura extensible para más juegos)

### 📊 Análisis y Métricas con IA

**Modelo Machine Learning (SVM):**
- **Clasificador de progreso** entrenado con datos sintéticos + reales
- **3 niveles de recomendación:**
  - `1` = Avanzar de nivel (Accuracy ≥80% Y Tiempo ≤1500ms)
  - `0` = Mantener nivel (Promedio, rango intermedio)
  - `2` = Retroceder/Apoyo (Accuracy <60% O Tiempo >2500ms)

**Métricas capturadas:**
- Precisión (accuracy) en juegos
- Tiempo promedio de respuesta
- Predicción automática de nivel
- Fecha y hora de sesión
- Historial de progreso

**Dashboard de Análisis:**
- Gráficas de progreso en el tiempo
- Tendencias por juego
- Comparativa de desempeño
- Recomendaciones de intervención

### 📅 Gestión de Citas y Sesiones

- Creación de citas con horarios específicos
- Asignación flexible de juegos a citas
- Auto-actualización de estados de sesión expiradas
- Validación de asistencia: presente/ausente/pendiente
- Historial completo de citas por paciente
- Notificaciones de citas próximas

### 💳 Sistema de Pagos

**Planes de pago:**
- Mensual (30 días)
- Quincenal (15 días)

**Métodos de pago aceptados:**
- Transferencia bancaria
- Yape (billetera digital)
- Efectivo
- Tarjeta de crédito

**Funcionalidades:**
- Seguimiento de pagos: estado, descuentos, fechas de vencimiento
- Carga de comprobantes con imágenes
- Recordatorios automáticos de pagos próximos
- Desactivación automática de cuentas con pagos vencidos (>30 días)
- Historial completo de transacciones

### 🔔 Notificaciones y Recordatorios

**Trabajos automatizados (APScheduler):**
- **Cada hora:** Auto-actualización de estado de sesiones expiradas
- **Diariamente:** Verificación de pagos vencidos
- **Cuando es necesario:** Envío de recordatorios de pago

**Sistema de notificaciones:**
- En-plataforma: notificaciones internas
- Email: recordatorios por correo electrónico
- Historial de notificaciones

### 💬 Sistema de Mensajería

- Comunicación directa entre terapeutas y pacientes
- Historial de conversaciones persistente
- Notificaciones de nuevos mensajes
- Marca como leído/no leído
- Búsqueda en conversaciones

### 📈 Paneles de Control (Dashboards)

#### **Admin Dashboard**
- Vista de todos los usuarios
- Gestión de pagos y reportes
- Estadísticas de sistema
- Configuración de juegos

#### **Therapist Dashboard**
- Citas programadas
- Pacientes asignados
- Métricas de progreso
- Mensajes pendientes
- Reportes de sesiones

#### **Patient Dashboard**
- Próximas citas
- Progreso en juegos
- Mensajes del terapeuta
- Información de perfil
- Historial de sesiones

---

## 📦 Stack Tecnológico

### Backend
- **Framework:** Flask 2.2.5
- **Database:** SQLAlchemy + SQLite
- **Autenticación:** Flask-Login, Authlib, Flask-Bcrypt
- **Email:** Flask-Mail con SMTP
- **Tareas programadas:** APScheduler
- **Validación:** email-validator, marshmallow

### Machine Learning & Análisis
- **ML Framework:** scikit-learn (SVM)
- **Procesamiento de datos:** pandas, numpy
- **Serialización de modelos:** joblib

### Frontend
- **Templating:** Jinja2 (HTML templates)
- **Estilos:** CSS3
- **Interactividad:** JavaScript vanilla

### DevOps & Producción
- **Servidor:** Gunicorn
- **Testing:** pytest, pytest-cov
- **Linting:** flake8

---

## 📋 Requisitos Previos

- Python 3.8 o superior
- pip (gestor de paquetes de Python)
- Cuenta de Gmail con verificación 2FA (para envío de emails)
- (Opcional) Credenciales OAuth2 de Google y Microsoft

---

## 🔧 Instalación y Configuración

### 1. Clonar el repositorio

```bash
cd /Users/apple/Documents/moscowle_ia_mvp
```

### 2. Crear entorno virtual

```bash
# macOS/Linux
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno

Crea un archivo `.env` en la raíz del proyecto:

```env
# ========== FLASK CONFIGURATION ==========
SECRET_KEY=moscowle_secret_key_production_2024
FLASK_ENV=production
DEBUG=False

# ========== DATABASE ==========
SQLALCHEMY_DATABASE_URI=sqlite:///moscowle.db

# ========== EMAIL CONFIGURATION (Gmail SMTP) ==========
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=tu_email@gmail.com
MAIL_PASSWORD=tu_contraseña_de_aplicacion
MAIL_DEFAULT_SENDER=tu_email@gmail.com

# ========== GEMINI API (Opcional, para futura IA) ==========
GEMINI_API_KEY=tu_gemini_api_key

# ========== OAUTH2 GOOGLE (Opcional) ==========
GOOGLE_CLIENT_ID=tu_google_client_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=tu_google_client_secret

# ========== OAUTH2 MICROSOFT (Opcional) ==========
MICROSOFT_CLIENT_ID=tu_microsoft_client_id
MICROSOFT_CLIENT_SECRET=tu_microsoft_client_secret

# ========== ADMIN CREDENTIALS ==========
ADMIN_EMAIL=diegocenteno537@gmail.com
ADMIN_PASSWORD=tu_contraseña_segura
```

### 5. Configurar Gmail para envío de emails

1. Ve a tu cuenta Google: https://myaccount.google.com/
2. Activa **Verificación en 2 pasos** (Seguridad)
3. Ve a **Contraseñas de aplicaciones**: https://myaccount.google.com/apppasswords
4. Selecciona "Correo" como tipo de aplicación
5. Genera una **contraseña de aplicación** (16 caracteres)
6. Copia esa contraseña en `MAIL_PASSWORD` del `.env`

### 6. (Opcional) Configurar OAuth2

#### **Google OAuth2:**
1. Ve a https://console.cloud.google.com/
2. Crea un nuevo proyecto
3. Habilita "Google+ API"
4. Ve a "Credenciales" → "Crear credenciales" → "ID de cliente de OAuth"
5. Selecciona "Aplicación web"
6. Agrega URI de redirección: `http://127.0.0.1:5000/authorize/google`
7. Copia `Client ID` y `Client Secret` al `.env`

#### **Microsoft OAuth2:**
1. Ve a https://portal.azure.com/
2. Registra una nueva aplicación en Azure AD
3. Configura permisos: `openid`, `email`, `profile`
4. Agrega URI de redirección: `http://127.0.0.1:5000/authorize/microsoft`
5. Copia `Client ID` y `Client Secret` al `.env`

---

## 🚀 Ejecutar la Aplicación

### Desarrollo

```bash
python run.py
```

Accede a: **http://127.0.0.1:5000**

### Producción (con Gunicorn)

```bash
gunicorn --workers 4 --bind 0.0.0.0:8000 run:app
```

---

## 👤 Credenciales de Acceso por Defecto

### Terapeuta (Administrador)
- **Email:** mamiebamos2@gmail.com
- **Contraseña:** @dm1n_123!
- **Rol:** admin

**Nota:** Estas credenciales pueden variar según la configuración del `.env`. Cambiar en producción.

---

## 📱 Uso del Sistema

### 🎓 Para Terapeutas

1. **Iniciar sesión** con correo y contraseña
2. **Dashboard del Terapeuta:**
   - Ver citas programadas
   - Visualizar métricas de pacientes asignados
   - Acceder a mensajería
   - Revisar reportes de sesiones

3. **Gestionar Citas:**
   - Crear nueva cita (fecha, hora, paciente)
   - Asignar juegos a la cita
   - Validar asistencia después de la sesión

4. **Análisis de Pacientes:**
   - Ver gráficas de progreso
   - Revisar predicciones de la IA
   - Enviar mensajes y recomendaciones

### 👶 Para Pacientes (Jugadores)

1. **Recibir email** con credenciales desde el terapeuta
2. **Iniciar sesión** en la plataforma
3. **Dashboard del Paciente:**
   - Ver próximas citas
   - Acceder a juegos asignados
   - Ver tu progreso
   - Leer mensajes del terapeuta

4. **Jugar:**
   - Seleccionar un juego asignado
   - Jugar el minijuego interactivo
   - Ver resultados inmediatamente (precisión, tiempo)
   - Recibir recomendaciones de la IA

### 🔧 Para Administradores

1. **Panel Admin:**
   - Ver todos los usuarios
   - Gestionar pagos
   - Visualizar estadísticas globales
   - Configurar disponibilidad de juegos

2. **Crear Terapeutas:**
   - Agregar nuevo terapeuta
   - Asignar pacientes
   - Cambiar permisos

---

## 🛡️ Características de Seguridad Implementadas

| Característica | Descripción |
|---|---|
| ✅ **Contraseñas encriptadas** | Bcrypt con salt automático |
| ✅ **Validación de emails** | RFC 5322 con email-validator |
| ✅ **Tokens de sesión** | Flask-Login session management |
| ✅ **Variables protegidas** | python-dotenv para credenciales |
| ✅ **Verificación de usuarios** | Validación de existencia antes de login |
| ✅ **Control de acceso (RBAC)** | Restricción por roles (admin/terapeuta/jugador) |
| ✅ **Separación de datos** | Pacientes solo ven sus datos |
| ✅ **Gestión de sesiones** | Auto-logout en inactividad |

**Score de Seguridad Actual:** 5/10
- ✅ Implementado: Autenticación, Encriptación, Validación
- ⚠️ Pendiente: HTTPS, Rate limiting, CSRF tokens, SQL injection prevention

---

## 📁 Estructura del Proyecto

```
moscowle_ia_mvp/
├── app.py                           # Archivo principal (app.py.backup)
├── run.py                           # Punto de entrada de la aplicación
├── config.py                        # Configuración de la aplicación
├── requirements.txt                 # Dependencias de Python
├── .env                             # Variables de entorno (NO SUBIR A GIT)
│
├── app/
│   ├── __init__.py                 # Factory de la aplicación
│   ├── extensions.py               # Extensiones (db, bcrypt, mail, oauth)
│   ├── models.py                   # Modelos de base de datos
│   ├── utils.py                    # Utilidades generales
│   │
│   ├── repositories/               # Acceso a datos
│   │   ├── user_repository.py
│   │   ├── appointment_repository.py
│   │   ├── metrics_repository.py
│   │   └── notification_repository.py
│   │
│   ├── routes/                     # Rutas de la aplicación
│   │   ├── main.py                 # Rutas principales (dashboard, logout)
│   │   ├── auth.py                 # Autenticación (login, OAuth)
│   │   ├── api_routes.py           # APIs REST
│   │   ├── admin_routes.py         # Rutas admin
│   │   ├── therapist_routes.py     # Rutas terapeutas
│   │   └── patient_routes.py       # Rutas pacientes
│   │
│   ├── services/                   # Lógica de negocio
│   │   ├── ai_service.py           # Modelo SVM y predicciones
│   │   ├── auth_service.py         # Autenticación
│   │   ├── email_service.py        # Envío de emails
│   │   ├── appointment_service.py  # Gestión de citas
│   │   ├── payment_service.py      # Sistema de pagos
│   │   ├── patient_service.py      # Gestión de pacientes
│   │   ├── admin_service.py        # Funciones admin
│   │   ├── dashboard_service.py    # Generación de dashboards
│   │   ├── game_service.py         # Gestión de juegos
│   │   ├── message_service.py      # Sistema de mensajería
│   │   └── notification_service.py # Notificaciones
│   │
│   ├── schemas/                    # Esquemas de datos (marshmallow)
│   │   └── __init__.py
│   │
│   ├── templates/                  # Plantillas HTML
│   │   ├── base.html               # Plantilla base
│   │   ├── login.html              # Página de login
│   │   ├── game.html               # Juego interactivo
│   │   ├── games.html              # Galería de juegos
│   │   ├── admin/
│   │   │   ├── dashboard.html
│   │   │   ├── payments.html
│   │   │   ├── payment_history.html
│   │   │   ├── reports.html
│   │   │   └── ...
│   │   ├── therapist/
│   │   │   ├── dashboard.html
│   │   │   ├── patients.html
│   │   │   └── ...
│   │   └── patient/
│   │       ├── dashboard.html
│   │       └── ...
│   │
│   ├── static/                     # Archivos estáticos
│   │   ├── style.css               # Estilos CSS
│   │   ├── game.js                 # Lógica de juegos
│   │   ├── games/                  # HTML de juegos
│   │   │   ├── aprender_a_mover_las_flechas.html
│   │   │   ├── cuento_cenicienta.html
│   │   │   └── ...
│   │   └── uploads/                # Cargas de usuarios
│   │       ├── receipts/           # Comprobantes de pago
│   │       └── session_images/     # Imágenes de sesiones
│   │
│   └── __pycache__/                # Caché de Python
│
├── ai_models/                       # Modelos entrenados
│   └── svm_model.pkl               # Modelo SVM serializado
│
├── migrations/                      # Migraciones de base de datos
│   ├── add_payment_system.py
│   ├── add_status_tracking_columns.py
│   ├── add_receipt_image.py
│   └── ...
│
├── instance/
│   └── moscowle.db                 # Base de datos SQLite
│
├── documentation/                   # Documentación del proyecto
│   ├── 00_INICIO_AQUI.md
│   ├── ANALISIS_INTEGRAL_PROYECTO.md
│   ├── CHECKLIST_FASE_5.md
│   ├── CONFIGURACION_EMAIL.md
│   └── ...
│
└── __pycache__/                    # Caché de Python
```

---

## 🗄️ Modelo de Base de Datos

### Tablas Principales

#### **User**
```sql
- id (PK)
- username, email (UNIQUE), password (encriptada)
- role (admin | terapista | jugador)
- oauth_provider, oauth_id (para OAuth2)
- created_at, is_active (booleano)
- avatar, phone, date_of_birth, timezone
- assigned_therapist_id (FK a User)
- payment_plan, payment_due_date, payment_amount
```

#### **Appointment**
```sql
- id (PK)
- therapist_id, patient_id (FK a User)
- title, start_time, end_time
- status (scheduled | completed | cancelled)
- attendance (pending | present | absent)
- location, notes, games (JSON)
```

#### **Payment**
```sql
- id (PK)
- patient_id (FK a User)
- amount, date, method
- receipt_image_path
- status, discount
```

#### **Game**
```sql
- id (PK)
- title, filename (UNIQUE)
- description, thumbnail
- is_active (booleano)
- created_at
```

#### **SessionMetrics**
```sql
- id (PK)
- user_id, session_id, game_id (FKs)
- game_name, accuracy, avg_time, prediction
- date
```

#### **AppointmentGame**
```sql
- id (PK)
- appointment_id, game_id (FKs)
- config (JSON con configuración específica)
- status (pending | completed)
```

---

## 📊 Flujo de Datos de la IA

```
Sesión del Paciente (Juego)
        ↓
   Capturar: Precisión, Tiempo
        ↓
   SessionMetrics (BD)
        ↓
   AI Service (SVM)
        ↓
   Predicción: 0 (mantener) | 1 (avanzar) | 2 (apoyo)
        ↓
   Dashboard del Terapeuta
```

---

## 🔄 Flujos de Trabajo Principales

### 1. Creación de Paciente
```
Admin → Crea terapeuta → Terapeuta agrega paciente
→ Sistema genera contraseña → Email con credenciales
→ Paciente inicializa sesión
```

### 2. Sesión de Terapia
```
Terapeuta crea cita → Asigna juegos → Paciente juega
→ Métricas capturadas → IA predice nivel
→ Terapeuta revisa progreso → Ajusta tratamiento
```

### 3. Gestión de Pagos
```
Paciente realiza pago → Carga comprobante
→ Admin valida → Marca como pagado
→ Recordatorios si está vencido → Desactiva si es >30 días
```

---

## ⚙️ Tareas Automatizadas (APScheduler)

| Tarea | Frecuencia | Función |
|---|---|---|
| `auto_update_session_status` | Cada hora | Actualiza estado de sesiones expiradas |
| `check_payment_reminders` | Diariamente | Envía recordatorios de pago vencido y desactiva cuentas |

---

## 🔍 Testing

### Ejecutar tests

```bash
pytest
```

### Con cobertura

```bash
pytest --cov=app
```

### Linting

```bash
flake8 app/
```

---

## 🐛 Solución de Problemas

### ❌ Error al enviar emails
```
FileNotFoundError o SMTPAuthenticationError
```
**Solución:**
- Verifica que hayas configurado la contraseña de aplicación de Gmail
- Asegúrate de tener verificación en 2 pasos activada
- Revisa que `MAIL_USERNAME` y `MAIL_PASSWORD` estén correctos en `.env`

### ❌ OAuth no funciona
```
Invalid redirect_uri
```
**Solución:**
- Verifica que las URIs de redirección estén configuradas correctamente en Google/Microsoft
- Asegúrate de haber habilitado las APIs necesarias
- Revisa que los Client IDs y Secrets estén correctos

### ❌ Error de base de datos
```
DatabaseError o IntegrityError
```
**Solución:**
- Elimina el archivo `instance/moscowle.db` y reinicia la app
- El sistema recreará la base de datos automáticamente
- Revisa que `SQLALCHEMY_DATABASE_URI` sea correcto

### ❌ Modelo IA no se carga
```
FileNotFoundError: ai_models/svm_model.pkl
```
**Solución:**
- El modelo se crea automáticamente al iniciar la app
- Si persiste, elimina `ai_models/svm_model.pkl` y reinicia

---

## 📊 Estado Actual del Proyecto

### ✅ Implementado
- [x] Autenticación (local + OAuth2)
- [x] Gestión de usuarios multi-rol
- [x] Sistema de emails SMTP
- [x] Juegos terapéuticos
- [x] Captura de métricas
- [x] Modelo SVM para predicciones
- [x] Dashboard de terapeutas
- [x] Gestión de citas
- [x] Sistema de pagos
- [x] Notificaciones automáticas
- [x] Sistema de mensajería

### ⚠️ Pendiente/Mejoras
- [ ] Implementar HTTPS en producción
- [ ] Rate limiting y CSRF tokens
- [ ] Más juegos terapéuticos
- [ ] Dashboard mejorado con más gráficas
- [ ] Integración con Google Drive para reportes
- [ ] Móvil-responsive avanzado
- [ ] Análisis predictivo avanzado con más datos

---

## 📧 Contacto y Soporte

**Centro de Terapias Juan Pablo II**
- Email: info@centrojuanpabloii.com
- Soporte técnico: contacto disponible en la plataforma

---

## 📄 Licencia

Este proyecto es **privado y confidencial** del Centro de Terapias Juan Pablo II.
No se permite reproducción, distribución o modificación sin autorización explícita.

---

## 📚 Documentación Adicional

Para análisis detallado del proyecto, consulta la carpeta `documentation/`:

- [00_INICIO_AQUI.md](documentation/00_INICIO_AQUI.md) - Introducción y resumen
- [ANALISIS_INTEGRAL_PROYECTO.md](documentation/ANALISIS_INTEGRAL_PROYECTO.md) - Análisis técnico profundo
- [DIAGRAMAS_FLUJO_DETALLADOS.md](documentation/DIAGRAMAS_FLUJO_DETALLADOS.md) - Flujos ASCII
- [CHECKLIST_FASE_5.md](documentation/CHECKLIST_FASE_5.md) - Validación pre-producción

---

**Última actualización:** 13 de enero de 2026
**Versión:** 1.0 MVP

