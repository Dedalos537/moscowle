# 📊 ANÁLISIS INTEGRAL ACTUALIZADO - MOSCOWLE IA MVP

**Fecha de Análisis:** 13 de enero de 2026  
**Versión del Proyecto:** 1.0 MVP  
**Estado:** ✅ ACTUALIZACIÓN COMPLETADA

---

## 🎯 Resumen Ejecutivo

Moscowle IA es una plataforma web completa de terapia digital que integra:
- **Frontend/Backend:** Flask + SQLAlchemy + SQLite
- **ML/IA:** Modelo SVM para adaptación automática de dificultad
- **Automatización:** APScheduler para tareas en background
- **Usuarios:** 3 roles (Admin, Terapeuta, Paciente/Jugador)
- **Características principales:** Juegos, métricas, pagos, notificaciones, mensajería

**Arquitectura:** Monolítica completa (no microservicios)

---

## 📦 Stack Tecnológico Completo

### Backend Framework
| Componente | Versión | Propósito |
|---|---|---|
| Flask | 2.2.5 | Framework web principal |
| Werkzeug | 2.3.8 | WSGI utilities |
| SQLAlchemy | ≥2.0.0 | ORM |
| Flask-SQLAlchemy | 3.0.3 | Integración SQLAlchemy-Flask |

### Autenticación & Seguridad
| Componente | Versión | Propósito |
|---|---|---|
| Flask-Login | 0.6.2 | Gestión de sesiones |
| Flask-Bcrypt | 1.0.1 | Encriptación de contraseñas |
| Authlib | 1.2.1 | OAuth2 (Google/Microsoft) |
| PyJWT | ≥2.8.0 | JSON Web Tokens |

### Email & Notificaciones
| Componente | Versión | Propósito |
|---|---|---|
| Flask-Mail | 0.9.1 | SMTP para envío de emails |
| email-validator | 2.1.0 | Validación RFC 5322 |
| APScheduler | 3.10.4 | Tareas programadas background |

### Data Science & ML
| Componente | Versión | Propósito |
|---|---|---|
| scikit-learn | ≥1.3.0 | Modelo SVM para predicciones |
| pandas | ≥1.5.0 | Procesamiento de datos |
| numpy | <2 | Operaciones numéricas |
| joblib | ≥1.3.0 | Serialización de modelos |

### Utilidades
| Componente | Versión | Propósito |
|---|---|---|
| python-dotenv | 1.0.0 | Gestión de variables de entorno |
| marshmallow | ≥3.21.0 | Serialización/validación de datos |
| requests | ≥2.31.0 | Cliente HTTP |

### Producción & Testing
| Componente | Versión | Propósito |
|---|---|---|
| gunicorn | ≥21.0.0 | Servidor WSGI en producción |
| pytest | ≥7.4.0 | Framework de testing |
| pytest-cov | ≥4.1.0 | Cobertura de tests |
| flake8 | ≥6.0.0 | Linting Python |

---

## 🏗️ Arquitectura del Proyecto

### Estructura de Directorios

```
moscowle_ia_mvp/
├── [Core Application]
│   ├── run.py                           # Punto de entrada (APScheduler setup)
│   ├── config.py                        # Configuración por ambiente
│   ├── requirements.txt                 # Dependencias (actualizado)
│   └── README.md                        # Documentación (actualizado)
│
├── app/                                 # Paquete principal
│   ├── __init__.py                     # Factory pattern (create_app)
│   ├── extensions.py                   # Extensiones Flask (db, bcrypt, mail, oauth)
│   ├── models.py                       # 7 modelos ORM
│   ├── utils.py                        # Funciones auxiliares
│   │
│   ├── repositories/                   # Data access layer
│   │   ├── user_repository.py
│   │   ├── appointment_repository.py
│   │   ├── metrics_repository.py
│   │   └── notification_repository.py
│   │
│   ├── routes/                         # 6 blueprints principales
│   │   ├── main.py                     # Dashboard, profile, logout
│   │   ├── auth.py                     # Login, OAuth (Google/Microsoft)
│   │   ├── api_routes.py               # APIs REST
│   │   ├── admin_routes.py             # Funciones administrativas
│   │   ├── therapist_routes.py         # Rutas de terapeuta
│   │   └── patient_routes.py           # Rutas de paciente
│   │
│   ├── services/                       # 11 servicios de lógica de negocio
│   │   ├── ai_service.py               # SVM, train_model, predicciones
│   │   ├── auth_service.py             # Autenticación
│   │   ├── email_service.py            # SMTP, plantillas
│   │   ├── appointment_service.py      # Citas, sesiones
│   │   ├── payment_service.py          # Pagos, descuentos, desactivación
│   │   ├── patient_service.py          # Gestión de pacientes
│   │   ├── admin_service.py            # Funciones admin
│   │   ├── dashboard_service.py        # Generación de dashboards
│   │   ├── game_service.py             # Gestión de juegos
│   │   ├── message_service.py          # Mensajería
│   │   └── notification_service.py     # Notificaciones
│   │
│   ├── schemas/                        # Marshmallow schemas
│   ├── templates/                      # Jinja2 templates (>20 archivos)
│   └── static/                         # CSS, JS, assets
│
├── ai_models/                          # Modelos entrenados
│   └── svm_model.pkl                   # SVM serializado (joblib)
│
├── migrations/                         # Migraciones de BD
│   └── *.py                            # 7+ scripts de migración
│
├── instance/                           # Runtime files
│   └── moscowle.db                     # SQLite (no en GIT)
│
├── documentation/                      # Docs completas
│   ├── 00_INICIO_AQUI.md
│   ├── ANALISIS_INTEGRAL_PROYECTO.md
│   ├── DIAGRAMAS_FLUJO_DETALLADOS.md
│   ├── CHECKLIST_FASE_5.md
│   └── más...
│
└── .env                                # Variables (NO GIT)
```

---

## 💾 Modelo de Datos (7 Tablas)

### 1. **User**
```sql
PK: id
Campos: username, email (UNIQUE), password (BCRYPT)
Roles: admin, terapista, jugador
OAuth: oauth_provider, oauth_id
Perfil: avatar, phone, date_of_birth, timezone
Terapia: assigned_therapist_id, game_profile
Pago: payment_plan, payment_due_date, payment_amount
Relaciones: assigned_patients (backref), payments
```

### 2. **Appointment**
```sql
PK: id
FKs: therapist_id, patient_id (User)
Campos: title, start_time, end_time
Status: scheduled, completed, cancelled
Attendance: pending, present, absent
Datos: location, notes, games (JSON)
```

### 3. **Payment**
```sql
PK: id
FK: patient_id (User)
Campos: amount, date, method (transfer, yape, cash, card)
Campos: receipt_image_path, status, discount
Relación: backref 'payments' en User
```

### 4. **Game**
```sql
PK: id
Campos: title, filename (UNIQUE), description, thumbnail
Flags: is_active, created_at
Juegos: aprender_a_mover_las_flechas.html, cuento_cenicienta.html
```

### 5. **AppointmentGame**
```sql
PK: id
FKs: appointment_id, game_id
Campos: config (JSON), status (pending, completed)
```

### 6. **SessionMetrics**
```sql
PK: id
FKs: user_id, session_id, game_id
Campos: game_name, accuracy, avg_time, prediction
Fecha: date (datetime)
```

### 7. **Notification** (implícito)
```sql
Sistema de notificaciones integrado
Seguimiento de alertas y recordatorios
```

---

## 🤖 Sistema de IA/ML

### Modelo: SVM (Support Vector Machine)

**Ubicación:** `app/services/ai_service.py`

**Función:** Clasificar el progreso del paciente en 3 niveles

**Datos de entrada:**
- `accuracy`: Precisión en el juego (0-100%)
- `avg_time_ms`: Tiempo promedio de respuesta en milisegundos

**Predicción:**
```python
1 = Avanzar de Nivel    # accuracy >= 80% AND avg_time <= 1500ms
0 = Mantener Nivel      # Promedio (60%-80% OR 1500-2500ms)
2 = Retroceder/Apoyo    # accuracy < 60% OR avg_time > 2500ms
```

**Entrenamiento:**
- 300 puntos sintéticos (datos de base)
- Datos reales de sesiones (adaptación)
- Reentrenamiento automático

**Modelo serializado:** `ai_models/svm_model.pkl` (joblib)

---

## 📊 Flujos Principales

### 1. Autenticación
```
Usuario → Login/OAuth
  ↓
  Email válido? + Contraseña correcta?
  ↓
  Crear sesión (Flask-Login)
  ↓
  Redirect a Dashboard (por rol)
```

### 2. Creación de Paciente
```
Terapeuta → Agregar Paciente
  ↓
  Generar contraseña segura
  ↓
  Crear User (role=jugador)
  ↓
  Enviar email SMTP
  ↓
  Paciente inicializa sesión
```

### 3. Sesión de Terapia
```
Terapeuta → Crear Cita + Asignar Juegos
  ↓
  Paciente → Juega en Appointment
  ↓
  Capturar: accuracy, avg_time
  ↓
  SessionMetrics (BD)
  ↓
  SVM → Predicción (0, 1, 2)
  ↓
  Dashboard Terapeuta (gráficas)
  ↓
  Terapeuta ajusta Plan
```

### 4. Gestión de Pagos
```
Paciente → Realizar Pago
  ↓
  Cargar comprobante (imagen)
  ↓
  Admin → Validar
  ↓
  Marcar como Pagado + Descuentos
  ↓
  APScheduler → Recordatorios automáticos
  ↓
  Si vencido >30 días → Desactivar cuenta
```

### 5. Notificaciones
```
APScheduler (cada hora) → auto_update_session_status()
  ↓
  Sesiones expiradas → Cambiar estado a completed
  
APScheduler (diariamente) → check_payment_reminders()
  ↓
  Pagos próximos → Enviar email
  ↓
  Pagos vencidos → Desactivar user
```

---

## 🔐 Seguridad Implementada

| Aspecto | Implementación | Score |
|---|---|---|
| **Encriptación de contraseñas** | Bcrypt con salt automático | ✅ |
| **Validación de emails** | RFC 5322 con email-validator | ✅ |
| **Manejo de sesiones** | Flask-Login session tokens | ✅ |
| **Variables protegidas** | python-dotenv para credenciales | ✅ |
| **OAuth2** | Google y Microsoft (configurables) | ✅ |
| **Control de acceso (RBAC)** | Roles: admin, terapista, jugador | ✅ |
| **Separación de datos** | Pacientes solo ven datos propios | ✅ |
| **Rate limiting** | NO implementado | ❌ |
| **HTTPS en producción** | NO (solo http desarrollo) | ❌ |
| **CSRF tokens** | NO implementado | ❌ |
| **SQL Injection prevention** | SQLAlchemy (parametrizado) | ✅ |

**Score de Seguridad Actual: 5/10**

---

## 📅 Tareas Automatizadas (APScheduler)

### En `run.py`:

1. **`auto_update_session_status()`**
   - Frecuencia: Cada hora
   - Acción: Actualizar sesiones expiradas a "completed"
   - Scope: Todos los pacientes

2. **`check_payment_reminders()`**
   - Frecuencia: Diariamente
   - Acciones:
     - Enviar recordatorios de pagos próximos
     - Desactivar cuentas con pagos >30 días vencidos
   - Scope: Todos los pacientes

---

## 📨 Sistema de Email

### Configuración SMTP
```env
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=tu_email@gmail.com
MAIL_PASSWORD=contraseña_aplicacion  # NOT contraseña cuenta
MAIL_DEFAULT_SENDER=tu_email@gmail.com
```

### Plantillas
- Bienvenida con credenciales
- Recordatorio de citas
- Notificación de pagos vencidos
- Mensajes de terapeuta

### Servicio: `app/services/email_service.py`

---

## 🎮 Juegos Terapéuticos

### Estructura
```
app/static/games/
├── aprender_a_mover_las_flechas.html  # Arrow key training
├── cuento_cenicienta.html              # Interactive story
└── [extensible para más]
```

### Captura de Métricas
```javascript
// En game.js
- accuracy: % de respuestas correctas
- avg_time: tiempo promedio por acción
- Envía a /api/save_metrics (POST)
```

### Almacenamiento: SessionMetrics

---

## 🌐 Rutas & Blueprints

### main.py (Dashboard routing)
```
/ → redirect a login
/dashboard → router por rol
/game, /logout → rutas principales
/messages, /profile → routers por rol
```

### auth.py (Autenticación)
```
/login (GET/POST)
/logout
/authorize/google (OAuth)
/authorize/microsoft (OAuth)
/api/auth/validate (POST)
```

### api_routes.py (REST APIs)
```
/api/save_metrics (POST)
/api/[otros endpoints específicos]
```

### admin_routes.py
```
/admin/dashboard
/admin/payments
/admin/users
/admin/[funciones admin]
```

### therapist_routes.py
```
/therapist/dashboard
/therapist/appointments
/therapist/patients
/therapist/[funciones terapeuta]
```

### patient_routes.py
```
/patient/dashboard
/patient/games
/patient/appointments
/patient/[funciones paciente]
```

---

## 📈 Estado Actual del Proyecto

### ✅ Completado (MVP)
- [x] Autenticación local y OAuth2
- [x] Modelo ORM completo (7 tablas)
- [x] 3 roles de usuario con acceso controlado
- [x] Sistema de emails SMTP
- [x] 2 juegos terapéuticos funcionales
- [x] Captura de métricas en tiempo real
- [x] Modelo SVM entrenado y operativo
- [x] Dashboards por rol
- [x] Gestión de citas y sesiones
- [x] Sistema de pagos con múltiples métodos
- [x] Recordatorios automáticos (APScheduler)
- [x] Sistema de mensajería
- [x] Validación de inputs

### ⚠️ Pendiente (Mejoras Post-MVP)
- [ ] HTTPS en producción
- [ ] Rate limiting y throttling
- [ ] CSRF tokens
- [ ] Más juegos terapéuticos
- [ ] Dashboard con más gráficas
- [ ] Análisis predictivo avanzado
- [ ] Integración con Google Drive
- [ ] Responsive design mejorado
- [ ] Tests unitarios y e2e completos
- [ ] Documentación API (Swagger)
- [ ] CI/CD pipeline

---

## 🚀 Instrucciones de Despliegue

### Desarrollo
```bash
python run.py
# Accede a http://127.0.0.1:5000
```

### Producción
```bash
gunicorn --workers 4 --bind 0.0.0.0:8000 run:app
```

### Configuración `.env`
- Cambiar `SECRET_KEY` a valor aleatorio fuerte
- Usar `DEBUG=False`
- Configurar MAIL_PASSWORD con Gmail App Password
- Configurar OAuth2 si es necesario

---

## 📊 Estadísticas del Proyecto

| Métrica | Valor |
|---|---|
| **Archivos Python** | ~40+ |
| **Modelos ORM** | 7 |
| **Servicios** | 11 |
| **Blueprints** | 6 |
| **Dependencias** | 23 |
| **Líneas de código** | ~5,000+ |
| **Plantillas HTML** | >20 |
| **Base de datos** | SQLite |
| **Juegos** | 2 implementados |

---

## 📝 Cambios en esta Actualización

### ✅ requirements.txt
- Reorganizado por categoría
- Agregadas versiones específicas
- Agregados: gunicorn, pytest, pytest-cov, flake8
- Agregado: PyJWT para JWT support

### ✅ README.md
- Completo rediseño estructural
- Agregadas tablas de características
- Secciones detalladas de cada componente
- Flujos de trabajo visuales
- Stack tecnológico completo
- Troubleshooting expandido
- Documentación de modelo de datos
- Score de seguridad actual

### ✅ ANALISIS_PROYECTO_ACTUALIZADO.md (este archivo)
- Análisis técnico integral
- Arquitectura detallada
- Stack completo
- Flujos de datos
- Estado actual del proyecto

---

## 📚 Documentación de Referencia

Para más información:
- [00_INICIO_AQUI.md](documentation/00_INICIO_AQUI.md)
- [ANALISIS_INTEGRAL_PROYECTO.md](documentation/ANALISIS_INTEGRAL_PROYECTO.md)
- [DIAGRAMAS_FLUJO_DETALLADOS.md](documentation/DIAGRAMAS_FLUJO_DETALLADOS.md)
- [CHECKLIST_FASE_5.md](documentation/CHECKLIST_FASE_5.md)

---

## 🎓 Conclusión

Moscowle IA es una plataforma completa, modular y extensible con:
- ✅ Arquitectura sólida
- ✅ Funcionalidades MVP completas
- ✅ Sistema de IA operativo
- ✅ Seguridad básica implementada
- ⚠️ Mejoras de seguridad y escalabilidad pendientes

**Listo para: Entorno de desarrollo y testing**
**Requiere antes de producción: HTTPS, Rate limiting, CSRF, Tests completos**

---

**Actualizado por:** Análisis Integral Automático  
**Fecha:** 13 de enero de 2026  
**Versión:** 1.0 MVP
