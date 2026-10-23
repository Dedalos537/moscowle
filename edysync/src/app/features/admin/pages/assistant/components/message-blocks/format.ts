import { ValueFormat } from '../../../../../../core/services/assistant';

const money = new Intl.NumberFormat('es-PE', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const int = new Intl.NumberFormat('es-PE', { maximumFractionDigits: 0 });
const dec = new Intl.NumberFormat('es-PE', { minimumFractionDigits: 1, maximumFractionDigits: 1 });

/** Mismos formatos que el resto de la plataforma: S/ con 2 decimales, % con 1, enteros con separador de miles. */
export function formatValue(v: unknown, format?: ValueFormat): string {
  if (v === null || v === undefined || v === '') return '—';
  if (format === 'date') {
    const d = new Date(String(v));
    return isNaN(d.getTime()) ? String(v) : d.toLocaleDateString('es-PE', { day: '2-digit', month: 'short' });
  }
  const n = Number(v);
  if (!format || isNaN(n)) return String(v);
  if (format === 'money') return `S/ ${money.format(n)}`;
  if (format === 'pct') return `${dec.format(n)} %`;
  if (format === 'dec') return dec.format(n);
  return int.format(n);
}
