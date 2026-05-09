# Plan de Migración: Flask → Angular — Módulo Admin

## Estado General

| # | Página (Flask) | Ruta Angular | Prioridad | Estado |
|---|---|---|---|---|
| 1 | Dashboard | `/admin/dashboard` | 🔴 Alta | ✅ Completado |
| 2 | Users (listado) | `/admin/users` | 🔴 Alta | ✅ Completado |
| 3 | User Detail | `/admin/users/:id` | 🔴 Alta | ✅ Completado |
| 4 | Payments | `/admin/payments` | 🔴 Alta | ✅ Completado |
| 5 | Payment History | `/admin/payments/history/:userId` | 🟡 Media | ✅ Completado |
| 6 | Deudores | `/admin/debtors` | 🔴 Alta | ✅ Completado |
| 7 | Sedes | `/admin/sedes` | 🟢 Hecho | ✅ Completado (pre-existente) |
| 8 | **Sessions (calendario)** | `/admin/sessions` | 🔴 Alta | ✅ Completado |
| 9 | **Expenses** | `/admin/expenses` | 🟡 Media | ✅ Completado |
| 10 | **Messages** | `/admin/messages` | 🟡 Media | ✅ Completado |
| 11 | **Reports** | `/admin/reports` | 🟡 Media | ✅ Completado |
| 12 | **Games** | `/admin/games` | 🟢 Baja | ✅ Completado |
| 13 | **CSP Reports** | `/admin/csp-reports` | 🔵 Baja | ✅ Completado |
| 14 | **API Tokens** | `/admin/api-tokens` | 🔵 Baja | ✅ Completado |
| 15 | **Profile** | `/admin/profile` | 🔵 Baja | ✅ Completado |
| 16 | **Yape Import** | `/admin/yape-import` | 🔵 Baja | ✅ Completado |
| 17 | **AI Training** | `/admin/ai` | 🟡 Media | ✅ Completado |

---

## Stack técnico

- **Frontend:** Angular 20, TypeScript 5.8, TailwindCSS 4, FontAwesome
- **Backend:** Flask (Python) — NO TOCAR, solo consumir APIs existentes
- **Arquitectura:** Core / Shared / Features (Domain-Driven Design)
- **CLI:** Usar `ng generate` para componentes y servicios

---

## Archivos Creados

### Modelos (`core/models/`)
- `api-response.ts` — `ApiResponse<T>`, `PaginatedResponse<T>`
- `user.ts` — `User`, `UserRole`, `AccountStatus`, `CreateUserPayload`
- `sede.ts` — `Sede`, `SedeStats`, `SedeAnalytics`
- `payment.ts` — `Payment`, `PatientPaymentStatus`, `DebtReport`, `DebtorItem`
- `appointment.ts` — `Appointment`, `CalendarEvent`, `BatchSessionPayload`
- `dashboard.ts` — `DashboardOverview`, `SmartAction`, `FinancialSummary`
- `expense.ts` — `Expense`, `CreateExpensePayload`

### Servicio (`core/services/`)
- `admin.service.ts` — 30 métodos: CRUD users/sedes/sessions/expenses + payments + debtors + messages + patients + reports

### Páginas del Admin (`features/admin/pages/`)

| Componente | Archivos |
|---|---|
| `dashboard` | dashboard.ts, dashboard.html, dashboard.scss |
| `sedes` | sedes.ts, sedes.html, sedes.scss + sede-card component |
| `edysync-dashboard` | edysync-dashboard.ts, edysync-dashboard.html |
| `users/users-list` | users-list.ts, users-list.html, users-list.scss |
| `users/user-detail` | user-detail.ts, user-detail.html, user-detail.scss |
| `payments` | payments.ts, payments.html, payments.scss |
| `debtors` | debtors.ts, debtors.html, debtors.scss |
| `payment-history` | payment-history.ts, payment-history.html, payment-history.scss |
| `sessions` | sessions.ts, sessions.html, sessions.scss |
| `expenses` | expenses.ts, expenses.html, expenses.scss |
| `messages` | messages.ts, messages.html, messages.scss |
| `reports` | reports.ts, reports.html, reports.scss |

### Routing
- `admin-routing-module.ts` — 13 rutas configuradas
- `admin-module.ts` — imports: CommonModule, FormsModule, FullCalendarModule, SharedModule

---

## APIs del Backend (Flask) — Endpoints Relevantes

### Usuarios
| Endpoint | Método | Uso |
|---|---|---|
| `/api/admin/list-users` | GET | Listar usuarios (filtro por role) |
| `/api/admin/create-user` | POST | Crear usuario |
| `/api/admin/update-user` | POST | Actualizar usuario |
| `/api/admin/delete-user` | POST | Eliminar usuario |
| `/api/admin/reset-password` | POST | Resetear contraseña |
| `/api/admin/assign-therapist` | POST | Asignar terapeuta(s) a paciente |

### Sedes
| Endpoint | Método | Uso |
|---|---|---|
| `/api/admin/sedes` | GET, POST | Listar / Crear sedes |
| `/api/admin/sedes/<id>` | GET, PUT | Obtener / Actualizar sede |
| `/api/admin/sedes/<id>/analytics` | GET | Analytics por sede |

### Pagos
| Endpoint | Método | Uso |
|---|---|---|
| `/api/admin/deudores` | GET | Reporte de deudas por sede |
| `/admin/payments/register` | POST | Registrar pago (form-data) |
| `/admin/payments/history/<id>` | GET | Historial de pagos del paciente |
| `/admin/payments/delete/<id>` | POST | Eliminar pago |
| `/admin/api/payment-info/<id>` | GET | Info de pago del paciente |
| `/admin/payments/<id>/receipt` | GET | Descargar recibo PDF |
| `/admin/analyze-receipt` | POST | OCR de voucher |
| `/api/admin/send-payment-reminder` | POST | Enviar recordatorio |

### Sesiones
| Endpoint | Método | Uso |
|---|---|---|
| `/admin/api/sessions` | GET | Listar sesiones (start, end, therapist_id) |
| `/admin/api/sessions/batch` | POST | Crear sesiones en lote |
| `/admin/api/sessions/<id>` | PUT | Actualizar sesión |
| `/admin/api/sessions/<id>` | DELETE | Eliminar sesión |

### Pacientes
| Endpoint | Método | Uso |
|---|---|---|
| `/api/patients?therapist_id=` | GET | Listar pacientes por terapeuta (para selector dinámico) |

### Smart Actions / Workflow
| Endpoint | Método | Uso |
|---|---|---|
| `/admin/api/workflow/execute/<id>` | POST | Ejecutar acción inteligente |

### Mensajería
| Endpoint | Método | Uso |
|---|---|---|
| `/api/admin/messages/broadcast` | POST | Enviar mensaje broadcast |
| `/api/notifications` | GET | Obtener notificaciones |
| `/api/notifications/mark-read` | POST | Marcar leídas |

### Gastos / Finanzas
| Endpoint | Método | Uso |
|---|---|---|
| `/admin/api/therapist-financials` | GET | Nómina de terapeutas (horas, proyectado, pagado) |
| `/admin/api/expenses` | GET | Listar gastos (filtros: start_date, end_date, category) |
| `/admin/api/expenses/create` | POST | Crear gasto (form-data con receipt) |
| `/admin/api/financial-summary` | GET | Resumen financiero mensual |
| `/admin/generate-ia-report` | POST | Generar reporte semanal IA |
| `/admin/reports/send-weekly-summary` | POST | Enviar reporte por correo |
| `/admin/reports/export-payments` | GET | Exportar pagos CSV |

### Reportes / Stats
| Endpoint | Método | Uso |
|---|---|---|
| `/admin/api/report-therapist-stats` | GET | Estadísticas de terapeutas (sesiones, precisión) |
| `/admin/api/report-patient-stats` | GET | Estadísticas de pacientes (juegos, precisión) |
| `/admin/api/contact-messages` | GET | Mensajes de contacto del sitio web |
| `/api/admin/metrics/capacity` | GET | Métricas de capacidad |

---

## Lo que falta por hacer

### Fase 5 — Sessions Calendar — ✅ COMPLETADO
- **Componente:** `features/admin/pages/sessions/` — sessions.ts, sessions.html, sessions.scss
- **Ruta:** `/admin/sessions`
- **Funcionalidad:**
  - FullCalendar con vistas month/week/day, locale es
  - Crear sesión individual (multi-fecha) o batch (días de semana × semanas)
  - Editar sesión (título, fecha, hora, estado)
  - Eliminar sesión
  - Filtro por terapeuta con recarga dinámica de pacientes
- **APIs:** `GET /admin/api/sessions`, `POST /admin/api/sessions/batch`, `PUT /admin/api/sessions/<id>`, `DELETE /admin/api/sessions/<id>`, `GET /api/patients?therapist_id=`
- **Dependencias nuevas:** `@fullcalendar/angular`, `@fullcalendar/core`, `@fullcalendar/daygrid`, `@fullcalendar/timegrid`, `@fullcalendar/interaction` (v6.1.20)
- **Template Flask:** `app/templates/admin/sessions.html`

### Fase 6 — Expenses, Messages, Reports — ✅ COMPLETADO
- **Expenses** (`/admin/expenses`):
  - Tabla de nómina de terapeutas (contrato, horas, proyectado, pagado, pendiente)
  - Botón "Pagar" por terapeuta con modal pre-rellenado
  - Historial de gastos recientes con categoría, método, comprobante
  - Modal de registro de gasto con upload de comprobante
  - **APIs nuevas (Flask):** `GET /admin/api/therapist-financials`, `GET /admin/api/expenses`, `POST /admin/api/expenses/create`
- **Messages** (`/admin/messages`):
  - Bandeja de mensajes de contacto (tabla con estado, remitente, urgencia, acciones reply/WhatsApp)
  - Sistema de mensajería interna (seleccionar terapeuta/paciente, escribir y enviar)
  - **APIs nuevas (Flask):** `GET /admin/api/contact-messages`
  - **API existente:** `POST /api/admin/messages/broadcast`
- **Reports** (`/admin/reports`):
  - KPIs financieros (ingresos reales, proyección, morosidad, ejecución)
  - Barras comparativas visuales (proyectado vs real vs deuda)
  - Tablas de terapeutas (sesiones, precisión) y pacientes (juegos, precisión)
  - Botones: Análisis Llama AI, Reporte Semanal, Exportar CSV
  - Modal de reporte IA generado
  - **APIs nuevas (Flask):** `GET /admin/api/financial-summary`, `GET /admin/api/report-therapist-stats`, `GET /admin/api/report-patient-stats`
  - **APIs existentes:** `POST /admin/generate-ia-report`, `POST /admin/reports/send-weekly-summary`, `GET /admin/reports/export-payments`

### Fase 7 — Páginas secundarias — ✅ COMPLETADO
- **Games** (`/admin/games`):
  - Grid de juegos HTML con apertura en nueva pestaña
  - Modal de subida (nombre + archivo .html)
  - Confirmación de eliminación
  - APIs: `GET /api/games`, `POST /api/games/upload`, `POST /api/admin/games/delete`
- **CSP Reports** (`/admin/csp-reports`):
  - Tabla paginada de violaciones CSP con filtros (directiva, URI, fecha)
  - Botón de exportación CSV
  - APIs: `GET /admin/api/csp-reports`, `GET /admin/csp-reports/export`
- **API Tokens** (`/admin/api-tokens`):
  - Tabla de tokens con estado activo/inactivo
  - Modal de creación con opción de rotar tokens existentes
  - Copia al portapapeles del token generado
  - **APIs nuevas (Flask):** `GET /admin/api/tokens/list`, `POST /admin/api/tokens/create`, `POST /admin/api/tokens/deactivate/<id>`
- **Profile** (`/admin/profile`):
  - Formulario de edición de nombre de usuario
  - Cambio de contraseña con confirmación
  - API: `POST /api/admin/profile`
- **Yape Import** (`/admin/yape-import`):
  - KPIs: total transacciones, pendientes
  - Tabla de transacciones sin comprobante
  - Historial de importaciones
  - Modal de subida de archivo CSV/XLSX
  - Buscador de transacciones
  - APIs: `POST /admin/yape/import`, `GET /admin/yape/dashboard`, `GET /admin/yape/pending`, `GET /admin/yape/history`, `GET /admin/yape/search`
- **AI Training** (`/admin/ai`):
  - Estado del modelo SVM (entrenado/en progreso)
  - Botón para disparar entrenamiento
  - Información técnica del modelo (algoritmo, clases, características)
  - APIs: `GET /admin/ai/status`, `POST /admin/ai/train`

---

## Cómo continuar

Cuando empieces un nuevo chat, usa este prompt:

```
Hemos estado migrando una app Flask a Angular. El proyecto está en la carpeta edysync/.
Revisa el archivo MIGRATION_PLAN.md y también el skill angular-strict-components-and-architecture.
Continúa con la [FASE X] según el plan. La fase anterior fue [FASE ANTERIOR].
```
