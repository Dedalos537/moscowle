# PRP: Remediación Arquitectura — Seguridad, DB, API, Monitoreo

> **Version:** 1.0
> **Created:** 2026-06-10
> **Status:** Ready
> **Fases:** 1 (Seguridad) → 2 (DB) → 3 (API) → 4 (Monitoreo)

---

## Goal

Llevar Moscowle IA a cumplimiento total en: gestión de refresh tokens + rate limiting MFA + OAuth providers, Read/Write split en BD, composite indexes, repositorio pattern + ServiceRequest CRUD, SocketIO CORS restrictivo, crisis monitor + health endpoint + Sentry validado.

## Why

- Auditoría encontró 0 refresh tokens, 0 rate limiting en MFA, 0 OAuth, CORS abierto en SocketIO
- Base de datos sin índices compuestos ni separación de lecturas/escrituras
- API sin patrón repositorio ni CRUD completo de ServiceRequest
- Sin monitoreo proactivo (crisis monitor), sin health endpoint funcional

## What

4 fases ejecutables, cada una con deploy gate.

### Success Criteria
- [ ] Refresh token con tabla propia + hash + revocación + rotación
- [ ] MFA rate limiting por usuario (5 intentos, lockout 15 min)
- [ ] OAuth Google + Facebook funcionales
- [ ] `.env` completo con todas las vars de configuración
- [ ] Read/Write split operativo (RoutingSession)
- [ ] Índices compuestos `session(therapist_id, scheduled_date)` y `payment(patient_id, status)`
- [ ] FK `assigned_therapist_id` explícita en migración
- [ ] Repositorio genérico `BaseRepository[T]`
- [ ] `ServiceRequestRepository` con approve/reject
- [ ] CRUD REST de ServiceRequests
- [ ] SocketIO CORS restrictivo (`https://moscowle.ai`)
- [ ] CrisisMonitor en background thread
- [ ] Health endpoint (`/api/health`)
- [ ] Sentry DSN configurado desde `.env`
- [ ] Todos los comandos de validación pasan

---

## All Needed Context

### Codebase Structure
```bash
app/
├── auth/
│   ├── routes.py          # Auth routes (login, register, etc.)
│   ├── mfa.py             # MFA verification
│   ├── oauth.py           # [CREAR] OAuth providers
│   └── decorators.py      # Auth decorators
├── models/
│   ├── user.py            # User model (+ assigned_therapist FK)
│   ├── service_request.py # ServiceRequest model
│   └── refresh_token.py   # [CREAR] RefreshToken model
├── repositories/
│   ├── base.py            # [CREAR] BaseRepository[T]
│   └── service_request_repo.py # [CREAR]
├── services/
│   ├── crisis_monitor.py  # [CREAR]
│   └── feature_flags.py   # Existing
├── api/
│   ├── service_requests.py # [CREAR] CRUD endpoints
│   └── health.py           # [CREAR] Health check
├── db/
│   └── routing.py          # [CREAR] Read/Write split
├── bootstrap.py            # [MODIFICAR] SocketIO CORS + crisis_monitor + OAuth init
├── config.py               # [MODIFICAR] Add new config vars
├── extensions.py           # Already has OAuth imported
└── auth_compat.py          # Already has login_required
```

### Config Vars to Add (in `config.py`)
```python
JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
MFA_MAX_ATTEMPTS = int(os.getenv('MFA_MAX_ATTEMPTS', '5'))
MFA_LOCKOUT_MINUTES = int(os.getenv('MFA_LOCKOUT_MINUTES', '15'))
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID', '')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET', '')
FACEBOOK_CLIENT_ID = os.getenv('FACEBOOK_CLIENT_ID', '')
FACEBOOK_CLIENT_SECRET = os.getenv('FACEBOOK_CLIENT_SECRET', '')
OAUTH_REDIRECT_URI = os.getenv('OAUTH_REDIRECT_URI', '')
REPLICA_DATABASE_URL = os.getenv('REPLICA_DATABASE_URL', '')
SOCKET_CORS_ORIGINS = os.getenv('SOCKET_CORS_ORIGINS', 'https://moscowle.ai')
```

### Known Gotchas
- `auth_compat.py` usa `flask_jwt_extended` con `locations=['cookies']` — los endpoints refresh deben devolver cookies
- `bootstrap.py` usa `socketio.init_app(app, cors_allowed_origins='*')` — cambiar a variable de config
- User model ya tiene `assigned_therapist_id = db.Column(db.Integer, db.ForeignKey('user.id'))` — solo falta FK explícita en migración
- `oauth` de `extensions.py` ya importa `OAuth` pero no se usa — init_oauth debe configurarlo

---

## Implementation Blueprint

### Tasks (in execution order)

```yaml
Task 1: Crear PRP file
  - CREATE: PRPs/002--remediation-arquitectura.md

Task 2: Phase 1 — Config + models + auth
  - MODIFY: config.py — add all new config vars
  - CREATE: app/models/refresh_token.py
  - MODIFY: app/models/__init__.py — add RefreshToken import
  - CREATE: app/auth/mfa.py — rate limiting functions
  - CREATE: app/auth/oauth.py — Google + Facebook OAuth
  - MODIFY: app/auth/routes.py — add refresh + logout endpoints
  - MODIFY: app/bootstrap.py — SocketIO CORS fix

Task 3: Phase 2 — DB optimization
  - CREATE: app/db/routing.py — Read/Write split
  - CREATE: migrations/versions/XXXX_remediation_phase12.py
  - RUN: flask db upgrade

Task 4: Phase 3 — Repository + API
  - CREATE: app/repositories/base.py
  - CREATE: app/repositories/__init__.py
  - CREATE: app/repositories/service_request_repo.py
  - CREATE: app/api/service_requests.py
  - CREATE: app/api/health.py

Task 5: Phase 4 — Monitoring
  - CREATE: app/services/crisis_monitor.py
  - MODIFY: app/bootstrap.py — add crisis_monitor init + health endpoint

Task 6: Validation
  - RUN: ruff check app/
  - RUN: flask db upgrade (verify)
  - RUN: pytest (if exists)
```

### Integration Points
```yaml
DATABASE:
  - migration: "Create refresh_token table"
  - migration: "Add mfa_failed_attempts, mfa_locked_until to User"
  - migration: "Add composite indexes on session(therapist_id, scheduled_date) and payment(patient_id, status)"
  - migration: "Add explicit FK for assigned_therapist_id"

CONFIG:
  - add to: config.py
  - pattern: "VAR = os.getenv('VAR', 'default')"

ROUTES:
  - auth_bp: POST /api/auth/refresh
  - auth_bp: POST /api/auth/logout
  - auth_bp: GET /auth/login/google
  - auth_bp: GET /auth/callback/google
  - auth_bp: GET /auth/login/facebook
  - auth_bp: GET /auth/callback/facebook
  - api_sr: GET/POST /api/service-requests
  - api_sr: GET /api/service-requests/<id>
  - api_sr: POST /api/service-requests/<id>/approve
  - api_sr: POST /api/service-requests/<id>/reject
  - health_bp: GET /api/health
```

---

## Validation Loop

### Level 1: Syntax & Style
```bash
ruff check app/ --fix
```

### Level 2: Migration
```bash
flask db upgrade
flask db downgrade  # verify rollback works
flask db upgrade    # back to current
```

### Level 3: Health endpoint
```bash
curl -s http://localhost:5000/api/health | python -m json.tool
# Expected: {"status": "ok", "database": "connected", ...}
```

### Level 4: API test
```bash
# Login to get token
curl -s -XPOST http://localhost:5000/auth/login -H 'Content-Type: application/x-www-form-urlencoded' -d 'email=admin@test.com&password=test'
```

---

## Final Checklist

- [ ] ruff check app/ — no errors
- [ ] flask db upgrade — no errors
- [ ] flask db downgrade — works
- [ ] All new files created with correct imports
- [ ] `.env` updated with all new vars
- [ ] No hardcoded secrets in code
- [ ] CORS restrictivo en SocketIO
- [ ] Refresh token rotación funcional
- [ ] MFA rate limiting activo

---

## Anti-Patterns to Avoid

- ❌ No hardcodear secrets en código fuente
- ❌ No dejar `cors_allowed_origins='*'` en producción
- ❌ No exponer stack traces en respuestas de error
- ❌ No crear RefreshToken sin hash
- ❌ No permitir refresh tokens ilimitados
- ❌ No ignorar excepciones sin log
- ❌ No mezclar sync/async en SocketIO
