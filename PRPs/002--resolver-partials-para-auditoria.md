# PRP: Resolver 4 PARTIALs de Auditoría Técnica

## Objetivo
Convertir los 4 criterios PARTIAL en PASS mediante implementación concreta, verificable y desplegable.

## Contexto
Auditoría contra especificación Semanas 1-13 reveló 4 PARTIALs:
1. **Índices FKs** — 35 FK columns sin `index=True`
2. **UX automatizada** — Cero tests de accesibilidad, E2E, responsive
3. **Monitoreo/Alertas** — CrisisMonitor detecta pero no alerta; Sentry DSN vacío
4. **Commits con trazabilidad** — Sin IDs de tickets ni validación de mensajes

---

## Fase 1: Índices en Foreign Keys

### 1.1 AuditMixin.created_by_id
**Archivo:** `app/models/base.py:8`
```python
# ANTES
created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
# DESPUÉS
created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, index=True)
```
**Impacto:** 27 modelos heredan el índice automáticamente.

### 1.2 Modelos restantes (34 FK columns)
Agregar `index=True` a cada FK column. Batch por archivo:

| Archivo | Columnas |
|---------|----------|
| `app/models/user.py` | `assigned_therapist_id`, `sede_id` |
| `app/models/service_request.py` | `requester_id`, `approved_by_id` |
| `app/models/notification.py` | `user_id` |
| `app/models/ai.py` | `user_id`, `conversation_id` |
| `app/models/chat.py` | `sender_id`, `receiver_id`, `parent_message_id`, `chat_id` |
| `app/models/appointment.py` | 10 FK columns (SessionMetrics: user_id, session_id, game_id; AppointmentGame: appointment_id, game_id; SessionImage: appointment_id, uploaded_by_id; Appointment: therapist_id, patient_id, status_changed_by) |
| `app/models/admin.py` | `user_id` |
| `app/models/payment.py` | `patient_id`, `therapist_id`, `expense_id` |
| `app/models/report.py` | `docx_uploaded_by`, `patient_id`, `therapist_id` (x4 report types) |

### 1.3 Migración Alembic
```bash
alembic revision --autogenerate -m "feat: add missing FK indexes (35 columns)"
alembic upgrade head
```

### 1.4 Verificación
```sql
SELECT count(*) FROM pg_indexes WHERE tablename IN (
  SELECT conrelid::regclass::text FROM pg_constraint WHERE contype = 'f'
);
```
Correr test suite: `python -m pytest tests/ --tb=short -q`

---

## Fase 2: UX Automatizada (a11y + E2E básico)

### 2.1 Playwright + axe-core para tests E2E + accesibilidad
**Instalar en frontend:**
```bash
cd edysync
npm install --save-dev @playwright/test @axe-core/playwright axe-html-reporter
npx playwright install chromium
```

### 2.2 Tests E2E: login flow + navegación básica
**Archivo:** `edysync/e2e/login.spec.ts`
- Escenario 1: Login exitoso → redirige a dashboard
- Escenario 2: Credenciales inválidas → muestra error
- Escenario 3: Campos vacíos → validación HTML5

### 2.3 Tests de accesibilidad (axe-core)
**Archivo:** `edysync/e2e/a11y.spec.ts`
- Escanear login page con axe-core
- Escanear dashboard post-login
- Umbral: 0 violaciones críticas/serias

### 2.4 CI: agregar stage de E2E en deploy-frontend.yml
```yaml
- name: Run E2E + a11y tests
  run: npx playwright test --reporter=html
```

### 2.5 Verificación
```bash
cd edysync
npx playwright test --reporter=list
```

---

## Fase 3: Monitoreo y Alertas Reales

### 3.1 Configurar Sentry activo
**Archivo:** `.env`
```
SENTRY_DSN=https://<real-dsn>@o<org>.ingest.sentry.io/<project>
```
El usuario debe generar un DSN real en sentry.io.

### 3.2 Webhook de alertas en CrisisMonitor
**Archivo:** `app/services/crisis_monitor.py`

Agregar notificaciones configurables:
- Soporte para Slack webhook + Telegram bot + Email
- Callback de alerta envía mensaje formateado
- Config via env vars:
  ```
  ALERT_SLACK_WEBHOOK_URL=https://hooks.slack.com/...
  ALERT_TELEGRAM_BOT_TOKEN=...
  ALERT_TELEGRAM_CHAT_ID=...
  ALERT_EMAIL_TO=admin@ejemplo.com
  ```

### 3.3 Pipeline de CrisisMonitor → on_alert
```python
def on_alert(self, callback):
    self._alert_callbacks.append(callback)

# En bootstrap.py:
def send_slack_alert(alert):
    requests.post(SLACK_WEBHOOK_URL, json={"text": format_alert(alert)})

crisis_monitor.on_alert(send_slack_alert)
```
Formatos: Slack (rich text blocks), Telegram (HTML), Email (HTML).

### 3.4 Metrics de pool de conexiones
**Archivo:** `app/routes/metrics_routes.py`
Agregar métricas: `db_pool_size`, `db_pool_overflow`, `db_pool_active_connections`.

### 3.5 Fix silent exception swallowing
**Archivo:** `app/services/crisis_monitor.py`
- Reemplazar `except: pass` con logging estructurado
- Agregar `logger.exception("CrisisMonitor check failed: ...")` en cada catch

### 3.6 Health endpoint extendido
**Archivo:** `app/api/health.py`
Agregar: uptime total, últimas 5 alertas con timestamp, estado de Sentry, pool info.

### 3.7 Verificación
```bash
curl -s https://moscowle-backend-production.up.railway.app/api/health | python3 -m json.tool
# Confirmar: db_status=ok, sentry=active, alert_count>=0
python -m pytest tests/ --tb=short -q
```

---

## Fase 4: Trazabilidad en Commits

### 4.1 Crear archivo CONTRIBUTING.md con convención de commits
**Archivo:** `CONTRIBUTING.md`

Formato requerido:
```
<tipo>(<ámbito>): <descripción>

[optional body]

[optional footer: Referencias: #TICKET-ID]
```

Tipos: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `spec`, `prp`, `plan`
Ámbitos: `models`, `api`, `auth`, `ui`, `db`, `ci`, `monitor`, etc.

### 4.2 Validación con commitlint local (sin Node)
Usar scripts/validate-commit.sh con Python:
```bash
#!/usr/bin/env bash
# scripts/validate-commit.sh
python3 -c "
import sys, re
msg = sys.argv[1]
pattern = r'^(feat|fix|refactor|test|docs|chore|spec|prp|plan)\([a-z]+\): .{10,100}'
if not re.match(pattern, msg):
    print('ERROR: Formato: <tipo>(<ámbito>): <descripción>')
    sys.exit(1)
print('✅ Commit message válido')
"
```

Hook: `scripts/install-hooks.sh` agrega `commit-msg` hook que ejecuta validación.

### 4.3 Configurar commit-msg hook via pre-commit
**Archivo:** `.pre-commit-config.yaml` → agregar hook `commit-msg` local.

### 4.4 Documentar en .github/ cómo referenciar tickets
Convención:
- Subject: `feat(auth): implementar login OAuth Google`
- Body: `Referencia: MOSCOWLE-42`
- Si no hay ticket: `Referencia: N/A`

### 4.5 Verificación
```bash
echo "fix(api): corregir validación email en login" > /tmp/test-msg
python3 scripts/validate-commit.sh "$(cat /tmp/test-msg)"
# ✅ Commit message válido
```

---

## Fase 5: Verificación Global

### 5.1 Test suite completa
```bash
python -m pytest tests/ --tb=short -q --cov=app --cov-report=term-missing
```

### 5.2 Lint + formato
```bash
ruff check app/ && ruff format app/ --check
```

### 5.3 Verificar endpoints deployados
```bash
curl -s https://moscowle-backend-production.up.railway.app/api/health | python3 -m json.tool
curl -sI https://moscowle.centrojuanpabloii.com | head -5
```

### 5.4 Commit y push
```bash
git add .
git commit -m "feat(core): resolver 4 partials de auditoria - indices, ux, monitoreo, commits"
git push
```

### 5.5 Verificar CI pasa
- GitHub Actions: ci-backend.yml (ruff + pytest + Docker build)
- GitHub Actions: deploy-frontend.yml (FTP a cPanel)
- Railway: auto-deploy desde main

---

## Anti-Pattern Guards
- No agregar `updated_by_id` a AuditMixin (la migración existe, no era requerida originalmente)
- No instalar `prometheus_client` sin evaluar si Railway lo permite
- No convertir tests frontend existentes a otra librería (Karma+Jasmine ya está configurado)
- No romper tests existentes al agregar index=True (SQLAlchemy no requiere migración para index=True nuevo en SQLite)

## Dependencias
- Sentry DSN real (debe generarlo el usuario en sent.io)
- Slack/Telegram webhook URLs (configuración manual en .env)
- Playwright requiere Chromium (~300MB) en CI
