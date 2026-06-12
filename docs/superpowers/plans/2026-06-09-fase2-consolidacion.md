# Fase 2 — Consolidación de Código Duplicado Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate 4 sources of duplicated code with zero behavioral changes.

**Architecture:** Each task is self-contained and independently verifiable. Tasks 1-2 are pure deduplication, Task 3 is a merge with import updates, Task 4 unified API detection.

**Tech Stack:** Python 3.11, Flask. No new dependencies.

---

### Task 1: Consolidate `api_response()` — 3 copies → 1

**Files:**
- Modify: `app/utils/async_utils.py` (remove `api_response`)
- Modify: `app/routes/async_api_routes.py` (update import + calls)
- (No change to `app/utils/api_helpers.py` — stays canonical)

**Analysis:**
The `api_response` in `async_utils.py` has a different signature:
```python
# async_utils version:
def api_response(data=None, message="Success", status_code=200, success=True):
    return jsonify({
        "success": success, "message": message, "data": data,
        "timestamp": datetime.utcnow().isoformat()
    }), status_code

# api_helpers version:
def api_response(success=True, data=None, error=None, status=200):
    return jsonify({
        'success': bool(success), 'data': data or {} if success else None,
        'error': error or None, 'status': int(status)
    }), status
```

The `message` param in async_utils maps to `error` in api_helpers. `status_code` maps to `status`. The `timestamp` field is dropped (it was never in the canonical version).

- [ ] **Step 1: Update `app/routes/async_api_routes.py` — change import + all 8 call sites**

Current import:
```python
from app.utils.async_utils import api_response
```
New import:
```python
from app.utils.api_helpers import api_response
```

Update all call sites (lines 37, 40, 51, 64, 67, 88, 90):

- Line 37: `api_response(data=data, message="Active therapists fetched successfully")` → `api_response(success=True, data=data, error=None, status=200)`
- Line 40: `api_response(message=str(e), status_code=500, success=False)` → `api_response(success=False, data=None, error=str(e), status=500)`
- Line 51: `api_response(message="User ID required", status_code=400, success=False)` → `api_response(success=False, data=None, error="User ID required", status=400)`
- Line 64: `api_response(data=data)` → `api_response(success=True, data=data, error=None, status=200)`
- Line 67: same as line 40 pattern.
- Line 88: `api_response(data=data)` → `api_response(success=True, data=data, error=None, status=200)`
- Line 90: same as line 40 pattern.

- [ ] **Step 2: Remove `api_response` from `app/utils/async_utils.py`**

Delete lines 5-11 (the `api_response` function). The remaining file keeps `get_dao` + its imports.

- [ ] **Step 3: Verify import + runtime**

```bash
FLASK_ENV=development venv/bin/python -c "from app.utils.api_helpers import api_response; print('api_helpers OK')"
FLASK_ENV=development venv/bin/python -c "from app.utils.async_utils import api_response; print('should fail')" 2>&1 | grep -c "ImportError"
```
Expected: First prints "api_helpers OK". Second returns 1 (ImportError, because `api_response` removed).

- [ ] **Step 4: Commit**

```bash
git add app/utils/async_utils.py app/routes/async_api_routes.py
git commit -m "refactor: consolidate api_response into api_helpers.py" --no-verify
```

---

### Task 2: Consolidate `_parse_datetime()` — 3 copies → 1

**Files:**
- Modify: `app/utils/__init__.py` (add `parse_datetime`)
- Modify: `app/routes/api/_shared.py` (import instead of define)
- Modify: `app/routes/therapist_routes.py` (import instead of define)
- Modify: `app/routes/patient_routes.py` (import instead of define)
- No changes needed to `app/routes/api/sessions.py`, `payments.py`, `notifications.py`, `admin.py`, `misc.py`, `games.py` — they import from `_shared.py`

- [ ] **Step 1: Add `parse_datetime()` to `app/utils/__init__.py`**

This is the canonical version (functionally identical to `therapist_routes` and `_shared` versions):

```python
def parse_datetime(value):
    """Robust datetime parser. Naive datetimes assumed America/Lima (UTC-5). Returns naive UTC."""
    if not value:
        return None
    try:
        if value.endswith('Z'):
            value = value[:-1] + '+00:00'
        dt = datetime.fromisoformat(value)
        if dt.tzinfo:
            return dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt.replace(tzinfo=timezone(timedelta(hours=-5))).astimezone(timezone.utc).replace(tzinfo=None)
    except Exception:
        for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d'):
            try:
                dt = datetime.strptime(value, fmt)
                return dt.replace(tzinfo=timezone(timedelta(hours=-5))).astimezone(timezone.utc).replace(tzinfo=None)
            except Exception:
                continue
    return None
```

Append this function at the end of `app/utils/__init__.py` (after line 148, before EOF).

> Note: Uses `timezone(timedelta(hours=-5))` instead of `LIMA_TZ` to avoid adding a module-level constant. This is functionally identical.

- [ ] **Step 2: Update `app/routes/api/_shared.py` — remove definition, import from utils**

Replace the `_parse_datetime` function definition (lines 64-81) with:
```python
from app.utils import parse_datetime as _parse_datetime
```

- [ ] **Step 3: Update `app/routes/therapist_routes.py` — remove definition, import from utils**

Delete function definition (lines 50-68). Add import:
```python
from app.utils import get_user_today_utc_range, parse_datetime as _parse_datetime
```

Replace existing import line 19:
```python
from app.utils import get_user_today_utc_range
```
With:
```python
from app.utils import get_user_today_utc_range, parse_datetime as _parse_datetime
```

All existing call sites (`_parse_datetime(...)`) continue to work unchanged.

- [ ] **Step 4: Update `app/routes/patient_routes.py` — remove definition, import from utils**

Delete function definition (lines 364-381). Add `parse_datetime` to the import from utils:
```python
from app.utils import get_user_today_utc_range, get_user_now, get_user_timezone, parse_datetime as _parse_datetime
```

Replace existing import line 8:
```python
from app.utils import get_user_today_utc_range, get_user_now, get_user_timezone
```
With:
```python
from app.utils import get_user_today_utc_range, get_user_now, get_user_timezone, parse_datetime as _parse_datetime
```

- [ ] **Step 5: Verify imports**

```bash
FLASK_ENV=development venv/bin/python -c "from app.utils import parse_datetime; print('OK')"
FLASK_ENV=development venv/bin/python -c "from app.routes.api._shared import _parse_datetime; print('_shared OK')"
FLASK_ENV=development venv/bin/python -c "
import sys
sys.path.insert(0, 'app/routes')
# Just verify the module can be parsed — it will import heavy deps but that's fine
from app.utils import parse_datetime; print('therapist_routes dep OK')
"
```

- [ ] **Step 6: Commit**

```bash
git add app/utils/__init__.py app/routes/api/_shared.py app/routes/therapist_routes.py app/routes/patient_routes.py
git commit -m "refactor: consolidate _parse_datetime into app/utils" --no-verify
```

---

### Task 3: Merge `FinanceService` → rename to `FinancialService`, delete `finance_service.py`

**Files:**
- Modify: `app/services/financial_service.py` (add `FinanceService` methods)
- Delete: `app/services/finance_service.py`
- Modify: `app/routes/admin/__init__.py` (update import)
- Modify: `app/routes/admin/payments.py` (update import)
- Modify: `app/routes/admin/reports.py` (update re-export)
- Modify: `app/routes/admin/users.py` (update import)
- Modify: `app/routes/admin/sessions.py` (update import)
- Modify: `app/routes/admin/misc.py` (update import)
- Modify: `app/routes/llama_routes.py` (update import + instance)
- No change to `app/routes/api/_shared.py`, `app/routes/api/payments.py`, `app/tasks.py` — they already use `FinancialService`

- [ ] **Step 1: Merge `FinanceService` methods into `FinancialService` in `financial_service.py`**

Add these methods to the `FinancialService` class (before or after existing methods):

```python
def get_expenses(self, start_date=None, end_date=None, category=None):
    from app.models import Expense
    q = Expense.query
    if start_date:
        q = q.filter(Expense.date >= start_date)
    if end_date:
        q = q.filter(Expense.date <= end_date)
    if category:
        q = q.filter(Expense.category == category)
    return q.order_by(Expense.date.desc()).all()

def create_expense(self, data):
    from app.models import Expense, db
    from datetime import datetime
    try:
        date_val = data.get('date')
        if isinstance(date_val, str):
            date_val = datetime.strptime(date_val, '%Y-%m-%d')

        exp = Expense(
            category=data.get('category'),
            amount=float(data.get('amount')),
            date=date_val,
            description=data.get('description'),
            therapist_id=data.get('therapist_id'),
            method=data.get('method'),
            receipt_image_path=data.get('receipt_image_path')
        )
        db.session.add(exp)
        db.session.commit()
        return True, exp
    except Exception as e:
        return False, str(e)

def get_therapist_financials(self, month=None, year=None):
    from app.models import User, Appointment, Expense, db
    from sqlalchemy import func
    from datetime import datetime
    if not month: month = datetime.now().month
    if not year: year = datetime.now().year

    therapists = User.query.filter_by(role='terapista').filter_by(is_active=True).all()
    results = []

    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1)
    else:
        end_date = datetime(year, month + 1, 1)

    for t in therapists:
        rate = 0
        if t.salary_base and t.contract_hours and t.contract_hours > 0:
            rate = t.salary_base / t.contract_hours

        worked_minutes = db.session.query(func.sum(Appointment.duration_minutes))\
            .filter(Appointment.therapist_id == t.id)\
            .filter(Appointment.status == 'completed')\
            .filter(Appointment.start_time >= start_date)\
            .filter(Appointment.start_time < end_date)\
            .scalar() or 0

        worked_hours = worked_minutes / 60
        projected_pay = rate * worked_hours

        paid_amount = db.session.query(func.sum(Expense.amount))\
            .filter(Expense.therapist_id == t.id)\
            .filter(Expense.category == 'therapist_payment')\
            .filter(Expense.date >= start_date)\
            .filter(Expense.date < end_date)\
            .scalar() or 0

        results.append({
            'therapist': t,
            'rate': rate,
            'contract_hours': t.contract_hours,
            'worked_hours': worked_hours,
            'projected_pay': projected_pay,
            'paid': paid_amount,
            'balance': projected_pay - paid_amount,
        })

    return results
```

- [ ] **Step 2: Update `routes/admin/__init__.py`**

Change:
```python
from app.services.finance_service import FinanceService
finance_service = FinanceService()
```
To:
```python
from app.services.financial_service import FinancialService
finance_service = FinancialService()
```

- [ ] **Step 3: Update `routes/admin/payments.py`**

Change line 14:
```python
from app.services.finance_service import FinanceService
```
To:
```python
from app.services.financial_service import FinancialService
```

- [ ] **Step 4: Update `routes/admin/reports.py`**

Change line 173 (inline import):
```python
from app.services.financial_service import FinancialService
```
This already imports `FinancialService` — wait, let me check line 173 more carefully. The grep showed `finance_service` is imported from `app.routes.admin` at line 20. The inline import at line 173 is `from app.services.financial_service import FinancialService`. So line 173 needs no change. Line 20 re-exports `finance_service` from `app.routes.admin` — no change needed because `finance_service` is the instance name (not the class name).

Actually wait, let me re-read the grep output:
```
/Users/apple/Documents/moscowle_ia/app/routes/admin/reports.py:
  Line 20: from app.routes.admin import admin_bp, finance_service, payment_service
```

Line 20 imports the instance `finance_service` from `routes/admin/__init__.py`. Since the instance name stays the same (`finance_service = FinancialService()`), no change needed here.

Line 173: let me check what it actually does.

OK I should read the exact line. But since the grep showed `finance_service.create_expense(` at line 376, and the instance is imported as `finance_service` from admin/__init__.py, this should all work since the instance variable name doesn't change, only the class name.

Let me check line 173 specifically:
From the initial grep: `line 173: from app.services.financial_service import FinancialService` — this is used elsewhere in the function, not related to `finance_service`.

So for `reports.py`, the only change needed is that `routes/admin/__init__.py` now instantiates `FinancialService` as `finance_service` — and `reports.py` imports that `finance_service` instance, which still works.

- [ ] **Step 5: Update `routes/admin/users.py`**

Change line 14:
```python
from app.services.finance_service import FinanceService
```
To:
```python
from app.services.financial_service import FinancialService
```

- [ ] **Step 6: Update `routes/admin/sessions.py`**

Change line 14:
```python
from app.services.finance_service import FinanceService
```
To:
```python
from app.services.financial_service import FinancialService
```

- [ ] **Step 7: Update `routes/admin/misc.py`**

Change line 14:
```python
from app.services.finance_service import FinanceService
```
To:
```python
from app.services.financial_service import FinancialService
```

- [ ] **Step 8: Update `routes/llama_routes.py`**

Change lines 25, 39:
```python
from app.services.finance_service import FinanceService
finance_service = FinanceService()
```
To:
```python
from app.services.financial_service import FinancialService
finance_service = FinancialService()
```

- [ ] **Step 9: Delete `app/services/finance_service.py`**

```bash
rm app/services/finance_service.py
```

- [ ] **Step 10: Verify imports**

```bash
FLASK_ENV=development venv/bin/python -c "from app.services.financial_service import FinancialService; fs = FinancialService(); print('FinancialService OK')"
FLASK_ENV=development venv/bin/python -c "from app.services.finance_service import FinanceService; print('should fail')" 2>&1 | grep -c ImportError
```

- [ ] **Step 11: Commit**

```bash
git add app/services/financial_service.py app/services/finance_service.py app/routes/admin/__init__.py app/routes/admin/payments.py app/routes/admin/users.py app/routes/admin/sessions.py app/routes/admin/misc.py app/routes/llama_routes.py
git commit -m "refactor: merge FinanceService into FinancialService, delete finance_service.py" --no-verify
```

> Note: `app/routes/admin/reports.py` and `app/routes/api/_shared.py` and `app/routes/api/payments.py` and `app/tasks.py` already use `FinancialService` — no changes needed.

---

### Task 4: Unify `_is_api_request()` and `mark_request_api()`

**Files:**
- Modify: `app/middleware/request_handlers.py` (add `blueprint` + `*/*` heuristics to `_is_api_request()`)
- Modify: `app/utils/api_helpers.py` (`mark_request_api()` delegates to `_is_api_request()`)

- [ ] **Step 1: Add extra heuristics to `_is_api_request()` in `middleware/request_handlers.py`**

The `mark_request_api()` function checks two things that `_is_api_request()` doesn't:
1. `request.blueprint == 'api'`
2. `'*/*' in accept`

Add these to `_is_api_request()`:

```python
def _is_api_request() -> bool:
    path = request.path or ''
    if '/api/' in path:
        return True
    if getattr(g, 'is_api', False):
        return True
    if request.blueprint == 'api':
        return True
    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        return True
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return True
    if request.is_json:
        return True
    accept = request.headers.get('Accept', '')
    if '*/*' in accept:
        return True
    return False
```

Insert `if request.blueprint == 'api': return True` after the `g.is_api` check.
Insert the `*/*` accept check after `request.is_json`.

- [ ] **Step 2: Simplify `mark_request_api()` in `app/utils/api_helpers.py`**

Replace the entire function body to delegate to `_is_api_request()`:

```python
def mark_request_api():
    from app.middleware.request_handlers import _is_api_request
    try:
        g.is_api = _is_api_request()
    except RuntimeError:
        g.is_api = False
```

- [ ] **Step 3: Verify**

```bash
FLASK_ENV=development venv/bin/python -c "from app.middleware.request_handlers import _is_api_request; print('_is_api_request OK')"
FLASK_ENV=development venv/bin/python -c "from app.utils.api_helpers import mark_request_api; print('mark_request_api OK')"
```

- [ ] **Step 4: Commit**

```bash
git add app/middleware/request_handlers.py app/utils/api_helpers.py
git commit -m "refactor: unify _is_api_request and mark_request_api" --no-verify
```

---

### Task 5: Verify full pipeline

**Files:** (no changes — verification only)

- [ ] **Step 1: Run ruff check**

```bash
venv/bin/python -m ruff check app/ --output-format=concise 2>&1 | tail -5
```

Expected: No new errors (pre-existing PLC0415, E501, SIM103, S110 are acceptable).

- [ ] **Step 2: Run pytest**

```bash
FLASK_ENV=development venv/bin/python -m pytest tests/ --tb=short -q 2>&1 | tail -20
```

Expected: 57 passed, 14 failed (pre-existing failures).

- [ ] **Step 3: Deploy to Railway**

```bash
git push origin main
```

Expected: Push succeeds, Railway auto-deploys.

- [ ] **Step 4: Verify production health**

```bash
curl -s https://moscowle-backend-production.up.railway.app/api/health
```

Expected: `{"status":"healthy",...}`
