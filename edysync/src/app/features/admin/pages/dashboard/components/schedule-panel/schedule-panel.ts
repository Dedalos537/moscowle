import { ChangeDetectionStrategy, Component, computed, effect, inject, input, output, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { AdminService } from '../../../../../../core/services/admin.service';
import { IncomingSchedule, PayrollPeriodRow } from '../../../../../../core/models/billing';
import { PersonLabelPipe } from '../../../../../../shared/pipes/person-label.pipe';
import { periodLabel } from '../../../../components/pay-therapist/pay-therapist';

const OPEN_KEY = 'moscowle_dash_schedule_open';

/**
 * Cronograma (PRP 008): «escondido y a la vista». Plegado por defecto (recuerda si lo abriste) con dos pestañas:
 * lo que entra (cuotas de pacientes) y lo que sale (nómina de terapeutas), más el flujo proyectado a 4 semanas.
 */
@Component({
  selector: 'app-schedule-panel',
  standalone: true,
  imports: [DatePipe, FontAwesomeModule, PersonLabelPipe],
  templateUrl: './schedule-panel.html',
  styleUrl: './schedule-panel.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SchedulePanel {
  private admin = inject(AdminService);

  sedeId = input<number | null>(null);
  /** Cambia cada vez que el tablero se recarga (tras cobrar o pagar), para refrescar el cronograma. */
  version = input(0);
  charge = output<{ id: number; name: string; code?: string }>();
  pay = output<{ therapist: { id: number; name: string }; period: string }>();

  readonly open = signal(this.readOpen());
  readonly tab = signal<'in' | 'out'>('in');
  readonly incoming = signal<IncomingSchedule | null>(null);
  readonly payroll = signal<PayrollPeriodRow[]>([]);
  readonly loading = signal(false);
  readonly label = periodLabel;
  readonly showAll = signal(false);

  readonly pendingPayroll = computed(() => this.payroll().filter((p) => p.balance > 0.005));
  readonly outTotal = computed(() => this.pendingPayroll().reduce((s, p) => s + p.balance, 0));
  readonly inNext = computed(() => (this.incoming()?.weeks ?? []).reduce((s, w) => s + w.total, 0));
  readonly maxWeek = computed(() => Math.max(1, ...(this.incoming()?.weeks ?? []).map((w) => w.total), this.incoming()?.overdue_total ?? 0));
  readonly visibleIn = computed(() => {
    const items = this.incoming()?.items ?? [];
    return this.showAll() ? items : items.slice(0, 10);
  });

  constructor() {
    effect(() => {
      this.sedeId();
      this.version();
      if (this.open()) this.load();
    });
  }

  toggle() {
    const next = !this.open();
    this.open.set(next);
    try {
      localStorage.setItem(OPEN_KEY, next ? '1' : '0');
    } catch {
      /* almacenamiento no disponible */
    }
  }

  private readOpen(): boolean {
    try {
      return localStorage.getItem(OPEN_KEY) === '1';
    } catch {
      return false;
    }
  }

  private load() {
    this.loading.set(true);
    this.admin.billingIncoming(this.sedeId(), 4).subscribe({
      next: (r) => {
        this.incoming.set(r);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
    this.admin.payroll(3).subscribe({ next: (r) => this.payroll.set(r.periods), error: () => {} });
  }

  weekLabel(iso: string, i: number): string {
    if (i === 0) return 'Esta semana';
    if (i === 1) return 'La próxima';
    const [, m, d] = iso.split('-').map(Number);
    return `Sem. del ${d}/${m}`;
  }
}
