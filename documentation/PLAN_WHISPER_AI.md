# PLAN DE IMPLEMENTACIÓN: Whisper AI + Database + API

**Proyecto:** Moscowle IA / EduSync AI  
**Centro:** Centro de Terapias Juan Pablo II  
**Curso:** Curso Integrador II: Sistemas — UTP  
**Versión:** 1.0  
**Fecha:** Mayo 2026

---

## Índice

- [Fase 0: Foundation — Database Migration & New Models](#fase-0-foundation--database-migration--new-models)
- [Fase 1: Whisper AI Service](#fase-1-whisper-ai-service)
- [Fase 2: API Endpoints](#fase-2-api-endpoints)
- [Fase 3: Semantic Comparison & Audit Engine](#fase-3-semantic-comparison--audit-engine)
- [Fase 4: Frontend — Recording UI & Reports](#fase-4-frontend--recording-ui--reports)
- [Fase 5: Security & Compliance](#fase-5-security--compliance)
- [Sprint Mapping](#sprint-mapping)
- [Riesgos y Mitigación](#riesgos-y-mitigación)
- [Dependencias Nuevas](#dependencias-nuevas)

---

## Fase 0: Foundation — Database Migration & New Models

**Objetivo:** Migrar de SQLite a PostgreSQL con esquema listo para replicación Maestro-Esclavo, y crear los modelos de datos para audio, transcripción y reportes.

### 0.1 Migración a PostgreSQL

- Agregar dependencias: `psycopg2-binary`, `flask-migrate` (Alembic)
- Configurar `SQLALCHEMY_DATABASE_URI` para PostgreSQL en lugar de SQLite
- Crear migración inicial que refleje el schema actual
- Implementar campos de auditoría en TODAS las tablas:
  - `creado_por` (VARCHAR)
  - `fecha_registro` (DATETIME)
  - `fecha_modificacion` (DATETIME, nullable)
  - `estado_registro` (TINYINT — 1=Activo, 0=Inactivo)
- Configurar índices B-Tree estratégicos por tabla (ver Context2.md):

| Tabla | Índice | Columnas | Justificación |
|-------|--------|----------|---------------|
| `appointment` | `idx_appointments_therapist_id` | `therapist_id` | KPIs del director (RF-22) |
| `appointment` | `idx_appointments_status_date` | `status, session_date` | Agenda diaria del terapista |
| `appointment` | `idx_appointments_patient_id` | `patient_id` | Historial clínico (HU-03) |
| `user` | `idx_users_role` | `role` | Filtro por rol |
| `user` | `idx_users_therapist` | `assigned_therapist_id` | Pacientes por terapista |

### 0.2 Modelos Nuevos

#### SessionRecording
```python
class SessionRecording(db.Model):
    __tablename__ = 'session_recording'
    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointment.id'), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.BigInteger, nullable=True)  # bytes
    duration_seconds = db.Column(db.Float, nullable=True)
    mime_type = db.Column(db.String(50), nullable=True)  # audio/wav, audio/mp3, etc.
    status = db.Column(db.String(30), default='uploading')
    # uploading, processing, completed, failed, deleted
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    deleted_at = db.Column(db.DateTime, nullable=True)  # secure deletion tracking
    estado_registro = db.Column(db.Integer, default=1)

    appointment = db.relationship('Appointment', backref=db.backref('recordings', lazy=True))
    uploaded_by = db.relationship('User', foreign_keys=[uploaded_by_id])
```

#### Transcription
```python
class Transcription(db.Model):
    __tablename__ = 'transcription'
    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointment.id'), nullable=False)
    recording_id = db.Column(db.Integer, db.ForeignKey('session_recording.id'), nullable=False)
    full_text = db.Column(db.Text, nullable=False)
    segments = db.Column(db.JSON, nullable=True)  # [{start, end, text, confidence}]
    model_used = db.Column(db.String(50), default='whisper-large-v3')
    language = db.Column(db.String(10), nullable=True)
    confidence_score = db.Column(db.Float, nullable=True)  # 0.0 - 1.0
    processing_time_ms = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    estado_registro = db.Column(db.Integer, default=1)

    appointment = db.relationship('Appointment', backref=db.backref('transcriptions', lazy=True))
    recording = db.relationship('SessionRecording', backref=db.backref('transcriptions', lazy=True))
```

#### TherapyObjective
```python
class TherapyObjective(db.Model):
    __tablename__ = 'therapy_objective'
    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointment.id'), nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(30), default='pendiente')
    # pendiente, logrado, parcial, no_cubierto
    source = db.Column(db.String(30), default='plan_extracted')
    # plan_extracted, ai_identified, manual
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    estado_registro = db.Column(db.Integer, default=1)

    appointment = db.relationship('Appointment', backref=db.backref('objectives', lazy=True))
```

#### AuditReport
```python
class AuditReport(db.Model):
    __tablename__ = 'audit_report'
    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointment.id'), nullable=False)
    transcription_id = db.Column(db.Integer, db.ForeignKey('transcription.id'), nullable=False)
    compliance_index = db.Column(db.Float, nullable=False)  # 0.0 - 100.0
    objectives_analysis = db.Column(db.JSON, nullable=True)
    # [{objective_id, description, status, evidence_quote, timestamp_start, timestamp_end}]
    summary = db.Column(db.Text, nullable=True)  # AI-generated summary
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)
    generated_by = db.Column(db.String(30), default='system')  # system, therapist
    estado_registro = db.Column(db.Integer, default=1)

    appointment = db.relationship('Appointment', backref=db.backref('audit_reports', lazy=True))
    transcription = db.relationship('Transcription', backref=db.backref('audit_reports', lazy=True))
```

#### ProgressReport
```python
class ProgressReport(db.Model):
    __tablename__ = 'progress_report'
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    block_start_date = db.Column(db.Date, nullable=False)
    block_end_date = db.Column(db.Date, nullable=False)
    summary = db.Column(db.Text, nullable=True)
    objectives_progress = db.Column(db.JSON, nullable=True)
    # [{objective, initial_status, current_status, trend}]
    status = db.Column(db.String(30), default='draft')
    # draft, pending_approval, approved, sent
    approved_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)
    estado_registro = db.Column(db.Integer, default=1)

    patient = db.relationship('User', foreign_keys=[patient_id])
    approved_by = db.relationship('User', foreign_keys=[approved_by_id])
```

### 0.3 Replicación Maestro-Esclavo (Context2)

- Configurar variables de entorno para nodos:

```env
# Nodo Maestro (Escrituras)
DB_WRITE_HOST=192.168.10.10
DB_WRITE_PORT=5432
DB_WRITE_USER=app_writer
DB_WRITE_PASS=*****
DB_WRITE_NAME=edusync_ai

# Nodo Esclavo (Lecturas)
DB_READ_HOST=192.168.10.20
DB_READ_PORT=5432
DB_READ_USER=app_reader
DB_READ_PASS=*****
DB_READ_NAME=edusync_ai

# Pool de Conexiones
DB_POOL_MIN=5
DB_POOL_MAX=20
DB_POOL_TIMEOUT=30000
```

- Implementar `ReadWriteSplitRepository` base class
  - `save()`, `update()`, `delete()` → Nodo Maestro
  - `findAll()`, `findById()` → Nodo Esclavo
- Configurar `pg_stat_replication` monitoring

---

## Fase 1: Whisper AI Service

**Objetivo:** Implementar transcripción de audio usando OpenAI Whisper (HU-08).

**Relación con Context1.md:**
- HU-07: Grabación de audio con micrófono lavalier
- HU-08: Transcripción con timestamps y eliminación del archivo
- Riesgo R03: Precisión insuficiente de Whisper → mitigado con noisereduce

### 1.1 Dependencias

```
openai-whisper         # Modelo de transcripción
faster-whisper         # Alternativa más rápida (recomendada para producción)
pydub                  # Conversión de formatos de audio
noisereduce            # Reducción de ruido (mitigación R03)
librosa                # Análisis de audio
soundfile              # I/O de audio
celery[redis]          # Tareas asíncronas (ya configurado en config.py)
```

### 1.2 Servicio: `app/services/whisper_service.py`

```
WhisperService
├── __init__() → Carga modelo Whisper (large-v3 o turbo)
│
├── transcribe(file_path) → Pipeline completo:
│   ├── 1. validate_audio() → formato, duración, tamaño
│   ├── 2. preprocess()
│   │   ├── convert_to_wav() → estandarizar formato
│   │   ├── normalize_volume() → nivel consistente
│   │   └── reduce_noise() → noisereduce (R03)
│   ├── 3. transcribe_segments()
│   │   ├── Whisper.transcribe() con timestamps
│   │   ├── segmentos con start/end/text/confidence
│   │   └── detección de lenguaje automática
│   ├── 4. post_process()
│   │   ├── merge_small_segments()
│   │   ├── clean_text() → corregir puntuación
│   │   └── format_output()
│   └── 5. return {full_text, segments, language, confidence}
│
├── get_supported_languages() → Lista de idiomas
├── get_audio_duration(file_path) → Duración en segundos
└── estimate_cost(duration_minutes) → Tiempo estimado de procesamiento
```

### 1.3 Procesamiento Asíncrono (Celery)

```python
# app/tasks.py
@celery.task(bind=True, max_retries=3)
def process_session_audio(self, recording_id):
    """
    Pipeline asíncrono de procesamiento de audio.
    1. Cargar grabación desde DB
    2. Desencriptar archivo (si está encriptado)
    3. Transcribir con Whisper
    4. Guardar Transcription en DB
    5. Encriptar y archivar (opcional)
    6. Programar eliminación segura
    7. Notificar al terapista
    """

@celery.task
def secure_delete_audio(recording_id):
    """
    Eliminación segura del archivo de audio (RNF-02, R06).
    - Sobrescribir con ceros
    - Eliminar archivo
    - Marcar como deleted en DB
    """
```

### 1.4 Almacenamiento y Cifrado

- Audio en reposo: AES-256 (HU-16)
- Ubicación: `instance/uploads/recordings/`
- Estructura: `instance/uploads/recordings/{appointment_id}/{uuid}.wav`
- Desencriptar solo durante procesamiento
- Eliminación segura post-transcripción (DoD 5220.22-M)

---

## Fase 2: API Endpoints

**Objetivo:** API RESTful para grabación, transcripción y reportes (HU-06, HU-07, HU-08, HU-09, HU-10, HU-13).

Blueprint: `recording_bp` → prefijo `/api/v2`

### 2.1 Endpoints de Grabación (HU-07)

| Método | Endpoint | Propósito |
|--------|----------|-----------|
| `POST` | `/api/v2/sessions/<id>/recording/start` | Inicializar sesión de grabación. Valida: asistencia registrada, plan cargado, micrófono conectado |
| `POST` | `/api/v2/sessions/<id>/recording/upload` | Subir chunk de audio (multipart, streaming) |
| `POST` | `/api/v2/sessions/<id>/recording/stop` | Finalizar grabación, gatillar procesamiento Whisper |
| `GET` | `/api/v2/sessions/<id>/recording` | Obtener estado de la grabación (uploading/processing/completed/failed) |
| `DELETE` | `/api/v2/sessions/<id>/recording` | Eliminar grabación (forzar) |

### 2.2 Endpoints de Transcripción (HU-08)

| Método | Endpoint | Propósito |
|--------|----------|-----------|
| `GET` | `/api/v2/sessions/<id>/transcription` | Obtener transcripción completa |
| `GET` | `/api/v2/sessions/<id>/transcription/segments` | Obtener segmentos con timestamps |
| `GET` | `/api/v2/sessions/<id>/transcription/status` | Ver estado del procesamiento |
| `GET` | `/api/v2/sessions/<id>/transcription/download` | Descargar transcripción como .txt o .srt |

### 2.3 Endpoints de Objetivos Terapéuticos (HU-06)

| Método | Endpoint | Propósito |
|--------|----------|-----------|
| `POST` | `/api/v2/sessions/<id>/objectives/extract` | Extraer objetivos del plan de sesión usando LLM |
| `GET` | `/api/v2/sessions/<id>/objectives` | Listar objetivos extraídos |
| `PUT` | `/api/v2/sessions/<id>/objectives/<obj_id>` | Actualizar/modificar objetivo (therapist validation) |

### 2.4 Endpoints de Reporte de Auditoría (HU-09, HU-10)

| Método | Endpoint | Propósito |
|--------|----------|-----------|
| `POST` | `/api/v2/sessions/<id>/compare` | Gatillar comparación semántica |
| `GET` | `/api/v2/sessions/<id>/audit-report` | Obtener reporte de auditoría |
| `POST` | `/api/v2/sessions/<id>/audit-report/regenerate` | Regenerar reporte |
| `GET` | `/api/v2/sessions/<id>/audit-report/download` | Descargar PDF del reporte |

### 2.5 Endpoints de Informe de Progreso (HU-13, HU-15)

| Método | Endpoint | Propósito |
|--------|----------|-----------|
| `POST` | `/api/v2/patients/<id>/progress-report/generate` | Generar informe de 4 semanas |
| `GET` | `/api/v2/patients/<id>/progress-report/latest` | Obtener último informe |
| `PUT` | `/api/v2/progress-reports/<id>/approve` | Aprobar informe (terapista) |
| `GET` | `/api/v2/progress-reports/<id>/download` | Descargar PDF |

---

## Fase 3: Semantic Comparison & Audit Engine

**Objetivo:** Comparar la transcripción de la sesión contra el plan terapéutico (HU-09) y generar reportes de auditoría (HU-10).

### 3.1 Servicio: `app/services/semantic_comparison_service.py`

```
SemanticComparisonService
├── compare(transcription_id, appointment_id) → AuditReport
│   ├── 1. Cargar transcripción (full_text + segments)
│   ├── 2. Cargar objetivos terapéuticos (TherapyObjective)
│   ├── 3. Para cada objetivo:
│   │   ├── Buscar coincidencias semánticas en transcripción
│   │   ├── Usar LLM (LLaMA 3 / Gemini) para clasificar:
│   │   │   - Logrado: evidencia clara y completa
│   │   │   - Parcial: evidencia parcial o mencionado
│   │   │   - No cubierto: sin evidencia
│   │   └── Extraer quote textual + timestamp
│   ├── 4. Calcular compliance_index:
│   │   └── (logrados + parciales*0.5) / total * 100
│   └── 5. Generar summary (LLM)
│
├── get_compliance_trend(patient_id, weeks=4) → [{date, index}]
└── generate_executive_summary(audit_report_id) → texto resumen
```

### 3.2 Prompt Engineering para LLaMA 3

```
System: Eres un asistente de auditoría clínica. 
Debes comparar objetivos terapéuticos con transcripciones de sesiones 
y clasificar el nivel de cumplimiento.

Input:
- Objetivo: "{descripcion_del_objetivo}"
- Transcripción: "{texto_de_transcripcion}"

Output (JSON):
{
  "classification": "logrado|parcial|no_cubierto",
  "evidence": "cita textual relevante",
  "confidence": 0.95,
  "reasoning": "explicación breve"
}
```

### 3.3 Integración con LLM Existente

- Reutilizar `app/services/enhanced_llm_service_v5.py`
- Usar `app/services/context_loader_service.py` para cargar contexto de la sesión
- La respuesta estructurada (JSON) permite parseo directo

---

## Fase 4: Frontend — Recording UI & Reports

**Objetivo:** Interfaces de usuario para grabación, revisión de transcripción y visualización de reportes.

### 4.1 Interfaz de Grabación (HU-07) — Jinja2

**Ruta:** `app/templates/therapist/session_recording.html`

- Botón "Iniciar Grabación" (bloqueado si no hay asistencia registrada — RNF-07)
- Indicador de grabación en curso con tiempo transcurrido
- Controles: Pausa / Reanudar / Detener
- Barra de progreso de subida
- Estado de procesamiento (polling cada 5 segundos)
- Al confirmar: redirect a vista de transcripción

**Flujo:**
```
1. Terapista marca asistencia → botón habilitado
2. Click "Iniciar Grabación" → POST /api/v2/sessions/{id}/recording/start
3. MediaRecorder API → chunks cada 5 segundos
4. Click "Detener" → POST /api/v2/sessions/{id}/recording/stop
5. Polling GET /status cada 5s → "Procesando..." → "Completado"
6. Redirect a vista de reporte
```

### 4.2 Vista de Transcripción (HU-08)

- Transcript scrollable con timestamps
- Segmentos resaltados por objetivo
- Terapista puede agregar notas manuales
- Botón "Iniciar Análisis" → gatilla comparación semántica

### 4.3 Vista de Reporte de Auditoría (HU-10)

- Medidor de cumplimiento (0-100%) con color coding:
  - ✅ Verde (>80%): Bueno
  - 🟡 Amarillo (50-80%): Regular
  - 🔴 Rojo (<50%): Requiere atención
- Tarjetas por objetivo:
  - **Logrado** → fondo verde, checkmark
  - **Parcial** → fondo amarillo, media estrella
  - **No cubierto** → fondo rojo, X
  - Cada tarjeta incluye: evidencia textual + timestamp
- Botón "Descargar Reporte PDF"

### 4.4 Informe de Progreso — Padre (HU-15)

- Gráfico de evolución por objetivo (inicio vs fin del bloque)
- Compliance trend line chart (4 semanas)
- Descargar PDF
- Versión para app Angular (edysync/)

---

## Fase 5: Security & Compliance

**Objetivo:** Garantizar privacidad, seguridad y cumplimiento normativo.

### 5.1 Privacidad de Audio (RNF-02, R06)

- Auto-eliminación de archivos de audio post-transcripción exitosa
- Algoritmo de eliminación segura (DoD 5220.22-M):
  1. Sobrescribir con 0x00
  2. Sobrescribir con 0xFF
  3. Sobrescribir con datos aleatorios
  4. Eliminar archivo
  5. Verificar eliminación
- TTL configurable: `AUDIO_RETENTION_HOURS` (default: 24h si falla transcripción)

### 5.2 Cifrado (HU-16)

- Audio en reposo: AES-256-GCM
- TLS en tránsito (ya configurado)
- Claves de cifrado en variables de entorno
- No almacenar claves en la base de datos

### 5.3 Protecciones OWASP (Context3.md)

| Vector | Defensa |
|--------|---------|
| SQLi | SQLAlchemy ORM + prepared statements (ya implementado) |
| XSS | Sanitizar transcripción antes de renderizar |
| CSRF | Tokens en formularios de grabación |
| Rate limiting | Flask-Limiter (ya configurado) |
| Auth | JWT + Flask-Login (ya implementado) |

### 5.4 Auditoría y Trazabilidad

- Log de todas las operaciones: grabación, transcripción, reportes
- Quién accedió a cada transcripción
- Reportes inmutables (versión + hash)
- Backup cifrado de transcripciones

---

## Sprint Mapping

Basado en el sprint plan de Context1.md:

| Sprint | User Stories | Tareas | Dependencias |
|--------|-------------|--------|--------------|
| **Sprint 0** | — | Setup PostgreSQL, crear modelos nuevos, configurar migraciones | Fase 0 |
| **Sprint 2** | HU-05, HU-06, HU-07, HU-08 | Carga de plan, extracción de objetivos, grabación, transcripción Whisper | Fase 0, Fase 1 |
| **Sprint 3** | HU-09, HU-10, HU-11, HU-12 | Comparación semántica, reporte auditoría, dashboard terapista | Fase 1, Fase 2 |
| **Sprint 4** | HU-13, HU-14, HU-15 | Informe 4 semanas, aprobación, vista padre, seguridad (HU-16) | Fase 3, Fase 4 |

### Dependencias entre Fases

```
Fase 0 (DB + Modelos)
    ↓
Fase 1 (Whisper Service) ─→ Fase 3 (Semantic Comparison)
    ↓                            ↓
Fase 2 (API Endpoints) ──────→ Fase 4 (Frontend)
                                    ↓
                              Fase 5 (Security + Compliance)
```

---

## Riesgos y Mitigación

Basado en Context1.md §6:

| ID | Riesgo | Mitigación | Fase |
|----|--------|-----------|------|
| R02 | Saturación de almacenamiento por audios | Auto-delete post-transcripción; comprimir uploads; límite de 100MB por archivo | Fase 1, Fase 5 |
| R03 | Precisión insuficiente de Whisper | Noise reduction preprocessing; modelo large-v3; idioma forzado (español) | Fase 1 |
| R04 | Fallo de micrófono lavalier | Prueba de grabación antes de iniciar; feedback visual en UI | Fase 4 |
| R05 | Interpretación incorrecta de LLaMA | Human-in-the-loop: terapista valida objetivos y reportes (HU-14) | Fase 3 |
| R06 | Privacidad de audios con menores | AES-256; eliminación segura DoD; auto-purge configurable | Fase 5 |

---

## Dependencias Nuevas

### Python (requirements.txt)
```
# Whisper AI
openai-whisper>=20231117
faster-whisper>=1.0.0        # Alternativa más rápida
pydub>=0.25.1
noisereduce>=3.0.0
librosa>=0.10.0
soundfile>=0.12.1

# Database
psycopg2-binary>=2.9.9
flask-migrate>=4.0.0
alembic>=1.13.0

# Async Tasks
celery[redis]>=5.3.0

# PDF Generation
reportlab>=4.1.0              # Ya listado, confirmar versión
```

### Frontend (Jinja2)
- MediaRecorder API (nativo en navegadores modernos)
- Chart.js para gráficos de evolución
- No se requieren librerías externas adicionales

---

## Resumen de Archivos a Crear/Modificar

### Nuevos
```
app/models/                     → split models.py en módulos
├── __init__.py
├── user.py
├── appointment.py
├── recording.py                → SessionRecording, Transcription
├── objective.py                → TherapyObjective
├── report.py                   → AuditReport, ProgressReport
└── ... (resto de modelos)

app/services/whisper_service.py
app/services/semantic_comparison_service.py
app/services/audio_encryption_service.py
app/routes/recording_routes.py
app/routes/transcription_routes.py
app/routes/report_routes.py
app/templates/therapist/session_recording.html
app/templates/therapist/transcription_view.html
app/templates/therapist/audit_report.html
app/templates/patient/progress_report.html
migrations/                     → estructura Alembic
documentation/PLAN_WHISPER_AI.md   ← este archivo
```

### Modificados
```
requirements.txt                → + openai-whisper, pydub, celery, etc.
config.py                       → + AUDIO_CONFIG, WHISPER_MODEL
app/__init__.py                 → + recording_bp, transcription_bp, report_bp
app/models.py                   → + nuevos modelos (o split a módulos)
app/tasks.py                    → + process_session_audio, secure_delete_audio
app/services/__init__.py        → export nuevos servicios
.editorconfig / .env.example    → + DB_WRITE_HOST, DB_READ_HOST, etc.
```

---

**Próximo paso:** Comenzar con Fase 0 — crear modelos, migración a PostgreSQL, y configurar replicación.
