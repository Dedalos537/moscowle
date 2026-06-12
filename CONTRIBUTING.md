# Contributing to Moscowle IA

## Commit Message Convention

All commits MUST follow this format:

```
<tipo>(<ámbito>): <descripción>
```

### Valid Types (tipo)
| Type | Usage |
|------|-------|
| `feat` | New feature |
| `fix` | Bug fix |
| `refactor` | Code restructuring without behavior change |
| `test` | Adding/modifying tests |
| `docs` | Documentation only |
| `chore` | Build, CI, dependencies |
| `spec` | Specification or design document |
| `prp` | PRP (Product Requirements Prompt) |
| `plan` | Implementation plan |
| `debug` | Debugging/investigation commit |

### Valid Scopes (ámbito)
Examples: `api`, `models`, `auth`, `ui`, `db`, `ci`, `monitor`, `chat`, `payment`, `report`, `core`, `config`, `deploy`

### Examples
```
feat(auth): implementar login OAuth Google
fix(api): corregir validación email en registro
refactor(models): extraer AuditMixin a base.py
test(ci): agregar stage E2E en deploy-frontend
docs(core): agregar CONTRIBUTING.md
```

### Ticket References
In the commit body (not subject), reference tickets when applicable:
```
feat(payment): agregar soporte para Yape

Referencia: MOSCOWLE-42
```

If no ticket exists, use `Referencia: N/A`.

### Breaking Changes
Add `!` before the colon for breaking changes:
```
refactor(db)!: migrar de SQLite a PostgreSQL
```

## Pre-commit Hooks

This project uses [pre-commit](https://pre-commit.com) for:
- `ruff` — linter + formatter
- `ruff (security)` — security lint rules
- `trailing-whitespace`, `end-of-file-fixer`, `check-yaml`, `check-json`
- `check-added-large-files`, `detect-private-key`, `debug-statements`
- `commit-msg-validator` — validates commit message format

Install hooks:
```bash
pre-commit install --hook-type pre-commit --hook-type commit-msg
```

## Development Setup
```bash
cp .env.example .env
# Fill in your .env values
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python run.py
```

## Running Tests
```bash
python -m pytest tests/ --tb=short -q --cov=app
```
