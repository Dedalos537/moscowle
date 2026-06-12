📋 AUDITORÍA vs ESPECIFICACIÓN TÉCNICA DEL STAKEHOLDER
1️⃣ Arquitectura Base, Entornos y Despliegue
Requisito	Estado	Evidencia
Dockerfile multi-capa	✅ Cumple	Dockerfile multi-stage (angular-builder → builder → runtime), non-root user, HEALTHCHECK
Gestión de Credenciales	❌ NO Cumple	.env en disco con 3 contraseñas = Rucula_530 (reuso crítico). API keys Gemini/Groq en texto plano. Fallback 'dev-key-change-in-production' en config.py
Pipeline CI/CD	✅ Cumple	GitHub Actions: lint → test → build. Frontend CD via FTP. Railway auto-deploy
Despliegue Cloud	✅ Cumple	Railway con railway.json, healthcheck /api/health
2️⃣ Capa de Persistencia y Bases de Datos
Requisito	Estado	Evidencia
Read/Write Split	❌ NO Cumple	SQLALCHEMY_BINDS = {} vacío. Solo hay comentarios en config.py:26-34
Patrón Repository/DAO	⚠️ Parcial	5 repositorios pero 15+ servicios bypassan usando db.session directo
Auditoría (created_by, updated_at)	✅ Cumple	AuditMixin en base.py. created_by_id + updated_at en todos los modelos
Borrado Lógico (is_active)	✅ Cumple	is_active en 19 modelos (3 sin: Sede, SmartAction, CSPReport)
Índices B-Tree	⚠️ Parcial	48 índices single-column. Cero índices compuestos en tablas con JOINs pesados
3️⃣ Seguridad de la Información
Requisito	Estado	Evidencia
JWT	✅ Cumple	Cookies HTTP-only + CSRF double-submit. Refresh tokens. Exp 1h/30d
OAuth	❌ NO Cumple	oauth = OAuth() en extensions.py, columnas oauth_provider/oauth_id en User, pero ningún provider registrado ni endpoints de login
repared Statements (SQLi)	✅ Cumple	SQLAlchemy ORM en 99% de queries. backup_service.py:35 con f-string es riesgo menor (solo table names de inspector)
XSS Protection	✅ Cumple	bleach sanitizer en utils/sanitizer.py. Jinja2 autoescaping. CSP headers. Gap: unsafe-inline en CSP por Tailwind CDN
CORS	✅ Cumple	Orígenes whitelist. Gap: cors_allowed_origins='*' en SocketIO
Password Hashing	✅ Cumple	bcrypt.generate_password_hash + check_password_hash consistentes
MFA/2FA	✅ Cumple (con gaps)	pyotp TOTP + QR. Gaps: Sin rate limiting en /mfa/login, sin refresh token en flujo MFA
CSRF Protection	✅ Cumple	23 endpoints @csrf.exempt pero la mayoría usa JWT (CSRF por cookie). WTF_CSRF_ENABLED = True
4️⃣ Front-End, UX y Rendimiento
Requisito	Estado	Evidencia
CSS Variables	✅ Cumple	:root con paleta completa en style.css, base.html, y Angular styles.scss
Mobile First	✅ Cumple	Tailwind responsive (sm:, md:, lg:) en 25+ templates. Viewport meta. Hamburger + slide-in sidebar
UX Implementado	✅ Cumple	Skeleton loaders, dark mode persistente, notificaciones poll, validación async de login, floating labels
5️⃣ Control de Calidad y Pruebas
Requisito	Estado	Evidencia
Framework de pruebas	✅ Cumple	pytest 8.x + pytest-cov. 85 tests definidos
BDD (Gherkin)	⚠️ Parcial	test_bdd_login.py con Given/When/Then en comentarios pero sin archivos .feature ni behave/pytest-bdd
Pruebas Login (TDD)	✅ Cumple	~28 tests de auth/login: éxito, fallo, vacío, SQLi, XSS, CSRF
Pruebas Caja Negra (SQLi)	✅ Cumple	test_security_integration.py con 7 payloads SQLi y 4 XSS
Tests PASAN	❌ 51/85 fallan	Error raíz: User.assigned_therapist sin foreign_keys → bloquea inicialización de mappers
6️⃣ Monitoreo, SLAs y Gestión
Requisito	Estado	Evidencia
Sentry (error tracking)	⚠️ Parcial	Código presente (bootstrap.py:153-174) pero SENTRY_DSN no está configurado en .env
Health endpoint	✅ Cumple	/api/health con checks de DB + APIs. Usado por Railway
Prometheus / Métricas	⚠️ Parcial	/metrics manual con 5 métricas. Sin prometheus_client ni request-level metrics
Feature Flags	✅ Cumple	feature_flags.py con 7 flags, decorator @flag_required, template injection
Crisis Monitor	⚠️ Parcial	crisis_monitor.py implementado pero record_error()/record_latency() nunca se llaman desde ningún handler
Rollback Plan	✅ Cumple	docs/ROLLBACK_PLAN.md con DB restore + Railway rollback + degraded mode
Rotación Credenciales	⚠️ Parcial	docs/ROTATE_CREDENTIALS.md documentado. Solo APP_SECRET_KEY rotado. Rucula_530 sin rotar
ServiceRequest API	❌ NO Cumple	Modelo ServiceRequest existe pero sin rutas HTTP para CRUD
7️⃣ Trazabilidad Código-Negocio
Requisito	Estado	Evidencia
Commits convencionales	✅ Cumple	fix:, feat:, refactor:, chore:, spec:, plan:, prp:
Frecuencia commits (~diaria)	✅ Cumple	158 commits en 42 días (~3.8/día)
PR template con User Stories	✅ Cumple	.github/pull_request_template.md con formato Como <rol> quiero <acción> + checklist
PRPs con Criterios de Aceptación	✅ Cumple	PRPs/001--plan-completo-fases-4-7.md con 579 líneas, checkboxes por criterio
GitHub Issues / Referencias	❌ NO Cumple	Cero referencias a issues en commits. No hay fixes #N / closes #N
Ramas (Git Flow)	❌ NO Cumple	Solo main e integrador. Sin develop, feature/*, staging, hotfix/*
🔴 RESUMEN: 7 CRÍTICOS, 8 MEDIOS, 22 CUMPLEN
🔴 Críticos (acción inmediata requerida):
1. Credenciales hardcodeadas — .env con MySQL/Email/Admin password = Rucula_530 + API keys en texto plano
2. Reuso de contraseña — Rucula_530 compartida entre DB, email y admin
3. Read/Write Split no implementado — SQLALCHEMY_BINDS = {} vacío
4. OAuth no implementado — infraestructura creada pero ningún provider configurado
5. 51/85 tests fallan — User.assigned_therapist sin foreign_keys
6. Sin ramas Git Flow — falta develop, feature/*, staging
7. Sin referencias a issues en commits — no hay trazabilidad a user stories
🟡 Medios:
- Crisis monitor sin conectar (record_error() nunca llamado)
- ServiceRequest sin API endpoints
- SENTRY_DSN no configurado (código presente, pero inactivo)
- Sin índices compuestos B-Tree
- Repositorio pattern inconsistente
- MFA sin rate limiting + sin refresh token
- SocketIO CORS wildcard
- Config defaults inseguros en config.py
✅ Cumplen: Docker, JWT, bcrypt, CSRF, XSS, CORS, Mobile First, CSS Variables, UX, BDD parcial, Health, Feature Flags, Rollback Plan, PR template, PRPs, ~28 tests login, logging JSON estructurado, rate limiting parcial
¿Quieres que prioricemos los críticos para resolver?
