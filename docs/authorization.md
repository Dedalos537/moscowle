# Matriz de Permisos — Moscowle IA

## Roles del Sistema

| Rol | Descripcion | Permisos |
|-----|-------------|----------|
| `admin` | Administrador completo | Todos los permisos |
| `supervisor` | Supervision general | Lectura global, gestion de usuarios limitada |
| `terapista` | Terapeuta asignado | Gestion de sesiones propias, pacientes asignados |
| `jugador` | Paciente/Jugador | Lectura de datos propios, creacion de incidencias |

## Matriz de Rutas

### Admin Routes (`/admin/*`)

| Ruta | Admin | Supervisor | Terapista | Jugador |
|------|-------|------------|-----------|---------|
| `/admin/dashboard` | ✅ | ✅ | ❌ | ❌ |
| `/admin/sessions` | ✅ | ✅ | ❌ | ❌ |
| `/admin/users` | ✅ | ❌ | ❌ | ❌ |
| `/admin/sedes` | ✅ | ✅ | ❌ | ❌ |
| `/admin/finanzas` | ✅ | ✅ | ❌ | ❌ |
| `/admin/games` | ✅ | ❌ | ❌ | ❌ |
| `/admin/reports` | ✅ | ✅ | ❌ | ❌ |
| `/admin/messages` | ✅ | ✅ | ❌ | ❌ |
| `/admin/incidents` | ✅ | ✅ | ❌ | ❌ |

### Therapist Routes (`/therapist/*`)

| Ruta | Admin | Supervisor | Terapista | Jugador |
|------|-------|------------|-----------|---------|
| `/therapist/dashboard` | ❌ | ❌ | ✅ | ❌ |
| `/therapist/sessions` | ❌ | ❌ | ✅ | ❌ |
| `/therapist/patients` | ❌ | ❌ | ✅ | ❌ |
| `/therapist/incidents` | ❌ | ❌ | ✅ | ❌ |

### Patient Routes (`/patient/*`)

| Ruta | Admin | Supervisor | Terapista | Jugador |
|------|-------|------------|-----------|---------|
| `/patient/dashboard` | ❌ | ❌ | ❌ | ✅ |
| `/patient/sessions` | ❌ | ❌ | ❌ | ✅ |
| `/patient/incidents` | ❌ | ❌ | ❌ | ✅ |

### API Incidents (`/api/incidents/*`)

| Endpoint | Admin | Supervisor | Terapista | Jugador |
|----------|-------|------------|-----------|---------|
| `GET /api/incidents/dashboard` | ✅ | ✅ | ❌ | ❌ |
| `GET /api/incidents/metrics` | ✅ | ✅ | ❌ | ❌ |
| `GET /api/incidents` | ✅ (all) | ✅ (all) | ✅ (own) | ✅ (own) |
| `GET /api/incidents/my` | ✅ | ✅ | ✅ | ✅ |
| `POST /api/incidents` | ✅ | ✅ | ✅ | ✅ |
| `PUT /api/incidents/:id/status` | ✅ | ✅ | ✅ (own) | ❌ |
| `PUT /api/incidents/:id/assign` | ✅ | ✅ | ❌ | ❌ |

## Uso del Decorador

```python
from app.middleware.authorization import role_required
from app.auth_compat import login_required

@api_bp.route('/admin/users', methods=['GET'])
@login_required
@role_required('admin')
def list_users():
    ...

@api_bp.route('/incidents', methods=['GET'])
@login_required
@role_required('admin', 'supervisor', 'terapista', 'jugador')
def list_incidents():
    ...
```
