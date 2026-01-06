# 🎫 TICKETS DE IMPLEMENTACIÓN - MÓDULO DE SESIONES
**Fecha de Creación:** 5 de enero de 2026  
**Prioridad:** Alta  
**Sprint:** Enero 2026

---

## 📋 RESUMEN DE PETICIONES DEL STAKEHOLDER

### Peticiones Originales (sin estructura):
1. Módulo de todas las sesiones con ingreso de imágenes de la cámara para comparar con notas
2. Que en el apartado de pacientes se vea la misma información
3. Crear sesiones con programación repetida hasta 3 veces por semana
4. Que se repitan los datos, notas y juegos en sesiones recurrentes
5. Poder editar detalles de la sesión incluyendo el paciente
6. Registrar asistencia al ingresar a los juegos
7. Registrar asistencia tras conclusión de sesión
8. Relacionar una foto a la sesión ya terminada
9. Al hacer click en sesión terminada, ver comparación entre notas y la imagen amplia

---

## 🎯 TICKETS ESTRUCTURADOS PARA IMPLEMENTACIÓN

### 🔵 TICKET #1: Modelo de Datos para Imágenes de Sesión
**Prioridad:** Alta  
**Estimación:** 2 horas  
**Dependencias:** Ninguna

**Descripción:**
Crear modelo de datos para almacenar imágenes de sesiones y relacionarlas con citas (Appointment).

**Tareas:**
- [ ] Crear modelo `SessionImage` en `app/models.py`
- [ ] Agregar campos: `id`, `appointment_id`, `image_path`, `uploaded_at`, `uploaded_by_id`, `image_type` (photo_board, therapy_notes, patient_work)
- [ ] Crear relación con `Appointment` (one-to-many)
- [ ] Crear migración de base de datos
- [ ] Ejecutar migración

**Criterios de Aceptación:**
- El modelo `SessionImage` existe y tiene relación con `Appointment`
- Se puede almacenar múltiples imágenes por sesión
- La migración se ejecuta sin errores

**Código Base:**
```python
class SessionImage(db.Model):
    __tablename__ = 'session_image'
    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointment.id'), nullable=False)
    image_path = db.Column(db.String(500), nullable=False)
    image_type = db.Column(db.String(50), default='session_photo')
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    notes = db.Column(db.Text, nullable=True)
    
    appointment = db.relationship('Appointment', backref=db.backref('session_images', lazy=True))
    uploaded_by = db.relationship('User', backref=db.backref('uploaded_images', lazy=True))
```

---

### 🔵 TICKET #2: Sistema de Carga de Imágenes
**Prioridad:** Alta  
**Estimación:** 3 horas  
**Dependencias:** TICKET #1

**Descripción:**
Implementar endpoint y lógica de backend para cargar imágenes de sesión con validación de archivos.

**Tareas:**
- [ ] Crear directorio `static/uploads/session_images/` con estructura por año/mes
- [ ] Crear endpoint POST `/api/appointments/<id>/upload_image` en `api_routes.py`
- [ ] Validar tipo de archivo (jpg, png, pdf máximo 5MB)
- [ ] Guardar imagen con nombre único (UUID)
- [ ] Crear registro en `SessionImage`
- [ ] Retornar URL de imagen guardada

**Criterios de Aceptación:**
- El endpoint acepta imágenes y las guarda correctamente
- Solo acepta formatos jpg, png, pdf
- Rechaza archivos > 5MB con mensaje de error
- Retorna JSON con URL y metadata de la imagen

**Testing:**
```bash
curl -X POST \
  -F "image=@test.jpg" \
  -F "image_type=session_photo" \
  http://localhost:5000/api/appointments/1/upload_image
```

---

### 🔵 TICKET #3: Vista de Sesión con Comparación de Notas e Imagen
**Prioridad:** Alta  
**Estimación:** 4 horas  
**Dependencias:** TICKET #2

**Descripción:**
Crear interfaz para visualizar sesión completada con comparación lado a lado de notas e imagen ampliable.

**Tareas:**
- [ ] Crear template `templates/therapist/session_review.html`
- [ ] Crear ruta GET `/therapist/appointments/<id>/review` en `therapist_routes.py`
- [ ] Diseño responsive con 2 columnas: notas (izquierda) e imagen (derecha)
- [ ] Implementar zoom de imagen con modal fullscreen
- [ ] Mostrar múltiples imágenes si existen (galería)
- [ ] Agregar botón "Cargar nueva imagen"

**Criterios de Aceptación:**
- La vista muestra notas de sesión y imágenes asociadas
- Las imágenes se pueden ampliar a pantalla completa
- El diseño es responsive (funciona en tablet/móvil)
- Se muestra placeholder si no hay imágenes

**UI/UX:**
```
+----------------------------------+----------------------------------+
|        NOTAS DE SESIÓN           |      IMÁGENES DE SESIÓN          |
|                                  |                                  |
| - Objetivos trabajados           |  [Imagen 1 - Click para ampliar] |
| - Progreso observado             |                                  |
| - Recomendaciones                |  [Imagen 2 - Click para ampliar] |
| - Próximos pasos                 |                                  |
|                                  |  [+ Cargar nueva imagen]         |
+----------------------------------+----------------------------------+
```

---

### 🟢 TICKET #4: Modelo de Sesiones Recurrentes
**Prioridad:** Media  
**Estimación:** 3 horas  
**Dependencias:** Ninguna

**Descripción:**
Agregar campos al modelo Appointment para soportar sesiones recurrentes (repetir hasta 3 veces por semana).

**Tareas:**
- [ ] Agregar campos a `Appointment`: `is_recurring`, `recurrence_pattern`, `recurrence_end_date`, `parent_appointment_id`
- [ ] Crear migración de base de datos
- [ ] Documentar patrones de recurrencia: `weekly_once`, `weekly_twice`, `weekly_three`

**Criterios de Aceptación:**
- El modelo soporta sesiones recurrentes
- Se puede identificar la sesión padre de una serie
- La migración se ejecuta sin errores

**Código Base:**
```python
# Agregar a Appointment model:
is_recurring = db.Column(db.Boolean, default=False)
recurrence_pattern = db.Column(db.String(50), nullable=True)  # weekly_once, weekly_twice, weekly_three
recurrence_end_date = db.Column(db.DateTime, nullable=True)
parent_appointment_id = db.Column(db.Integer, db.ForeignKey('appointment.id'), nullable=True)
```

---

### 🟢 TICKET #5: Servicio de Creación de Sesiones Recurrentes
**Prioridad:** Media  
**Estimación:** 4 horas  
**Dependencias:** TICKET #4

**Descripción:**
Implementar lógica de negocio para crear múltiples sesiones automáticamente basadas en patrón de recurrencia.

**Tareas:**
- [ ] Crear función `create_recurring_appointments()` en `appointment_service.py`
- [ ] Implementar lógica para patrones: 1x, 2x, 3x por semana
- [ ] Copiar datos base (notas, juegos, paciente) de la sesión padre
- [ ] Calcular fechas automáticamente (ej: Lunes/Miércoles/Viernes)
- [ ] Marcar todas las sesiones con el mismo `parent_appointment_id`
- [ ] Crear endpoint POST `/api/appointments/create_recurring`

**Criterios de Aceptación:**
- Se pueden crear series de sesiones (hasta 3 por semana)
- Las fechas se calculan correctamente según el patrón
- Los datos se copian de la sesión padre
- El endpoint retorna lista de sesiones creadas

**Ejemplo de Uso:**
```json
POST /api/appointments/create_recurring
{
  "patient_id": 5,
  "therapist_id": 1,
  "start_date": "2026-01-10",
  "recurrence_pattern": "weekly_three",
  "weeks": 4,
  "time": "14:00",
  "duration_minutes": 60,
  "games": [1, 2, 3],
  "notes": "Sesión de terapia ocupacional"
}

Response: {
  "created_count": 12,
  "appointments": [...]
}
```

---

### 🟢 TICKET #6: Edición de Sesiones con Actualización del Paciente
**Prioridad:** Media  
**Estimación:** 2 horas  
**Dependencias:** Ninguna

**Descripción:**
Permitir editar detalles de una sesión incluyendo cambiar el paciente asignado.

**Tareas:**
- [ ] Crear endpoint PUT `/api/appointments/<id>` en `api_routes.py`
- [ ] Validar que solo el terapeuta asignado pueda editar
- [ ] Permitir modificar: `patient_id`, `title`, `start_time`, `end_time`, `notes`, `games`
- [ ] Agregar log de cambios en campo `updated_at`
- [ ] Actualizar vista de edición en frontend

**Criterios de Aceptación:**
- Se puede cambiar el paciente de una sesión
- Solo el terapeuta dueño puede editar
- Los cambios se guardan correctamente
- Se actualiza timestamp `updated_at`

**Validaciones:**
- El paciente nuevo debe estar asignado al terapeuta
- No se puede editar una sesión `completed` sin permisos especiales
- La fecha de inicio debe ser futura (o permitir con advertencia)

---

### 🟡 TICKET #7: Registro Automático de Asistencia por Ingreso a Juegos
**Prioridad:** Media-Baja  
**Estimación:** 2 horas  
**Dependencias:** Ninguna

**Descripción:**
Marcar sesión como "en progreso" y registrar asistencia automáticamente cuando el paciente ingresa a un juego.

**Tareas:**
- [ ] Agregar campo `attendance_registered` y `attendance_type` a `Appointment`
- [ ] Modificar endpoint `/api/save_game` para detectar primera ejecución
- [ ] Si es el primer juego, marcar `attendance_registered=True`, `attendance_type='auto_game'`
- [ ] Cambiar status a `in_progress` si estaba en `scheduled`
- [ ] Registrar timestamp en nuevo campo `attendance_registered_at`

**Criterios de Aceptación:**
- La asistencia se marca automáticamente al jugar el primer juego
- El status cambia de `scheduled` a `in_progress`
- Se registra el timestamp de asistencia

**Código Base:**
```python
# Agregar a Appointment model:
attendance_registered = db.Column(db.Boolean, default=False)
attendance_registered_at = db.Column(db.DateTime, nullable=True)
attendance_type = db.Column(db.String(50), nullable=True)  # auto_game, manual_therapist
```

---

### 🟡 TICKET #8: Registro Manual de Asistencia Post-Sesión
**Prioridad:** Media-Baja  
**Estimación:** 2 horas  
**Dependencias:** TICKET #7

**Descripción:**
Permitir al terapeuta registrar asistencia manualmente después de que finalice la sesión.

**Tareas:**
- [ ] Crear endpoint POST `/api/appointments/<id>/mark_attendance` en `api_routes.py`
- [ ] Agregar botón "Registrar Asistencia" en vista de sesiones del terapeuta
- [ ] Marcar `attendance_registered=True`, `attendance_type='manual_therapist'`
- [ ] Permitir agregar notas de asistencia (ej: "llegó 10 min tarde")
- [ ] Cambiar status a `completed` opcionalmente

**Criterios de Aceptación:**
- El terapeuta puede marcar asistencia manualmente
- Se puede agregar notas sobre la asistencia
- El sistema diferencia entre asistencia automática y manual

**UI:**
```
[Botón: ✓ Registrar Asistencia]

Modal:
+--------------------------------+
| Registrar Asistencia           |
|                                |
| ☑ Paciente asistió             |
| Notas: [__________________]    |
|                                |
| [Cancelar]  [Confirmar]        |
+--------------------------------+
```

---

### 🟡 TICKET #9: Vista Unificada de Pacientes con Sesiones
**Prioridad:** Baja  
**Estimación:** 3 horas  
**Dependencias:** Todos los anteriores

**Descripción:**
Crear vista en el panel del paciente donde vea la misma información de sesiones que ve el terapeuta (adaptada a su contexto).

**Tareas:**
- [ ] Crear ruta `/patient/my_sessions` en `patient_routes.py`
- [ ] Crear template `templates/patient/my_sessions.html`
- [ ] Mostrar lista de sesiones pasadas y futuras
- [ ] Incluir: fecha, juegos asignados, notas del terapeuta, imágenes
- [ ] Agregar filtros: próximas, completadas, canceladas
- [ ] Diseño similar al panel del terapeuta pero con permisos de solo lectura

**Criterios de Aceptación:**
- El paciente ve todas sus sesiones (pasadas y futuras)
- Puede ver imágenes y notas de sesiones completadas
- No puede editar ni eliminar sesiones
- El diseño es intuitivo y responsive

---

## 📊 RESUMEN DE IMPLEMENTACIÓN

### Por Prioridad:
- **Alta (🔵):** 3 tickets - 9 horas estimadas
- **Media (🟢):** 3 tickets - 9 horas estimadas  
- **Media-Baja (🟡):** 3 tickets - 7 horas estimadas

**Total Estimado:** ~25 horas de desarrollo

### Orden Recomendado para Hoy:
1. TICKET #1 - Modelo de Imágenes (2h)
2. TICKET #2 - Sistema de Carga (3h)  
3. TICKET #3 - Vista de Comparación (4h)
4. ☕ **Break**
5. TICKET #4 - Modelo Recurrente (3h)

---

## 🚀 PRÓXIMOS PASOS

### Para empezar hoy:
```bash
# 1. Activar entorno
cd /Users/apple/Documents/moscowle_ia_mvp
source venv/bin/activate

# 2. Crear rama de desarrollo
git checkout -b feature/session-images-module

# 3. Empezar con TICKET #1
```

### Notas Importantes:
- Cada ticket debe tener commit separado
- Probar cada funcionalidad antes de continuar
- Documentar cambios en el código
- Crear tests unitarios si es posible

---

**Documento creado por:** GitHub Copilot  
**Última actualización:** 5 de enero de 2026