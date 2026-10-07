import { Component, ChangeDetectionStrategy, computed, input, model, signal } from '@angular/core';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { toLocalDateString } from '../../../core/utils/date.util';

interface DayCell {
  date: string; // YYYY-MM-DD local
  day: number;
  inMonth: boolean;
  disabled: boolean;
  holiday: string | null;
  weekend: boolean;
}

const MONTHS = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Setiembre', 'Octubre', 'Noviembre', 'Diciembre'];
const WEEKDAYS = ['Lu', 'Ma', 'Mi', 'Ju', 'Vi', 'Sa', 'Do'];

/**
 * Selector de varias fechas (clic suelto o rango). Trabaja siempre con fechas locales «YYYY-MM-DD»:
 * el formulario anterior usaba toISOString() y se corría un día en husos horarios al este de UTC.
 */
@Component({
  selector: 'app-multi-date-picker',
  standalone: true,
  imports: [FontAwesomeModule],
  templateUrl: './multi-date-picker.html',
  styleUrl: './multi-date-picker.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class MultiDatePicker {
  /** Fechas elegidas (two-way). */
  dates = model<string[]>([]);
  max = input(10);
  allowPast = input(false);
  holidays = input<Map<string, string>>(new Map());

  readonly weekdays = WEEKDAYS;
  month = signal(new Date(new Date().getFullYear(), new Date().getMonth(), 1));
  rangeMode = signal(false);
  rangeStart = signal<string | null>(null);
  /** Dirección de la última navegación: orienta la animación de entrada de la cuadrícula. */
  direction = signal<'next' | 'prev'>('next');
  announce = signal('');

  label = computed(() => `${MONTHS[this.month().getMonth()]} ${this.month().getFullYear()}`);
  atLimit = computed(() => this.dates().length >= this.max());

  weeks = computed<DayCell[][]>(() => {
    const m = this.month();
    const first = new Date(m.getFullYear(), m.getMonth(), 1);
    const cursor = new Date(first);
    cursor.setDate(cursor.getDate() - ((first.getDay() + 6) % 7));
    const today = toLocalDateString(new Date());
    const out: DayCell[][] = [];
    for (let w = 0; w < 6; w++) {
      const row: DayCell[] = [];
      for (let d = 0; d < 7; d++) {
        const date = toLocalDateString(cursor);
        row.push({
          date,
          day: cursor.getDate(),
          inMonth: cursor.getMonth() === m.getMonth(),
          disabled: !this.allowPast() && date < today,
          holiday: this.holidays().get(date) ?? null,
          weekend: d >= 5,
        });
        cursor.setDate(cursor.getDate() + 1);
      }
      out.push(row);
      if (cursor.getMonth() !== m.getMonth() && out.length >= 4) break;
    }
    return out;
  });

  sorted = computed(() => [...this.dates()].sort());

  isSelected(date: string): boolean {
    return this.dates().includes(date);
  }

  step(delta: number) {
    this.direction.set(delta > 0 ? 'next' : 'prev');
    const m = this.month();
    this.month.set(new Date(m.getFullYear(), m.getMonth() + delta, 1));
  }

  toggleRange() {
    this.rangeMode.update((v) => !v);
    this.rangeStart.set(null);
  }

  pick(cell: DayCell) {
    if (cell.disabled) return;
    if (this.rangeMode()) {
      const start = this.rangeStart();
      if (!start) {
        this.rangeStart.set(cell.date);
        this.announce.set(`Inicio del rango: ${cell.date}. Elige la fecha final.`);
        return;
      }
      const [from, to] = start <= cell.date ? [start, cell.date] : [cell.date, start];
      const next = new Set(this.dates());
      for (let d = this.parse(from); toLocalDateString(d) <= to; d.setDate(d.getDate() + 1)) {
        const key = toLocalDateString(d);
        if (next.size >= this.max()) break;
        const skip = this.holidays().has(key) || (!this.allowPast() && key < toLocalDateString(new Date()));
        if (!skip) next.add(key);
      }
      this.dates.set([...next].sort());
      this.rangeStart.set(null);
      this.rangeMode.set(false);
      this.announce.set(`${this.dates().length} fechas seleccionadas.`);
      return;
    }
    this.toggle(cell.date);
  }

  toggle(date: string) {
    const current = this.dates();
    if (current.includes(date)) {
      this.dates.set(current.filter((d) => d !== date));
      this.announce.set(`Fecha ${date} quitada.`);
    } else if (current.length < this.max()) {
      this.dates.set([...current, date].sort());
      this.announce.set(`Fecha ${date} añadida.`);
    } else {
      this.announce.set(`Máximo ${this.max()} fechas.`);
    }
  }

  clear() {
    this.dates.set([]);
    this.rangeStart.set(null);
  }

  inPendingRange(date: string): boolean {
    return this.rangeMode() && this.rangeStart() === date;
  }

  pretty(date: string): string {
    const d = this.parse(date);
    return d.toLocaleDateString('es-PE', { weekday: 'short', day: 'numeric', month: 'short' });
  }

  private parse(date: string): Date {
    const [y, m, d] = date.split('-').map(Number);
    return new Date(y, m - 1, d);
  }
}
