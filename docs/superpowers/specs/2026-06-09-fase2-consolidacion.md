# Fase 2: Consolidación de Código Duplicado

## Objetivo
Eliminar código duplicado y ambigüedades de naming: 4 items concretos con cero cambio de comportamiento.

## Motivación
El código base tiene 3 definiciones de `api_response()`, 3 de `_parse_datetime()`, dos servicios financieros con nombres casi idénticos, y lógica de detección de API requests duplicada. Esto causa bugs silenciosos (como patient_routes que no convierte naive→UTC) y confusión al navegar el código.

## Items

### Item 1: `api_response()` — 3 copias → 1

**Estado actual:**
- `utils/api_helpers.py`: `api_response(success, data, error, status)` — usada en `bootstrap.py` y `routes/api/_shared.py`
- `utils/async_utils.py`: `api_response(data, message, status_code, success)` — firma distinta, agrega campo `timestamp`, usada SOLO en `routes/async_api_routes.py`
- `app/utils/async_utils.py` tiene además `get_dao()` (usado en `async_api_routes.py`)

**Cambio:**
- `async_api_routes.py` cambia a importar `api_response` desde `api_helpers`
- Se actualizan las llamadas en `async_api_routes.py` para usar la firma de `api_helpers` (success → bool, error en vez de message)
- `async_utils.py` se queda solo con `get_dao()` (renombrar a `dao_helpers.py` es nice-to-have, no necesario)

### Item 2: `_parse_datetime()` — 3 copias → 1

**Estado actual:**
- `routes/therapist_routes.py` (línea 50): asume naive=America/Lima, convierte a UTC
- `routes/api/_shared.py` (línea 64): misma lógica que therapist_routes
- `routes/patient_routes.py` (línea 364): **bug** — no convierte naive→UTC, retorna naive datetime sin timezone

**Cambio:**
- Extraer a `app/utils/__init__.py` como `parse_datetime()` (exportada)
- `therapist_routes.py` importa de utils
- `_shared.py` importa de utils
- `patient_routes.py` importa de utils (se arregla el bug automáticamente)

### Item 3: `finance_service.py` vs `financial_service.py` → merge

**Estado actual:**
- `services/finance_service.py`: `FinanceService` — CRUD de gastos + financials por terapeuta (87 líneas)
- `services/financial_service.py`: `FinancialService` — reportes de deuda agrupados por sede (169 líneas)
- `FinanceService` se instancia como `finance_service` en `routes/admin/__init__.py`
- `FinancialService` se instancia como `fs` en `routes/api/_shared.py` y se importa inline en varios archivos

**Cambio:**
- Mover métodos de `FinanceService` a `FinancialService` en `financial_service.py`
- Borrar `services/finance_service.py`
- Actualizar imports: `FinanceService` → `FinancialService` en todos los archivos
- Actualizar instancias: en `routes/admin/__init__.py` y donde se use

### Item 4: `_is_api_request()` vs `mark_request_api()` → unificar

**Estado actual:**
- `middleware/request_handlers.py`: `_is_api_request()` — chequea path, g.is_api, mimetypes, XHR, is_json
- `utils/api_helpers.py`: `mark_request_api()` — misma idea pero con heurísticas adicionales (blueprint='api', '*/*' en Accept)

**Cambio:**
- `mark_request_api()` delega a `_is_api_request()` del middleware, eliminando la lógica duplicada
- Si hay heurísticas en `mark_request_api()` que no están en `_is_api_request()`, migrarlas a `_is_api_request()` antes de delegar

## No Cambia
- `routes/` — estructura de archivos intacta
- `dao/`, `repositories/` — intactos
- `models/`, `templates/`, `static/` — intactos
- Comportamiento de runtime en producción — IDÉNTICO

## Verificación
1. `ruff check app/` — sin nuevos errores
2. `pytest tests/ --tb=short -q` — mismos resultados (57 pass, 14 fail pre-existentes)
3. Railway healthcheck: `GET /api/health` → 200
