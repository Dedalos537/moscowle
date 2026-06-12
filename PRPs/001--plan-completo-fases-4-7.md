# PRP: Plan Completo Fases 4-7 — Adecuación a Especificación Técnica

> **Version:** 1.0
> **Created:** 2026-06-09
> **Status:** Draft
> **Fases:** 4 (Seguridad) → 5 (Base de Datos) → 6 (Pruebas) → 7 (Monitoreo)

---

## Goal
Llevar el proyecto Moscowle IA al 100% de cumplimiento contra la especificación técnica de arquitectura (Semanas 1-13), cubriendo Seguridad, Base de Datos, Pruebas automatizadas y Monitoreo/Operaciones.

## Why
- **Seguridad:** .env con secrets reales commiteados, 0 protección XSS, password hardcoded `changeme123`, CSP con `unsafe-inline`
- **Base de Datos:** 0 índices en FKs, sin soft delete ni auditoría, migraciones vacías
- **Pruebas:** 0 BDD/Gherkin, 0 pruebas de seguridad, 1 test roto
- **Operaciones:** 0 feature flags, 0 plan de rollback, 0 request catalog

## What
Cuatro fases ejecutables secuencialmente, cada una con deploy gate.

### Success Criteria (Generales)
- [ ] .env removido de git, credenciales rotadas
- [ ] XSS mitigado vía bleach + CSP endurecido
- [ ] Rate limiting en TODOS los endpoints
- [ ] Índices B-Tree en todas las FK de la base de datos
- [ ] Soft delete + auditoría en tablas maestras
- [ ] Migraciones Alembic reales (fin de db.create_all())
- [ ] 3+ escenarios Gherkin para login
- [ ] Scripts de prueba SQLi
- [ ] Feature flags operativos
- [ ] Plan de rollback documentado

---

## All Needed Context

### Current State Summary

| Dimensión | Estado | Gravedad |
|-----------|--------|----------|
| Docker / CI / Cloud | ✅ Completo | -- |
| CSS Variables + Mobile First | ✅ Completo | -- |
| UX + Templates | ✅ Completo | -- |
| .env commiteado | 🔴 Secrets expuestos | Crítica |
| XSS (sin bleach, CSP unsafe-inline) | 🔴 Sin protección | Crítica |
| Password débil (werkzeug + changeme123) | 🔴 Hardcoded | Crítica |
| Índices B-Tree en FKs | 🔴 Ausentes | Alta |
| Soft delete + auditoría | 🔴 Faltante | Alta |
| Rate limiting (solo 6/50+ endpoints) | 🟡 Parcial | Alta |
| BDD Gherhin (3 escenarios login) | 🔴 No existe | Alta |
| CSRF (22 exemptions) | 🟡 Excesivo | Media |
| Feature flags | 🔴 No existe | Media |
| JWT / OAuth | 🟡 Solo flask-login | Media |

### Key Files & Architecture

```bash
app/
├── routes/                    # ~209 rutas en 23 archivos (Blueprints)
│   ├── therapist_routes.py    # 33 rutas (FIXED: conflict markers removed)
│   ├── patient_routes.py      # 16 rutas
│   ├── auth.py                # Login/logout (flask-login, bcrypt)
│   ├── llama_routes.py        # LLM chat (TIENE password hardcoded)
│   ├── api/                   # API endpoints (sessions, reports, etc.)
│   └── admin/                 # Admin routes
├── models/                    # 25 clases en 9 archivos
│   ├── user.py                # Sede, User, associations
│   ├── appointment.py         # SessionMetrics, Appointment
│   ├── payment.py             # Payment, Expense, YapeTransaction
│   ├── report.py              # WeeklyReport, MonthlyReport, etc.
│   └── ...
├── repositories/              # Data access layer (sync)
├── services/                  # Business logic
├── utils/
│   ├── cache_utils.py         # Flask-Caching wrapper
│   └── __init__.py            # parse_datetime, etc.
├── middleware/
│   └── request_handlers.py    # CORS, CSRF, X-App-Key validation
├── bootstrap.py               # App factory helpers
├── extensions.py              # Flask extensions
└── __init__.py                # App factory (~80 lines)

tests/
├── conftest.py                # SQLite in-memory, test user fixture
├── test_auth.py               # 1 test FAILING (wrong assertion)
├── test_models.py
├── test_api_auth.py
├── test_therapist_routes.py
├── test_admin_routes.py
├── test_security.py
└── ...

config.py                     # 187 lines: all env-driven settings
Dockerfile                    # Multi-stage (Node 20 → Python 3.11)
docker-compose.yml            # MySQL 8.0 + Redis 7 + Backend
railway.json                  # Dockerfile builder + healthcheck
```

### Known Gotchas
- Ruff ~2361 pre-existing errors (PLC0415, E501, etc.) — don't add new ones
- No local pytest venv — tests run via CI only
- Railway auto-deploys from GitHub push
- SQLALCHEMY_COMMIT_ON_TEARDOWN = True + 119+ explicit db.session.commit()
- therapist_routes.py merge conflict markers already removed in Fase 3 crisis
- Login manager session_protection = 'basic' (needs 'strong' in prod)

---

## Implementation Blueprint

---

### FASE 4: Seguridad (Semana 4/7/13 de especificación)

**Goal:** Eliminar vulnerabilidades críticas y altas. Endurecer XSS, CSP, rate limiting, CSRF, passwords.

#### Tasks

```yaml
Task 4.1: Git — Remover .env del tracking + rotar credenciales
  - MODIFY: .gitignore (add .env if missing)
  - REMOVE from git: git rm --cached .env
  - CREATE: docs/ROTATE_CREDENTIALS.md with list of ALL secrets to rotate
    - DB password in SQLALCHEMY_DATABASE_URI (Railway)
    - Email password (MAIL_PASSWORD)
    - Gemini API key (GEMINI_API_KEY)
    - Groq API key (GROQ_API_KEY)
    - Admin password in .env
  - CRITICAL: Do NOT commit new .env after removal
  - VERIFY: rg '.env' .gitignore > /dev/null

Task 4.2: llama_routes.py — Fix password hashing
  - MODIFY: app/routes/llama_routes.py
  - FIND: "from werkzeug.security import generate_password_hash"
  - REPLACE with: "from app.extensions import bcrypt"
  - FIND: "password=generate_password_hash('changeme123')"
  - REPLACE with: "password=bcrypt.generate_password_hash('CHANGE_ME').decode('utf-8')"
  - VERIFY: python -c "import py_compile; py_compile.compile('app/routes/llama_routes.py', doraise=True)"

Task 4.3: XSS — Integrar bleach en todos los inputs de usuario
  - VERIFY bleach is in requirements.txt (should be: bleach>=6.0.0)
  - CREATE: app/utils/sanitizer.py
    - def sanitize_html(value: str) -> str: return bleach.clean(value, tags=[], strip=True)
    - def sanitize_input(value: str) -> str: strip tags, trim whitespace, max length
  - FIND all routes that accept user text input:
    - ContactMessage (chat_routes.py)
    - LLM prompts (llama_routes.py, _shared.py)
    - Profile updates (therapist_routes.py, patient_routes.py)
    - Message sending (chat_routes.py)
    - Yape import comments
  - MODIFY each: wrap user input with sanitize_input() before processing
  - MODIFY: app/routes/api/_shared.py (prompt injection — sanitize name, email, message)
  - VERIFY: all test_inputs properly sanitized

Task 4.4: CSP — Endurecer Content Security Policy
  - MODIFY: app/bootstrap.py (init_security_headers section)
  - FIND: "'unsafe-inline'" in script-src and style-src
  - REPLACE with: nonce-based or hash-based approach for inline scripts/styles
    - Generate nonce per request via Flask g
    - Pass nonce to templates
    - Add {{ nonce }} to inline <script>/<style> tags in base.html
  - VERIFY: Page loads without CSP violations in browser console

Task 4.5: Rate limiting — Cubrir todos los endpoints
  - REVIEW: Current rate limits (only 6 endpoints have them)
  - CREATE: app/utils/rate_limiter.py or centralized decorator
    - Define tiers: STRICT (login, register), MEDIUM (API writes), RELAXED (reads)
    - Apply sensible defaults: 30/min for writes, 60/min for reads
  - MODIFY: All route blueprints to apply rate limits
    - Priority: auth endpoints first, then API, then therapist/patient/admin
    - Use existing flask-limiter from extensions.py
  - VERIFY: Rate limits applied via limiter.limit() decorator

Task 4.6: CSRF — Reducir exemptions
  - AUDIT: All 22 @csrf.exempt decorators
    - Legitimate: API routes with X-App-Key or token auth
    - Illegitimate: Routes that should use CSRF token
  - MODIFY: Remove unnecessary exemptions, add CSRF token where missing
  - VERIFY: exempted list reduced to minimum

Task 4.7: Login manager — 'strong' session protection in production
  - MODIFY: app/extensions.py
  - FIND: "login_manager.session_protection = 'basic'"
  - REPLACE with env-based: "'strong' if os.getenv('FLASK_ENV') == 'production' else 'basic'"
  - VERIFY: Login still works in dev and prod
```

#### Validation (Fase 4)
```bash
# 4.1 - .env not tracked
git ls-files .env | wc -l  # expect 0

# 4.2 - No werkzeug password hash in llama_routes
rg 'werkzeug.security' app/routes/llama_routes.py | wc -l  # expect 0

# 4.3 - bleach imported anywhere
rg 'import bleach' app/ -n | wc -l  # expect > 0

# 4.6 - Count CSRF exemptions
rg '@csrf.exempt' app/routes/ -n | wc -l  # expect < 22

# Syntax
python -c "import py_compile; py_compile.compile('app/routes/llama_routes.py', doraise=True)"

# Full test suite
python -m pytest tests/ -x --tb=short -q
```

---

### FASE 5: Base de Datos (Semana 7/8/9 de especificación)

**Goal:** Índices, soft delete, auditoría, migraciones reales. Preparar para Maestro-Esclavo.

#### Tasks

```yaml
Task 5.1: Índices B-Tree en todas las FK
  - IDENTIFY all FK columns across models:
    - User.sede_id → Sede.id
    - User.assigned_therapist_id → User.id
    - Appointment.therapist_id, patient_id → User.id
    - Message.sender_id, receiver_id → User.id
    - Payment.patient_id → User.id
    - SessionMetrics.user_id, session_id → User.id, Appointment.id
    - SessionImage.appointment_id → Appointment.id
    - Chat.created_by_id → User.id
    - ChatParticipant.user_id, chat_id → User.id, Chat.id
    - Notification.user_id → User.id
    - AIConversation.user_id → User.id
    - AIChatMessage.conversation_id → AIConversation.id
    - WeeklyReport.patient_id, therapist_id → User.id
    - MonthlyReport.patient_id, therapist_id → User.id
    - QuarterlyReport.patient_id, therapist_id → User.id
    - SessionAudit.appointment_id → Appointment.id
    - DailyReport.patient_id, therapist_id → User.id
    - SmartAction.created_by_id → User.id
    - Expense.created_by_id → User.id
    - AdminAPIToken.created_by_id, user_id → User.id
  - MODIFY each model file:
    - FIND: "db.Column(db.Integer, db.ForeignKey('user.id'))"
    - ADD: ", index=True" to each
    - PRESERVE: existing unique=True if present
  - VERIFY: Each FK has index=True or is covered by a composite index

Task 5.2: Soft delete en tablas maestras
  - ADD fields to base model or individually:
    - deleted_at = db.Column(db.DateTime, nullable=True)
    - deleted_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    - is_deleted = db.Column(db.Boolean, default=False, index=True)
  - Tables requiring soft delete:
    - User, Sede, Game, Payment, Expense, YapeTransaction
    - Appointment, Message, Chat
    - WeeklyReport, MonthlyReport, QuarterlyReport, DailyReport
  - MODIFY queries to filter by is_deleted=False by default:
    - Add __query_filter__ or similar on model level
    - Or modify Repository methods to add .filter_by(is_deleted=False)
  - VERIFY: All existing queries still work

Task 5.3: Auditoría — updated_by en tablas transaccionales
  - ADD fields:
    - created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    - updated_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    - updated_at = db.Column(db.DateTime, onupdate=utcnow)
  - CREATE: app/utils/audit_mixin.py with AuditMixin class
  - APPLY to: Appointment, SessionMetrics, Payment, Message, AIConversation
  - MODIFY service layer to set created_by/updated_by on writes
  - VERIFY: Audit fields populated on create/update

Task 5.4: Migraciones Alembic reales
  - INIT: flask db init (if not already)
  - CREATE: Real migration with ALL schema changes from tasks 5.1-5.3
  - MODIFY: app/__init__.py — remove db.create_all(), use flask db upgrade
  - UPDATE: Dockerfile entrypoint to run flask db upgrade before starting
  - UPDATE: conftest.py to create tables for tests (create_all is fine for tests)
  - VERIFY: flask db upgrade applies cleanly on fresh database

Task 5.5: Read/Write Split (Maestro-Esclavo) — DISEÑO
  - CREATE: docs/superpowers/designs/read-write-split.md
  - DESIGN:
    - SQLAlchemy binds for master (write) and replica(s) (read)
    - _is_read_only_operation() heuristic in repository base
    - Config: SQLALCHEMY_BINDS with master/replica URIs
    - Session routing via custom session or SQLAlchemy 2.0 bind
  - Mark as DESIGN ONLY — implementation deferred to post-Fase 7
```

#### Validation (Fase 5)
```bash
# 5.1 - Count FK columns with index=True
rg 'db\.Column.*db\.ForeignKey.*index=True' app/models/ -n | wc -l
rg 'db\.Column.*db\.ForeignKey' app/models/ -n | wc -l
# First should be close to second

# 5.2 - Soft delete fields exist
rg 'is_deleted\|deleted_at\|deleted_by' app/models/ -n | wc -l  # expect > 10

# 5.4 - Migration has content
rg 'def upgrade\|op\.' migrations/versions/ -n | wc -l  # expect > 0

# Full test suite
python -m pytest tests/ -x --tb=short -q
```

---

### FASE 6: Pruebas (Semana 12/13 de especificación)

**Goal:** BDD con Gherkin, pruebas de seguridad, fix test roto, expandir cobertura.

#### Tasks

```yaml
Task 6.1: Install behave + configure BDD
  - ADD to requirements.txt: behave, selenium (or use requests for API-level BDD)
  - CREATE: tests/features/ directory
  - CREATE: tests/features/steps/ directory

Task 6.2: BDD — 3+ escenarios Gherkin para login
  - CREATE: tests/features/login.feature
    Scenario 1: Login exitoso con credenciales válidas
      Given un usuario registrado con email "test@example.com" y password "correcta"
      When el usuario hace POST a "/api/login" con esas credenciales
      Then recibe HTTP 200 con {"success": true}
      And la sesión contiene el user_id del usuario

    Scenario 2: Login fallido por password incorrecto
      Given un usuario registrado con email "test@example.com" y password "correcta"
      When el usuario hace POST a "/api/login" con password "incorrecta"
      Then recibe HTTP 401 con {"success": false}

    Scenario 3: Intento de acceso sin autenticación
      Given un endpoint protegido "/api/sessions"
      When se hace GET sin token de sesión
      Then recibe HTTP 401

    Scenario 4: Rate limiting en login
      Given un usuario registrado
      When hace 21 requests POST a "/api/login" en 1 minuto
      Then el request 21 recibe HTTP 429

  - CREATE: tests/features/steps/login_steps.py with behave step implementations
  - VERIFY: behave tests/features/ passes

Task 6.3: Pruebas de seguridad — SQLi simulation
  - CREATE: tests/test_security_sqli.py
    Test 1: SQLi en email field "' OR 1=1 --"
    Test 2: SQLi en search params
    Test 3: SQLi en ID parameter
  - EXPECT: All return validation errors (400/422), not 500 or data leakage
  - VERIFY: python -m pytest tests/test_security_sqli.py -v

Task 6.4: Fix test existente
  - MODIFY: tests/test_auth.py
  - FIND: test_protected_route_requires_login
  - Current: asserts 200 when unauthenticated
  - FIX: Change assertion from 200 to 302 (redirect to login) or check for login page
  - VERIFY: ALL tests pass: python -m pytest tests/ --tb=short -q

Task 6.5: Expandir cobertura
  - CREATE: tests/test_routes_therapist.py (key therapist endpoints)
  - CREATE: tests/test_routes_patient.py (key patient endpoints)
  - CREATE: tests/test_api_sessions.py (session CRUD)
  - Focus on: happy path + auth errors + validation errors
  - VERIFY: coverage increases: python -m pytest tests/ --cov=app/routes --cov-report=term-missing
```

#### Validation (Fase 6)
```bash
# 6.2 - BDD tests
behave tests/features/  # or python -m behave tests/features/

# 6.3 - Security tests
python -m pytest tests/test_security_sqli.py -v

# 6.4 + 6.5 - All tests pass
python -m pytest tests/ --tb=short -q
# Expect: ALL passing, 0 failed
```

---

### FASE 7: Monitoreo y Operaciones (Semana 4/10/11 de especificación)

**Goal:** Feature flags, rollback plan, request catalog, KPIs con alertas.

#### Tasks

```yaml
Task 7.1: Feature flags — Sistema simple basado en config
  - CREATE: app/utils/feature_flags.py
    - FEATURE_FLAGS = {} dict read from FLAGS_* env vars
    - def is_enabled(flag_name: str) -> bool
    - def disable_feature(flag_name: str) — crisis protocol
    - Predefined flags:
      - LLM_CHAT_ENABLED = True
      - YAPE_IMPORT_ENABLED = True
      - ANALYTICS_ENABLED = True
      - EMAIL_NOTIFICATIONS_ENABLED = True
      - AUTO_REPORTS_ENABLED = True
  - MODIFY: app/bootstrap.py to load flags
  - MODIFY: Routes/services to check flags before processing
    - llama_routes.py: check LLM_CHAT_ENABLED
    - yape_routes.py: check YAPE_IMPORT_ENABLED
    - analytics_routes.py: check ANALYTICS_ENABLED
  - CREATE: Admin endpoint to toggle flags POST /admin/features/<flag>/toggle
  - VERIFY: Disabled feature returns 503 with meaningful message

Task 7.2: Crisis protocol — Health check con auto-desactivación
  - MODIFY: app/routes/health_routes.py
    - Track response times per endpoint group
    - If avg response time > threshold (e.g., 2s for login), auto-disable non-critical features
    - Store in Flask g or Redis
  - CREATE: app/middleware/crisis_monitor.py
    - Decorator that measures endpoint latency
    - If threshold breached, sets feature flag to False
  - VERIFY: Crisis monitor doesn't add >5ms overhead

Task 7.3: Plan de rollback documentado
  - CREATE: docs/ops/ROLLBACK_PLAN.md
    - Database rollback: alembic downgrade + restore from backup
    - Application rollback: Redeploy previous Docker image
    - Railway: Point to previous deployment
    - Backup scripts: app/services/backup_service.py review
    - Restore procedure step by step
  - UPDATE: railway.json if needed for deployment versioning

Task 7.4: Request Catalog — Información vs Acceso
  - AUDIT: All routes for request type classification
  - CATEGORIZE:
    - Información: reports, analytics, patient lists, schedules
    - Acceso: password changes, role changes, data export, account deletion
  - MODIFY: Routes marked as "Acceso" to require:
    - Additional confirmation step
    - Audit log entry
    - Email notification to user/owner
  - CREATE: app/utils/request_catalog.py with decorators
    - @request_type('info') — lightweight
    - @request_type('access', require_approval=True) — strict validation
  - VERIFY: Access requests logged and notified

Task 7.5: Monitoreo KPIs con alertas
  - CONFIGURE: Sentry alerts for error rate > 1%
  - CREATE: docs/ops/KPI_MONITORING.md
    - KPIs: uptime > 98%, login response < 2s, API p95 < 500ms
    - Alert channels: Sentry, email, logs
    - Dashboard: Railway metrics + Sentry
  - VERIFY: Alerts configured in Sentry dashboard
```

#### Validation (Fase 7)
```bash
# 7.1 - Feature flags importable
python -c "from app.utils.feature_flags import is_enabled; print('OK')"

# 7.2 - Crisis monitor importable
python -c "from app.middleware.crisis_monitor import check_crisis; print('OK')"

# 7.4 - Request catalog importable
python -c "from app.utils.request_catalog import request_type; print('OK')"

# Full test suite
python -m pytest tests/ -x --tb=short -q

# Docs exist
ls docs/ops/ROLLBACK_PLAN.md docs/ops/KPI_MONITORING.md
```

---

## Integration Points

### Database (Fase 5)
```yaml
migration: "Add indexes, soft delete columns, audit fields to ALL tables"
index: "CREATE INDEX idx_<table>_<fk> ON <table>(<fk_column>)"
config: "SQLALCHEMY_ENGINE_OPTIONS updated for connection pooling"
```

### Config (Fase 4, 7)
```yaml
add to: config.py
pattern: |
  FEATURE_LLM_CHAT = os.getenv('FEATURE_LLM_CHAT', 'True') == 'True'
  FEATURE_YAPE_IMPORT = os.getenv('FEATURE_YAPE_IMPORT', 'True') == 'True'
  CRISIS_RESPONSE_TIME_THRESHOLD = int(os.getenv('CRISIS_RESPONSE_TIME_THRESHOLD', '2000'))
```

### Routes (Fase 4, 6, 7)
```yaml
rate_limits: "Apply @limiter.limit() to all route blueprints"
csrf: "Remove unnecessary @csrf.exempt decorators"
feature_flags: "Add @require_feature('FLAG_NAME') decorator"
request_catalog: "Add @request_type('info'|'access') decorator"
```

### Templates (Fase 4)
```yaml
nonce: "Add {{ nonce }} to inline <script> and <style> tags in base.html"
```

### CI (Fase 6)
```yaml
add to: .github/workflows/ci-backend.yml
run: "behave tests/features/"
run: "python -m pytest tests/test_security_sqli.py -v"
```

---

## Validation Loop (Global)

### Level 1: Syntax
```bash
# All Python files compile
python -c "
import py_compile, os
errors = []
for root, dirs, files in os.walk('app'):
    for f in files:
        if f.endswith('.py'):
            path = os.path.join(root, f)
            try:
                py_compile.compile(path, doraise=True)
            except py_compile.PyCompileError as e:
                errors.append(str(e))
print(f'{len(errors)} errors') if errors else print('All OK')
"
```

### Level 2: No conflict markers
```bash
rg '<<<<<<<|=======|>>>>>>>' app/ -n | wc -l  # expect 0
```

### Level 3: Tests
```bash
python -m pytest tests/ -x --tb=short -q  # ALL pass
```

### Level 4: No new secrets in tracking
```bash
git diff --cached --name-only | xargs rg -l 'api_key\|password\|secret\|token' 2>/dev/null
```

---

## Final Checklist

- [ ] **Fase 4**: .env out of git, credenciales rotadas, XSS mitigado, CSP endurecido, rate limiting completo, CSRF exemptions reducidas
- [ ] **Fase 5**: Índices en todas las FK, soft delete + auditoría, migraciones reales, diseño read/write split
- [ ] **Fase 6**: 3+ escenarios Gherkin, SQLi scripts, fix test roto, cobertura expandida
- [ ] **Fase 7**: Feature flags, crisis protocol, rollback plan, request catalog, KPIs
- [ ] Deploy gate: Cada fase termina con deploy a Railway
- [ ] Commits: Cada task es un commit con mensaje descriptivo
- [ ] No regresiones: `python -m pytest tests/ -x --tb=short -q` pasa siempre

---

## Anti-Patterns to Avoid

- ❌ No hacer todo en un solo commit gigante (una task = un commit)
- ❌ No deployar sin pasar tests primero
- ❌ No ignorar el .env — si está en git, está expuesto
- ❌ No crear nuevos patrones de acceso a datos (usar Repository)
- ❌ No mezclar responsabilidades de Fase (terminar una antes de empezar otra)
- ❌ No desplegar Fase 5 sin pasar Fase 4 validation gate

---

## Notes

- **Prioridad:** Fase 4 > Fase 5 > Fase 6 > Fase 7
- **Fase 4 es crítica:** Los secrets expuestos y la falta de XSS son riesgos reales en producción
- **Fase 5.5** (read/write split) es diseño solamente — implementación post-Fase 7
- **Railway deploy:** automático desde push a main. Cada fase termina con push + verificación healthcheck
- **Testing:** Sin venv local, los tests corren via CI. Verificar en GitHub Actions antes de mergear
- **Historial de Fases 0-3:** Ver `docs/superpowers/plans/` y `docs/superpowers/specs/`
