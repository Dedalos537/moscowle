# Archivos Legacy - Backup

**Fecha:** 9 de diciembre de 2025  
**Razón:** Limpieza de estructura del proyecto

## Archivos Movidos a Esta Carpeta

Estos archivos fueron reemplazados por versiones mejoradas en la carpeta `patient/`:

### 1. `dashboard.html` → `patient/dashboard.html`
- **Motivo:** Archivo duplicado. La nueva versión usa template inheritance con `patient/base.html`
- **Estado:** REEMPLAZADO ✅

### 2. `calendar_patient.html` → `patient/calendar.html`
- **Motivo:** Archivo duplicado. La nueva versión tiene JavaScript conectado a la API real
- **Estado:** REEMPLAZADO ✅

### 3. `my_therapist.html` → `patient/my_therapist.html`
- **Motivo:** Archivo duplicado. La nueva versión usa template inheritance
- **Estado:** REEMPLAZADO ✅

### 4. `progress.html` → `patient/progress.html`
- **Motivo:** Archivo duplicado. La nueva versión usa template inheritance
- **Estado:** REEMPLAZADO ✅

### 5. `games.html`
- **Motivo:** Archivo no utilizado (typo "exetends" en línea 1). Reemplazado por `game.html`
- **Estado:** NO USADO ❌

### 6. `base.html` (raíz de templates)
- **Motivo:** No utilizado. Se usan `patient/base.html` y `therapist/base.html` en su lugar
- **Estado:** NO USADO ❌

## Estructura Nueva (Organizada)

```
templates/
├── patient/                    # Todo lo relacionado con pacientes
│   ├── base.html              # Template base con header + sidebar + notificaciones
│   ├── dashboard.html         # Panel principal del paciente
│   ├── calendar.html          # Calendario con citas reales (API conectada)
│   ├── progress.html          # Gráficos y logros
│   └── my_therapist.html      # Información del terapeuta
│
├── therapist/                  # Todo lo relacionado con terapeutas
│   ├── base.html              # Template base con sidebar + notificaciones
│   ├── dashboard.html         # Panel principal del terapeuta
│   ├── calendar.html          # Calendario con creación de citas (API conectada)
│   ├── patients.html          # Gestión de pacientes
│   ├── sessions.html          # Vista de sesiones
│   ├── analytics.html         # Análisis con IA
│   ├── games.html             # Juegos disponibles
│   └── reports.html           # Reportes y estadísticas
│
├── game.html                   # Juego de reflejos (standalone)
├── login.html                  # Página de login
└── _legacy_backup/            # Archivos antiguos (este folder)
```

## Mejoras Implementadas

1. **Template Inheritance:** Eliminación de código duplicado
2. **Notificaciones:** Sistema de campana funcional en header
3. **Calendarios Conectados:** JavaScript que consume APIs reales
4. **Separación Clara:** patient/ vs therapist/ folders

## ¿Puedo Eliminar Esta Carpeta?

**NO recomendado por ahora.** Mantén este backup por 1-2 semanas mientras verificas que todo funcione correctamente. Después puedes eliminarla de forma segura.

## Verificación

Para confirmar que todo funciona:
1. Login como paciente → Verifica dashboard, calendario, progreso, notificaciones
2. Login como terapeuta → Verifica dashboard, calendario, crear citas, notificaciones
3. Si todo funciona bien por 2 semanas → Elimina esta carpeta
