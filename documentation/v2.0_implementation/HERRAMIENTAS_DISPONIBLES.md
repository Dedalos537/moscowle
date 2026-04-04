# 📚 HERRAMIENTAS DISPONIBLES - MOSCOWLE IA v2.0

**Última actualización:** 2026-03-19  
**Estado del proyecto:** ✅ Production Ready (Fase 4 Completada)

---

## 🔨 Herramientas Command-Line

### 1. Deploy Script
**Ubicación:** `scripts/deploy.sh`  
**Tipo:** Bash (executable)  
**Propósito:** Generar ZIP optimizado para cPanel/Hostinger/DirectAdmin

```bash
# Uso
./scripts/deploy.sh

# Genera
├─ deploy_moscowle_v2.zip (18 MB, optimizado)
├─ DEPLOYMENT_GUIDE.md (instrucciones paso a paso)
├─ DEPLOYMENT_SUMMARY.txt (checklist pre-deployment)
└─ Excluye automáticamente:
   ├─ .git, .gitignore
   ├─ .venv, venv/, __pycache__
   ├─ instance/moscowle.db (local)
   ├─ instance/uploads/ (archivos previos)
   ├─ .env, .DS_Store
   ├─ *.pyc, *.pyo
   └─ node_modules (si existe)
```

### 2. Migration Script
**Ubicación:** `migrations/add_yape_transaction.py`  
**Tipo:** Python migration  
**Propósito:** Crear tabla YapeTransaction en base de datos

```bash
# Uso (development)
python3 migrations/add_yape_transaction.py

# O dentro de app context
from migrations.add_yape_transaction import migrate
migrate()

# Crea
├─ Tabla YapeTransaction con 13 columnas
├─ UNIQUE INDEX en operation_number
└─ FK constraints a Expense
```

---

## 🐍 Servicios Python

### YapeService (app/services/yape_service.py)

**Utilidad:** Procesar importaciones de Yape/Plin con idempotencia garantizada

```python
from app.services.yape_service import YapeService

yape_service = YapeService()

# 1. IMPORTAR CSV
with open('yape_report.csv', 'rb') as f:
    success, stats = yape_service.import_transactions(f, file_type='csv')
    # stats = {total_rows, processed, duplicates_skipped, errors, batch_id}

# 2. IMPORTAR EXCEL
with open('yape_report.xlsx', 'rb') as f:
    success, stats = yape_service.import_transactions(f, file_type='xlsx')

# 3. BUSCAR TRANSACTION
results = yape_service.search_transactions(
    query='OPERACION123',
    limit=20,
    offset=0
)

# 4. ADJUNTAR RECEIPT
receipt_path = yape_service.attach_receipt_to_transaction(
    operation_number='OPERACION123',
    receipt_image_path='instance/uploads/comprobante_abc123.jpg'
)

# 5. SACAR ESTADISTICAS
stats = yape_service.get_import_statistics(batch_id='batch_xyz')
```

**Métodos principales:**
- `parse_yape_csv(file_stream)` - Generator que parsea CSV línea por línea
- `parse_yape_excel(file_stream)` - Generator que parsea XLSX línea por línea
- `_map_csv_row(row, batch_id)` - Valida + sanitiza row individual
- `import_transactions(file_stream, file_type)` - Main entry point con transacción atómica
- `_insert_or_ignore_transaction(tx_data, batch_id)` - UPSERT pattern (unique index)
- `_is_important_expense(tx_data)` - Detecta si crear Expense automáticamente
- `attach_receipt_to_transaction(operation_number, receipt_path)` - UPDATE con foto

---

## 🌐 REST API Endpoints

**Base URL:** `https://moscowle.com` (o localhost:9000 en dev)  
**Autorización:** Requiere @admin_required en todas

### POST /admin/yape/import
**Propósito:** Importar archivo CSV/XLSX de Yape

```http
POST /admin/yape/import HTTP/1.1
Content-Type: multipart/form-data

file=<CSV_O_XLSX_FILE>

Response:
{
  "success": true,
  "message": "Import successful",
  "stats": {
    "total_rows": 100,
    "processed": 98,
    "duplicates_skipped": 2,
    "errors": 0,
    "expenses_created": 45,
    "batch_id": "batch_12345"
  }
}
```

### GET /admin/yape/search
**Propósito:** Buscar transacción por operation_number o sender_name

```http
GET /admin/yape/search?q=OPERACION123&limit=20&offset=0

Response:
{
  "success": true,
  "total": 5,
  "results": [
    {
      "id": "tx_abc123",
      "operation_number": "OPERACION123",
      "transaction_date": "2026-03-15",
      "sender_name": "Juan Pérez",
      "amount": 150.50,
      "message": "Pago consulta",
      "category": "therapist_payment",
      "receipt_image_path": null,
      "created_at": "2026-03-19T10:30:00"
    }
  ]
}
```

### POST /admin/yape/{operation_number}/attach-receipt
**Propósito:** Adjuntar foto de comprobante a transacción existente

```http
POST /admin/yape/OPERACION123/attach-receipt HTTP/1.1
Content-Type: multipart/form-data

file=<JPG_O_PNG_IMAGE>

Response:
{
  "success": true,
  "message": "Receipt attached",
  "receipt_path": "instance/uploads/yape_receipts/uuid_abc123.jpg"
}
```

### GET /admin/yape/pending
**Propósito:** Listar transacciones sin receipt adjuntado

```http
GET /admin/yape/pending?limit=50&offset=0

Response:
{
  "success": true,
  "total": 23,
  "pending": [
    {
      "id": "tx_xyz",
      "operation_number": "OP001",
      "sender_name": "María García",
      "amount": 200.00,
      "transaction_date": "2026-03-15"
    },
    ...
  ]
}
```

### GET /admin/yape/history
**Propósito:** Historial de todas las importaciones (batches)

```http
GET /admin/yape/history?page=1&per_page=10

Response:
{
  "success": true,
  "total_batches": 15,
  "batches": [
    {
      "batch_id": "batch_001",
      "import_date": "2026-03-19T10:30:00",
      "total_transactions": 100,
      "total_amount": 15000.50,
      "duplicates_skipped": 2,
      "errors": 0
    },
    ...
  ]
}
```

### GET /admin/yape/dashboard
**Propósito:** Página HTML del panel de control Yape

```http
GET /admin/yape/dashboard

Response: HTML page con
├─ Import form de drag-drop
├─ Estadísticas recientes
├─ Pending receipts counter
└─ Historial de imports
```

---

## 🔐 Decoradores de Autorización

**Ubicación:** `app/utils/decorators.py`

```python
from app.utils.decorators import admin_required, therapist_required, patient_required

# Uso en rutas
@app.route('/admin/panel')
@admin_required
def admin_panel():
    return "Solo admin puede ver esto"

@app.route('/therapist/schedule')
@therapist_required
def therapist_schedule():
    return "Solo terapista puede ver esto"

@app.route('/patient/history')
@patient_required
def patient_history():
    return "Solo paciente puede ver esto"
```

---

## 📊 Modelo Base de Datos

**Ubicación:** `app/models.py`

### YapeTransaction

```python
from app.models import YapeTransaction

# Crear
tx = YapeTransaction(
    operation_number='OP123456',  # UNIQUE - Previene duplicados
    transaction_date=datetime(2026, 3, 15),
    sender_name='Juan Pérez',
    amount=150.50,
    message='Pago consulta',
    category='therapist_payment',
    is_expense=True,
    import_batch_id='batch_001'
)
db.session.add(tx)
db.session.commit()

# Buscar
tx = YapeTransaction.query.filter_by(
    operation_number='OP123456'
).first()

# Actualizar receipt
tx.receipt_image_path = 'instance/uploads/yape_receipts/abc123.jpg'
db.session.commit()

# Stats
total = YapeTransaction.query.count()
sum_amount = db.session.query(
    db.func.sum(YapeTransaction.amount)
).scalar()
```

**Campos principales:**
- `id`: UUID (Primary Key)
- `operation_number`: STRING UNIQUE (← Previene duplicados)
- `transaction_date`: DATE
- `sender_name`: STRING (sanitizado)
- `amount`: DECIMAL(10, 2)
- `message`: TEXT (sanitizado)
- `category`: ENUM (therapist_payment, operational, etc.)
- `receipt_image_path`: STRING (nullable, ruta a foto)
- `expense_id`: INT FK (optional link a Expense)
- `import_batch_id`: UUID (tracking de batch)
- `created_at`, `updated_at`, `processed_at`: TIMESTAMP audit fields

---

## 📁 Estructura de Archivos Generados

```
moscowle_ia_mvp/
├── app/
│   ├── models.py ..................... ✨ +YapeTransaction (40 líneas)
│   ├── services/
│   │   └── yape_service.py ........... ✨ NEW (270 líneas)
│   ├── routes/
│   │   └── yape_routes.py ............ ✨ NEW (180 líneas)
│   ├── utils/
│   │   └── decorators.py ............. ✨ NEW (30 líneas)
│   └── __init__.py ................... ✨ +yape_bp registration
│
├── migrations/
│   └── add_yape_transaction.py ........ ✨ NEW (25 líneas)
│
├── scripts/
│   └── deploy.sh ..................... ✨ NEW (430 líneas)
│
├── documentation/
│   └── TECHNICAL_AUDIT_2026.md ........ ✨ NEW (400+ líneas)
│
├── QUICK_START.md ..................... ✨ NEW (referencia rápida)
├── ARQUITECTURA_YAPE.md ............... ✨ NEW (diagramas)
├── EXECUTIVE_SUMMARY.md ............... ✨ NEW (resumen ejecutivo)
└── HERRAMIENTAS_DISPONIBLES.md ........ THIS FILE
```

---

## 🧪 Testing & Debugging

### Test Local (Dev)

```bash
# 1. Iniciar servidor
PORT=9000 python3 run.py

# 2. En otra terminal, crear tabla
python3 migrations/add_yape_transaction.py

# 3. Testear importación
curl -X POST \
  -F "file=@test_yape.csv" \
  http://localhost:9000/admin/yape/import

# 4. Buscar
curl http://localhost:9000/admin/yape/search?q=OPERACION123

# 5. Ver adjuntos pendientes
curl http://localhost:9000/admin/yape/pending
```

### Test Python Directo

```python
from app import create_app
from app.services.yape_service import YapeService
from app.models import YapeTransaction
from app.extensions import db

app = create_app()

with app.app_context():
    # Crear tabla
    db.create_all()
    
    # Test UPSERT (importar 2x)
    service = YapeService()
    
    with open('test_yape.csv') as f:
        success1, stats1 = service.import_transactions(f, 'csv')
    
    print(f"Primer import: {stats1}")  # processed: 100
    
    with open('test_yape.csv') as f:
        success2, stats2 = service.import_transactions(f, 'csv')
    
    print(f"Segundo import: {stats2}")  # processed: 0, duplicates_skipped: 100
    
    # Verificar
    total = YapeTransaction.query.count()
    print(f"Total en DB: {total}")  # Debe ser 100, NOT 200 ✅ Idempotencia
```

---

## 📋 Checklist de Deployment

```
ANTES DE DESPLEGAR:
─────────────────

[ ] Leer DEPLOYMENT_GUIDE.md completamente
[ ] Ejecutar ./scripts/deploy.sh localmente
[ ] Verificar deploy_moscowle_v2.zip (18 MB, sin .git, .venv)
[ ] Testear importación con CSV pequeño (10 filas)
[ ] Testear idempotencia (importar 2x, verificar 0 duplicados)
[ ] Testear adjuntos (upload foto, verificar guardada)
[ ] Crear base de datos MySQL en cPanel
[ ] Configurar .env.production con DB credentials
[ ] Crear directorio uploads/ con permisos 755

DEPLOYMENT:
───────────

[ ] Subir ZIP a cPanel
[ ] Unzip en public_html/
[ ] Ejecutar migraciones (add_yape_transaction.py)
[ ] Verificar permisos (755 para dirs, 644 para files)
[ ] Configurar cron para backups
[ ] Habilitar HTTPS con certificado SSL
[ ] Testear /admin/yape/import en producción
[ ] Configurar log rotation
[ ] Backup base de datos

POST-DEPLOYMENT:
────────────────

[ ] Monitor error logs (tail -f logs/error.log)
[ ] Verificar rate limiting active (100 req/hour)
[ ] Test de carga (importar 100k rows)
[ ] Validar backups automáticos
[ ] Documentar acceso SSH + DB
[ ] Setup monitoring (NewRelic/DataDog)
```

---

## 🔄 Workflow Típico

### 1. Developer (Local)

```bash
# Setup inicial
python3 migrations/add_yape_transaction.py
PORT=9000 python3 run.py

# Test
curl -F "file=@yape_test.csv" http://localhost:9000/admin/yape/import

# Verificar idempotencia
# (importar mismo CSV 2x, esperar 0 duplicados)
```

### 2. QA (Testing)

```bash
# Funcional tests
- Importar CSV válido
- Importar CSV con datos inválidos (debe fallar cleanly)
- Importar XLSX
- Buscar por operation_number
- Adjuntar receipt foto
- Verificar pending list
- Test de carga (1000 rows)

# Security tests
- MIME validation (try upload EXE file → rechazado)
- XSS en CSV (try injection en sender_name → sanitizado)
- Authorization (try sin @admin → 401)
```

### 3. DevOps (Deployment)

```bash
# Pre-deployment
./scripts/deploy.sh
# Check: deploy_moscowle_v2.zip + DEPLOYMENT_GUIDE.md

# Deployment (cPanel)
unzip deploy_moscowle_v2.zip
python3 migrate.py
python3 run.py  # Or configure with Passenger/cPanel

# Post-deployment
# Monitor logs, check endpoints, validate data
```

---

## ⚡ Performance Tuning Tips

| Problema | Solución |
|----------|----------|
| Importación lenta | Aumentar batch size, usar pooling |
| Memory overflow | Verificar streaming (generadores) |
| Búsquedas lentas | Agregar índices, usar pagination |
| Adjuntos lentos | Validar tamaño max < 5 MB |
| DB locks | Usar savepoints for nested transactions |

---

## 🆘 Troubleshooting

### Import falla con "Unique constraint violation"
**Solución:** El archivo ya fue importado. Los duplicados son skipped (expected).

### "File too large"
**Solución:** Máximo 10 MB. Dividir CSV en partes más pequeñas.

### Receipt attachment devuelve 403
**Solución:** Verificar usuario tiene @admin_required. O directorio uploads/ no existe (crear con chmod 755).

### "Operation number not found"
**Solución:** Verificar operation_number exacto (case-sensitive). Usar GET /admin/yape/search.

### DB connection pooling issue
**Solución:** PostgreSQL recomendado para producción (vs SQLite). Ver TECHNICAL_AUDIT_2026.md.

---

## 📞 Referencia Rápida

| Qué necesitas | Archivo |
|---|---|
| Importar Yape CSV | YapeService + POST /admin/yape/import |
| Adjuntar foto | POST /admin/yape/{op}/attach-receipt |
| Ver transacciones | GET /admin/yape/search o /admin/yape/pending |
| Desplegar | ./scripts/deploy.sh + DEPLOYMENT_GUIDE.md |
| Entender seguridad | TECHNICAL_AUDIT_2026.md |
| Referencia rápida | QUICK_START.md |
| Diagrama visual | ARQUITECTURA_YAPE.md |

---

**Estado:** ✅ **PRODUCTION READY**  
**Última verificación:** 2026-03-19 10:30 UTC  
**Responsable:** Senior Software Architect Team  

Para preguntas, revisar el documento correspondiente o ejecutar tests locales.
