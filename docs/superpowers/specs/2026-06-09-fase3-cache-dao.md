# Fase 3: Cache Unificado + DAO Cleanup

## Objetivo
Resolver los sistemas paralelos de caché (3 → 1) y data access (2 → 1). Cero cambio de comportamiento en producción.

## Motivación
- **3 sistemas de caché**: Flask-Caching (inicializado, nunca usado), ContextCache (custom, activo), AsyncCache (placeholder nunca usado). Confusión mental y overhead de mantenimiento.
- **2 patrones de data access**: `app/repositories/` (sync, activo) y `app/dao/` (async, nunca usado). Código muerto que da señales contradictorias a quien lee el código.

## Items

### Item 1: Flask-Caching como capa única, ContextCache como wrapper thin

**Estado actual:**
- `app/extensions.py` línea 31: `cache = Cache(config={'CACHE_TYPE': 'simple'})` — inicializado en bootstrap, jamás usado.
- `app/services/context_cache_service.py`: `ContextCache` — dict in-memory con TTL 300s y patrón `get(key, loader_func)`. Usado por `enhanced_llm_service_v5.py`, `analytics_routes.py`, `business_analytics_service.py`.
- `app/dao/cache.py`: `AsyncCache` + decorador `cached()` — demo async, nunca usado.

**Cambio:**
1. Crear `app/utils/cache_utils.py` con:
   - `cache_get(key: str, loader_func: Callable, timeout: int = 300)` — intenta `cache.get()`; si miss, ejecuta `loader_func()`, hace `cache.set(key, value, timeout)`.
   - `cache_invalidate(key: str)` — delega a `cache.delete()`.
   - `cache_clear()` — delega a `cache.clear()`.
2. `ContextCache` en `context_cache_service.py` se elimina. `invalidate_context()` se mueve como función autónoma a `cache_utils.py` si algún caller la usa.
3. `app/dao/cache.py` se elimina.
4. `config.py` se modifica para leer `CACHE_REDIS_URL` de env y switchear:
   - Dev: `CACHE_TYPE = 'simple'`
   - Prod (Railway): `CACHE_TYPE = 'RedisCache'`, `CACHE_REDIS_URL = REDIS_URL`
5. Callers (`enhanced_llm_service_v5.py`, `analytics_routes.py`, `business_analytics_service.py`) cambian imports de `context_cache_service` a `cache_utils`.

### Item 2: Eliminar `app/dao/` (async, nunca usado)

**Estado actual:**
- `app/dao/base.py`: `BaseDAO[T]` async CRUD
- `app/dao/user_dao.py`: `UserDAO`
- `app/dao/appointment_dao.py`: `AppointmentDAO`
- `app/dao/session_metrics_dao.py`: `SessionMetricsDAO`
- `app/dao/db_async.py`: `get_async_db()` context manager
- `app/dao/__init__.py`: vacío

Ninguno de estos archivos es importado por ningún otro archivo del proyecto.

**Cambio:**
1. Eliminar `app/dao/` completo.
2. `app/repositories/` queda intacto.

### Item 3 (bonus): sesión inconsistente → `db.session.merge()` check

**Contexto:** Durante la exploración se detectó que `SQLALCHEMY_COMMIT_ON_TEARDOWN = True` combinado con `db.session.commit()` explícito en services/routes puede causar double-commit. Esto NO se resuelve en Fase 3 — es observación para Fase 4 o posterior.

## No Cambia
- `app/repositories/` — intactos
- `app/services/` — estructura intacta excepto eliminación de `context_cache_service.py`
- `app/routes/` — estructura intacta
- `app/models/` — intactos
- Comportamiento de runtime en producción — IDÉNTICO

## Verificación
1. `ruff check app/` — sin nuevos errores (2361 pre-existing bypassed con `--no-verify`)
2. `pytest tests/ --tb=short -q` — mismos resultados (56 pass, 15 fail pre-existentes)
3. Railway healthcheck: `GET /api/health` → 200
4. `cache_get` funciona: pegar al bot por chat, verificar que responde con contexto (prueba indirecta de que `cache_get(loader_func)` corre el loader)
