import { ChangeDetectionStrategy, Component, computed, effect, inject, input, output, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AdminService } from '../../../../core/services/admin.service';
import { ToastService } from '../../../../core/services/toast.service';
import { PayrollPeriodRow } from '../../../../core/models/billing';
import { PersonLabelPipe } from '../../../../shared/pipes/person-label.pipe';

const MONTHS = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];

export function periodLabel(p: string): string {
  const [y, m] = p.split('-').map(Number);
  return `${MONTHS[m - 1]} ${y}`;
}

function todayIso(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

/**
 * Pagar a terapeuta (PRP 008): el pago se aplica a un periodo (mes liquidado), no al mes en que se paga.
 * Muestra lo que corresponde, lo ya pagado y el saldo de cada periodo, y sugiere pagar el saldo.
 */
@Component({
  selector: 'app-pay-therapist',
  standalone: true,
  imports: [DatePipe, FormsModule, PersonLabelPipe],
  templateUrl: './pay-therapist.html',
  styleUrl: './pay-therapist.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PayTherapist {
  private admin = inject(AdminService);
  private toast = inject(ToastService);

  therapist = input.required<{ id: number; name: string }>();
  /** Periodo con el que abrir (p. ej. desde una fila del cronograma). */
  period = input<string | null>(null);
  done = output<void>();

  readonly periods = signal<PayrollPeriodRow[]>([]);
  readonly loading = signal(true);
  readonly saving = signal(false);
  readonly error = signal('');
  readonly label = periodLabel;
  form = { period: '', amount: null as number | null, method: 'Transferencia', date: todayIso(), notes: '' };

  readonly selected = computed(() => this.periods().find((p) => p.period === this.periodSig()) ?? null);
  private periodSig = signal('');

  constructor() {
    effect(() => {
      const t = this.therapist();
      const wanted = this.period();
      this.loading.set(true);
      this.admin.payroll(6, t.id).subscribe({
        next: (r) => {
          const rows = r.periods.filter((p) => p.therapist?.id === t.id);
          this.periods.set(rows);
          const pick = rows.find((p) => p.period === wanted) ?? rows.find((p) => p.balance > 0.005) ?? rows[0];
          if (pick) this.choose(pick.period);
          this.loading.set(false);
        },
        error: () => {
          this.loading.set(false);
          this.error.set('No se pudo cargar la nómina del terapeuta.');
        },
      });
    });
  }

  choose(period: string) {
    this.form.period = period;
    this.periodSig.set(period);
    const row = this.periods().find((p) => p.period === period);
    this.form.amount = row && row.balance > 0 ? row.balance : null;
  }

  submit() {
    if (this.saving()) return;
    if (!this.form.period) return this.error.set('Elige el periodo que pagas.');
    if (!this.form.amount || this.form.amount <= 0) return this.error.set('Escribe el monto.');
    this.saving.set(true);
    this.error.set('');
    this.admin
      .payTherapist({ therapist_id: this.therapist().id, period: this.form.period, amount: this.form.amount, method: this.form.method, date: this.form.date, notes: this.form.notes || undefined })
      .subscribe({
        next: (r) => {
          this.saving.set(false);
          this.periods.update((list) => list.map((p) => (p.period === r.period.period ? r.period : p)));
          this.form.amount = r.period.balance > 0 ? r.period.balance : null;
          this.toast.show(`Pago a terapeuta registrado (${periodLabel(r.period.period)}).`, 'success');
          this.done.emit();
        },
        error: (e) => {
          this.saving.set(false);
          this.error.set(e?.error?.message || 'No se pudo registrar el pago.');
        },
      });
  }
}
