# Plan de Mejora Integral y Holístico - Moscowle IA MVP

Este documento detalla un análisis profundo de la arquitectura actual y propone mejoras estructurales para garantizar la escalabilidad, robustez y mantenibilidad del proyecto.

## 1. Análisis de Modelos de Datos (`app/models.py`)

### Estado Actual
- **Appointment**: Almacena `games` como un campo de texto/JSON. Esto dificulta las consultas SQL directas (ej. "¿Cuántas veces se ha jugado el juego X?").
- **SessionMetrics**: Relaciona métricas con `user_id` y `session_id`.
- **Relaciones**: La relación entre `Appointment` y los resultados de los juegos es débil. Si un paciente juega 3 juegos en una sesión, `SessionMetrics` crea 3 registros, pero no hay una validación estricta de que esos juegos correspondan a los asignados en `Appointment`.

### Mejoras Propuestas
1.  **Normalización de Juegos**: Crear una tabla `Game` (id, name, file_path, config) y una tabla intermedia `AppointmentGame` o `SessionAssignment`.
    *   *Beneficio*: Permite gestionar el catálogo de juegos dinámicamente sin depender de nombres de archivos en strings.
    *   *Beneficio*: Permite asignar configuraciones específicas por juego (ej. dificultad, tiempo límite) en la tabla intermedia.
2.  **Integridad Referencial**: Asegurar que `SessionMetrics` siempre tenga un `appointment_id` válido si se jugó dentro de una sesión.

## 2. Integración Frontend-Backend (Juegos)

### Estado Actual
- **Carga de Juegos**: Los juegos son archivos HTML estáticos en `static/games/` cargados en un iframe.
- **Comunicación**: `game.js` envía resultados a `/api/save_game` mediante `fetch`.
- **Seguridad**: El frontend envía `accuracy` y `avg_time`. Un usuario malintencionado podría manipular estos datos fácilmente.

### Mejoras Propuestas
1.  **Validación de Sesión**: El endpoint `/api/save_game` debe validar que la sesión (`session_id`) esté activa y pertenezca al usuario actual antes de aceptar datos.
2.  **Token de Sesión de Juego**: Generar un token único temporal cuando se abre el juego, y requerirlo al guardar los datos para evitar envíos fuera de contexto.
3.  **Estandarización de API de Juegos**: Definir una interfaz estricta (TypeScript o JSON Schema) para la comunicación entre el iframe del juego y la ventana padre (`postMessage`) en lugar de que el juego llame directamente a la API. Esto desacopla el juego de la lógica de backend.

## 3. Ciclo de Vida de la Sesión

### Estado Actual
- **Estados**: `scheduled`, `completed`.
- **Lógica**: Una sesión se marca como `completed` automáticamente cuando se guarda *cualquier* juego (`save_game`).
- **Problema**: Si una sesión tiene 3 juegos asignados, jugar el primero cierra la sesión prematuramente.

### Mejoras Propuestas
1.  **Estado Granular**: Introducir estado `in_progress`.
2.  **Lógica de Completitud**: La sesión solo debe marcarse como `completed` cuando se hayan jugado *todos* los juegos asignados, o cuando el tiempo haya expirado, o manualmente por el terapeuta.
3.  **Tracking de Progreso**: Almacenar el estado de cada juego dentro de la sesión (ej. Juego 1: Completado, Juego 2: Pendiente).

## 4. Reportes y Zonas Horarias

### Estado Actual
- **Fechas**: Uso de `datetime.utcnow()` en backend.
- **Consultas**: Filtros como `Appointment.start_time >= today_start` asumen que el servidor y el usuario están alineados o que UTC es suficiente.
- **Riesgo**: Un paciente en UTC-5 podría no ver sus sesiones de "hoy" si el servidor ya pasó a "mañana" en UTC.

### Mejoras Propuestas
1.  **Manejo de Zonas Horarias**: Almacenar todo en UTC pero requerir la zona horaria del usuario en el perfil (`User.timezone`). Convertir a hora local *antes* de renderizar en Jinja o enviar JSON.
2.  **Consultas Robustas**: Ajustar las consultas de "hoy" para usar el rango de tiempo local del usuario convertido a UTC.

## 5. Arquitectura de Software

### Estado Actual
- **Estructura**: MVC con Servicios (`app/services`).
- **Acoplamiento**: `main.py` contiene mucha lógica de enrutamiento mezclada con llamadas a servicios.
- **Manejo de Errores**: Bloques `try-except` genéricos que a veces ocultan errores críticos (ej. `pass` en notificaciones fallidas).

### Mejoras Propuestas
1.  **Blueprints por Dominio**: Separar `main.py` en `patient_routes.py`, `therapist_routes.py`, `api_routes.py`.
2.  **Logging Estructurado**: Reemplazar `print` y `pass` con un logger configurado adecuadamente para trazar errores en producción.
3.  **Inyección de Dependencias**: Formalizar la instanciación de servicios para facilitar testing unitario.

## Plan de Acción Inmediato (Siguientes Pasos)

1.  **Refactorizar `save_game`**: Evitar que la sesión se cierre al primer juego. --- ##ya está
2.  **Centralizar Zonas Horarias**: Crear un helper `get_user_now(user)` para unificar la lógica de tiempo. 
3.  **Separar Rutas**: Dividir `main.py` para mejorar la legibilidad.
