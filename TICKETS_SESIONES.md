# TICKETS: Flujo de Creación y Gestión de Sesiones

## Análisis de Errores Detectados

###  Problemas Identificados

1. **Manejo Inconsistente de Timezone**
   - El backend almacena en UTC (naive datetime)
   - El frontend envía datetimes locales sin timezone info
   - La conversión entre UTC y timezone del usuario es inconsistente
   - Los pacientes ven horarios incorrectos (UTC en lugar de su zona local)
   - La lógica de "is_active" usa UTC pero debería considerar timezone del usuario

2. **Validaciones Insuficientes en Creación de Sesiones**
   - No se valida que `start_time < end_time`
   - No se valida superposición de sesiones (double-booking)
   - No se valida que la fecha no sea en el pasado
   - No hay validación de duración mínima/máxima
   - Los errores no se propagan correctamente al frontend

3. **Asignación de Juegos Frágil**
   - Dos sistemas paralelos: JSON column + AppointmentGame table
   - La asignación via modal no actualiza la lista inmediatamente
   - No hay validación de que los juegos existen
   - El API `/sessions/assign-games` sobrescribe completamente (no hace merge)
   - Los juegos asignados en creación no se sincronizan correctamente

4. **Estado de Sesión Inconsistente**
   - `update_expired_appointments` solo se llama en `get_patient_appointments`
   - Las sesiones no se actualizan automáticamente en el dashboard del terapeuta
   - El status "completed" se determina de forma diferente en distintas partes del código
   - No hay validación de transiciones de estado (ej: completed → scheduled)
   - Las notificaciones no se envían cuando cambia el estado automáticamente

5. **UI/UX de Calendario y Gestión**
   - El calendario del terapeuta requiere doble-click para cargar sesiones del día
   - No hay indicador visual de loading al crear/editar sesiones
   - Los errores se muestran como alerts genéricos sin contexto
   - No hay confirmación de acciones críticas (ej: eliminar sesión)
   - La zona horaria del usuario no se muestra en ningún lado
   - El formulario de creación no persiste valores en caso de error

---

## 📋 TICKETS PRIORIZADOS

---

### 🎫 TICKET #1: Normalizar y Estandarizar Manejo de Timezone en Sesiones
**Prioridad:** 🔴 ALTA  
**Tipo:** Bug Fix / Refactor  
**Estimación:** 4-6 horas

#### Problema
El sistema maneja timezones de forma inconsistente causando que:
- Los pacientes vean horarios incorrectos (UTC vs timezone local)
- La lógica `is_active` sea imprecisa
- Los terapeutas puedan crear sesiones con horarios ambiguos

#### Criterios de Aceptación
- [ ] Crear función centralizada `normalize_datetime_for_storage(dt, user_timezone)` que convierta cualquier datetime a UTC naive para almacenar en DB
- [ ] Crear función `localize_datetime_for_display(dt_utc, user_timezone)` que convierta de UTC a timezone local
- [ ] Actualizar `api_create_session` para detectar timezone del frontend y normalizar antes de guardar
- [ ] Actualizar todas las rutas de lectura (`/sessions`, `/sessions/day`, `/appointments/patient`) para retornar datetimes en UTC con sufijo 'Z'
- [ ] Actualizar frontend (JavaScript) para convertir correctamente ISO strings con 'Z' a hora local del navegador
- [ ] Actualizar la lógica `is_active` en `patient_routes.py` para usar timezone-aware comparisons
- [ ] Agregar campo `timezone` visible en el perfil del usuario (ya existe en DB pero no se muestra)
- [ ] Escribir tests unitarios para conversiones de timezone

#### Archivos a Modificar
- `app/utils.py` (nuevas funciones)
- `app/routes/api_routes.py` (normalize en POST/PUT)
- `app/routes/patient_routes.py` (localize para display)
- `app/routes/therapist_routes.py` (localize para display)
- `app/templates/therapist/sessions.html` (JS timezone handling)
- `app/templates/patient/sessions.html` (display con timezone local)

#### Notas Técnicas
```python
# Ejemplo de implementación
def normalize_datetime_for_storage(dt_str, user_timezone_str='UTC'):
    """Convert any datetime string to UTC naive for DB storage"""
    user_tz = pytz.timezone(user_timezone_str)
    
    # Parse datetime (could be naive or aware)
    dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
    
    # If naive, assume it's in user's local time
    if dt.tzinfo is None:
        dt = user_tz.localize(dt)
    
    # Convert to UTC and make naive
    return dt.astimezone(pytz.UTC).replace(tzinfo=None)
```

---

### 🎫 TICKET #2: Implementar Validaciones Robustas en Creación y Edición de Sesiones
**Prioridad:** 🔴 ALTA  
**Tipo:** Feature / Bug Fix  
**Estimación:** 3-4 horas

#### Problema
La creación de sesiones carece de validaciones críticas, permitiendo:
- Sesiones con `end_time < start_time`
- Sesiones que se superponen (double-booking)
- Sesiones en fechas pasadas
- Duraciones inválidas (ej: 5 minutos o 10 horas)

#### Criterios de Aceptación
- [ ] Crear método `AppointmentService.validate_session_times(start, end, patient_id, therapist_id, session_id=None)`
- [ ] Validar que `start_time < end_time`
- [ ] Validar que `start_time >= now()` (excepto para ediciones de sesiones ya iniciadas)
- [ ] Validar duración mínima (15 min) y máxima (4 horas)
- [ ] Validar no-superposición con sesiones existentes del mismo terapeuta
- [ ] Validar no-superposición con sesiones existentes del mismo paciente
- [ ] Retornar errores descriptivos con códigos HTTP apropiados (400 para validation, 409 para conflicts)
- [ ] Actualizar frontend para mostrar errores específicos en el formulario (no alerts genéricos)
- [ ] Agregar indicadores visuales de loading durante la validación

#### Archivos a Modificar
- `app/services/appointment_service.py` (nuevo método `validate_session_times`)
- `app/routes/api_routes.py` (`api_create_session`, `api_update_session`)
- `app/templates/therapist/sessions.html` (mejorar manejo de errores)
- `app/templates/therapist/calendar.html` (mejorar manejo de errores)

#### Ejemplo de Validación
```python
def validate_session_times(self, start_time, end_time, patient_id, therapist_id, session_id=None):
    errors = []
    
    # Basic time validation
    if start_time >= end_time:
        errors.append("La hora de inicio debe ser anterior a la hora de fin")
    
    # Duration validation
    duration = (end_time - start_time).total_seconds() / 60
    if duration < 15:
        errors.append("La duración mínima de una sesión es 15 minutos")
    if duration > 240:
        errors.append("La duración máxima de una sesión es 4 horas")
    
    # Past date validation (for new sessions)
    if not session_id and start_time < datetime.utcnow():
        errors.append("No se pueden crear sesiones en el pasado")
    
    # Check therapist double-booking
    query = Appointment.query.filter(
        Appointment.therapist_id == therapist_id,
        Appointment.status.in_(['scheduled', 'in_progress']),
        or_(
            and_(Appointment.start_time <= start_time, Appointment.end_time > start_time),
            and_(Appointment.start_time < end_time, Appointment.end_time >= end_time),
            and_(Appointment.start_time >= start_time, Appointment.end_time <= end_time)
        )
    )
    if session_id:
        query = query.filter(Appointment.id != session_id)
    
    if query.first():
        errors.append("Ya tienes una sesión programada en ese horario")
    
    # Check patient double-booking
    query = Appointment.query.filter(
        Appointment.patient_id == patient_id,
        Appointment.status.in_(['scheduled', 'in_progress']),
        or_(
            and_(Appointment.start_time <= start_time, Appointment.end_time > start_time),
            and_(Appointment.start_time < end_time, Appointment.end_time >= end_time),
            and_(Appointment.start_time >= start_time, Appointment.end_time <= end_time)
        )
    )
    if session_id:
        query = query.filter(Appointment.id != session_id)
    
    if query.first():
        errors.append("El paciente ya tiene una sesión programada en ese horario")
    
    return errors
```

---

### 🎫 TICKET #3: Unificar y Robustecer Sistema de Asignación de Juegos
**Prioridad:** 🟡 MEDIA  
**Tipo:** Refactor / Feature  
**Estimación:** 4-5 horas

#### Problema
Existen dos sistemas paralelos y desincronizados:
1. JSON column `Appointment.games` (legacy)
2. Tabla `AppointmentGame` (nueva, no se usa consistentemente)

Esto causa:
- Juegos que desaparecen tras editar una sesión
- Inconsistencia entre lo mostrado en el modal y lo guardado
- Falta de validación de existencia de archivos

#### Criterios de Aceptación
- [ ] Deprecar completamente el uso de `Appointment.games` (JSON column) para escritura
- [ ] Migrar toda la asignación a usar la tabla `AppointmentGame`
- [ ] Crear método `AppointmentService.set_session_games(session_id, game_filenames_list)` que:
  - Valide que cada juego existe en la tabla `Game`
  - Valide que los archivos físicos existen en `/static/games/`
  - Elimine las asociaciones anteriores y cree las nuevas (transaccional)
- [ ] Actualizar `api_create_session` para usar el nuevo método
- [ ] Actualizar `/api/sessions/assign-games` para usar el nuevo método
- [ ] Actualizar `Appointment.games_list` property para leer siempre de `appointment_games` relationship
- [ ] Crear script de migración de datos para mover `games` JSON → `appointment_game` table
- [ ] Agregar endpoint GET `/api/games/validate` que retorne qué juegos existen (para dropdown dinámico)
- [ ] Actualizar UI del modal de asignación para mostrar thumbnails y descripciones de juegos

#### Archivos a Modificar
- `app/services/appointment_service.py` (nuevo método `set_session_games`)
- `app/routes/api_routes.py` (`api_create_session`, `assign_games_to_session`)
- `app/models.py` (actualizar `games_list` property)
- `app/templates/therapist/sessions.html` (UI de asignación)
- `app/templates/therapist/games.html` (UI de asignación)
- Crear script `migrations/migrate_games_to_table.py`

#### Ejemplo de Implementación
```python
def set_session_games(self, session_id, game_filenames):
    """Set games for a session, replacing existing associations"""
    from app.models import Game, AppointmentGame
    
    appt = Appointment.query.get(session_id)
    if not appt:
        raise ValueError("Sesión no encontrada")
    
    # Validate games exist
    validated_games = []
    for filename in game_filenames:
        game = Game.query.filter_by(filename=filename).first()
        if not game:
            # Check if file exists physically
            game_path = os.path.join(current_app.static_folder, 'games', filename)
            if not os.path.exists(game_path):
                raise ValueError(f"Juego no encontrado: {filename}")
            # Auto-create game entry
            game = Game(
                title=filename.replace('.html', '').replace('_', ' ').title(),
                filename=filename,
                is_active=True
            )
            db.session.add(game)
            db.session.flush()
        validated_games.append(game)
    
    # Remove old associations
    AppointmentGame.query.filter_by(appointment_id=session_id).delete()
    
    # Create new associations
    for game in validated_games:
        assoc = AppointmentGame(appointment_id=session_id, game_id=game.id)
        db.session.add(assoc)
    
    db.session.commit()
    return validated_games
```

---

### 🎫 TICKET #4: Automatizar y Sincronizar Estado de Sesiones
**Prioridad:** 🟡 MEDIA  
**Tipo:** Feature / Optimization  
**Estimación:** 3-4 horas

#### Problema
El estado de las sesiones (`scheduled`, `completed`, `cancelled`) se actualiza de forma reactiva y no proactiva:
- `update_expired_appointments` solo se llama en `get_patient_appointments`
- El dashboard del terapeuta muestra sesiones "scheduled" que ya pasaron
- No hay notificaciones cuando una sesión se auto-completa
- No hay validación de transiciones de estado

#### Criterios de Aceptación
- [ ] Crear job background (usando APScheduler o similar) que ejecute `update_expired_appointments` cada 5 minutos para TODOS los pacientes
- [ ] Crear método `AppointmentService.transition_status(session_id, new_status, notify=True)` que:
  - Valide la transición sea válida (scheduled → completed/cancelled, pero no completed → scheduled)
  - Envíe notificaciones si `notify=True`
  - Registre en logs la transición
- [ ] Implementar endpoint `/api/sessions/<id>/complete` (POST) que marque una sesión como completada manualmente
- [ ] Implementar endpoint `/api/sessions/<id>/cancel` (POST) que cancele una sesión con validación
- [ ] Agregar columna `status_changed_at` a la tabla `Appointment` para auditoría
- [ ] Agregar columna `status_changed_by` (user_id) para saber quién hizo el cambio
- [ ] Crear vista de "Historial de Estado" en el detalle de la sesión (modal)
- [ ] Actualizar cards del dashboard del terapeuta para reflejar estados actuales en tiempo real

#### Archivos a Modificar
- `app/services/appointment_service.py` (nuevo método `transition_status`)
- `app/routes/api_routes.py` (nuevos endpoints `/complete`, `/cancel`)
- `app/models.py` (nuevas columnas `status_changed_at`, `status_changed_by`)
- `run.py` (configurar APScheduler)
- `app/templates/therapist/sessions.html` (botones de acciones manuales)
- Crear migration para nuevas columnas

#### Ejemplo de Background Job
```python
# En run.py
from apscheduler.schedulers.background import BackgroundScheduler
from app.services.appointment_service import AppointmentService

scheduler = BackgroundScheduler()

def auto_update_session_status():
    with app.app_context():
        service = AppointmentService()
        # Update for all patients
        patients = User.query.filter_by(role='jugador').all()
        for patient in patients:
            service.update_expired_appointments(patient.id)

scheduler.add_job(func=auto_update_session_status, trigger="interval", minutes=5)
scheduler.start()
```

---

### 🎫 TICKET #5: Mejorar UX del Calendario y Formularios de Sesiones
**Prioridad:** 🟢 BAJA  
**Tipo:** UX Improvement  
**Estimación:** 3-4 horas

#### Problema
La experiencia de usuario al crear y gestionar sesiones es subóptima:
- El calendario requiere doble-click para ver sesiones del día
- No hay feedback visual durante operaciones async
- Los errores se muestran como `alert()` genéricos
- No hay confirmación para acciones críticas
- El formulario no persiste valores en caso de error
- La timezone del usuario no es visible

#### Criterios de Aceptación
- [ ] Reemplazar todos los `alert()` por toasts/notifications estilo Tailwind
- [ ] Agregar spinners/loaders en botones durante operaciones (ej: "Guardando...")
- [ ] Implementar modal de confirmación para eliminar/cancelar sesiones (con razón opcional)
- [ ] Persistir valores del formulario en `localStorage` y recuperarlos en caso de error
- [ ] Agregar badge en header del usuario mostrando su timezone (ej: "🕐 GMT-5")
- [ ] Auto-cargar sesiones del día actual al abrir el calendario (ya se hizo parcialmente, verificar funcionamiento)
- [ ] Agregar indicador de "sesión activa ahora" en el calendario (borde pulsante verde)
- [ ] Implementar búsqueda/filtrado en tiempo real en la tabla de sesiones
- [ ] Agregar vista de "Conflictos" que muestre sesiones superpuestas (si las hay)
- [ ] Agregar quick-actions: "Reprogramar", "Duplicar", "Cancelar" desde la tabla

#### Archivos a Modificar
- `app/templates/therapist/sessions.html` (mejorar UX completa)
- `app/templates/therapist/calendar.html` (mejorar UX)
- `app/templates/patient/sessions.html` (agregar timezone badge)
- `app/templates/therapist/base.html` (agregar timezone badge en header)
- `app/static/style.css` (nuevos estilos para toasts y badges)
- Crear componente JavaScript reutilizable `toast.js` para notificaciones

#### Ejemplo de Toast Component
```javascript
// app/static/toast.js
function showToast(message, type = 'info', duration = 3000) {
  const colors = {
    success: 'bg-green-500',
    error: 'bg-red-500',
    warning: 'bg-yellow-500',
    info: 'bg-blue-500'
  };
  
  const toast = document.createElement('div');
  toast.className = `fixed bottom-4 right-4 ${colors[type]} text-white px-6 py-3 rounded-lg shadow-lg z-50 animate-slide-up`;
  toast.textContent = message;
  
  document.body.appendChild(toast);
  
  setTimeout(() => {
    toast.classList.add('animate-fade-out');
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

// Reemplazar en sessions.html:
// alert('Sesión creada'); → showToast('Sesión creada exitosamente', 'success');
```

---

## 🎯 Resumen de Prioridades

| Ticket | Prioridad | Impacto | Esfuerzo | Ratio |
|--------|-----------|---------|----------|-------|
| #1 Timezone | 🔴 ALTA | ⭐⭐⭐⭐⭐ | 5h | 1.0 |
| #2 Validaciones | 🔴 ALTA | ⭐⭐⭐⭐⭐ | 3.5h | 1.4 |
| #3 Juegos | 🟡 MEDIA | ⭐⭐⭐⭐ | 4.5h | 0.9 |
| #4 Estado Auto | 🟡 MEDIA | ⭐⭐⭐ | 3.5h | 0.9 |
| #5 UX Mejorar | 🟢 BAJA | ⭐⭐⭐ | 3.5h | 0.9 |

**Total Estimado:** 19-23 horas (~3 días de desarrollo)

---

## 🚀 Orden de Implementación Sugerido

1. **Ticket #2 (Validaciones)** - Previene creación de datos inválidos
2. **Ticket #1 (Timezone)** - Corrige un bug crítico que afecta UX
3. **Ticket #3 (Juegos)** - Estabiliza un feature core
4. **Ticket #4 (Estado Auto)** - Mejora confiabilidad del sistema
5. **Ticket #5 (UX)** - Polish final para mejor experiencia

---

## 📝 Notas Adicionales

### Testing Recomendado
- Cada ticket debe incluir tests unitarios para servicios
- Tests de integración para los endpoints API modificados
- Tests manuales de UX en diferentes timezones
- Tests de carga para el background job (Ticket #4)

### Consideraciones de Migración
- El Ticket #3 requiere migración de datos existentes
- Backups de DB recomendados antes de ejecutar migraciones
- Plan de rollback si algo falla

### Documentación
- Actualizar README con sección de "Manejo de Timezone"
- Documentar nuevos endpoints en formato OpenAPI/Swagger
- Crear guía de usuario para terapeutas sobre validaciones y conflictos




#2 → #1 → #3 → #4 → #5