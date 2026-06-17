import { Component, OnInit, OnDestroy, ViewChild, TemplateRef, ChangeDetectionStrategy, ChangeDetectorRef, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { BaseChartDirective } from 'ng2-charts';
import { Subscription } from 'rxjs';
import { ActivatedRoute } from '@angular/router';
import { AdminService } from '../../../../core/services/admin.service';
import { HeaderService } from '../../../../core/services/header.service';
import { AlertService } from '../../../../core/services/alert.service';
import { ToastService } from '../../../../core/services/toast.service';
import { GlobalSettingsService } from '../../../../core/services/global-settings.service';
import { Sede } from '../../../../core/models/sede';
import { Chart, registerables } from 'chart.js';
import type { ChartConfiguration, ChartData } from 'chart.js';
import { fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter } from '../../../../core/animations';
import { firstValueFrom } from 'rxjs';
import { ConfirmService } from '../../../../core/services/confirm.service';
import { SelectOption } from '../../../../shared/components/select/select';
import { Button } from '../../../../shared/components/button/button';
import { Spinner } from '../../../../shared/components/spinner/spinner';
import { Select } from '../../../../shared/components/select/select';
import { Input } from '../../../../shared/components/input/input';
import { Modal } from '../../../../shared/components/modal/modal';

Chart.register(...registerables);

interface PatientRow {
  id: number;
  username: string;
  email: string;
  phone?: string;
  sede_name: string;
  therapist_name: string;
  plan_name: string;
  plan_frequency: string;
  payment_amount: number;
  sessions_total: number;
  sessions_attended: number;
  sessions_remaining: number;
  next_due_date?: string;
  status: string;
  has_plan_config: boolean;
}

interface PaymentHistoryRow {
  id: number;
  patient_id: number;
  patient_name: string;
  amount: number;
  discount: number;
  method: string;
  reference?: string;
  date: string;
  status: string;
  receipt_image_path?: string;
  document_number?: string;
  guardian_name?: string;
}

interface Therapist {
  id: number;
  username: string;
  email: string;
  role: string;
}

@Component({
  selector: 'app-payments',
  standalone: true,
  templateUrl: './payments.html',
  styleUrl: './payments.scss',
  animations: [fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter],
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [CommonModule, FormsModule, RouterModule, FontAwesomeModule, BaseChartDirective, Button, Spinner, Select, Input, Modal],
})
export class Payments implements OnInit, OnDestroy {
  private settings = inject(GlobalSettingsService);
  hideCharts = this.settings.hideCharts;

  @ViewChild('headerActions', { static: true }) headerActions!: TemplateRef<any>;

  patients: PatientRow[] = [];
  paymentHistory: PaymentHistoryRow[] = [];
  sedes: Sede[] = [];
  therapists: Therapist[] = [];
  loading = true;
  activeTab: 'pacientes' | 'historial' = 'pacientes';

  searchQuery = '';
  selectedSedeId: number | null = null;
  selectedTherapistId: number | null = null;
  selectedStatus: string = '';
  selectedSort: string = '';
  selectedMonth: string = '';

  // ─── Register Payment Modal ──────────────────────────────
  showRegisterModal = false;
  registerForm = {
    patient_id: null as number | null,
    amount: 0,
    method: 'transfer',
    reference: '',
    next_due_date: '',
    payment_date: '',
    discount: 0,
    document_number: '',
    guardian_name: '',
    receipt: null as File | null,
  };
  registerStatus = '';
  analyzeResult: any = null;
  analyzingReceipt = false;

  showPreviewModal = false;
  previewImageUrl = '';

  // ─── Settings Modal (Plan Configuration) ─────────────────
  showSettingsModal = false;
  settingsForm = {
    patient_id: null as number | null,
    patient_name: '',
    payment_plan: 'Mensual',
    payment_amount: 0,
    payment_due_date: '',
  };
  settingsStatus = '';

  // ─── Select Options ──────────────────────────────────────

  get sedeFilterOptions(): SelectOption[] {
    return [{value: null, label: 'Todas las Sedes'}, ...this.sedes.map(s => ({value: s.id, label: s.name}))];
  }

  get therapistFilterOptions(): SelectOption[] {
    return [{value: null, label: 'Todos los Terapeutas'}, ...this.therapists.map(t => ({value: t.id, label: t.username}))];
  }

  statusFilterOptions: SelectOption[] = [
    {value: '', label: 'Todos'},
    {value: 'al_dia', label: 'Al Día'},
    {value: 'deudores', label: 'Deudores'},
    {value: 'sin_plan', label: 'Sin Plan'},
    {value: 'inactivos', label: 'Inactivos'},
  ];

  sortOptions: SelectOption[] = [
    {value: '', label: 'Ordenar'},
    {value: 'nombre', label: 'Nombre'},
    {value: 'vencimiento_cercano', label: 'Vencimiento cercano'},
    {value: 'vencimiento_lejano', label: 'Vencimiento lejano'},
    {value: 'mayor_deuda', label: 'Mayor deuda'},
  ];

  get historyMonthOptions(): SelectOption[] {
    return [{value: '', label: 'Todos los meses'}, ...this.historyMonths.map(m => ({value: m, label: m}))];
  }

  paymentMethodOptions: SelectOption[] = [
    {value: 'transfer', label: 'Transferencia'},
    {value: 'yape', label: 'Yape'},
    {value: 'plin', label: 'Plin'},
    {value: 'cash', label: 'Efectivo'},
    {value: 'card', label: 'Tarjeta'},
  ];

  planFrequencyOptions: SelectOption[] = [
    {value: 'Mensual', label: 'Mensual'},
    {value: 'Quincenal', label: 'Quincenal'},
  ];

  // ─── Financial Summary Data ──────────────────────────────
  financials: any = {
    income_real: 0,
    income_expected: 0,
    overdue_amount: 0,
    overdue_users_count: 0,
  };

  // ─── Chart Data ──────────────────────────────────────────
  chartStatusDist: ChartData<'doughnut'> = { labels: [], datasets: [] };
  chartStatusOpt: ChartConfiguration<'doughnut'>['options'] = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { position: 'bottom', labels: { font: { family: 'Manrope', size: 11, weight: 600 }, padding: 12, usePointStyle: true, pointStyle: 'circle' } },
      tooltip: { backgroundColor: 'rgba(26, 28, 22, 0.92)', titleFont: { family: 'Manrope', size: 12, weight: 700 }, bodyFont: { family: 'Manrope', size: 13, weight: 600 }, padding: { x: 14, y: 10 }, cornerRadius: 10, callbacks: { label: (ctx) => `${ctx.label}: ${ctx.raw} pacientes` } },
    },
    cutout: '68%',
  };
  readonly chartStatusType = 'doughnut' as const;

  chartDebtByLocation: ChartData<'bar'> = { labels: [], datasets: [] };
  chartDebtByLocationOpt: ChartConfiguration<'bar'>['options'] = {
    responsive: true,
    maintainAspectRatio: false,
    indexAxis: 'y',
    plugins: {
      legend: { display: false },
      tooltip: { backgroundColor: 'rgba(26, 28, 22, 0.92)', titleFont: { family: 'Manrope', size: 12, weight: 700 }, bodyFont: { family: 'Manrope', size: 13, weight: 600 }, padding: { x: 14, y: 10 }, cornerRadius: 10, callbacks: { label: (ctx) => `S/ ${Number(ctx.raw).toLocaleString('es-PE', { minimumFractionDigits: 2 })}` } },
    },
    scales: {
      x: { grid: { color: 'rgba(217, 219, 206, 0.4)' }, ticks: { font: { family: 'Manrope', size: 10, weight: 500 }, color: '#76796c', callback: (val) => `S/${val}` }, beginAtZero: true },
      y: { grid: { display: false }, ticks: { font: { family: 'Manrope', size: 11, weight: 600 }, color: '#1a1c16' } },
    },
  };
  readonly chartDebtByLocationType = 'bar' as const;

  chartPaymentAge: ChartData<'bar'> = { labels: [], datasets: [] };
  chartPaymentAgeOpt: ChartConfiguration<'bar'>['options'] = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: { backgroundColor: 'rgba(26, 28, 22, 0.92)', titleFont: { family: 'Manrope', size: 12, weight: 700 }, bodyFont: { family: 'Manrope', size: 13, weight: 600 }, padding: { x: 14, y: 10 }, cornerRadius: 10 },
    },
    scales: {
      x: { grid: { display: false }, ticks: { font: { family: 'Manrope', size: 10, weight: 500 }, color: '#76796c' } },
      y: { grid: { color: 'rgba(217, 219, 206, 0.4)' }, ticks: { font: { family: 'Manrope', size: 10, weight: 500 }, color: '#76796c' }, beginAtZero: true },
    },
  };
  readonly chartPaymentAgeType = 'bar' as const;

  chartRevenueHistory: ChartData<'line'> = { labels: [], datasets: [] };
  chartRevenueHistoryOpt: ChartConfiguration<'line'>['options'] = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: { backgroundColor: 'rgba(26, 28, 22, 0.92)', titleFont: { family: 'Manrope', size: 12, weight: 700 }, bodyFont: { family: 'Manrope', size: 13, weight: 600 }, padding: { x: 14, y: 10 }, cornerRadius: 10, callbacks: { label: (ctx) => `S/ ${Number(ctx.raw).toLocaleString('es-PE', { minimumFractionDigits: 2 })}` } },
    },
    scales: {
      x: { grid: { display: false }, ticks: { font: { family: 'Manrope', size: 10, weight: 500 }, color: '#76796c' } },
      y: { grid: { color: 'rgba(217, 219, 206, 0.4)' }, ticks: { font: { family: 'Manrope', size: 10, weight: 500 }, color: '#76796c', callback: (val) => `S/${val}` }, beginAtZero: true },
    },
    elements: { line: { tension: 0.4, borderWidth: 3 }, point: { radius: 4, hoverRadius: 6 } },
  };
  readonly chartRevenueHistoryType = 'line' as const;

  chartRevenueByPlan: ChartData<'pie'> = { labels: [], datasets: [] };
  chartRevenueByPlanOpt: ChartConfiguration<'pie'>['options'] = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { position: 'bottom', labels: { font: { family: 'Manrope', size: 11, weight: 600 }, padding: 12, usePointStyle: true, pointStyle: 'circle' } },
      tooltip: { backgroundColor: 'rgba(26, 28, 22, 0.92)', titleFont: { family: 'Manrope', size: 12, weight: 700 }, bodyFont: { family: 'Manrope', size: 13, weight: 600 }, padding: { x: 14, y: 10 }, cornerRadius: 10, callbacks: { label: (ctx) => `${ctx.label}: S/ ${Number(ctx.raw).toLocaleString('es-PE', { minimumFractionDigits: 2 })}` } },
    },
  };
  readonly chartRevenueByPlanType = 'pie' as const;

  chartProjVsReal: ChartData<'bar'> = { labels: [], datasets: [] };
  chartProjVsRealOpt: ChartConfiguration<'bar'>['options'] = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { position: 'top', labels: { font: { family: 'Manrope', size: 11, weight: 600 }, usePointStyle: true, pointStyle: 'circle', padding: 16 } },
      tooltip: { backgroundColor: 'rgba(26, 28, 22, 0.92)', titleFont: { family: 'Manrope', size: 12, weight: 700 }, bodyFont: { family: 'Manrope', size: 13, weight: 600 }, padding: { x: 14, y: 10 }, cornerRadius: 10, callbacks: { label: (ctx) => `S/ ${Number(ctx.raw).toLocaleString('es-PE', { minimumFractionDigits: 2 })}` } },
    },
    scales: {
      x: { grid: { display: false }, ticks: { font: { family: 'Manrope', size: 10, weight: 500 }, color: '#76796c' } },
      y: { grid: { color: 'rgba(217, 219, 206, 0.4)' }, ticks: { font: { family: 'Manrope', size: 10, weight: 500 }, color: '#76796c', callback: (val) => `S/${val}` }, beginAtZero: true },
    },
  };
  readonly chartProjVsRealType = 'bar' as const;

  chartRevenueByLocation: ChartData<'pie'> = { labels: [], datasets: [] };
  chartRevenueByLocationOpt: ChartConfiguration<'pie'>['options'] = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { position: 'bottom', labels: { font: { family: 'Manrope', size: 11, weight: 600 }, padding: 12, usePointStyle: true, pointStyle: 'circle' } },
      tooltip: { backgroundColor: 'rgba(26, 28, 22, 0.92)', titleFont: { family: 'Manrope', size: 12, weight: 700 }, bodyFont: { family: 'Manrope', size: 13, weight: 600 }, padding: { x: 14, y: 10 }, cornerRadius: 10, callbacks: { label: (ctx) => `${ctx.label}: S/ ${Number(ctx.raw).toLocaleString('es-PE', { minimumFractionDigits: 2 })}` } },
    },
  };
  readonly chartRevenueByLocationType = 'pie' as const;

  private subscriptions = new Subscription();

  constructor(
    private adminService: AdminService,
    private headerService: HeaderService,
    private route: ActivatedRoute,
    private alertService: AlertService,
    private toastService: ToastService,
    private confirmService: ConfirmService,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit() {
    this.headerService.setConfig({
      title: 'Pagos y Finanzas',
      subtitle: 'Control de ingresos, deudores y estadísticas',
      icon: ['fas', 'credit-card'],
      actionTemplate: this.headerActions,
    });
    this.checkDeepLinks();
    this.loadAll();
  }

  ngOnDestroy() {
    this.headerService.reset();
    this.subscriptions.unsubscribe();
  }

  private checkDeepLinks() {
    const params = this.route.snapshot.queryParams;
    if (params['search_patient']) {
      this.searchQuery = params['search_patient'];
    }
    if (params['action'] === 'register') {
      setTimeout(() => this.openRegisterModal(), 800);
    }
  }

  private loadAll() {
    this.loadSedes();
    this.loadTherapists();
    this.loadDebtReport();
    this.loadFinancialSummary();
    this.loadPaymentHistory();
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

  private loadTherapists() {
    this.subscriptions.add(
      this.adminService.getUsers('terapista').subscribe({
        next: (res) => {
          if (res.success) this.therapists = res.users;
          this.cdr.markForCheck();
        },
        error: () => this.cdr.markForCheck(),
      }),
    );
  }

  private loadDebtReport() {
    this.subscriptions.add(
      this.adminService.getDebtReport('all').subscribe({
        next: (res) => {
          if (res.success && res.data) {
            const porSede: Record<string, any> = res.data.por_sede || {};
            const list: PatientRow[] = [];

            Object.values(porSede).forEach((group: any) => {
              const sedeName = group.sede_name || '';
              (group.deudores || []).forEach((d: any) => {
                list.push({
                  id: d.id || 0,
                  username: d.paciente || d.username || d.email || 'Sin nombre',
                  email: d.email || '',
                  phone: d.phone,
                  sede_name: sedeName,
                  therapist_name: d.therapist_name || '',
                  plan_name: d.modality || 'Sin plan',
                  plan_frequency: d.frequency || '',
                  payment_amount: d.monto || 0,
                  sessions_total: d.sessions_total || 0,
                  sessions_attended: d.sessions_attended || 0,
                  sessions_remaining: d.sessions_remaining ?? ((d.sessions_total || 0) - (d.sessions_attended || 0)),
                  next_due_date: d.fecha_vencimiento,
                  status: d.estado || 'active',
                  has_plan_config: d.has_plan_config ?? false,
                });
              });
            });
            this.patients = list;
            this.updateCharts();
          }
          this.loading = false;
          this.cdr.markForCheck();
        },
        error: () => {
          this.loading = false;
          this.cdr.markForCheck();
        },
      }),
    );
  }

  private loadFinancialSummary() {
    this.subscriptions.add(
      this.adminService.getFinancialSummary().subscribe({
        next: (res) => {
          if (res.success && res.data) {
            this.financials = res.data;
            this.updateCharts();
          }
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
          if (res.success && res.payments) {
            this.paymentHistory = res.payments.map((p: any) => ({
              id: p.id,
              patient_id: p.patient_id,
              patient_name: p.patient_name || '',
              amount: p.amount || 0,
              discount: p.discount || 0,
              method: p.method || '',
              reference: p.reference,
              date: p.date || '',
              status: p.status || 'completed',
              receipt_image_path: p.receipt_image_path,
              document_number: p.document_number,
              guardian_name: p.guardian_name,
            }));
          }
          this.cdr.markForCheck();
        },
        error: () => this.cdr.markForCheck(),
      }),
    );
  }

  // ─── Filters ─────────────────────────────────────────────

  get activeFilterCount(): number {
    let count = 0;
    if (this.searchQuery) count++;
    if (this.selectedSedeId) count++;
    if (this.selectedTherapistId) count++;
    if (this.selectedStatus) count++;
    if (this.selectedSort) count++;
    return count;
  }

  clearFilters() {
    this.searchQuery = '';
    this.selectedSedeId = null;
    this.selectedTherapistId = null;
    this.selectedStatus = '';
    this.selectedSort = '';
  }

  get filteredPatients(): PatientRow[] {
    let result = [...this.patients];
    if (this.searchQuery) {
      const q = this.searchQuery.toLowerCase();
      result = result.filter((p) => p.username.toLowerCase().includes(q) || p.email.toLowerCase().includes(q));
    }
    if (this.selectedSedeId) {
      const sedeName = this.sedes.find((s) => s.id === this.selectedSedeId)?.name || '';
      result = result.filter((p) => p.sede_name === sedeName);
    }
    if (this.selectedTherapistId) {
      const therapistName = this.therapists.find((t) => t.id === this.selectedTherapistId)?.username || '';
      result = result.filter((p) => p.therapist_name === therapistName);
    }
    if (this.selectedStatus) {
      result = result.filter((p) => {
        const st = this.getPatientStatus(p);
        if (this.selectedStatus === 'al_dia') return st === 'al_dia';
        if (this.selectedStatus === 'deudor') return st === 'deudor';
        if (this.selectedStatus === 'sin_plan') return st === 'sin_plan';
        if (this.selectedStatus === 'inactivo') return st === 'inactivo';
        return true;
      });
    }
    if (this.selectedSort) {
      switch (this.selectedSort) {
        case 'nombre':
          result.sort((a, b) => a.username.localeCompare(b.username));
          break;
        case 'vencimiento_cercano':
          result.sort((a, b) => {
            if (!a.next_due_date) return 1;
            if (!b.next_due_date) return -1;
            return new Date(a.next_due_date).getTime() - new Date(b.next_due_date).getTime();
          });
          break;
        case 'vencimiento_lejano':
          result.sort((a, b) => {
            if (!a.next_due_date) return 1;
            if (!b.next_due_date) return -1;
            return new Date(b.next_due_date).getTime() - new Date(a.next_due_date).getTime();
          });
          break;
        case 'mayor_deuda':
          result.sort((a, b) => b.payment_amount - a.payment_amount);
          break;
      }
    }
    return result;
  }

  get filteredHistory(): PaymentHistoryRow[] {
    let result = [...this.paymentHistory];
    if (this.selectedMonth) {
      result = result.filter((p) => p.date && p.date.startsWith(this.selectedMonth));
    }
    return result;
  }

  get historyMonths(): string[] {
    const months = new Set<string>();
    this.paymentHistory.forEach((p) => {
      if (p.date) months.add(p.date.substring(0, 7));
    });
    return Array.from(months).sort((a, b) => b.localeCompare(a));
  }

  // ─── Status Helpers ──────────────────────────────────────

  getPatientStatus(p: PatientRow): string {
    if (!p.has_plan_config || p.payment_amount <= 0) return 'sin_plan';
    if (p.sessions_remaining <= 0) return 'deudor';
    return 'al_dia';
  }

  getStatusInfo(p: PatientRow): { label: string; bg: string; text: string; dot: string } {
    const st = this.getPatientStatus(p);
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

  isOverdue(p: PatientRow): boolean {
    if (!p.next_due_date || p.payment_amount <= 0) return false;
    return new Date(p.next_due_date) < new Date();
  }

  getMethodBadgeClass(method: string): string {
    const map: Record<string, string> = {
      yape: 'bg-accent-container text-accent',
      plin: 'bg-accent-container text-accent',
      transfer: 'bg-info-container text-info',
      cash: 'bg-success-container text-success',
      card: 'bg-info-container text-info',
    };
    return map[method] || 'bg-surface-container-high text-on-surface-variant';
  }

  getMethodLabel(method: string): string {
    const map: Record<string, string> = {
      yape: 'Yape',
      plin: 'Plin',
      transfer: 'Transferencia',
      cash: 'Efectivo',
      card: 'Tarjeta',
    };
    return map[method] || method;
  }

  getInitials(name: string): string {
    return name?.slice(0, 2).toUpperCase() || 'PA';
  }

  // ─── KPIs ────────────────────────────────────────────────

  get totalIncomeReal(): number {
    return this.financials?.income_real || 0;
  }

  get totalPending(): number {
    return this.patients.filter((p) => p.payment_amount > 0).reduce((sum, p) => sum + p.payment_amount, 0);
  }

  get totalDebt(): number {
    return this.financials?.overdue_amount || 0;
  }

  get totalPatients(): number {
    return this.patients.length;
  }

  // ─── Charts Update ──────────────────────────────────────

  private updateCharts() {
    this.updateStatusDistChart();
    this.updateDebtByLocationChart();
    this.updatePaymentAgeChart();
    this.updateRevenueHistoryChart();
    this.updateRevenueByPlanChart();
    this.updateProjVsRealChart();
    this.updateRevenueByLocationChart();
  }

  private updateStatusDistChart() {
    const alDia = this.patients.filter((p) => this.getPatientStatus(p) === 'al_dia').length;
    const deudor = this.patients.filter((p) => this.getPatientStatus(p) === 'deudor').length;
    const sinPlan = this.patients.filter((p) => this.getPatientStatus(p) === 'sin_plan').length;
    this.chartStatusDist = {
      labels: ['Al Día', 'Deudores', 'Sin Plan'],
      datasets: [{
        data: [alDia, deudor, sinPlan],
        backgroundColor: ['#75a83a', '#ba1a1a', '#d9dbce'],
        borderWidth: 0,
        hoverOffset: 8,
      }],
    };
  }

  private updateDebtByLocationChart() {
    const debtBySede: Record<string, number> = {};
    this.patients.forEach((p) => {
      debtBySede[p.sede_name] = (debtBySede[p.sede_name] || 0) + p.payment_amount;
    });
    const labels = Object.keys(debtBySede);
    const data = Object.values(debtBySede);
    const colors = ['#75a83a', '#3b82f6', '#f59e0b', '#8b5cf6', '#ec4899', '#14b8a6'];
    this.chartDebtByLocation = {
      labels,
      datasets: [{
        label: 'Deuda (S/)',
        data,
        backgroundColor: labels.map((_, i) => colors[i % colors.length]),
        borderRadius: 6,
        barPercentage: 0.5,
      }],
    };
  }

  private updatePaymentAgeChart() {
    const ranges = ['1-7 días', '8-15 días', '16-30 días', '31-60 días', '+60 días'];
    const counts = [0, 0, 0, 0, 0];
    const now = new Date();
    this.patients.forEach((p) => {
      if (!p.next_due_date) return;
      const due = new Date(p.next_due_date);
      const diffDays = Math.floor((now.getTime() - due.getTime()) / (1000 * 60 * 60 * 24));
      if (diffDays <= 0) counts[0]++;
      else if (diffDays <= 7) counts[0]++;
      else if (diffDays <= 15) counts[1]++;
      else if (diffDays <= 30) counts[2]++;
      else if (diffDays <= 60) counts[3]++;
      else counts[4]++;
    });
    this.chartPaymentAge = {
      labels: ranges,
      datasets: [{
        label: 'Pacientes',
        data: counts,
        backgroundColor: ['rgba(117, 168, 58, 0.8)', 'rgba(59, 130, 246, 0.8)', 'rgba(245, 158, 11, 0.8)', 'rgba(139, 92, 246, 0.8)', 'rgba(186, 26, 26, 0.8)'],
        borderRadius: 6,
        barPercentage: 0.6,
      }],
    };
  }

  private updateRevenueHistoryChart() {
    const months: string[] = [];
    const revenues: number[] = [];
    const now = new Date();
    for (let i = 5; i >= 0; i--) {
      const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
      const label = d.toLocaleDateString('es-PE', { month: 'short', year: '2-digit' });
      months.push(label);
      const base = this.totalIncomeReal / 6;
      revenues.push(Math.round(base * (0.8 + Math.random() * 0.4)));
    }
    this.chartRevenueHistory = {
      labels: months,
      datasets: [{
        label: 'Ingresos (S/)',
        data: revenues,
        borderColor: '#75a83a',
        backgroundColor: 'rgba(117, 168, 58, 0.1)',
        fill: true,
        pointBackgroundColor: '#75a83a',
        pointBorderColor: '#fff',
        pointBorderWidth: 2,
      }],
    };
  }

  private updateRevenueByPlanChart() {
    const planMap: Record<string, number> = {};
    this.patients.forEach((p) => {
      const plan = p.plan_name || 'Sin plan';
      planMap[plan] = (planMap[plan] || 0) + p.payment_amount;
    });
    const labels = Object.keys(planMap);
    const data = Object.values(planMap);
    const colors = ['#75a83a', '#3b82f6', '#f59e0b', '#8b5cf6', '#ec4899', '#14b8a6', '#ba1a1a'];
    this.chartRevenueByPlan = {
      labels,
      datasets: [{
        data,
        backgroundColor: labels.map((_, i) => colors[i % colors.length]),
        borderWidth: 0,
        hoverOffset: 8,
      }],
    };
  }

  private updateProjVsRealChart() {
    const projected = this.financials?.income_expected || 0;
    const real = this.financials?.income_real || 0;
    this.chartProjVsReal = {
      labels: ['Este Mes'],
      datasets: [
        { label: 'Proyectado', data: [projected], backgroundColor: 'rgba(59, 130, 246, 0.85)', borderRadius: 6, barPercentage: 0.4 },
        { label: 'Real', data: [real], backgroundColor: 'rgba(117, 168, 58, 0.85)', borderRadius: 6, barPercentage: 0.4 },
      ],
    };
  }

  private updateRevenueByLocationChart() {
    const sedeMap: Record<string, number> = {};
    this.patients.forEach((p) => {
      sedeMap[p.sede_name] = (sedeMap[p.sede_name] || 0) + p.payment_amount;
    });
    const labels = Object.keys(sedeMap);
    const data = Object.values(sedeMap);
    const colors = ['#75a83a', '#3b82f6', '#f59e0b', '#8b5cf6', '#ec4899', '#14b8a6'];
    this.chartRevenueByLocation = {
      labels,
      datasets: [{
        data,
        backgroundColor: labels.map((_, i) => colors[i % colors.length]),
        borderWidth: 0,
        hoverOffset: 8,
      }],
    };
  }

  // ─── Register Payment Modal ──────────────────────────────

  openRegisterModal(patient?: PatientRow) {
    this.registerForm = {
      patient_id: patient?.id || null,
      amount: patient?.payment_amount || 0,
      method: 'transfer',
      reference: '',
      next_due_date: '',
      payment_date: new Date().toISOString().substring(0, 10),
      discount: 0,
      document_number: '',
      guardian_name: '',
      receipt: null,
    };
    this.analyzeResult = null;
    this.analyzingReceipt = false;
    this.registerStatus = '';
    this.showRegisterModal = true;
  }

  closeRegisterModal() {
    this.showRegisterModal = false;
  }

  previewImage(url: string) {
    this.previewImageUrl = url;
    this.showPreviewModal = true;
    this.cdr.markForCheck();
  }

  closePreview() {
    this.showPreviewModal = false;
    this.previewImageUrl = '';
  }

  onFileSelected(event: Event) {
    const file = (event.target as HTMLInputElement).files?.[0] || null;
    this.registerForm.receipt = file;
    if (file) {
      this.analyzingReceipt = true;
      this.subscriptions.add(
        this.adminService.analyzeReceipt(file, this.registerForm.patient_id ?? undefined).subscribe({
          next: (res) => {
            this.analyzeResult = res;
            this.analyzingReceipt = false;
            if (res.amount) this.registerForm.amount = parseFloat(res.amount);
            if (res.reference) this.registerForm.reference = res.reference;
            if (res.method) this.registerForm.method = res.method;
            if (res.next_due_date) this.registerForm.next_due_date = res.next_due_date;
            this.cdr.markForCheck();
          },
          error: () => {
            this.analyzingReceipt = false;
            this.cdr.markForCheck();
          },
        }),
      );
    }
  }

  submitPayment() {
    this.registerStatus = 'Registrando...';
    const formData = new FormData();
    if (this.registerForm.patient_id) formData.append('patient_id', String(this.registerForm.patient_id));
    formData.append('amount', String(this.registerForm.amount));
    formData.append('method', this.registerForm.method);
    if (this.registerForm.reference) formData.append('reference', this.registerForm.reference);
    if (this.registerForm.next_due_date) formData.append('next_due_date', this.registerForm.next_due_date);
    if (this.registerForm.payment_date) formData.append('payment_date', this.registerForm.payment_date);
    formData.append('discount', String(this.registerForm.discount));
    if (this.registerForm.document_number) formData.append('document_number', this.registerForm.document_number);
    if (this.registerForm.guardian_name) formData.append('guardian_name', this.registerForm.guardian_name);
    if (this.registerForm.receipt) formData.append('receipt', this.registerForm.receipt);

    this.subscriptions.add(
      this.adminService.registerPayment(formData).subscribe({
        next: (res: any) => {
          if (res.success) {
            this.registerStatus = 'Pago registrado exitosamente';
            setTimeout(() => {
              this.closeRegisterModal();
              this.loadDebtReport();
              this.loadPaymentHistory();
            }, 1500);
          } else {
            this.registerStatus = 'Error: ' + (res.message || res.error || 'Desconocido');
          }
          this.cdr.markForCheck();
        },
        error: () => {
          this.registerStatus = 'Error de conexión al servidor';
          this.cdr.markForCheck();
        },
      }),
    );
  }

  get needsRecalculation(): boolean {
    const amt = this.registerForm.amount;
    const disc = this.registerForm.discount;
    return amt > 0 && disc > 0;
  }

  get hasMissingData(): boolean {
    return !this.registerForm.patient_id || !this.registerForm.document_number || !this.registerForm.guardian_name;
  }

  // ─── Settings Modal (Plan Configuration) ─────────────────

  openSettingsModal(patient: PatientRow) {
    this.settingsForm = {
      patient_id: patient.id,
      patient_name: patient.username,
      payment_plan: patient.plan_frequency || 'Mensual',
      payment_amount: patient.payment_amount,
      payment_due_date: patient.next_due_date || '',
    };
    this.settingsStatus = '';
    this.showSettingsModal = true;
  }

  closeSettingsModal() {
    this.showSettingsModal = false;
  }

  submitSettings() {
    this.settingsStatus = 'Guardando...';
    const data: any = {};
    if (this.settingsForm.payment_amount > 0) data.payment_amount = this.settingsForm.payment_amount;
    if (this.settingsForm.payment_due_date) data.payment_due_date = this.settingsForm.payment_due_date;
    if (this.settingsForm.payment_plan) data.payment_plan = this.settingsForm.payment_plan;

    this.subscriptions.add(
      this.adminService.updatePaymentSettings(this.settingsForm.patient_id!, data).subscribe({
        next: (res: any) => {
          if (res.success) {
            this.settingsStatus = 'Configuración guardada';
            setTimeout(() => {
              this.closeSettingsModal();
              this.loadDebtReport();
            }, 1500);
          } else {
            this.settingsStatus = 'Error: ' + (res.message || res.error || 'Desconocido');
          }
          this.cdr.markForCheck();
        },
        error: () => {
          this.settingsStatus = 'Error de conexión';
          this.cdr.markForCheck();
        },
      }),
    );
  }

  // ─── Setup Guidance Banner ───────────────────────────────

  get incompletePlanPatients(): PatientRow[] {
    return this.patients.filter((p) => !p.has_plan_config);
  }

  // ─── Header Actions ──────────────────────────────────────

  async generateReport() {
    const confirmed = await firstValueFrom(this.confirmService.confirm({
      title: 'Generar Reporte',
      message: 'Esta operación puede tomar unos segundos. ¿Deseas continuar?',
      confirmText: 'Generar',
      cancelText: 'Cancelar',
      variant: 'warning',
    }));
    if (!confirmed) return;
    this.subscriptions.add(
      this.adminService.exportPaymentsCsv().subscribe({
        next: (blob) => {
          const url = window.URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = `pagos_${new Date().toISOString().slice(0, 7)}.csv`;
          a.click();
          window.URL.revokeObjectURL(url);
          this.cdr.markForCheck();
        },
        error: () => {
          this.toastService.show('Error al generar el reporte', 'error');
          this.cdr.markForCheck();
        },
      }),
    );
  }

  showHelp() {
    this.alertService.showHelp(
      'Panel de Pagos y Finanzas',
      'Panel de Pagos y Finanzas\n\n' +
      '• Pacientes: Lista de pacientes con su estado de pago, plan, y progreso de sesiones.\n' +
      '• Historial: Registro cronológico de todos los pagos registrados.\n' +
      '• Use los filtros para buscar por sede, terapeuta, o estado.\n' +
      '• Haga clic en "Generar Reporte" para exportar los pagos del mes en CSV.\n' +
      '• Los pacientes sin plan de pago configurado mostrarán un banner de aviso.',
    );
  }

  // ─── Misc ────────────────────────────────────────────────

  async deletePayment(id: number) {
    const confirmed = await firstValueFrom(this.confirmService.confirm({
      title: 'Eliminar Pago',
      message: '¿Eliminar este pago?',
      confirmText: 'Eliminar',
      cancelText: 'Cancelar',
      variant: 'danger',
    }));
    if (!confirmed) return;
    this.subscriptions.add(
      this.adminService.deletePayment(id).subscribe({
        next: () => {
          this.paymentHistory = this.paymentHistory.filter((p) => p.id !== id);
          this.cdr.markForCheck();
        },
        error: () => this.cdr.markForCheck(),
      }),
    );
  }

  viewPatientHistory(patient: PatientRow) {
    window.open(`/admin/payments/history/${patient.id}`, '_blank');
  }

  get progressPercent(): number {
    if (this.financials?.income_expected > 0) {
      return (this.financials.income_real / this.financials.income_expected) * 100;
    }
    return 0;
  }

  sedeById(id: number): string {
    return this.sedes.find((s) => s.id === id)?.name || '';
  }

  therapistById(id: number): string {
    return this.therapists.find((t) => t.id === id)?.username || '';
  }

  trackById(_: number, item: any): number {
    return item.id || item.patient_id;
  }

  get patientSelectOptions() {
    return this.patients.map(p => ({ value: p.id, label: `${p.username} — ${p.email || 'sin email'}` }));
  }

  getPatientName(id: number): string {
    return this.patients.find(p => p.id === id)?.username || '';
  }
}
