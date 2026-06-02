import { Component, OnInit, OnDestroy, ViewChild, TemplateRef, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { Subscription } from 'rxjs';
import { ActivatedRoute } from '@angular/router';
import { AdminService } from '../../../../core/services/admin.service';
import { HeaderService } from '../../../../core/services/header.service';
import { AuthService } from '../../../../core/services/auth.service';
import { AlertService } from '../../../../core/services/alert.service';
import { Sede } from '../../../../core/models/sede';
import { Expense, TherapistFinancial } from '../../../../core/models/expense';
import { User } from '../../../../core/models/user';
import { Chart, registerables } from 'chart.js';
import type { ChartConfiguration, ChartData } from 'chart.js';
import { fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter } from '../../../../core/animations';
import { firstValueFrom, forkJoin } from 'rxjs';
import { ConfirmService } from '../../../../core/services/confirm.service';
import { SelectOption } from '../../../../shared/components/select/select';

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
  selector: 'app-finanzas',
  standalone: false,
  templateUrl: './finanzas.html',
  styleUrl: './finanzas.scss',
  animations: [fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Finanzas implements OnInit, OnDestroy {
  readonly Math = Math;
  isSupervisor = false;
  @ViewChild('headerActions', { static: true }) headerActions!: TemplateRef<any>;

  activeTab: 'resumen' | 'pagos' | 'yape' | 'gastos' = 'resumen';

  switchTab(tab: 'resumen' | 'pagos' | 'yape' | 'gastos') {
    this.activeTab = tab;
  }

  summaryTotalDeuda = 0;
  summaryIngresos = 0;
  summaryGastos = 0;

  patients: PatientRow[] = [];
  paymentHistory: PaymentHistoryRow[] = [];
  sedes: Sede[] = [];
  therapistsList: Therapist[] = [];
  paymentsLoading = true;
  historyLoading = true;
  pagosTab: 'pacientes' | 'historial' = 'pacientes';

  searchQuery = '';
  selectedSedeId: number | null = null;
  selectedTherapistId: number | null = null;
  selectedStatus: string = '';
  selectedSort: string = '';
  historyMonth: string = '';

  get sedeFilterOptions(): SelectOption[] {
    return [{value: null, label: 'Todas las Sedes'}, ...this.sedes.map(s => ({value: s.id, label: s.name}))];
  }

  get therapistFilterOptions(): SelectOption[] {
    return [{value: null, label: 'Todos los Terapeutas'}, ...this.therapistsList.map(t => ({value: t.id, label: t.username}))];
  }

  get historyMonthOptions(): SelectOption[] {
    return [{value: '', label: 'Todos los meses'}, ...this.historyMonths.map(m => ({value: m, label: m}))];
  }

  statusFilterOptions: SelectOption[] = [
    {value: '', label: 'Todos los Estados'},
    {value: 'al_dia', label: 'Al Día'},
    {value: 'deudor', label: 'Deudores'},
    {value: 'sin_plan', label: 'Sin Plan'},
    {value: 'inactivo', label: 'Inactivos'},
  ];

  sortOptions: SelectOption[] = [
    {value: '', label: 'Ordenar por...'},
    {value: 'nombre', label: 'Nombre'},
    {value: 'vencimiento_cercano', label: 'Vencimiento cercano'},
    {value: 'vencimiento_lejano', label: 'Vencimiento lejano'},
    {value: 'mayor_deuda', label: 'Mayor deuda'},
  ];

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

  expenseCategoryOptions: SelectOption[] = [
    {value: 'therapist_payment', label: 'Pago a Terapeuta'},
    {value: 'operational', label: 'Gasto Operativo'},
    {value: 'bonus', label: 'Bonificación'},
    {value: 'other', label: 'Otro'},
  ];

  expenseMethodOptions: SelectOption[] = [
    {value: 'transfer', label: 'Transferencia Bancaria'},
    {value: 'yape_plin', label: 'Yape / Plin'},
    {value: 'cash', label: 'Efectivo'},
    {value: 'other', label: 'Otro'},
  ];

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

  showSettingsModal = false;
  settingsForm = {
    patient_id: null as number | null,
    patient_name: '',
    payment_plan: 'Mensual',
    payment_amount: 0,
    payment_due_date: '',
  };
  settingsStatus = '';

  financials: any = {
    income_real: 0,
    income_expected: 0,
    overdue_amount: 0,
    overdue_users_count: 0,
  };

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

  dashIncomeExpenseChart: ChartData<'line'> = { labels: [], datasets: [] };
  dashIncomeExpenseOpt: ChartConfiguration<'line'>['options'] = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: 'rgba(26, 28, 22, 0.92)',
        titleFont: { family: 'Manrope', size: 12, weight: 700 },
        bodyFont: { family: 'Manrope', size: 13, weight: 600 },
        padding: { x: 14, y: 10 },
        cornerRadius: 10,
        callbacks: { label: (ctx) => `S/ ${Number(ctx.raw).toLocaleString('es-PE', { minimumFractionDigits: 2 })}` }
      },
    },
    scales: {
      x: { grid: { display: false }, ticks: { font: { family: 'Manrope', size: 10, weight: 500 }, color: '#76796c' } },
      y: { grid: { color: 'rgba(217, 219, 206, 0.4)' }, ticks: { font: { family: 'Manrope', size: 10, weight: 500 }, color: '#76796c', callback: (val) => `S/${val}` }, beginAtZero: true },
    },
    elements: { line: { tension: 0.4, borderWidth: 3 }, point: { radius: 4, hoverRadius: 6 } },
  };
  readonly dashIncomeExpenseType = 'line' as const;

  dashExpenseCategoryChart: ChartData<'doughnut'> = { labels: [], datasets: [] };
  dashExpenseCategoryOpt: ChartConfiguration<'doughnut'>['options'] = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { position: 'bottom', labels: { font: { family: 'Manrope', size: 11, weight: 600 }, padding: 12, usePointStyle: true, pointStyle: 'circle' } },
      tooltip: {
        backgroundColor: 'rgba(26, 28, 22, 0.92)',
        titleFont: { family: 'Manrope', size: 12, weight: 700 },
        bodyFont: { family: 'Manrope', size: 13, weight: 600 },
        padding: { x: 14, y: 10 },
        cornerRadius: 10,
        callbacks: { label: (ctx) => `${ctx.label}: S/ ${Number(ctx.raw).toLocaleString('es-PE', { minimumFractionDigits: 2 })}` }
      },
    },
    cutout: '68%',
  };
  readonly dashExpenseCategoryType = 'doughnut' as const;

  therapistFinancials: TherapistFinancial[] = [];
  recentExpenses: Expense[] = [];
  expenseTherapists: User[] = [];
  expensesLoading = true;
  submitting = false;

  showExpenseModal = false;
  expenseModalMode: 'therapist_payment' | 'operational' = 'operational';
  expenseForm = {
    category: 'operational' as string,
    therapist_id: null as number | null,
    therapist_name: '',
    amount: 0,
    method: 'transfer' as string,
    date: '',
    description: '',
    receipt: null as File | null,
  };

  private subscriptions = new Subscription();

  constructor(
    private adminService: AdminService,
    private headerService: HeaderService,
    private route: ActivatedRoute,
    private alertService: AlertService,
    private confirmService: ConfirmService,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit() {
    this.authService.currentUser$.subscribe(u => {
      this.isSupervisor = u?.role === 'supervisor';
      this.cdr.markForCheck();
    });
    this.headerService.setConfig({
      title: 'Finanzas',
      subtitle: 'Gestión integrada de finanzas del centro',
      icon: ['fas', 'university'],
      actionTemplate: this.headerActions,
    });
    this.loadSummaryData();
    this.checkDeepLinks();
    this.loadPaymentsData();
    this.loadExpensesData();
  }

  ngOnDestroy() {
    this.headerService.reset();
    this.subscriptions.unsubscribe();
  }


  private loadSummaryData() {
    this.subscriptions.add(
      this.adminService.getDebtReport('all').subscribe({
        next: (res) => {
          if (res.success && res.data) {
            const porSede: Record<string, any> = res.data.por_sede || {};
            this.summaryTotalDeuda = Object.values(porSede).reduce((sum: number, g: any) => {
              return sum + ((g.deudores || []).reduce((s: number, d: any) => s + (d.monto || 0), 0));
            }, 0);
          }
          this.genDashboardCharts();
          this.cdr.markForCheck();
        },
        error: () => this.cdr.markForCheck(),
      }),
    );

    this.subscriptions.add(
      this.adminService.getFinancialSummary().subscribe({
        next: (res) => {
          if (res.success && res.data) {
            this.summaryIngresos = res.data.income_real || 0;
          }
          this.genDashboardCharts();
          this.cdr.markForCheck();
        },
        error: () => this.cdr.markForCheck(),
      }),
    );

    this.subscriptions.add(
      this.adminService.getExpenses().subscribe({
        next: (res) => {
          if (res.success && res.data) {
            this.summaryGastos = res.data.reduce((sum: number, e: Expense) => sum + e.amount, 0);
          }
          this.genDashboardCharts();
          this.cdr.markForCheck();
        },
        error: () => this.cdr.markForCheck(),
      }),
    );
  }

  private getMonthlyIncome(): Map<string, number> {
    const map = new Map<string, number>();
    this.paymentHistory.forEach((p) => {
      if (p.date) {
        const key = p.date.substring(0, 7);
        map.set(key, (map.get(key) || 0) + (p.amount - (p.discount || 0)));
      }
    });
    return map;
  }

  private getMonthlyExpenses(): Map<string, number> {
    const map = new Map<string, number>();
    this.recentExpenses.forEach((e) => {
      if (e.date) {
        const key = e.date.substring(0, 7);
        map.set(key, (map.get(key) || 0) + e.amount);
      }
    });
    return map;
  }

  private getLast6MonthsKeys(): string[] {
    const keys: string[] = [];
    const now = new Date();
    for (let i = 5; i >= 0; i--) {
      const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
      keys.push(`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`);
    }
    return keys;
  }

  private formatMonthLabel(key: string): string {
    const [y, m] = key.split('-');
    return new Date(+y, +m - 1, 1).toLocaleDateString('es-PE', { month: 'short', year: '2-digit' });
  }

  private genDashboardCharts() {
    const incomeByMonth = this.getMonthlyIncome();
    const expenseByMonth = this.getMonthlyExpenses();
    const monthKeys = this.getLast6MonthsKeys();
    const revenues = monthKeys.map((k) => incomeByMonth.get(k) || 0);
    const expValues = monthKeys.map((k) => expenseByMonth.get(k) || 0);
    const labels = monthKeys.map((k) => this.formatMonthLabel(k));

    this.dashIncomeExpenseChart = {
      labels,
      datasets: [
        {
          label: 'Ingresos',
          data: revenues,
          borderColor: '#75a83a',
          backgroundColor: 'rgba(117, 168, 58, 0.1)',
          fill: true,
          pointBackgroundColor: '#75a83a',
          pointBorderColor: '#fff',
          pointBorderWidth: 2,
        },
        {
          label: 'Gastos',
          data: expValues,
          borderColor: '#ba1a1a',
          backgroundColor: 'rgba(186, 26, 26, 0.08)',
          fill: true,
          pointBackgroundColor: '#ba1a1a',
          pointBorderColor: '#fff',
          pointBorderWidth: 2,
        },
      ],
    };

    const catMap: Record<string, number> = {};
    this.recentExpenses.forEach((e) => {
      const cat = e.category || 'Otros';
      catMap[cat] = (catMap[cat] || 0) + e.amount;
    });
    if (Object.keys(catMap).length === 0) catMap['Sin datos'] = 0;
    const catLabels = Object.keys(catMap);
    const catData = Object.values(catMap);
    const catColors: Record<string, string> = {
      therapist_payment: '#75a83a',
      operational: '#3b82f6',
      bonus: '#f59e0b',
      other: '#8b5cf6',
    };
    this.dashExpenseCategoryChart = {
      labels: catLabels.map((k) => this.getCategoryLabel(k)),
      datasets: [{
        data: catData,
        backgroundColor: catLabels.map((k) => catColors[k] || '#8b5cf6'),
        borderWidth: 0,
        hoverOffset: 8,
      }],
    };
  }

  private getCategoryLabel(key: string): string {
    const map: Record<string, string> = {
      therapist_payment: 'Pago Terapeutas',
      operational: 'Gastos Operativos',
      bonus: 'Bonificaciones',
      other: 'Otros',
    };
    return map[key] || key;
  }

  get summaryBalance(): number {
    return this.summaryIngresos - this.summaryGastos;
  }

  get dashCollectionRate(): number {
    if (this.financials?.income_expected > 0) {
      return Math.min(100, (this.financials.income_real / this.financials.income_expected) * 100);
    }
    return 0;
  }

  get dashRecentTransactions(): any[] {
    return this.paymentHistory.slice(0, 10);
  }

  get dashExpenseStats() {
    const total = this.recentExpenses.reduce((sum, e) => sum + e.amount, 0);
    const therapistPayments = this.recentExpenses
      .filter((e) => e.category === 'therapist_payment')
      .reduce((sum, e) => sum + e.amount, 0);
    const operational = this.recentExpenses
      .filter((e) => e.category === 'operational')
      .reduce((sum, e) => sum + e.amount, 0);
    return { total, therapistPayments, operational, other: total - therapistPayments - operational };
  }


  getWhatsAppLink(phone: string | undefined, name: string, amount: number): string | null {
    if (!phone) return null;
    const clean = phone.replace(/\D/g, '');
    const msg = encodeURIComponent(`Hola ${name}, te saludamos de Moscowle. Recordarte que el pago de tu mensualidad (S/ ${amount}) está pendiente. ¡Gracias!`);
    return `https://wa.me/51${clean}?text=${msg}`;
  }

  getInitials(name: string): string {
    return name?.slice(0, 2).toUpperCase() || 'XX';
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

  private loadPaymentsData() {
    this.loadSedes();
    this.loadPaymentsTherapists();
    this.loadPaymentsDebtReport();
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

  private loadPaymentsTherapists() {
    this.subscriptions.add(
      this.adminService.getUsers('terapista').subscribe({
        next: (res) => {
          if (res.success) this.therapistsList = res.users;
          this.cdr.markForCheck();
        },
        error: () => this.cdr.markForCheck(),
      }),
    );
  }

  private loadPaymentsDebtReport() {
    this.paymentsLoading = true;
    this.subscriptions.add(
      forkJoin({
        patients: this.adminService.getUsers('jugador'),
        debt: this.adminService.getDebtReport('all'),
      }).subscribe({
        next: ({ patients, debt }) => {
          const porSede: Record<string, any> = debt?.data?.por_sede || {};
          const debtByName = new Map<string, any>();
          Object.values(porSede).forEach((group: any) => {
            (group.deudores || []).forEach((d: any) => {
              const key = (d.paciente || d.email || '').toLowerCase().trim();
              if (key) debtByName.set(key, d);
            });
          });

          const list: PatientRow[] = (patients.users || []).map((u: any) => {
            const nameKey = (u.username || u.email || '').toLowerCase().trim();
            const d = debtByName.get(nameKey) || {};
            return {
              id: u.id,
              username: u.username || 'Sin nombre',
              email: u.email || '',
              phone: u.phone,
              sede_name: d.sede_name || u.sede_name || '',
              therapist_name: d.therapist_name || '',
              plan_name: d.modality || u.plan_type || 'Sin plan',
              plan_frequency: d.frequency || u.payment_plan || '',
              payment_amount: d.monto || u.payment_amount || 0,
              sessions_total: u.sessions_total || 0,
              sessions_attended: u.sessions_attended || 0,
              sessions_remaining: u.sessions_remaining ?? ((u.sessions_total || 0) - (u.sessions_attended || 0)),
              next_due_date: d.fecha_vencimiento || u.payment_due_date,
              status: u.account_status || 'active',
              has_plan_config: !!(u.payment_plan || u.payment_amount),
            };
          });
          this.patients = list;
          this.updateCharts();
          this.paymentsLoading = false;
          this.cdr.markForCheck();
        },
        error: () => {
          this.paymentsLoading = false;
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
    this.historyLoading = true;
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
          this.historyLoading = false;
          this.genDashboardCharts();
          this.updateRevenueHistoryChart();
          this.cdr.markForCheck();
        },
        error: () => {
          this.historyLoading = false;
          this.cdr.markForCheck();
        },
      }),
    );
  }

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
      const therapistName = this.therapistsList.find((t) => t.id === this.selectedTherapistId)?.username || '';
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
    if (this.historyMonth) {
      result = result.filter((p) => p.date && p.date.startsWith(this.historyMonth));
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

  get yapeTransactions(): PaymentHistoryRow[] {
    return this.paymentHistory.filter((p) => p.method === 'yape' || p.method === 'plin');
  }

  get yapeTotal(): number {
    return this.yapeTransactions.reduce((sum, p) => sum + (p.amount - (p.discount || 0)), 0);
  }

  get yapeMonthlyTotal(): number {
    const currentMonth = new Date().toISOString().substring(0, 7);
    return this.yapeTransactions
      .filter((p) => p.date && p.date.startsWith(currentMonth))
      .reduce((sum, p) => sum + (p.amount - (p.discount || 0)), 0);
  }

  get yapeCount(): number {
    return this.yapeTransactions.length;
  }

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
    const incomeByMonth = this.getMonthlyIncome();
    const monthKeys = this.getLast6MonthsKeys();
    const revenues = monthKeys.map((k) => incomeByMonth.get(k) || 0);
    const labels = monthKeys.map((k) => this.formatMonthLabel(k));

    this.chartRevenueHistory = {
      labels,
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
    this.cdr.markForCheck();
  }

  closeRegisterModal() {
    this.showRegisterModal = false;
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

  submitRegisterPayment() {
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
              this.loadPaymentsDebtReport();
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
    return !this.registerForm.document_number || !this.registerForm.guardian_name;
  }

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
              this.loadPaymentsDebtReport();
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

  get incompletePlanPatients(): PatientRow[] {
    return this.patients.filter((p) => !p.has_plan_config);
  }

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
          this.alertService.show('Error al generar el reporte', 'error');
          this.cdr.markForCheck();
        },
      }),
    );
  }

  showHelp() {
    this.alertService.showHelp(
      'Panel de Finanzas',
      'Panel de Finanzas\n\n' +
      '• Dashboard: Resumen financiero del centro.\n' +
      '• Pagos: Lista de pacientes con su estado de pago, plan y progreso.\n' +
      '• Yape: Transacciones registradas vía Yape / Plin.\n' +
      '• Gastos: Pagos a personal y gastos operativos.\n' +
      '• Use los filtros para buscar por sede, terapeuta, o estado.',
    );
  }

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

  getPatientName(id: number): string {
    return this.patients.find((p) => p.id === id)?.username || '';
  }

  sedeById(id: number): string {
    return this.sedes.find((s) => s.id === id)?.name || '';
  }

  therapistById(id: number): string {
    return this.therapistsList.find((t) => t.id === id)?.username || '';
  }

  trackById(_: number, item: any): number {
    return item.id || item.patient_id;
  }


  private loadExpensesData() {
    this.expensesLoading = true;
    this.subscriptions.add(
      this.adminService.getTherapistFinancials().subscribe({
        next: (res) => {
          this.therapistFinancials = res.data;
          this.cdr.markForCheck();
        },
        error: () => this.cdr.markForCheck(),
      }),
    );
    this.subscriptions.add(
      this.adminService.getUsers('terapista').subscribe({
        next: (res) => {
          this.expenseTherapists = res.users.map((u) => ({ ...u, is_active: true } as User));
          this.cdr.markForCheck();
        },
        error: () => this.cdr.markForCheck(),
      }),
    );
    this.subscriptions.add(
      this.adminService.getExpenses().subscribe({
        next: (res) => {
          this.recentExpenses = res.data;
          this.expensesLoading = false;
          this.genDashboardCharts();
          this.cdr.markForCheck();
        },
        error: () => {
          this.expensesLoading = false;
          this.cdr.markForCheck();
        },
      }),
    );
  }

  openTherapistPaymentModal(therapist: TherapistFinancial) {
    this.expenseModalMode = 'therapist_payment';
    this.expenseForm = {
      category: 'therapist_payment',
      therapist_id: therapist.therapist.id,
      therapist_name: therapist.therapist.username,
      amount: therapist.balance > 0 ? therapist.balance : 0,
      method: 'transfer',
      date: new Date().toISOString().split('T')[0],
      description: `Pago a ${therapist.therapist.username}`,
      receipt: null,
    };
    this.showExpenseModal = true;
  }

  openOperationalModal() {
    this.expenseModalMode = 'operational';
    this.expenseForm = {
      category: 'operational',
      therapist_id: null,
      therapist_name: '',
      amount: 0,
      method: 'transfer',
      date: new Date().toISOString().split('T')[0],
      description: '',
      receipt: null,
    };
    this.showExpenseModal = true;
  }

  closeExpenseModal() {
    this.showExpenseModal = false;
  }

  onExpenseFileSelected(event: any) {
    const file = event.target.files[0];
    if (file) this.expenseForm.receipt = file;
  }

  submitExpenseForm() {
    this.submitting = true;
    const fd = new FormData();
    fd.append('category', this.expenseForm.category);
    fd.append('amount', String(this.expenseForm.amount));
    fd.append('date', this.expenseForm.date);
    fd.append('description', this.expenseForm.description);
    fd.append('method', this.expenseForm.method);
    if (this.expenseForm.therapist_id) fd.append('therapist_id', String(this.expenseForm.therapist_id));
    if (this.expenseForm.receipt) fd.append('receipt', this.expenseForm.receipt);

    this.subscriptions.add(
      this.adminService.createExpense(fd).subscribe({
        next: () => {
          this.submitting = false;
          this.closeExpenseModal();
          this.loadExpensesData();
          this.cdr.markForCheck();
        },
        error: () => {
          this.submitting = false;
          this.cdr.markForCheck();
        },
      }),
    );
  }
}
