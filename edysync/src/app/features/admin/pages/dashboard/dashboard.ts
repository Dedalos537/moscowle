import { Component, OnInit, OnDestroy, ViewChild, TemplateRef, ChangeDetectionStrategy, ChangeDetectorRef, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { fadeInUp, scaleIn, listStagger, cardEnter } from '../../../../core/animations';
import { Subscription } from 'rxjs';
import { forkJoin } from 'rxjs';
import { AdminService } from '../../../../core/services/admin.service';
import { HeaderService } from '../../../../core/services/header.service';
import { GlobalSettingsService } from '../../../../core/services/global-settings.service';
import { Sede } from '../../../../core/models/sede';
import { Spinner } from '../../../../shared/components/spinner/spinner';
import { Button } from '../../../../shared/components/button/button';
import { QuickPayment } from '../../components/quick-payment/quick-payment';
import { SummaryCard } from '../../../../shared/components/summary-card/summary-card';
import { ActionCard } from '../../../../shared/components/action-card/action-card';
import { BaseChartDirective } from 'ng2-charts';
import { Chart, registerables } from 'chart.js';
import { MonthRange, MonthRangePicker } from '../../../../shared/components/month-range-picker/month-range-picker';
import { PatientRow, PaymentHistoryRow } from '../finanzas/finanzas.models';
import { getPatientStatus, getStatusInfo, getMonthlyIncome, getLast6MonthsKeys, formatMonthLabel, buildChartStatusDist, buildChartDebtByLocation, buildChartPaymentAge, buildChartRevenueHistory, buildChartRevenueByPlan, buildChartProjVsReal, buildChartRevenueByLocation } from '../finanzas/finanzas-utils';
import { makeDoughnutOpts, makeBarOpts, makeLineOpts, makePieOpts } from '../finanzas/finanzas-charts-config';

Chart.register(...registerables);

interface SedeStat {
  id: number;
  name: string;
  count: number;
}

interface FinancialData {
  income_real: number;
  income_expected: number;
  overdue_amount: number;
  overdue_users_count: number;
}

interface IncompletePatient {
  paciente: string;
  email?: string;
  sede: string;
  details: string;
  monto?: number;
}

interface DailyPending {
  paciente: string;
  sede: string;
  monto: number;
  phone?: string;
  username?: string;
}

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, RouterModule, FontAwesomeModule, Spinner, Button, QuickPayment, SummaryCard, ActionCard, BaseChartDirective, MonthRangePicker],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.scss',
  animations: [fadeInUp, scaleIn, listStagger, cardEnter],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Dashboard implements OnInit, OnDestroy {
  private settings = inject(GlobalSettingsService);
  hideCharts = this.settings.hideCharts;

  @ViewChild('headerActions', { static: true }) headerActions!: TemplateRef<any>;

  summary = { therapists: 0, patients: 0, sessions_total: '-' as string | number, avg_accuracy: '-' as string | number };
  avgAuditCompliance: number | null = null;
  auditsCount = 0;
  therapistCount = 0;
  patientCount = 0;
  sedes: Sede[] = [];
  sedesStats: SedeStat[] = [];
  financials: FinancialData | null = null;
  incompletePatients: IncompletePatient[] = [];
  dailyPendings: DailyPending[] = [];
  loading = true;
  error: string | null = null;
  today = new Date();
  showGuidanceModal = false;
  showDailyModal = false;

  periodRange: MonthRange | null = null;
  patients: PatientRow[] = [];
  paymentHistory: PaymentHistoryRow[] = [];
  patientContractMap: Record<number, any> = {};

  chartStatusDist: any;
  chartStatusOpt: any;
  chartStatusType: 'doughnut' = 'doughnut';
  chartDebtByLocation: any;
  chartDebtByLocationOpt: any = makeBarOpts('y');
  chartDebtByLocationType: 'bar' = 'bar';
  chartPaymentAge: any;
  chartPaymentAgeOpt: any = makeBarOpts();
  chartPaymentAgeType: 'bar' = 'bar';
  chartRevenueHistory: any;
  chartRevenueHistoryOpt: any = makeLineOpts();
  chartRevenueHistoryType: 'line' = 'line';
  chartRevenueByPlan: any;
  chartRevenueByPlanOpt: any = makePieOpts();
  chartRevenueByPlanType: 'pie' = 'pie';
  chartProjVsReal: any;
  chartProjVsRealOpt: any;
  chartProjVsRealType: 'bar' = 'bar';
  chartRevenueByLocation: any;
  chartRevenueByLocationOpt: any = makePieOpts();
  chartRevenueByLocationType: 'pie' = 'pie';

  totalIncomeReal = 0;
  totalPending = 0;
  totalDebt = 0;
  totalPatients = 0;

  private subscriptions = new Subscription();

  constructor(
    private adminService: AdminService,
    private headerService: HeaderService,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit() {
    this.headerService.setConfig({
      title: 'Panel de Administración',
      subtitle: 'Control integral de terapeutas y pacientes',
      icon: ['fas', 'shield-alt'],
      actionTemplate: this.headerActions,
    });
    this.loadData();
  }

  ngOnDestroy() {
    this.headerService.reset();
    this.subscriptions.unsubscribe();
  }

  loadData() {
    this.loading = true;
    this.error = null;
    this.loadUserCounts();
    this.loadSedes();
    this.loadSedesStats();
    this.loadDebtData();
    this.loadPatients();
    this.loadPaymentHistory();
    this.loadContracts();
  }

  private setFinancialSummary() {
    this.subscriptions.add(
      this.adminService.getFinancialSummary().subscribe({
        next: (res) => {
          if (res.success && res.data && this.financials) {
            this.financials.income_real = res.data.income_real;
          }
          this.cdr.markForCheck();
        },
        error: () => this.cdr.markForCheck(),
      }),
    );
  }

  private loadUserCounts() {
    this.subscriptions.add(
      this.adminService.getOverview().subscribe({
        next: (res) => {
          if (res.success && res.users) {
            this.therapistCount = res.users.filter((u) => u.role === 'terapista').length;
            this.patientCount = res.users.filter((u) => u.role === 'jugador').length;
            this.summary = { therapists: this.therapistCount, patients: this.patientCount, sessions_total: '-', avg_accuracy: '-' };
          }
          this.loading = false;
          this.cdr.markForCheck();
        },
        error: (err) => {
          this.loading = false;
          this.error = err.error?.message || err.message || 'Error al cargar usuarios';
          this.cdr.markForCheck();
        },
      }),
    );
    this.subscriptions.add(
      this.adminService.getAdminOverview().subscribe({
        next: (res) => {
          if (res.success && res.data) {
            this.avgAuditCompliance = res.data.avg_audit_compliance;
            this.auditsCount = res.data.audits_count;
            this.summary.sessions_total = res.data.sessions_total;
          }
          this.cdr.markForCheck();
        },
        error: () => this.cdr.markForCheck(),
      }),
    );
  }

  private loadSedes() {
    this.subscriptions.add(
      this.adminService.getSedes().subscribe({
        next: (list) => {
          this.sedes = list;
          this.cdr.markForCheck();
        },
        error: () => this.cdr.markForCheck(),
      }),
    );
  }

  private loadSedesStats() {
    this.subscriptions.add(
      this.adminService.getSedesStats().subscribe({
        next: (res) => {
          if (res.success && res.data) {
            this.sedesStats = res.data;
          }
          this.cdr.markForCheck();
        },
        error: () => this.cdr.markForCheck(),
      }),
    );
  }

  private loadDebtData() {
    this.subscriptions.add(
      this.adminService.getDebtReport('all').subscribe({
        next: (res) => {
          if (!res.success || !res.data) return;
          const porSede: Record<string, any> = res.data.por_sede || {};
          const todayDay = this.today.getDate();

          let incomeReal = 0;
          let incomeExpected = 0;
          let overdueAmount = 0;
          let overdueCount = 0;
          const incomplete: IncompletePatient[] = [];
          const daily: DailyPending[] = [];

          Object.values(porSede).forEach((group: any) => {
            const sedeName = group.sede_name || '';
            const deudores: any[] = group.deudores || [];

            deudores.forEach((d: any) => {
              const amount = d.monto || 0;
              incomeExpected += amount;
              if (amount > 0) overdueAmount += amount;

              const isPriceInc = !d.monto || d.monto <= 0;
              const isPlanInc = !d.modality || d.modality.includes('Sin Modalidad');
              const isDateInc = !d.fecha_vencimiento || d.fecha_vencimiento === 'N/A';

              if (isPriceInc || isPlanInc || isDateInc) {
                incomplete.push({
                  paciente: d.paciente || d.email || 'Alumno',
                  email: d.email,
                  sede: sedeName,
                  details: [isPriceInc ? 'Monto' : null, isPlanInc ? 'Modalidad' : null, isDateInc ? 'Fecha' : null].filter(Boolean).join(', '),
                });
              }

              if (d.payment_day == todayDay && !isPriceInc) {
                daily.push({ paciente: d.paciente, sede: sedeName, monto: amount, phone: d.phone, username: d.username });
              }
            });

            if (deudores.length > 0) overdueCount += deudores.length;
          });

          this.financials = { income_real: 0, income_expected: incomeExpected, overdue_amount: overdueAmount, overdue_users_count: overdueCount };
          this.incompletePatients = incomplete;
          this.dailyPendings = daily;

          this.setFinancialSummary();

          if (incomplete.length > 5) {
            setTimeout(() => (this.showGuidanceModal = true), 2000);
          }
          if (daily.length > 0 && incomplete.length <= 5) {
            setTimeout(() => (this.showDailyModal = true), 2000);
          }
          this.cdr.markForCheck();
        },
        error: (err) => {
          this.error = err.error?.message || err.message || 'Error al cargar deudas';
          this.loading = false;
          this.cdr.markForCheck();
        },
      }),
    );
  }

  private loadPatients() {
    this.subscriptions.add(
      forkJoin({
        debt: this.adminService.getDebtReport('all'),
        users: this.adminService.getUsers('jugador'),
      }).subscribe({
        next: ({ debt, users }) => {
          const debtBySede: Record<string, any> = {};
          if (debt.success && debt.data?.por_sede) {
            Object.values(debt.data.por_sede).forEach((group: any) => {
              (group.deudores || []).forEach((d: any) => {
                debtBySede[d.paciente || d.email || ''] = d;
              });
            });
          }
          const list: PatientRow[] = (users.users || []).map((u: any) => {
            const d = debtBySede[u.username] || debtBySede[u.email] || {};
            return {
              id: u.id, username: u.username, email: u.email || '',
              sede_name: u.sede_name || '', therapist_name: u.therapist_name || '',
              payment_amount: d.monto || 0, plan_name: d.modality || '',
              plan_frequency: d.plan_frequency || '',
              sessions_total: d.sessions_total || 0,
              sessions_attended: d.sessions_attended || 0,
              sessions_remaining: d.sessions_remaining || 0,
              next_due_date: d.fecha_vencimiento || undefined,
              payment_day: d.payment_day || null,
              phone: u.phone || '', is_active: u.is_active,
              status: u.account_status || 'active',
              contract_status: undefined, contract_pending: undefined, contract_overdue: undefined,
              has_plan_config: !!d.modality && !d.modality.includes('Sin Modalidad'),
            } as PatientRow;
          });
          this.patients = list;
          this.totalPatients = list.length;
          this.updateCharts();
          this.cdr.markForCheck();
        },
        error: () => this.cdr.markForCheck(),
      }),
    );
  }

  private loadPaymentHistory() {
    this.subscriptions.add(
      this.adminService.getAllPayments().subscribe({
        next: (res) => {
          if (res.success) {
            this.paymentHistory = res.payments.map((p: any) => ({
              id: p.id, patient_id: p.patient_id, patient_name: p.patient_name,
              amount: p.amount, discount: p.discount || 0, method: p.method,
              date: p.date, status: p.status,
            } as PaymentHistoryRow));
          }
          this.updateCharts();
          this.cdr.markForCheck();
        },
        error: () => this.cdr.markForCheck(),
      }),
    );
  }

  private loadContracts() {
    this.subscriptions.add(
      this.adminService.getContractsFiltered({}).subscribe({
        next: (res) => {
          if (res.success) {
            const map: Record<number, any> = {};
            (res.contracts || []).forEach((c: any) => {
              if (!map[c.patient_id] || c.status === 'active') map[c.patient_id] = c;
            });
            this.patientContractMap = map;
            this.syncPatientContractState();
            this.updateCharts();
            this.cdr.markForCheck();
          }
        },
        error: () => this.cdr.markForCheck(),
      }),
    );
  }

  private syncPatientContractState() {
    this.patients.forEach(p => {
      const c = this.patientContractMap[p.id];
      if (c) {
        p.contract_status = c.status;
        p.contract_pending = c.pending_installments || 0;
        p.contract_overdue = c.overdue_installments || 0;
      } else {
        p.contract_status = undefined;
        p.contract_pending = undefined;
        p.contract_overdue = undefined;
      }
    });
  }

  onPeriodChange(range: MonthRange | null) {
    this.periodRange = range;
    this.updateCharts();
    this.cdr.markForCheck();
  }

  private updateCharts() {
    this.updateChartStatusDist();
    this.updateChartDebtByLocation();
    this.updateChartPaymentAge();
    this.updateChartRevenueHistory();
    this.updateChartRevenueByPlan();
    this.updateChartProjVsReal();
    this.updateChartRevenueByLocation();
  }

  private updateChartStatusDist() { this.chartStatusDist = buildChartStatusDist(this.patients); }
  private updateChartDebtByLocation() { this.chartDebtByLocation = buildChartDebtByLocation(this.patients); }
  private updateChartPaymentAge() { this.chartPaymentAge = buildChartPaymentAge(this.patients); }

  private updateChartRevenueHistory() {
    let monthKeys = getLast6MonthsKeys();
    if (this.periodRange && this.periodRange.start && this.periodRange.end) {
      if (this.periodRange.start === this.periodRange.end) {
        const [y, m] = this.periodRange.start.split('-').map(Number);
        const keys: string[] = [];
        let cy = y, cm = m;
        for (let i = 0; i < 6; i++) {
          keys.unshift(`${cy}-${String(cm).padStart(2, '0')}`);
          cm--;
          if (cm < 1) { cm = 12; cy--; }
        }
        monthKeys = keys;
      } else {
        const keys: string[] = [];
        const [sy, sm] = this.periodRange.start.split('-').map(Number);
        const [ey, em] = this.periodRange.end.split('-').map(Number);
        let y = sy, m = sm;
        let count = 0;
        while ((y < ey || (y === ey && m <= em)) && count < 24) {
          keys.push(`${y}-${String(m).padStart(2, '0')}`);
          m++;
          if (m > 12) { m = 1; y++; }
          count++;
        }
        monthKeys = keys;
      }
    }
    this.chartRevenueHistory = buildChartRevenueHistory(this.paymentHistory, monthKeys);
  }

  private updateChartRevenueByPlan() { this.chartRevenueByPlan = buildChartRevenueByPlan(this.patients); }
  private updateChartProjVsReal() {
    const expected = this.financials?.income_expected || 0;
    const real = this.financials?.income_real || 0;
    this.chartProjVsReal = buildChartProjVsReal(expected, real);
    this.totalIncomeReal = real;
    this.totalPending = this.patients.filter(p => p.payment_amount > 0).reduce((s, p) => s + p.payment_amount, 0);
    this.totalDebt = this.financials?.overdue_amount || 0;
  }
  private updateChartRevenueByLocation() { this.chartRevenueByLocation = buildChartRevenueByLocation(this.patients); }

  private loadFinancialSummary() {
    this.subscriptions.add(
      this.adminService.getFinancialSummary().subscribe({
        next: (res) => {
          if (res.success && res.data && this.financials) {
            this.financials.income_real = res.data.income_real;
          }
          this.cdr.markForCheck();
        },
        error: () => this.cdr.markForCheck(),
      }),
    );
  }

  onPaymentCompleted() {
    this.loadData();
  }

  get pendingAmount(): number {
    return Math.max(0, (this.financials?.income_expected ?? 0) - (this.financials?.income_real ?? 0));
  }

  get activeSedesCount(): number {
    return this.sedes.filter((s) => s.active).length;
  }

  getWhatsAppLink(phone: string | undefined, name: string, amount: number): string | null {
    if (!phone) return null;
    const clean = phone.replace(/\D/g, '');
    const msg = encodeURIComponent(`Hola ${name}, te saludamos de Moscowle. Recordarte que el pago de tu mensualidad (S/ ${amount}) vence hoy. ¡Gracias!`);
    return `https://wa.me/51${clean}?text=${msg}`;
  }

  barHeight(value: number): number {
    const max = Math.max(this.financials?.income_expected || 1, 1);
    return Math.max((value / max) * 200, 8);
  }

  trackById(_index: number, item: any): number {
    return item.id;
  }
}
