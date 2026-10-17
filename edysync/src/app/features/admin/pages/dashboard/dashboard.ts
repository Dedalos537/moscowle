import { Component, OnInit, OnDestroy, ViewChild, TemplateRef, ChangeDetectionStrategy, inject, signal, computed } from '@angular/core';
import { DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { Subscription } from 'rxjs';
import { AdminService } from '../../../../core/services/admin.service';
import { HeaderService } from '../../../../core/services/header.service';
import { GlobalSettingsService } from '../../../../core/services/global-settings.service';
import { DataCacheService } from '../../../../core/services/cache.service';
import { PeopleService } from '../../../../core/services/people.service';
import { CenterDashboard, DuePayment } from '../../../../core/models/center-dashboard';
import { ScorecardPeriod, Sede } from '../../../../core/models/sede';
import { Drawer } from '../../../../shared/components/drawer/drawer';
import { RegisterPayment } from '../../components/register-payment/register-payment';
import { PersonLabelPipe } from '../../../../shared/pipes/person-label.pipe';
import { SessionLabelPipe } from '../../../../shared/pipes/session-label-pipe';
import { rangeLabel, scoreTone } from '../sedes/kpi-format';
import { GrowthPanel } from './components/growth-panel/growth-panel';
import { RiskPanel } from './components/risk-panel/risk-panel';
import { TeamPanel } from './components/team-panel/team-panel';
import { SedeCompare } from './components/sede-compare/sede-compare';

type TodayKey = 'sessions' | 'payments' | 'approvals' | 'incidents';

/**
 * Panel de administración organizado alrededor de tres preguntas: qué hay que hacer hoy, si el centro crece y
 * quién está en riesgo de dejar el servicio. Una sola petición trae todo (rápido con datos móviles).
 */
@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [
    DatePipe,
    FormsModule,
    RouterLink,
    FontAwesomeModule,
    Drawer,
    RegisterPayment,
    PersonLabelPipe,
    SessionLabelPipe,
    GrowthPanel,
    RiskPanel,
    TeamPanel,
    SedeCompare,
  ],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Dashboard implements OnInit, OnDestroy {
  @ViewChild('headerActions', { static: true }) headerActions!: TemplateRef<unknown>;

  private admin = inject(AdminService);
  private header = inject(HeaderService);
  private cache = inject(DataCacheService);
  private settings = inject(GlobalSettingsService);
  readonly people = inject(PeopleService);

  readonly hideCharts = this.settings.hideCharts;
  readonly periods: { key: ScorecardPeriod; label: string }[] = [
    { key: 'month', label: 'Mes' },
    { key: 'quarter', label: 'Trimestre' },
    { key: 'year', label: 'Año' },
  ];

  readonly period = signal<ScorecardPeriod>('month');
  readonly sedeId = signal<number | null>(null);
  readonly sedes = signal<Sede[]>([]);
  readonly data = signal<CenterDashboard | null>(null);
  readonly loading = signal(true);
  readonly error = signal<string | null>(null);
  readonly openToday = signal<TodayKey | null>(null);
  readonly showQuality = signal(false);
  readonly showPayment = signal(false);
  /** Paciente con el que se abre «Registrar pago» (desde Cobrar en Hoy o en Continuidad). */
  readonly payPatient = signal<{ id: number; name: string; code?: string } | null>(null);

  readonly range = computed(() => {
    const d = this.data();
    return d ? `${rangeLabel(d.range)} · comparado con ${rangeLabel(d.previous_range)}` : '';
  });
  readonly scoreTone = computed(() => scoreTone(this.data()?.score));
  readonly sedeName = computed(() => this.sedes().find((s) => s.id === this.sedeId())?.name ?? null);
  readonly approvals = computed(() => {
    const p = this.data()?.today.pending;
    return p ? p.requests + p.password_resets : 0;
  });

  private sub?: Subscription;
  private subs = new Subscription();

  ngOnInit() {
    this.header.setConfig({
      title: 'Panel de Administración',
      subtitle: 'Cómo va el centro y qué hacer hoy',
      icon: ['fas', 'gauge-high'],
      actionTemplate: this.headerActions,
    });
    this.subs.add(this.admin.getSedes().subscribe({ next: (list) => this.sedes.set(list.filter((s) => s.active)), error: () => {} }));
    this.load();
  }

  ngOnDestroy() {
    this.header.reset();
    this.sub?.unsubscribe();
    this.subs.unsubscribe();
  }

  load(fresh = false) {
    if (fresh) this.cache.invalidateContaining('/api/admin/dashboard');
    this.sub?.unsubscribe();
    this.loading.set(true);
    this.error.set(null);
    this.sub = this.admin.getCenterDashboard(this.period(), this.sedeId()).subscribe({
      next: (d) => {
        this.data.set(d);
        this.loading.set(false);
      },
      error: (e) => {
        this.loading.set(false);
        this.error.set(e?.status === 0 ? 'No pudimos conectar con el servidor. Revisa tu internet.' : e?.error?.message || 'No se pudo cargar el panel.');
      },
    });
  }

  setPeriod(p: ScorecardPeriod) {
    if (p === this.period()) return;
    this.period.set(p);
    this.load();
  }

  setSede(id: number | null) {
    this.sedeId.set(id || null);
    this.openToday.set(null);
    this.load();
  }

  toggleToday(key: TodayKey) {
    this.openToday.set(this.openToday() === key ? null : key);
  }

  openPayment(patient: { id: number; name: string; code?: string } | null = null) {
    this.payPatient.set(patient);
    this.showPayment.set(true);
  }

  /** El panel queda abierto (muestra el cronograma actualizado); el tablero se refresca detrás. */
  onPaymentCompleted() {
    this.load(true);
  }

  whatsapp(p: DuePayment): string | null {
    if (!p.phone) return null;
    const digits = p.phone.replace(/\D/g, '');
    const phone = digits.length === 9 ? '51' + digits : digits;
    const name = p.patient.name.split(' ')[0] || '';
    const text = `Hola ${name}, te saludamos del Centro Juan Pablo II. Te recordamos que hoy vence tu cuota de S/ ${p.amount.toFixed(2)}. ¡Gracias!`;
    return `https://wa.me/${phone}?text=${encodeURIComponent(text)}`;
  }
}
