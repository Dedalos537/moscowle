import { KpiStatus, KpiUnit, ScorecardKpi } from '../../../../core/models/sede';

const money0 = new Intl.NumberFormat('es-PE', { style: 'currency', currency: 'PEN', maximumFractionDigits: 0 });
const money2 = new Intl.NumberFormat('es-PE', { style: 'currency', currency: 'PEN', minimumFractionDigits: 2, maximumFractionDigits: 2 });
const num1 = new Intl.NumberFormat('es-PE', { maximumFractionDigits: 1 });
const int = new Intl.NumberFormat('es-PE', { maximumFractionDigits: 0 });

export function fmtValue(v: number | null | undefined, unit: KpiUnit): string {
  if (v == null) return 'Sin datos';
  switch (unit) {
    case 'money':
      return (Math.abs(v) >= 1000 ? money0 : money2).format(v);
    case 'pct':
      return `${num1.format(v)} %`;
    case 'dec':
      return num1.format(v);
    default:
      return int.format(v);
  }
}

/** Valor corto para ejes y etiquetas de barras. */
export function fmtShort(v: number | null | undefined, unit: KpiUnit): string {
  if (v == null) return '—';
  if (unit === 'money' && Math.abs(v) >= 1000) return `S/ ${num1.format(v / 1000)} mil`;
  return fmtValue(v, unit);
}

export type DeltaTone = 'better' | 'worse' | 'same' | 'none';

/** Variación frente al periodo anterior; en porcentajes se expresa en puntos, no en % de un %. */
export function delta(k: ScorecardKpi): { text: string; tone: DeltaTone } {
  if (k.value == null || k.previous == null) return { text: 'Sin comparación', tone: 'none' };
  const diff = k.value - k.previous;
  if (Math.abs(diff) < 0.05) return { text: 'Igual que antes', tone: 'same' };
  const better = k.direction === 'up' ? diff > 0 : diff < 0;
  const arrow = diff > 0 ? '↑' : '↓';
  let text: string;
  if (k.unit === 'pct') text = `${arrow} ${num1.format(Math.abs(diff))} pts`;
  else if (k.previous === 0) text = `${arrow} desde 0`;
  else text = `${arrow} ${int.format(Math.abs((diff / k.previous) * 100))} %`;
  return { text, tone: better ? 'better' : 'worse' };
}

export function statusLabel(k: Pick<ScorecardKpi, 'status' | 'target' | 'value'>): string {
  const labels: Record<KpiStatus, string> = { good: 'En meta', warn: 'Cerca de la meta', bad: 'Fuera de meta', none: '' };
  if (k.status !== 'none') return labels[k.status];
  return k.target == null ? 'Sin meta' : 'Sin datos';
}

export function targetLabel(k: ScorecardKpi): string {
  if (k.target == null) return 'Sin meta definida';
  return `Meta ${k.direction === 'up' ? '≥' : '≤'} ${fmtValue(k.target, k.unit)}`;
}

export function scoreTone(score: number | null | undefined): KpiStatus {
  if (score == null) return 'none';
  return score >= 80 ? 'good' : score >= 50 ? 'warn' : 'bad';
}

const MONTHS = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];

export function monthLabel(iso: string): string {
  const [, m] = iso.split('-').map(Number);
  return MONTHS[m - 1];
}

/** «1–20 oct» o «1 jul – 20 oct 2026». */
export function rangeLabel(r: { from: string; to: string }): string {
  const [fy, fm, fd] = r.from.split('-').map(Number);
  const [ty, tm, td] = r.to.split('-').map(Number);
  if (fy === ty && fm === tm) return `${fd}–${td} ${MONTHS[tm - 1]} ${ty}`;
  if (fy === ty) return `${fd} ${MONTHS[fm - 1]} – ${td} ${MONTHS[tm - 1]} ${ty}`;
  return `${fd} ${MONTHS[fm - 1]} ${fy} – ${td} ${MONTHS[tm - 1]} ${ty}`;
}
