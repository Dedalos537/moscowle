# PRP: [Feature Name]

> **Version:** 1.0
> **Created:** [Date]
> **Status:** Draft | Ready | In Progress | Completed

---

## Goal
[What needs to be built - be specific about the end state]

## Why
- [Business value and user impact]
- [Integration with existing features]
- [Problems this solves and for whom]

## What
[User-visible behavior and technical requirements]

### Success Criteria
- [ ] [Specific measurable outcome 1]
- [ ] [Specific measurable outcome 2]
- [ ] [Specific measurable outcome 3]

---

## All Needed Context

### Project Stack
- **Language:** Python 3.11
- **Framework:** Flask + Flask-Login + SQLAlchemy
- **Database:** MySQL 8.0 (Railway), SQLite (tests)
- **Cache:** Flask-Caching (Redis in prod, memory in dev)
- **CI:** GitHub Actions (ruff → pytest → Docker build)
- **Deploy:** Railway (Dockerfile builder)
- **Auth:** Flask-Login session-based + bcrypt
- **Frontend:** Jinja2 templates + Tailwind CSS (CDN) + vanilla CSS

### Validation Commands
```bash
# Lint (ruff errors pre-existing)
ruff check app/ --output-format=github

# Tests (uses SQLite in-memory)
python -m pytest tests/ --tb=short -q

# Syntax check specific file
python -c "import py_compile; py_compile.compile('app/routes/file.py', doraise=True)"

# Check for leftover conflict markers
rg '<<<<<<<|=======|>>>>>>>' app/ -n
```

### Pre-existing Issues (don't reintroduce)
- Ruff has ~2361 pre-existing errors (PLC0415, E501, SIM103, S110, F401)
- .env file COMMITED with real production secrets (must gitignore + rotate)
- therapist_routes.py had 7 merge conflict markers (now fixed)
- SQLALCHEMY_COMMIT_ON_TEARDOWN = True (deprecated, explicit commits everywhere)
- Tests: 26 passed / 1 failed (false positive: test_protected_route_requires_login)
- No pytest venv locally — tests verified via CI only

### Code Conventions
- All routes use Flask Blueprints
- Data access via Repository pattern (app/repositories/)
- Cache via cache_utils.py wrapper over Flask-Caching
- Services in app/services/, routes in app/routes/
- Models in app/models/ (one file per domain)
- Templates: role-based dirs (therapist/, patient/, admin/)

---

## Implementation Blueprint

### Tasks (in execution order)
```yaml
Task N: [Description]
  - MODIFY: [path]
  - FIND pattern: "..."
  - INJECT after: "..."
```

---

## Validation Loop

### Level 1: Syntax & Style
```bash
python -c "import py_compile; py_compile.compile('PATH', doraise=True)"
```

### Level 2: Tests
```bash
python -m pytest tests/ -x --tb=short -q
```

---

## Anti-Patterns to Avoid
- ❌ Don't commit .env with real secrets
- ❌ Don't leave merge conflict markers
- ❌ Don't introduce new async patterns (all sync now)
- ❌ Don't create new DAO classes (use existing Repository pattern)
- ❌ Don't hardcode values that should be env vars
- ❌ Don't bypass pre-commit with --no-verify without documenting why
- ❌ Don't create new cache layers (use cache_utils.py)
