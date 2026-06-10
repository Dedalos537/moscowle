# Fase 3: Cache Unificado + DAO Cleanup — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Unify 3 cache systems into 1 (Flask-Caching + Redis) and eliminate the unused async DAO layer by migrating its single consumer (`async_api_routes.py`) to sync Repositories.

**Architecture:**
- Cache: Flask-Caching initialized in `extensions.py` as the single cache layer; a thin `cache_utils.py` wrapper provides `cache_get(key, loader_func, timeout)` to preserve the ContextCache loader pattern; `CACHE_TYPE` switches to `RedisCache` in production via `REDIS_URL` env var.
- DAO: 3 methods from async DAOs get added to sync Repositories; `async_api_routes.py` converts from `async def` + `get_async_db()` to sync `def` + `Repository` static methods; entire `app/dao/` deleted.

**Tech Stack:** Flask-Caching, Redis (optional prod backend), SQLAlchemy, Flask-SQLAlchemy

---

### Task 1: Create `app/utils/cache_utils.py`

**Files:**
- Create: `app/utils/cache_utils.py`
- Modify: (none yet)

- [ ] **Step 1: Write `app/utils/cache_utils.py`**

```python
import logging
from app.extensions import cache

logger = logging.getLogger('app')

def cache_get(key: str, loader_func=None, timeout: int = 300):
    data = cache.get(key)
    if data is not None:
        logger.info(f"Cache HIT: {key}")
        return data
    logger.info(f"Cache MISS: {key}, loading...")
    if loader_func:
        data = loader_func()
        if data is not None:
            cache.set(key, data, timeout=timeout)
        return data
    return None

def cache_invalidate(key: str = None):
    if key:
        cache.delete(key)
        logger.info(f"Cache invalidated: {key}")
    else:
        cache.clear()
        logger.info("Cache cleared")

def invalidate_context():
    cache_invalidate('full_context')
```

- [ ] **Step 2: Commit**

```bash
git add app/utils/cache_utils.py
git commit -m "feat: add cache_utils.py wrapper over Flask-Caching"
```

---

### Task 2: Wire Redis support in `config.py` and `extensions.py`

**Files:**
- Modify: `config.py` (lines 138-141 add `CACHE_REDIS_URL`)
- Modify: `app/extensions.py` (line 31 make `CACHE_TYPE` dynamic from config)

- [ ] **Step 1: Update `config.py` — add `CACHE_REDIS_URL` and `CACHE_TYPE`**

Replace lines 138-141 (the `RATELIMIT_STORAGE_URL` / Redis comment block):

Old:
```python
    # ========== RATE LIMITING - OPTIMIZED ==========
    # Use Redis in production: redis://localhost:6379
    # Fallback to memory if not set
    RATELIMIT_STORAGE_URL = os.getenv('RATELIMIT_STORAGE_URL', 'memory://')
```

New:
```python
    # ========== CACHE - Redis support for production ==========
    CACHE_TYPE = os.getenv('CACHE_TYPE', 'simple')
    CACHE_REDIS_URL = os.getenv('REDIS_URL')

    # ========== RATE LIMITING - OPTIMIZED ==========
    # Use Redis in production: redis://localhost:6379
    # Fallback to memory if not set
    RATELIMIT_STORAGE_URL = os.getenv('RATELIMIT_STORAGE_URL', 'memory://')
```

- [ ] **Step 2: Update `app/extensions.py` — load `CACHE_TYPE` from app config**

Replace line 31:
```python
cache = Cache(config={'CACHE_TYPE': 'simple'})
```

With:
```python
cache = Cache()
```

- [ ] **Step 3: Update `app/bootstrap.py` — pass config to cache.init_app**

Find `cache.init_app(app)` and add config before it:

Old:
```python
    cache.init_app(app)
```

New:
```python
    cache_config = {
        'CACHE_TYPE': app.config.get('CACHE_TYPE', 'simple'),
    }
    if app.config.get('CACHE_REDIS_URL'):
        cache_config['CACHE_REDIS_URL'] = app.config['CACHE_REDIS_URL']
    cache.init_app(app, cache_config)
```

- [ ] **Step 4: Commit**

```bash
git add config.py app/extensions.py app/bootstrap.py
git commit -m "feat: wire Redis support for Flask-Caching"
```

---

### Task 3: Migrate `context_cache_service.py` callers to `cache_utils`

**Files:**
- Modify: `app/services/enhanced_llm_service_v5.py` (lines 11, 490, 507)
- Modify: `app/routes/analytics_routes.py` (line 4)
- Search: `business_analytics_service.py` for context_cache usage

- [ ] **Step 1: Check if `business_analytics_service.py` uses context_cache**

Run: `rg "context_cache|ContextCache" app/services/business_analytics_service.py`

If it does, update that import too.

- [ ] **Step 2: Update `enhanced_llm_service_v5.py`**

Change line 11 from:
```python
from app.services.context_cache_service import get_cached_context, get_cached_context_text, invalidate_context
```
To:
```python
from app.utils.cache_utils import invalidate_context
from app.services.context_loader_service import context_loader

def get_cached_context():
    from app.utils.cache_utils import cache_get
    return cache_get('full_context', loader_func=context_loader.get_full_context)

def get_cached_context_text():
    context = get_cached_context()
    if context:
        return context_loader.format_context_for_llama(context)
    return ""
```

Lines 490 and 507 call `invalidate_context()` — those stay as-is since the import now resolves to `cache_utils.invalidate_context`.

- [ ] **Step 3: Update `analytics_routes.py`**

Change line 4 from:
```python
from app.services.context_cache_service import context_cache
```
To:
```python
from app.utils.cache_utils import cache_get, cache_invalidate
```

Then update the usages of `context_cache.get(...)` to `cache_get(...)` and `context_cache.invalidate(...)` to `cache_invalidate(...)` in the file.

- [ ] **Step 4: Commit**

```bash
git add app/services/enhanced_llm_service_v5.py app/routes/analytics_routes.py
git commit -m "refactor: migrate context_cache callers to cache_utils"
```

---

### Task 4: Delete `context_cache_service.py`

**Files:**
- Delete: `app/services/context_cache_service.py`

- [ ] **Step 1: Delete file and commit**

```bash
git rm app/services/context_cache_service.py
git commit -m "refactor: remove context_cache_service.py (replaced by cache_utils)"
```

---

### Task 5: Add missing methods to sync Repositories

**Files:**
- Modify: `app/repositories/user_repository.py` — add `get_active_therapists()`
- Modify: `app/repositories/appointment_repository.py` — add `get_upcoming_for_user()`
- Modify: `app/repositories/metrics_repository.py` — add `get_by_user()` and `get_average_scores()`

- [ ] **Step 1: Add `get_active_therapists` to `UserRepository`**

Add to `app/repositories/user_repository.py`:

```python
    @staticmethod
    def get_active_therapists(skip=0, limit=50):
        from app.models import User, db
        return User.query.options(db.joinedload(User.assigned_sedes)).filter(
            User.role == 'terapista',
            User.is_active == True
        ).offset(skip).limit(limit).all()
```

- [ ] **Step 2: Add `get_upcoming_for_user` to `AppointmentRepository`**

Add to `app/repositories/appointment_repository.py`:

```python
    @staticmethod
    def get_upcoming_for_user(user_id, role, limit=5):
        from datetime import datetime
        from app.models import Appointment
        now = datetime.utcnow()
        query = Appointment.query.filter(
            Appointment.start_time >= now,
            Appointment.status != 'cancelled'
        ).order_by(Appointment.start_time).limit(limit)
        if role == 'terapista':
            query = query.filter(Appointment.therapist_id == user_id)
        else:
            query = query.filter(Appointment.patient_id == user_id)
        return query.all()
```

- [ ] **Step 3: Add `get_by_user` and `get_average_scores` to `MetricsRepository`**

Add to `app/repositories/metrics_repository.py`:

```python
    @staticmethod
    def get_by_user(user_id, limit=20, skip=0):
        from app.models import SessionMetrics
        return SessionMetrics.query.filter_by(user_id=user_id).order_by(
            SessionMetrics.date.desc()
        ).offset(skip).limit(limit).all()

    @staticmethod
    def get_average_scores(user_id, game_id=None):
        from app.models import SessionMetrics, db
        from sqlalchemy import func
        query = db.session.query(func.avg(SessionMetrics.accurracy)).filter(
            SessionMetrics.user_id == user_id
        )
        if game_id:
            query = query.filter(SessionMetrics.game_id == game_id)
        return query.scalar() or 0.0
```

- [ ] **Step 4: Commit**

```bash
git add app/repositories/user_repository.py app/repositories/appointment_repository.py app/repositories/metrics_repository.py
git commit -m "feat: add async DAO-equivalent methods to sync repositories"
```

---

### Task 6: Migrate `async_api_routes.py` from async DAO to sync Repository

**Files:**
- Modify: `app/routes/async_api_routes.py`

- [ ] **Step 1: Rewrite imports and endpoints**

Replace the entire file content:

```python
from flask import Blueprint, jsonify, request
from app.models import User, Appointment, SessionMetrics
from app.repositories.user_repository import UserRepository
from app.repositories.appointment_repository import AppointmentRepository
from app.repositories.metrics_repository import MetricsRepository
from app.utils.api_helpers import api_response

async_api_bp = Blueprint('async_api', __name__, url_prefix='/api/async')

@async_api_bp.route('/users/active', methods=['GET'])
def get_active_users():
    try:
        skip = request.args.get('skip', default=0, type=int)
        limit = request.args.get('limit', default=20, type=int)

        therapists = UserRepository.get_active_therapists(skip=skip, limit=limit)

        data = []
        for t in therapists:
            sedes = [{'id': s.id, 'name': s.name} for s in t.assigned_sedes]
            data.append({
                'id': t.id,
                'username': t.username,
                'email': t.email,
                'role': t.role,
                'sedes': sedes
            })

        return api_response(success=True, data=data, error=None, status=200)

    except Exception as e:
        return api_response(success=False, data=None, error=str(e), status=500)

@async_api_bp.route('/appointments/upcoming', methods=['GET'])
def get_upcoming_appointments():
    try:
        user_id = request.args.get('user_id', type=int)
        role = request.args.get('role', default='terapista', type=str)
        limit = request.args.get('limit', default=10, type=int)

        if not user_id:
            return api_response(success=False, data=None, error="User ID required", status=400)

        appointments = AppointmentRepository.get_upcoming_for_user(
            user_id=user_id, role=role, limit=limit
        )

        data = [{
            'id': a.id,
            'title': a.title,
            'start': a.start_time.isoformat(),
            'status': a.status
        } for a in appointments]

        return api_response(success=True, data=data, error=None, status=200)

    except Exception as e:
        return api_response(success=False, data=None, error=str(e), status=500)

@async_api_bp.route('/metrics/user/<int:user_id>', methods=['GET'])
def get_user_metrics(user_id):
    try:
        metrics = MetricsRepository.get_by_user(user_id=user_id, limit=20)
        avg_score = MetricsRepository.get_average_scores(user_id=user_id)

        data = {
            "average_accuracy": round(avg_score, 2),
            "recent_sessions": [{
                "id": m.id,
                "game": m.game_name,
                "accuracy": m.accurracy,
                "date": m.date.isoformat()
            } for m in metrics]
        }

        return api_response(success=True, data=data, error=None, status=200)
    except Exception as e:
        return api_response(success=False, data=None, error=str(e), status=500)
```

- [ ] **Step 2: Commit**

```bash
git add app/routes/async_api_routes.py
git commit -m "refactor: migrate async_api_routes from async DAO to sync repositories"
```

---

### Task 7: Delete `app/dao/` directory

**Files:**
- Delete: `app/dao/base.py`
- Delete: `app/dao/user_dao.py`
- Delete: `app/dao/appointment_dao.py`
- Delete: `app/dao/session_metrics_dao.py`
- Delete: `app/dao/db_async.py`
- Delete: `app/dao/cache.py`

- [ ] **Step 1: Remove entire directory**

```bash
rm -rf app/dao
```

- [ ] **Step 2: Commit**

```bash
git add -A
git commit -m "refactor: remove unused app/dao/ directory (migrated to sync repositories)"
```

---

### Task 8: Delete `app/utils/async_utils.py`

**Files:**
- Delete: `app/utils/async_utils.py`

- [ ] **Step 1: Verify it has no remaining callers**

Run: `rg "async_utils\|get_dao" app/ --include '*.py'`

Expected output: only the file itself (if still exists).

- [ ] **Step 2: Delete and commit**

```bash
git rm app/utils/async_utils.py
git commit -m "refactor: remove async_utils.py (no remaining callers)"
```

---

### Task 9: Verification

- [ ] **Step 1: Run ruff check**

```bash
ruff check app/ --no-verify 2>&1 | tail -5
```
Expected: same 2361 pre-existing errors, no new ones.

- [ ] **Step 2: Run tests**

```bash
pytest tests/ --tb=short -q 2>&1 | tail -10
```
Expected: same baseline (56 pass, 15 fail pre-existing).

- [ ] **Step 3: Push and deploy**

```bash
git push origin main && git push dedalos main
```

- [ ] **Step 4: Verify Railway healthcheck**

```bash
curl -s https://moscowle-backend-production.up.railway.app/api/health
```
Expected: `{"status":"healthy","database":"ok","gemini":"ok","groq":"ok"}`
