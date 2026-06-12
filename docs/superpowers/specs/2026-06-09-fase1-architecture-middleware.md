# Fase 1: Arquitectura + Middleware

## Objetivo
Refactorizar el `app/__init__.py` (655 líneas) extrayendo cada responsabilidad a su propio módulo, sin cambiar comportamiento de runtime.

## Motivación
El app factory actual mezcla 7 responsabilidades distintas en un solo archivo:
1. Configuración de logging
2. Setup de Swagger / Sentry
3. Middleware de seguridad (ProxyFix, Talisman, APP_SECRET_KEY validation)
4. Inicialización de extensiones (db, migrate, bcrypt, mail, cors, etc.)
5. Request/response handlers (before_request, after_request)
6. Error handlers (400, 403, 404, 429, 500, Exception)
7. CLI commands (migrate-messages)
8. Blueprint registration (16 blueprints)
9. Template filters
10. Scheduler initialization
11. Ollama health check

## Estructura Propuesta

```
app/
├── __init__.py              # Solo create_app() (~30 líneas)
├── middleware/
│   └── request_handlers.py  # before_request + after_request (~120 líneas)
├── logging_setup.py         # setup_logging() extraído (~40 líneas)
├── cli.py                   # Comandos CLI extraídos (~50 líneas)
├── bootstrap.py             # init_extensions(), register_blueprints(), register_template_filters() (~100 líneas)
├── extensions.py            # (sin cambios - singleton de extensiones Flask)
├── tasks.py                 # (sin cambios - scheduler tasks)
└── routes/                  # (sin cambios - 16 blueprints)
```

## Cambios Específicos

### 1. `app/middleware/__init__.py` + `app/middleware/request_handlers.py`
- Mover `register_request_handlers(app)` completo
- Incluye: logging de requests, App-Key validation, security headers
- Sin cambios de lógica

### 2. `app/logging_setup.py`
- Mover `setup_logging(app)` completo
- Incluye: JSON formatter, RotatingFileHandler, console handler, log capture

### 3. `app/cli.py`
- Mover el comando `migrate-messages` y `@app.cli.command`
- En el futuro aquí irán más comandos CLI

### 4. `app/bootstrap.py`
- Mover `register_auth_loader(app)`
- Mover `register_error_handlers(app)`
- Mover inicialización de extensiones (Swagger, Sentry, Security, Extensions init, CORS, Rate Limiting)
- Mover `register_blueprints()` (todos los 16 blueprints)
- Mover inline template filter `from_json`
- Mover scheduler init + Ollama init

### 5. `app/__init__.py` (renovado)
```python
from app.logging_setup import setup_logging
from app.middleware.request_handlers import register_request_handlers
from app.bootstrap import (
    init_swagger, init_sentry, init_security,
    init_extensions, register_blueprints, init_scheduler_and_ollama
)
from app.cli import register_cli_commands
# ... solo llamadas a funciones

def create_app(config_class=None):
    # config detection (sin cambios)
    # setup_logging(app)
    # init_swagger(app)
    # init_sentry(app)
    # init_security(app)
    # init_extensions(app)
    # register_error_handlers(app)
    # register_request_handlers(app)
    # register_blueprints(app)
    # register_cli_commands(app)
    # init_scheduler_and_ollama(app)
    # return app
```

## No Cambia
- `extensions.py` — singleton pattern intacto
- `tasks.py` — scheduler jobs intactos
- `routes/` — 16 blueprints intactos
- `services/` — service layer intacto
- `models/` — modelos intactos
- `dao/`, `repositories/` — intactos
- `config.py` — intacto
- `run.py`, `server.py`, `run_gunicorn.py` — intactos
- Comportamiento de before_request / after_request: IDÉNTICO

## Verificación
1. `ruff check app/` — sin nuevos errores
2. `pytest tests/ --tb=short -q` — mismos resultados que antes (57 pass, 14 fail pre-existentes)
3. Railway healthcheck: `GET /api/health` → 200
