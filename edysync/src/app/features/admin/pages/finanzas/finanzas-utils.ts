import { PatientRow, PaymentHistoryRow } from './finanzas.models';

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

export function getPatientStatus(p: PatientRow): string {
  if (!p.has_plan_config || p.payment_amount <= 0) return 'sin_plan';
  if (p.sessions_remaining <= 0) return 'deudor';
  return 'al_dia';
}

export function getStatusInfo(p: PatientRow): { label: string; bg: string; text: string; dot: string } {
  const st = getPatientStatus(p);
  switch (st) {
    case 'al_dia':
      return { label: 'Al Dia', bg: 'bg-success-container', text: 'text-success', dot: 'bg-success' };
    case 'deudor':
      return { label: 'Deudor', bg: 'bg-error-container', text: 'text-error', dot: 'bg-error' };
    case 'sin_plan':
      return { label: 'Sin Plan', bg: 'bg-warning-container', text: 'text-warning', dot: 'bg-warning' };
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
