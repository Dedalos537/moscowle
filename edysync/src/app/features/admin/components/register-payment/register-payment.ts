import { ChangeDetectionStrategy, Component, OnDestroy, computed, inject, input, output, signal, effect } from '@angular/core';
import { DatePipe, NgTemplateOutlet } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { Subject, Subscription, debounceTime, distinctUntilChanged, switchMap, of } from 'rxjs';
import { AdminService } from '../../../../core/services/admin.service';
import { ToastService } from '../../../../core/services/toast.service';
import { PatientSchedule, ScheduleInstallment } from '../../../../core/models/billing';
import { PersonLabelPipe } from '../../../../shared/pipes/person-label.pipe';

type Mode = 'pay' | 'plan' | 'one_off';
interface Hit { id: number; username: string; email?: string; login_code?: string }

const METHODS = ['Yape', 'Plin', 'Efectivo', 'Transferencia', 'Tarjeta', 'Otro'];
const CATEGORIES = [
  { value: 'evaluacion', label: 'Evaluación' },
  { value: 'material', label: 'Material' },
  { value: 'inscripcion', label: 'Inscripción' },
  { value: 'otro', label: 'Otro' },
];

function todayIso(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

/**
 * Registrar pago (PRP 008): elige al paciente, muestra su cronograma y dice a qué cuotas irá el pago antes de
 * confirmarlo. Sin contrato, ofrece crear el plan de pago o registrar un pago suelto clasificado: así ningún
 * pago queda fuera del cronograma ni de la cobranza.
 */
@Component({
  selector: 'app-register-payment',
  standalone: true,
  imports: [DatePipe, NgTemplateOutlet, FormsModule, FontAwesomeModule, PersonLabelPipe],
  templateUrl: './register-payment.html',
  styleUrl: './register-payment.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class RegisterPayment implements OnDestroy {
  private admin = inject(AdminService);
  private toast = inject(ToastService);

  /** Paciente ya elegido (p. ej. desde «Cobrar» en el cronograma). */
  patient = input<{ id: number; name: string; code?: string } | null>(null);
  done = output<void>();

  readonly methods = METHODS;
  readonly categories = CATEGORIES;
  readonly query = signal('');
  readonly hits = signal<Hit[]>([]);
  readonly searching = signal(false);
  readonly picked = signal<{ id: number; name: string; code?: string } | null>(null);
  readonly schedule = signal<PatientSchedule | null>(null);
  readonly loading = signal(false);
  readonly saving = signal(false);
  readonly mode = signal<Mode>('pay');
  readonly error = signal('');

  pay = { amount: null as number | null, method: 'Yape', date: todayIso(), reference: '', notes: '' };
  plan = { amount: null as number | null, billing_type: 'Mensual' as 'Mensual' | 'Quincenal', payment_day: new Date().getDate(), first_due: todayIso(), installments: null as number | null };
  oneOff = { category: 'evaluacion', amount: null as number | null, method: 'Yape', date: todayIso(), reference: '' };
  receipt: File | null = null;

  readonly hasContract = computed(() => (this.schedule()?.contracts ?? []).some((c) => c.status === 'active'));
  readonly open = computed<ScheduleInstallment[]>(() =>
    (this.schedule()?.contracts ?? [])
      .filter((c) => c.status === 'active')
      .flatMap((c) => c.installments)
      .filter((i) => i.remaining > 0.005 && (i.status === 'pending' || i.status === 'partial'))
      .sort((a, b) => a.due_date.localeCompare(b.due_date) || a.number - b.number),
  );
  readonly overdue = computed(() => this.open().filter((i) => i.overdue).reduce((s, i) => s + i.remaining, 0));
  readonly dueToday = computed(() => this.open().filter((i) => i.due_date === todayIso()).reduce((s, i) => s + i.remaining, 0));
  readonly amountSignal = signal(0);

  /** A qué cuotas irá el pago (FIFO, igual que el servidor) y cuánto quedará a favor. */
  readonly preview = computed(() => {
    let left = this.amountSignal();
    const parts: { inst: ScheduleInstallment; take: number; full: boolean }[] = [];
    for (const inst of this.open()) {
      if (left <= 0.005) break;
      const take = Math.min(inst.remaining, left);
      parts.push({ inst, take, full: take >= inst.remaining - 0.005 });
      left -= take;
    }
    return { parts, credit: Math.max(0, Math.round(left * 100) / 100) };
  });

  private search$ = new Subject<string>();
  private subs = new Subscription();

  constructor() {
    this.subs.add(
      this.search$
        .pipe(
          debounceTime(250),
          distinctUntilChanged(),
          switchMap((q) => {
            if (q.trim().length < 2) {
              this.searching.set(false);
              return of({ patients: [] as Hit[] });
            }
            this.searching.set(true);
            return this.admin.searchPatients(q.trim());
          }),
        )
        .subscribe({
          next: (res) => {
            this.hits.set((res.patients ?? []) as Hit[]);
            this.searching.set(false);
          },
          error: () => this.searching.set(false),
        }),
    );
    effect(() => {
      const p = this.patient();
      if (p) this.choose({ id: p.id, username: p.name, login_code: p.code });
    });
  }

  ngOnDestroy() {
    this.subs.unsubscribe();
  }

  onQuery(q: string) {
    this.query.set(q);
    this.search$.next(q);
  }

  choose(h: Hit) {
    this.picked.set({ id: h.id, name: h.username, code: h.login_code });
    this.hits.set([]);
    this.query.set('');
    this.error.set('');
    this.load();
  }

  reset() {
    this.picked.set(null);
    this.schedule.set(null);
    this.mode.set('pay');
    this.error.set('');
  }

  private load() {
    const p = this.picked();
    if (!p) return;
    this.loading.set(true);
    this.subs.add(
      this.admin.patientSchedule(p.id).subscribe({
        next: (s) => {
          this.schedule.set(s);
          this.loading.set(false);
          const suggested = Math.round((this.overdue() + this.dueToday()) * 100) / 100 || this.open()[0]?.remaining || null;
          this.pay.amount = suggested;
          this.amountSignal.set(suggested ?? 0);
          this.mode.set(this.hasContract() ? 'pay' : 'plan');
          const first = s.other_payments.find((x) => x.kind === 'unassigned');
          if (first && !this.hasContract()) this.plan.amount = first.amount;
        },
        error: () => {
          this.loading.set(false);
          this.error.set('No se pudo cargar el cronograma del paciente.');
        },
      }),
    );
  }

  setAmount(v: number | null) {
    this.pay.amount = v;
    this.amountSignal.set(Number(v) || 0);
  }

  readonly receiptName = signal('');

  onReceipt(ev: Event) {
    this.receipt = (ev.target as HTMLInputElement).files?.[0] ?? null;
    this.receiptName.set(this.receipt?.name ?? '');
  }

  submitPayment(kind: 'installment' | 'one_off') {
    const p = this.picked();
    if (!p || this.saving()) return;
    const f = kind === 'installment' ? this.pay : this.oneOff;
    if (!f.amount || f.amount <= 0) {
      this.error.set('Escribe el monto del pago.');
      return;
    }
    const fd = new FormData();
    fd.append('patient_id', String(p.id));
    fd.append('amount', String(f.amount));
    fd.append('method', f.method);
    fd.append('payment_date', f.date);
    fd.append('kind', kind);
    if (f.reference) fd.append('reference', f.reference);
    if (kind === 'one_off') fd.append('category', this.oneOff.category);
    if (kind === 'installment' && this.pay.notes) fd.append('notes', this.pay.notes);
    if (this.receipt) fd.append('receipt', this.receipt);
    this.saving.set(true);
    this.error.set('');
    this.subs.add(
      this.admin.registerPayment(fd).subscribe({
        next: (res: any) => {
          this.saving.set(false);
          this.toast.show(res?.message || 'Pago registrado', 'success');
          this.receipt = null;
          this.receiptName.set('');
          this.done.emit();
          this.load();
        },
        error: (err) => {
          this.saving.set(false);
          this.error.set(err?.status === 0 ? 'No hay conexión con el servidor.' : err?.error?.error || 'No se pudo registrar el pago.');
        },
      }),
    );
  }

  submitPlan() {
    const p = this.picked();
    if (!p || this.saving()) return;
    if (!this.plan.amount || this.plan.amount <= 0) {
      this.error.set('Escribe el monto de cada cuota.');
      return;
    }
    this.saving.set(true);
    this.error.set('');
    this.subs.add(
      this.admin
        .createPaymentPlan({
          patient_id: p.id,
          amount: this.plan.amount,
          payment_day: this.plan.payment_day,
          first_due: this.plan.first_due,
          installments: this.plan.installments || null,
          billing_type: this.plan.billing_type,
        })
        .subscribe({
          next: () => {
            this.saving.set(false);
            this.toast.show('Plan de pago creado. Ya puedes registrar el pago.', 'success');
            this.load();
          },
          error: (err) => {
            this.saving.set(false);
            this.error.set(err?.error?.message || 'No se pudo crear el plan.');
          },
        }),
    );
  }
}
