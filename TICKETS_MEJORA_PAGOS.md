# Tickets de Mejora: Módulo de Gestión de Pagos

Estos tickets detallan las mejoras recomendadas para escalar el sistema de pagos actual, aumentar la seguridad y mejorar la experiencia del usuario (Stakeholders, Terapeutas y Admin).

## Ticket 1: Automatización de Recordatorios de Vencimiento
**Prioridad:** Alta | **Impacto:** Reducción de morosidad
**Descripción:** Actualmente, el sistema desactiva usuarios silenciosamente cuando vence el pago. Se necesita un sistema de notificaciones preventivas.
**Tareas:**
- [x] Implementar tarea programada (Cron/APScheduler) que corra diariamente.
- [x] Enviar correo electrónico al paciente 3 días antes de su fecha de vencimiento.
- [x] Enviar correo electrónico el día del vencimiento.
- [x] Enviar notificación interna en el dashboard del paciente advirtiendo del bloqueo inminente.

## Ticket 2: Historial de Transacciones Detallado para Pacientes - ✅ COMPLETADO
**Prioridad:** Media | **Impacto:** Transparencia y Autogestión
**Descripción:** Los pacientes actualmente pueden ser bloqueados pero no tienen visibilidad de su historial de pagos o de su próxima fecha de corte en su propio dashboard.
**Tareas:**
- [x] Crear vista "Mis Pagos" en el portal del Paciente (`/patient/payments`).
- [x] Mostrar tabla histórica con fechas, montos y métodos de pago registrados por manualemente por el admin.
- [x] Mostrar widget destacado con "Próximo Vencimiento" y "Estado de Cuenta" en el Dashboard principal.

## Ticket 3: Soporte para Comprobantes de Pago (Upload de Archivos) - ✅ COMPLETADO
**Prioridad:** Media | **Impacto:** Auditoría y Control
**Descripción:** El registro de pagos actual solo pide una referencia de texto. Es necesario adjuntar la evidencia (foto del voucher, captura de Yape/Plin).
**Tareas:**
- [x] Modificar modelo `Payment` para incluir campo `receipt_image_path`.
- [x] Actualizar formulario de registro de pago en Admin para permitir subida de imágenes.
- [x] Implementar visualizador de comprobantes (pop-up) en el historial de pagos del Admin.

## Ticket 4: Lógica de Prorrateo y Cálculos Automáticos de Fechas - ✅ COMPLETADO
**Prioridad:** Alta | **Impacto:** Precisión Contable
**Descripción:** Actualmente la fecha de "Nuevo Vencimiento" se selecciona manualmente. El sistema debería calcularla automáticamente basándose en el plan (Quincenal/Mensual).
**Tareas:**
- [x] Implementar lógica en backend que, al registrar un pago, sugiera automáticamente la fecha: `fecha_actual + 1 mes` o `fecha_actual + 15 días`.
- [x] Implementar manejo de "Feriados" y "Ausencias" (se detectan sesiones ausentes desde último pago y se alerta al Admin).
- [x] Agregar campo de "Descuento/Ajuste" en el formulario de pago para casos excepcionales.

## Ticket 5: Reporte Financiero Exportable para Stakeholders - ✅ COMPLETADO
**Prioridad:** Baja (pero estratégica) | **Impacto:** Toma de Decisiones
**Descripción:** Los administradores necesitan ver el flujo de caja global, no solo paciente por paciente.
**Tareas:**
- [x] Crear vista de reporte "Ingresos Mensuales".
- [x] Generar gráfico de barras: Ingresos Esperados vs. Ingresos Reales vs. Morosidad.
- [x] Botón para exportar listado de pagos del mes a Excel/CSV para contabilidad externa.
