import type { ChartData } from 'chart.js';
import { PatientRow, PaymentHistoryRow, MonthCell } from './finanzas.models';
import { chartColors } from './finanzas-charts-config';

export function getCategoryLabel(key: string): string {
  const map: Record<string, string> = {
    therapist_payment: 'Pago Terapeutas',
    operational: 'Gastos Operativos',
    bonus: 'Bonificaciones',
    other: 'Otros',
  };
  return map[key] || key;
}

export function getMethodBadgeClass(method: string): string {
  const map: Record<string, string> = {
    yape: 'bg-accent-container text-accent',
    plin: 'bg-accent-container text-accent',
    transfer: 'bg-info-container text-info',
    cash: 'bg-success-container text-success',
    card: 'bg-info-container text-info',
  };
  return map[method] || 'bg-surface-container-high text-on-surface-variant';
}

export function getMethodLabel(method: string): string {
  const map: Record<string, string> = {
    yape: 'Yape', plin: 'Plin', transfer: 'Transferencia', cash: 'Efectivo', card: 'Tarjeta',
  };
  return map[method] || method;
}

export function formatMonthLabel(key: string): string {
  const [y, m] = key.split('-');
  return new Date(+y, +m - 1, 1).toLocaleDateString('es-PE', { month: 'short', year: '2-digit' });
}

export function getLast6MonthsKeys(): string[] {
  const keys: string[] = [];
  const now = new Date();
  for (let i = 5; i >= 0; i--) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
    keys.push(`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`);
  }
  return keys;
}

export function getMonthsFromKey(key: string, offset: number): string {
  const [y, m] = key.split('-').map(Number);
  const d = new Date(y, m - 1 + offset, 1);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
}

export function getAnchorMonthsKeys(anchor: string): string[] {
  const keys: string[] = [];
  for (let i = 5; i >= 0; i--) keys.push(getMonthsFromKey(anchor, -i));
  return keys;
}

/**
 * Fecha LOCAL en formato AAAA-MM-DD. `toISOString()` devuelve la fecha en UTC: en Lima (UTC-5), a partir
 * de las 19:00 ya es "mañana" y los gastos/cancelaciones se registraban con un día de adelanto.
 */
export function localDateString(date: Date = new Date()): string {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

/** Interpreta 'AAAA-MM-DD' como fecha local. `new Date('2026-10-05')` la toma como UTC y en Lima cae el día anterior. */
export function parseLocalDate(value: string): Date {
  const [y, m, d] = value.substring(0, 10).split('-').map(Number);
  return new Date(y, (m || 1) - 1, d || 1);
}

/** Un pago cuenta como ingreso solo si está cobrado (igual que el resumen del backend): completed, paid o sin estado. */
export function isCollectedPayment(payment: { status?: string | null }): boolean {
  return !payment.status || payment.status === 'completed' || payment.status === 'paid';
}

export function getYearMonthKeys(year: number): string[] {
  return Array.from({ length: 12 }, (_, i) => `${year}-${String(i + 1).padStart(2, '0')}`);
}

/** Días ('AAAA-MM-DD') de un mes; con `fortnight` solo la 1ra (1-15) o la 2da (16-fin). */
export function getMonthDayKeys(month: string, fortnight: 1 | 2 | null = null): string[] {
  const [y, m] = month.split('-').map(Number);
  const last = new Date(y, m, 0).getDate();
  const from = fortnight === 2 ? 16 : 1;
  const to = fortnight === 1 ? Math.min(15, last) : last;
  const keys: string[] = [];
  for (let d = from; d <= to; d++) keys.push(`${month}-${String(d).padStart(2, '0')}`);
  return keys;
}

/**
 * Meses a mostrar en una serie temporal. Una línea con UN solo punto no dibuja nada, así que si el período
 * abarca menos de `minMonths` se completa con meses anteriores hasta `minMonths` (terminando en el fin del período).
 */
export function getContextMonthKeys(start: string, end: string | null | undefined, minMonths = 6): string[] {
  const keys = getRangeMonthKeys(start, end);
  if (keys.length >= minMonths) return keys;
  return getAnchorMonthsKeys(keys[keys.length - 1]).slice(-minMonths);
}

export function getRangeMonthKeys(start: string, end?: string | null): string[] {
  if (!start) return [];
  const last = end && end > start ? end : start;
  const [sy, sm] = start.split('-').map(Number);
  const [ey, em] = last.split('-').map(Number);
  const keys: string[] = [];
  let y = sy;
  let m = sm;
  while (y < ey || (y === ey && m <= em)) {
    keys.push(`${y}-${String(m).padStart(2, '0')}`);
    m += 1;
    if (m > 12) { m = 1; y += 1; }
    if (keys.length > 120) break;
  }
  return keys;
}

export function isDateInRange(date: string | null | undefined, start: string, end?: string | null): boolean {
  if (!date || !start) return false;
  const last = end && end > start ? end : start;
  const key = date.substring(0, 7);
  return key >= start && key <= last;
}

export function isDateInFortnight(date: string, fortnight: 1 | 2 | null): boolean {
  if (!fortnight) return true;
  const day = Number(date.substring(8, 10));
  return fortnight === 1 ? day <= 15 : day > 15;
}

export function getMonthlyIncome(paymentHistory: PaymentHistoryRow[]): Map<string, number> {
  const map = new Map<string, number>();
  paymentHistory.forEach((p) => {
    if (p.date) {
      const key = p.date.substring(0, 7);
      map.set(key, (map.get(key) || 0) + (p.amount - (p.discount || 0)));
    }
  });
  return map;
}

export function getMonthlyExpenses(recentExpenses: any[]): Map<string, number> {
  const map = new Map<string, number>();
  recentExpenses.forEach((e: any) => {
    if (e.date) {
      const key = e.date.substring(0, 7);
      map.set(key, (map.get(key) || 0) + e.amount);
    }
  });
  return map;
}

export function getWhatsAppLink(phone: string | undefined, name: string, amount: number): string | null {
  if (!phone) return null;
  const clean = phone.replace(/\D/g, '');
  const msg = encodeURIComponent(`Hola ${name}, te saludamos de Moscowle. Recordarte que el pago de tu mensualidad (S/ ${amount}) está pendiente. ¡Gracias!`);
  return `https://wa.me/51${clean}?text=${msg}`;
}

export function getInitials(name: string): string {
  return name?.slice(0, 2).toUpperCase() || 'XX';
}

export function rankContract(status: string): number {
  const ranks: Record<string, number> = { active: 4, pending: 3, completed: 2, cancelled: 1, none: 0 };
  return ranks[status] ?? 0;
}

export function getPatientStatus(p: PatientRow): string {
  if (!p.contract_status) return 'sin_contrato';
  if (p.contract_status === 'cancelled') return 'cancelado';
  if (p.contract_status === 'pending') return 'sin_contrato';
  if ((p.contract_overdue || 0) > 0) return 'deudor';
  return 'al_dia';
}

export function getStatusInfo(p: PatientRow): { label: string; bg: string; text: string; dot: string } {
  const st = getPatientStatus(p);
  switch (st) {
    case 'al_dia':
      return { label: 'Al Dia', bg: 'bg-success-container', text: 'text-success', dot: 'bg-success' };
    case 'deudor':
      return { label: 'Deudor', bg: 'bg-error-container', text: 'text-error', dot: 'bg-error' };
    case 'cancelado':
      return { label: 'Cancelado', bg: 'bg-surface-container-high', text: 'text-on-surface-variant', dot: 'bg-outline' };
    case 'sin_contrato':
      return { label: 'Sin Contrato', bg: 'bg-warning-container', text: 'text-warning', dot: 'bg-warning' };
    default:
      return { label: 'Inactivo', bg: 'bg-surface-container-high', text: 'text-on-surface-variant', dot: 'bg-outline' };
  }
}

export function isOverdue(p: PatientRow): boolean {
  if (!p.next_due_date || p.payment_amount <= 0) return false;
  return new Date(p.next_due_date) < new Date();
}

export function getOverdueDays(p: PatientRow): number {
  if (!p.next_due_date) return 0;
  const diff = new Date().getTime() - new Date(p.next_due_date).getTime();
  return Math.max(0, Math.floor(diff / (1000 * 60 * 60 * 24)));
}
export function buildChartStatusDist(patients: PatientRow[]): ChartData<'doughnut'> {
  const alDia = patients.filter(p => getPatientStatus(p) === 'al_dia').length;
  const deudor = patients.filter(p => getPatientStatus(p) === 'deudor').length;
  const cancelado = patients.filter(p => getPatientStatus(p) === 'cancelado').length;
  const sinContrato = patients.filter(p => getPatientStatus(p) === 'sin_contrato').length;
  return { labels: ['Al Día', 'Deudores', 'Cancelados', 'Sin Contrato'], datasets: [{ data: [alDia, deudor, cancelado, sinContrato], backgroundColor: ['#75a83a', '#ba1a1a', '#9ca3af', '#d9dbce'], borderWidth: 0, hoverOffset: 8 }] };
}

export function buildChartDebtByLocation(patients: PatientRow[]): ChartData<'bar'> {
  const debtBySede: Record<string, number> = {};
  patients.forEach(p => { debtBySede[p.sede_name] = (debtBySede[p.sede_name] || 0) + p.payment_amount; });
  const labels = Object.keys(debtBySede);
  return { labels, datasets: [{ label: 'Deuda (S/)', data: Object.values(debtBySede), backgroundColor: labels.map((_, i) => chartColors[i % chartColors.length]), borderRadius: 6, barPercentage: 0.5 }] };
}

export function buildChartPaymentAge(patients: PatientRow[]): ChartData<'bar'> {
  const ranges = ['1-7 días', '8-15 días', '16-30 días', '31-60 días', '+60 días'];
  const counts = [0, 0, 0, 0, 0];
  const now = new Date();
  patients.forEach(p => {
    if (!p.next_due_date) return;
    const diffDays = Math.floor((now.getTime() - new Date(p.next_due_date).getTime()) / (1000 * 60 * 60 * 24));
    if (diffDays <= 0) counts[0]++; else if (diffDays <= 7) counts[0]++; else if (diffDays <= 15) counts[1]++; else if (diffDays <= 30) counts[2]++; else if (diffDays <= 60) counts[3]++; else counts[4]++;
  });
  return { labels: ranges, datasets: [{ label: 'Pacientes', data: counts, backgroundColor: ['rgba(117, 168, 58, 0.8)', 'rgba(59, 130, 246, 0.8)', 'rgba(245, 158, 11, 0.8)', 'rgba(139, 92, 246, 0.8)', 'rgba(186, 26, 26, 0.8)'], borderRadius: 6, barPercentage: 0.6 }] };
}

export function buildChartRevenueHistory(paymentHistory: PaymentHistoryRow[], monthKeys?: string[]): ChartData<'line'> {
  const incomeByMonth = getMonthlyIncome(paymentHistory);
  const keys = monthKeys || getLast6MonthsKeys();
  const revenues = keys.map(k => incomeByMonth.get(k) || 0);
  const labels = keys.map(k => formatMonthLabel(k));
  return { labels, datasets: [{ label: 'Ingresos (S/)', data: revenues, borderColor: '#75a83a', backgroundColor: 'rgba(117, 168, 58, 0.1)', fill: true, pointBackgroundColor: '#75a83a', pointBorderColor: '#fff', pointBorderWidth: 2 }] };
}

export function buildChartRevenueByPlan(patients: PatientRow[]): ChartData<'pie'> {
  const planMap: Record<string, number> = {};
  patients.forEach(p => { const k = p.plan_name || 'Sin plan'; planMap[k] = (planMap[k] || 0) + p.payment_amount; });
  const labels = Object.keys(planMap);
  return { labels, datasets: [{ data: Object.values(planMap), backgroundColor: labels.map((_, i) => chartColors[i % chartColors.length]), borderWidth: 0, hoverOffset: 8 }] };
}

export function buildChartProjVsReal(incomeExpected: number, incomeReal: number): ChartData<'bar'> {
  return { labels: ['Este Mes'], datasets: [{ label: 'Proyectado', data: [incomeExpected], backgroundColor: 'rgba(59, 130, 246, 0.85)', borderRadius: 6, barPercentage: 0.4 }, { label: 'Real', data: [incomeReal], backgroundColor: 'rgba(117, 168, 58, 0.85)', borderRadius: 6, barPercentage: 0.4 }] };
}

export function buildChartRevenueByLocation(patients: PatientRow[]): ChartData<'pie'> {
  const sedeMap: Record<string, number> = {};
  patients.forEach(p => { sedeMap[p.sede_name] = (sedeMap[p.sede_name] || 0) + p.payment_amount; });
  const labels = Object.keys(sedeMap);
  return { labels, datasets: [{ data: Object.values(sedeMap), backgroundColor: labels.map((_, i) => chartColors[i % chartColors.length]), borderWidth: 0, hoverOffset: 8 }] };
}

export function getMonthKeysBetween(start: string, end: string): string[] {
  const keys: string[] = [];
  const [sy, sm] = start.split('-').map(Number);
  const [ey, em] = end.split('-').map(Number);
  let y = sy, m = sm;
  while (y < ey || (y === ey && m <= em)) {
    keys.push(`${y}-${String(m).padStart(2, '0')}`);
    m++;
    if (m > 12) { m = 1; y++; }
  }
  return keys;
}

export function getPatientMonthDebt(p: PatientRow, monthKey: string): boolean {
  if (!p.next_due_date) return false;
  return p.next_due_date.substring(0, 7) === monthKey;
}

export function getPatientFortnightDebt(p: PatientRow, monthKey: string, fortnight: 1 | 2): boolean {
  if (!p.next_due_date || p.payment_amount <= 0) return false;
  const datePart = p.next_due_date.substring(0, 7);
  if (datePart !== monthKey) return false;
  const day = new Date(p.next_due_date).getDate();
  return fortnight === 1 ? day <= 15 : day > 15;
}

export function buildPatientYearGrid(payments: PaymentHistoryRow[], patient: PatientRow): MonthCell[] {
  const now = new Date();
  const year = now.getFullYear();
  const grid: MonthCell[] = [];
  const payByMonth = new Map<string, PaymentHistoryRow>();
  for (const p of payments) {
    if (p.date) {
      const key = p.date.substring(0, 7);
      payByMonth.set(key, p);
    }
  }
  const isRetirado = patient.status === 'retirado' || patient.status === 'inactive';
  for (let m = 0; m < 12; m++) {
    const monthKey = `${year}-${String(m + 1).padStart(2, '0')}`;
    const payment = payByMonth.get(monthKey) || null;
    let status: MonthCell['status'] = 'missing';
    if (payment) {
      status = 'paid';
    } else if (monthKey > `${year}-${String(now.getMonth() + 1).padStart(2, '0')}`) {
      status = 'future';
    } else if (isRetirado) {
      status = 'na';
    }
    grid.push({
      monthKey,
      label: new Date(year, m, 1).toLocaleDateString('es-PE', { month: 'short' }),
      year,
      month: m + 1,
      payment,
      status,
    });
  }
  return grid;
}
