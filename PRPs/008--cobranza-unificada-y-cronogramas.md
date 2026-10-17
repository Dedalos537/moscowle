# PRP: Cobranza unificada y cronogramas (pacientes y terapeutas)

> **Version:** 1.0
> **Created:** 2026-10-16
> **Status:** Para aprobar

---

## Goal

Que **todo pago entre por una sola puerta** y quede **conectado** con el cronograma, la cobranza, la deuda y los gráficos:

1. **Un pago de paciente siempre se aplica a su cronograma de cuotas**, en orden, sea cual sea la pantalla desde donde se registre (Pagos, Finanzas, «Registrar pago» del dashboard, importación Yape, asistente IA).
2. **Pacientes sin contrato**: «Registrar pago» no los deja en un limbo. Ofrece **crear el plan en el mismo panel** (monto, día de pago, duración) o registrar un **pago suelto clasificado** (evaluación, material u otro), que cuenta como ingreso pero no como cobranza de cuotas.
3. **Cronograma de terapeutas**: cada mes se liquida lo que corresponde a cada terapeuta y se registra lo pagado **contra ese periodo**, con estados (pendiente, parcial, pagado, vencido). El botón **«Pagar a terapeuta»** vuelve a estar a mano: en el dashboard y en la ficha del terapeuta.
4. **Cronogramas «escondidos y a la vista»**: en el dashboard, una sección plegable **«Cronograma»** con dos pestañas:
   - **«Lo que entra»**: cuotas de pacientes por vencer y vencidas.
   - **«Lo que sale»**: pagos a terapeutas.

   Con totales por semana y la acción directa en cada fila (Cobrar / Pagar). Lo mismo en la ficha de cada paciente y de cada terapeuta.
5. **Una sola definición de deuda y cobranza** para Dashboard, Sedes, Finanzas, Pagos y Reportes.

## Why: hallazgos de la auditoría (verificados en código)

### 1. El pago rápido no toca las cuotas (desconectado)

- `quick-payment.ts:257` llama a `POST /admin/payments/register` (`app/routes/admin/payments.py:302`), que llama a `payment_service.register_payment` (`app/services/payment_service.py:107-150`).
- Ese método **solo crea un `Payment`**: no lo vincula a ninguna `Installment` (`installment_id` queda vacío) ni suma `paid_amount` a la cuota.
- **Efecto en el dashboard** después de cobrarle a un paciente con contrato:

  | Indicador | Fuente | Qué pasa |
  |---|---|---|
  | Ingresos cobrados | `Payment` | Sube ✔ |
  | Cobranza | `Installment.paid_amount` | **No cambia** ✘ |
  | Deuda vencida | Cuotas | **No baja** ✘ |
  | Continuidad del servicio | Riesgo «Deuda vencida» | El paciente **sigue apareciendo** ✘ |
  | Cobros que vencen hoy | Cuotas del día | La cuota del día **sigue pendiente** ✘ |

- El camino correcto ya existe: `contract_service.pay_installment` (`contract_service.py:443-500`) crea el pago, lo enlaza (`installment_id` / `payment_id`), actualiza saldo y estado. Solo lo usa Finanzas → «Pagar cuota» (`contracts.py:237`) y el asistente IA (`tools_registry.py:3254`).

### 2. Conviven dos sistemas de cobro

| | **A. Contrato + cuotas** | **B. Plan «heredado» en el usuario** |
|---|---|---|
| Datos | `Contract` / `Installment` | `User.payment_amount`, `payment_plan`, `payment_due_date`, `payment_day` |
| Cronograma | Real, cuota por cuota | Una sola «próxima fecha» que se mueve a mano |
| Lo usan | Finanzas, scorecard de Sedes, dashboard nuevo (`contract_debt`) | Pago rápido (`next_due_date`), reporte de deudores, `get_financial_summary` |

- `get_financial_summary` (`payment_service.py:272-330`) **mezcla A y B**: la deuda de quien no tiene contrato sale de su `payment_amount` (una cuota entera por estar vencido, no lo realmente adeudado).
- El scorecard y el dashboard **solo ven A**. Resultado: **Finanzas y el Dashboard pueden mostrar deudas distintas** para el mismo mes.
- `register_payment` además **reinicia `sessions_total` / `sessions_attended`** del paciente en cada pago (`payment_service.py:131-134`). Es un efecto lateral oculto que distorsiona «Plan por terminar».

### 3. Errores que el usuario no ve

- Si la validación falla, `/admin/payments/register` responde **una redirección HTML** (`payments.py:333-336`) aunque lo llame Angular: el panel solo muestra un error genérico.
- `pay_installment` con un monto mayor al saldo marca la cuota pagada pero **el excedente no pasa a la siguiente cuota**.
- El asistente IA registra pagos buscando al paciente con `ilike('%nombre%')` y toma el primero (`reports.py:230-240`): **puede cobrarle al paciente equivocado**.

### 4. Terapeutas: liquidación sin cronograma

- Lo que se le debe a cada terapeuta se calcula al vuelo (`finance_service.get_therapist_financials`, `finance_service.py:40-110`):
  - tarifa = `salary_base / contract_hours`;
  - horas = sesiones **completadas** del mes × `duration_minutes`.
- **Lo pagado se cuenta por la fecha del pago**: si la liquidación de abril se paga el 5 de mayo, abril sigue «debiendo» y mayo aparece «sobrepagado». No hay periodo, vencimiento ni estado.
- **Hay dos implementaciones** del mismo cálculo (`finance_service.py:40` y `financial_service.py:270`).
- `duration_minutes` vacío cuenta como **0 horas** (sesión trabajada que no se paga).
- El botón **«Pagar»** a terapeuta existe solo en Finanzas → Gastos (`finanzas.html:1256`, `openTherapistPaymentModal`). No está en el dashboard ni en el historial (el dashboard anterior tampoco lo tenía; el que existía era «Registrar pago rápido» de pacientes).

## What

### Backend: un «libro de cobranza» único (`app/services/billing.py`)

| Función | Qué hace |
|---|---|
| `apply_patient_payment(patient, amount, method, date, reference, receipt, notes, source)` | Reparte el pago en las **cuotas abiertas más antiguas primero** (FIFO). Crea un `Payment` y una fila por cada cuota tocada (`payment_allocation`). Si sobra, deja **saldo a favor** que se aplica sola a la próxima cuota. Todo en una transacción. |
| `create_plan(patient, monthly_amount, payment_day, months \| None, start)` | Crea el contrato con su cronograma. `months=None` es un plan **renovable**: un job mensual genera la cuota siguiente. |
| `register_one_off(patient, amount, category, ...)` | **Pago suelto** clasificado (evaluación, material, otro). Cuenta como ingreso, **no** como cobranza de cuotas. |
| `schedule(patient)` | Cronograma del paciente: cuotas con monto, pagado, saldo, estado y pagos aplicados. |
| `incoming(range, sede)` | Lo que entra: cuotas por vencer y vencidas, agrupadas por semana. |
| `revert_payment(payment)` | Deshace un pago. Ya existe en `contract_service.revert_payment`; se movería aquí. |

- **Todas las puertas usan `apply_patient_payment`:**
  - `/admin/payments/register` (pagos y pago rápido);
  - `pay_installment` (Finanzas: «pagar esta cuota» aplica a esa cuota y el resto sigue FIFO);
  - importación Yape;
  - asistente IA, que **exige el id del paciente** y confirma su nombre antes de cobrar.
- **Migración de planes heredados** (con **simulación primero**): cada paciente con `payment_amount > 0` y sin contrato recibe un **contrato renovable** cuya primera cuota vence en su `payment_due_date`. Lo ya pagado no se toca. Después de migrar, `get_financial_summary` y el reporte de deudores leen **solo** del libro.
- `register_payment` deja de reiniciar las sesiones. Las sesiones del plan salen del contrato.
- **Errores JSON** (400 con mensaje por campo) cuando la petición es de la API.

### Backend: nómina de terapeutas con periodos

- **Modelo nuevo `PayrollPeriod`**:
  - campos: terapeuta, periodo (AAAA-MM), horas, tarifa, monto a pagar (congelado al cerrar), pagado, saldo, vence (día configurable, por defecto **5 del mes siguiente**), estado;
  - mientras el mes esté abierto, el monto se recalcula;
  - un job lo **cierra** el día 1.
- **Pago a terapeuta**: se registra como `Expense(category='therapist_payment')` **con `payroll_period_id`**, así se aplica al periodo correcto aunque se pague después.
- Un solo cálculo (se elimina el duplicado). Las sesiones sin `duration_minutes` usan la duración estándar de la sesión (configurable) en vez de 0, y se marcan para revisión.
- `outgoing(range)`: lo que sale (periodos por pagar y vencidos).

### Frontend

1. **«Registrar pago» (dashboard) rediseñado en tres pasos dentro del panel lateral**:
   1. Elegir paciente.
   2. Ver su **cronograma resumido**: próximas cuotas, deuda, saldo a favor.
   3. Monto (sugerido: lo vencido + la cuota del día), método, comprobante (OCR actual), referencia.

   Antes de confirmar se ve a qué cuotas se aplicará. **Sin contrato**: dos caminos claros, «Crear plan de pago» (formulario corto en el mismo panel) o «Pago suelto» (con categoría). El formulario modal antiguo se retira.
2. **Sección «Cronograma» en el dashboard** (plegada por defecto, recuerda si la abriste), con dos pestañas:
   - **Lo que entra**: semanas con total esperado vs. cobrado; filas de cuotas vencidas y por vencer con «Cobrar» (abre el panel con ese paciente y esa cuota).
   - **Lo que sale**: terapeutas con periodo, monto, pagado y vencimiento, con «Pagar» (panel lateral con el monto sugerido = saldo del periodo).
   - **Arriba**, una línea simple de **flujo de caja proyectado** a 4 semanas (entra vs. sale).
3. **«Pagar a terapeuta»**:
   - en el panel **Equipo** del dashboard (al abrir un terapeuta: «Liquidación de octubre: S/ 1,240 · pagado S/ 600 · Pagar saldo»);
   - en la ficha del terapeuta;
   - el de Finanzas → Gastos se mantiene, usando el mismo panel.
4. **Ficha del paciente**: pestaña «Pagos» con el cronograma completo (cuotas y pagos aplicados), saldo a favor y «Registrar pago».
5. **(Opcional)** El terapeuta ve **sus propios pagos recibidos** y el periodo en curso en su panel.

### Gráficos y KPIs conectados

- Ingresos, Cobranza, Deuda vencida, Cobros de hoy y «Deuda» en Continuidad salen todos del **mismo libro**. Tras registrar un pago, el dashboard se refresca y **todos** se mueven juntos.
- **Nuevos indicadores** en Crecimiento:
  - **«Saldo de nómina»** (lo que se debe a terapeutas);
  - **«Margen del periodo»** (cobrado − nómina − gastos).

### Success Criteria

- [ ] Cobrar S/ 300 a un paciente con dos cuotas vencidas de S/ 150 desde **cualquier** pantalla deja ambas cuotas pagadas, y además:
  - la deuda vencida baja S/ 300;
  - la cobranza sube;
  - el paciente sale de «Continuidad» por deuda.

  Test con el endpoint real.
- [ ] Un pago mayor a la deuda deja **saldo a favor** y la próxima cuota nace cubierta.
- [ ] Un paciente sin contrato no puede quedar con un pago «suelto» sin clasificar: o se crea el plan, o se elige categoría.
- [ ] Dashboard, Sedes, Finanzas y Pagos muestran **la misma deuda** para el mismo mes y sede (test que compara las 3 fuentes).
- [ ] Pagar en mayo la liquidación de abril deja abril «pagado» y mayo sin sobrepago.
- [ ] «Pagar a terapeuta» funciona desde el dashboard, la ficha y Finanzas con el mismo resultado.
- [ ] Simulación de la migración: informe de cuántos planes heredados se convierten, con monto y primera fecha, **antes** de aplicar; se aplica solo con aprobación.
- [ ] `pytest` no baja del baseline; `ruff` limpio en lo tocado; `ng build` OK; axe sin violaciones en las pantallas nuevas.

## Decisiones para aprobar

1. **Migrar los planes heredados a contratos renovables.** *Recomendado:* sí, con simulación previa. *Alternativa:* mantener los dos sistemas y que el libro los «traduzca», con más casos borde y riesgo de cifras distintas.
2. **Saldo a favor.** Si alguien paga de más: *recomendado*, se guarda como saldo y cubre la próxima cuota. *Alternativa:* rechazar el pago y pedir el monto exacto.
3. **Vencimiento de la nómina.** ¿Qué día se paga a los terapeutas? *Por defecto:* el 5 del mes siguiente, configurable.
4. **Sesiones sin duración registrada.** *Recomendado:* usar la duración estándar (¿45 o 60 min?) y marcarlas para revisión, en lugar de pagar 0.
5. **Vista del terapeuta** con sus pagos recibidos. ¿Se incluye en esta fase o después?
6. **Asistente IA**: dejarlo cobrar solo con paciente confirmado (*recomendado*) o quitarle la acción de cobrar.

## Plan de trabajo (por fases, cada una desplegable sola)

| Fase | Entrega | Riesgo |
|---|---|---|
| **1. Libro único** | `billing.apply_patient_payment` (FIFO + saldo a favor + `payment_allocation`); `/payments/register` y `pay_installment` pasan por él; errores JSON; se quita el reinicio de sesiones; tests. | Medio: toca dinero, va con tests de cada caso. |
| **2. Sin contrato** | `create_plan` / `register_one_off`; nuevo panel «Registrar pago» en 3 pasos con vista previa de aplicación. | Bajo. |
| **3. Migración heredados** | Comando de simulación + aplicación (con respaldo de la BD antes); `financial_summary` y deudores leen del libro. | Alto: se ejecuta solo tras revisar la simulación contigo. |
| **4. Nómina** | `PayrollPeriod`, job de cierre, pago contra periodo, cálculo único; «Pagar a terapeuta» en dashboard, ficha y Finanzas. | Medio. |
| **5. Cronogramas a la vista** | Sección plegable «Cronograma» (entra/sale + flujo proyectado), pestaña Pagos en la ficha del paciente, KPIs «Saldo de nómina» y «Margen». | Bajo. |
| **6. Asistente IA y Yape** | Usan el libro; IA con paciente confirmado. | Bajo. |

## Validation Loop

```bash
venv/bin/ruff check app/ tests/
venv/bin/python -m pytest tests/test_billing.py tests/test_payroll.py tests/test_center_dashboard.py -q   # nuevos
venv/bin/python -m pytest tests/ -q        # no bajar del baseline (CI)
cd edysync && npx ng build                  # CI
```

Además:
- **Antes de cada despliegue**, verificación visual con datos de ejemplo (escritorio, tablet y móvil, claro y oscuro) y axe, como en el dashboard.
- **En producción**, la fase 3 se ejecuta primero en modo simulación y se revisa el informe juntos.

## Anti-Patterns a evitar

- Crear `Payment` sin pasar por el libro (prohibido después de la fase 1).
- Calcular deuda en el frontend o con fórmulas distintas por pantalla.
- Aplicar la migración sin simulación ni respaldo.
- Contar pagos a terapeutas por fecha de pago en lugar de por periodo.
