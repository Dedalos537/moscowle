import { Component, OnInit, OnDestroy, ViewChild, TemplateRef, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { BaseChartDirective } from 'ng2-charts';
import { Subscription, firstValueFrom, forkJoin } from 'rxjs';
import { ActivatedRoute } from '@angular/router';
import { Chart, registerables } from 'chart.js';
import type { ChartConfiguration, ChartData } from 'chart.js';
import { AdminService } from '../../../../core/services/admin.service';
import { HeaderService } from '../../../../core/services/header.service';
import { AuthService } from '../../../../core/services/auth.service';
import { AlertService } from '../../../../core/services/alert.service';
import { ToastService } from '../../../../core/services/toast.service';
import { ConfirmService } from '../../../../core/services/confirm.service';
import { Sede } from '../../../../core/models/sede';
import { Expense, TherapistFinancial } from '../../../../core/models/expense';
import { User } from '../../../../core/models/user';
import { fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter } from '../../../../core/animations';
import { SelectOption } from '../../../../shared/components/select/select';
import { Button } from '../../../../shared/components/button/button';
import { Spinner } from '../../../../shared/components/spinner/spinner';
import { Select } from '../../../../shared/components/select/select';
import { Input } from '../../../../shared/components/input/input';
import { Modal } from '../../../../shared/components/modal/modal';
import { SummaryCard } from '../../../../shared/components/summary-card/summary-card';
import { Table, TableCell, TableColumn } from '../../../../shared/components/table/table';
import { PatientRow, PaymentHistoryRow, Therapist, RegisterForm, SettingsForm, ExpenseForm, Contract, ContractDetail, ContractFilter, CreateContractForm, PayInstallmentForm, CancelContractForm } from './finanzas.models';
import {
  getCategoryLabel, getMethodBadgeClass, getMethodLabel, formatMonthLabel,
  getLast6MonthsKeys, getMonthlyIncome, getMonthlyExpenses,
  getWhatsAppLink, getInitials, getPatientStatus, getStatusInfo, isOverdue,
} from './finanzas-utils';
import {
  makeDoughnutOpts, makeBarOpts, makeLineOpts, makePieOpts, chartColors,
} from './finanzas-charts-config';

Chart.register(...registerables);

@Component({
  selector: 'app-finanzas',
  standalone: true,
  imports: [CommonModule, FormsModule, FontAwesomeModule, BaseChartDirective, Button, Spinner, Select, Input, Modal, SummaryCard, Table, TableCell],
  templateUrl: './finanzas.html',
  styleUrl: './finanzas.scss',
  animations: [fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Finanzas implements OnInit, OnDestroy {
  readonly Math = Math;
  readonly getCategoryLabel = getCategoryLabel;
  readonly getMethodBadgeClass = getMethodBadgeClass;
  readonly getMethodLabel = getMethodLabel;
  readonly getWhatsAppLink = getWhatsAppLink;
  readonly getInitials = getInitials;
  readonly getPatientStatus = getPatientStatus;
  readonly getStatusInfo = getStatusInfo;
  readonly isOverdue = isOverdue;

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
  selectedStatus = '';
  selectedSort = '';
  historyMonth = '';

  get sedeFilterOptions(): SelectOption[] {
    return [{ value: null, label: 'Todas las Sedes' }, ...this.sedes.map(s => ({ value: s.id, label: s.name }))];
  }

  get therapistFilterOptions(): SelectOption[] {
    return [{ value: null, label: 'Todos los Terapeutas' }, ...this.therapistsList.map(t => ({ value: t.id, label: t.username }))];
  }

  get historyMonthOptions(): SelectOption[] {
    return [{ value: '', label: 'Todos los meses' }, ...this.historyMonths.map(m => ({ value: m, label: m }))];
  }

  statusFilterOptions: SelectOption[] = [
    { value: '', label: 'Todos los Estados' },
    { value: 'al_dia', label: 'Al Día' },
    { value: 'deudor', label: 'Deudores' },
    { value: 'sin_plan', label: 'Sin Plan' },
    { value: 'inactivo', label: 'Inactivos' },
  ];

  sortOptions: SelectOption[] = [
    { value: '', label: 'Ordenar por...' },
    { value: 'nombre', label: 'Nombre' },
    { value: 'vencimiento_cercano', label: 'Vencimiento cercano' },
    { value: 'vencimiento_lejano', label: 'Vencimiento lejano' },
    { value: 'mayor_deuda', label: 'Mayor deuda' },
  ];

  paymentMethodOptions: SelectOption[] = [
    { value: 'transfer', label: 'Transferencia' },
    { value: 'yape', label: 'Yape' },
    { value: 'plin', label: 'Plin' },
    { value: 'cash', label: 'Efectivo' },
    { value: 'card', label: 'Tarjeta' },
  ];

  planFrequencyOptions: SelectOption[] = [
    { value: 'Mensual', label: 'Mensual' },
    { value: 'Quincenal', label: 'Quincenal' },
  ];

  patientColumns: TableColumn[] = [
    { key: 'paciente', label: 'Paciente', width: '22%' },
    { key: 'sede', label: 'Sede', width: '12%' },
    { key: 'terapeuta', label: 'Terapeuta', width: '14%' },
    { key: 'plan', label: 'Plan / Frecuencia', width: '14%' },
    { key: 'progreso', label: 'Progreso', align: 'center', width: '10%' },
    { key: 'deuda', label: 'Deuda Est.', align: 'right', width: '10%' },
    { key: 'vencimiento', label: 'Próx. Venc.', align: 'center', width: '10%' },
    { key: 'estado', label: 'Estado', align: 'center', width: '8%' },
  ];

  patientPage = 1;
  patientPageSize = 20;
  patientTotalPages = 1;

  patientStatusFilter: 'all' | 'al_dia' | 'deudor' | 'sin_plan' = 'all';

  expandedPatientId: number | null = null;
  selectedPatientContract: ContractDetail | null = null;
  contractLoading = false;
  today = new Date().toISOString().split('T')[0];

  get patientStats() {
    const total = this.patients.length;
    const alDia = this.patients.filter(p => getPatientStatus(p) === 'al_dia').length;
    const deudores = this.patients.filter(p => getPatientStatus(p) === 'deudor').length;
    const sinPlan = this.patients.filter(p => getPatientStatus(p) === 'sin_plan').length;
    const totalDeuda = this.patients.reduce((s, p) => s + (p.payment_amount || 0), 0);
    return { total, alDia, deudores, sinPlan, totalDeuda };
  }

  expenseCategoryOptions: SelectOption[] = [
    { value: 'therapist_payment', label: 'Pago a Terapeuta' },
    { value: 'operational', label: 'Gasto Operativo' },
    { value: 'bonus', label: 'Bonificación' },
    { value: 'other', label: 'Otro' },
  ];

  expenseMethodOptions: SelectOption[] = [
    { value: 'transfer', label: 'Transferencia Bancaria' },
    { value: 'yape_plin', label: 'Yape / Plin' },
    { value: 'cash', label: 'Efectivo' },
    { value: 'other', label: 'Otro' },
  ];

  showRegisterModal = false;
  registerForm: RegisterForm = {
    patient_id: null, amount: 0, method: 'transfer', reference: '',
    next_due_date: '', payment_date: '', discount: 0,
    document_number: '', guardian_name: '', guardian_dni: '', receipt: null,
  };
  registerStatus = '';
  analyzeResult: any = null;
  analyzingReceipt = false;

  contractsLoading = false;
  contracts: Contract[] = [];
  expandedContractId: number | null = null;
  contractDetail: ContractDetail | null = null;
  contractFilter: ContractFilter = { search: '', status: 'active', month: null, year: null, sede_id: null };
  contractSummaryActive = 0;
  contractSummaryPending = 0;
  contractSummaryOverdue = 0;
  contractSummaryCollected = 0;
  migrationDone = localStorage.getItem('contracts_migration_done') === 'true';
  migrating = false;

  showCreateContractModal = false;
  createContractForm: CreateContractForm = {
    patient_id: null, total_amount: 0, billing_type: 'Mensual', currency: 'PEN',
    installment_count: 4, start_date: '', implementation_cost: 0, billing_rule: 'standard',
    bonus_months: 0, name: '', notes: '',
  };
  createContractStatus = '';

  showPayInstallmentModal = false;
  payInstallmentForm: PayInstallmentForm = {
    installment_id: null, contract_id: null, contract_name: '', patient_name: '',
    installment_number: 0, due_date: '', amount: 0, method: 'transfer',
    payment_date: '', reference: '', payment_notes: '', is_free_month: false,
  };
  payInstallmentStatus = '';

  showCancelContractModal = false;
  cancelContractForm: CancelContractForm = {
    contract_id: null, contract_name: '', patient_name: '',
    cancellation_date: '', reason: '', comment: '', disposition: 'none',
  };
  cancelContractStatus = '';

  showReactivateContractModal = false;
  reactivateContractId: number | null = null;
  reactivateNextPaymentDate = '';
  reactivateStatus = '';

  patientsList: User[] = [];

  showSettingsModal = false;
  settingsForm: SettingsForm = {
    patient_id: null, patient_name: '', payment_plan: 'Mensual',
    payment_amount: 0, payment_due_date: '',
  };
  settingsStatus = '';

  financials: any = { income_real: 0, income_expected: 0, overdue_amount: 0, overdue_users_count: 0 };

  chartStatusDist: ChartData<'doughnut'> = { labels: [], datasets: [] };
  chartStatusOpt = makeDoughnutOpts();
  readonly chartStatusType = 'doughnut' as const;

  chartDebtByLocation: ChartData<'bar'> = { labels: [], datasets: [] };
  chartDebtByLocationOpt = makeBarOpts('y');
  readonly chartDebtByLocationType = 'bar' as const;

  chartPaymentAge: ChartData<'bar'> = { labels: [], datasets: [] };
  chartPaymentAgeOpt = makeBarOpts();
  readonly chartPaymentAgeType = 'bar' as const;

  chartRevenueHistory: ChartData<'line'> = { labels: [], datasets: [] };
  chartRevenueHistoryOpt = makeLineOpts();
  readonly chartRevenueHistoryType = 'line' as const;

  chartRevenueByPlan: ChartData<'pie'> = { labels: [], datasets: [] };
  chartRevenueByPlanOpt = makePieOpts();
  readonly chartRevenueByPlanType = 'pie' as const;

  chartProjVsReal: ChartData<'bar'> = { labels: [], datasets: [] };
  chartProjVsRealOpt: ChartConfiguration<'bar'>['options'] = {
    responsive: true, maintainAspectRatio: false,
    plugins: {
      legend: { position: 'top', labels: { font: { family: 'Manrope', size: 11, weight: 600 }, usePointStyle: true, pointStyle: 'circle', padding: 16 } },
      tooltip: { backgroundColor: 'rgba(26, 28, 22, 0.92)', titleFont: { family: 'Manrope', size: 12, weight: 700 }, bodyFont: { family: 'Manrope', size: 13, weight: 600 }, padding: { x: 14, y: 10 }, cornerRadius: 10, callbacks: { label: (ctx: any) => `S/ ${Number(ctx.raw).toLocaleString('es-PE', { minimumFractionDigits: 2 })}` } },
    },
    scales: { x: { grid: { display: false }, ticks: { font: { family: 'Manrope', size: 10, weight: 500 }, color: '#76796c' } }, y: { grid: { color: 'rgba(217, 219, 206, 0.4)' }, ticks: { font: { family: 'Manrope', size: 10, weight: 500 }, color: '#76796c', callback: (val: any) => `S/${val}` }, beginAtZero: true } },
  };
  readonly chartProjVsRealType = 'bar' as const;

  chartRevenueByLocation: ChartData<'pie'> = { labels: [], datasets: [] };
  chartRevenueByLocationOpt = makePieOpts();
  readonly chartRevenueByLocationType = 'pie' as const;

  dashIncomeExpenseChart: ChartData<'line'> = { labels: [], datasets: [] };
  dashIncomeExpenseOpt = makeLineOpts();
  readonly dashIncomeExpenseType = 'line' as const;

  dashExpenseCategoryChart: ChartData<'doughnut'> = { labels: [], datasets: [] };
  dashExpenseCategoryOpt = makeDoughnutOpts();
  readonly dashExpenseCategoryType = 'doughnut' as const;

  therapistFinancials: TherapistFinancial[] = [];
  recentExpenses: Expense[] = [];
  expenseTherapists: User[] = [];
  expensesLoading = true;
  submitting = false;

  showExpenseModal = false;
  expenseModalMode: 'therapist_payment' | 'operational' = 'operational';
  expenseForm: ExpenseForm = {
    category: 'operational', therapist_id: null, therapist_name: '',
    amount: 0, method: 'transfer', date: '', description: '', receipt: null,
  };

  contractAlerts: { id: number; patient_name: string; contract_name: string; installment_number: number; amount: number; due_date: string; type: 'overdue' | 'upcoming' | 'due_today' }[] = [];

  private subscriptions = new Subscription();

  constructor(
    private adminService: AdminService,
    private headerService: HeaderService,
    private route: ActivatedRoute,
    private authService: AuthService,
    private alertService: AlertService,
    private toastService: ToastService,
    private confirmService: ConfirmService,
    private cdr: ChangeDetectorRef,
    private http: HttpClient,
  ) {}

  ngOnInit() {
    this.authService.currentUser$.subscribe((u: User | null) => {
      this.isSupervisor = u?.role === 'supervisor';
      this.cdr.markForCheck();
    });
    this.headerService.setConfig({
      title: 'Finanzas', subtitle: 'Gestión integrada de finanzas del centro',
      icon: ['fas', 'university'], actionTemplate: this.headerActions,
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
            this.summaryTotalDeuda = Object.values(porSede).reduce((sum: number, g: any) =>
              sum + ((g.deudores || []).reduce((s: number, d: any) => s + (d.monto || 0), 0)), 0);
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
          if (res.success && res.data) this.summaryIngresos = res.data.income_real || 0;
          this.genDashboardCharts();
          this.cdr.markForCheck();
        },
        error: () => this.cdr.markForCheck(),
      }),
    );
    this.subscriptions.add(
      this.adminService.getExpenses().subscribe({
        next: (res) => {
          if (res.success && res.data) this.summaryGastos = res.data.reduce((sum: number, e: Expense) => sum + e.amount, 0);
          this.genDashboardCharts();
          this.cdr.markForCheck();
        },
        error: () => this.cdr.markForCheck(),
      }),
    );
  }

  private genDashboardCharts() {
    const incomeByMonth = getMonthlyIncome(this.paymentHistory);
    const expenseByMonth = getMonthlyExpenses(this.recentExpenses);
    const monthKeys = getLast6MonthsKeys();
    const revenues = monthKeys.map((k) => incomeByMonth.get(k) || 0);
    const expValues = monthKeys.map((k) => expenseByMonth.get(k) || 0);
    const labels = monthKeys.map((k) => formatMonthLabel(k));

    this.dashIncomeExpenseChart = {
      labels,
      datasets: [
        { label: 'Ingresos', data: revenues, borderColor: '#75a83a', backgroundColor: 'rgba(117, 168, 58, 0.1)', fill: true, pointBackgroundColor: '#75a83a', pointBorderColor: '#fff', pointBorderWidth: 2 },
        { label: 'Gastos', data: expValues, borderColor: '#ba1a1a', backgroundColor: 'rgba(186, 26, 26, 0.08)', fill: true, pointBackgroundColor: '#ba1a1a', pointBorderColor: '#fff', pointBorderWidth: 2 },
      ],
    };

    const catMap: Record<string, number> = {};
    this.recentExpenses.forEach((e) => { const k = e.category || 'Otros'; catMap[k] = (catMap[k] || 0) + e.amount; });
    if (Object.keys(catMap).length === 0) catMap['Sin datos'] = 0;
    const catLabels = Object.keys(catMap);
    const catColors: Record<string, string> = { therapist_payment: '#75a83a', operational: '#3b82f6', bonus: '#f59e0b', other: '#8b5cf6' };
    this.dashExpenseCategoryChart = {
      labels: catLabels.map((k) => getCategoryLabel(k)),
      datasets: [{ data: Object.values(catMap), backgroundColor: catLabels.map((k) => catColors[k] || '#8b5cf6'), borderWidth: 0, hoverOffset: 8 }],
    };
  }

  get summaryBalance(): number { return this.summaryIngresos - this.summaryGastos; }

  get dashCollectionRate(): number {
    if (this.financials?.income_expected > 0) return Math.min(100, (this.financials.income_real / this.financials.income_expected) * 100);
    return 0;
  }

  get dashRecentTransactions(): any[] { return this.paymentHistory.slice(0, 10); }

  get dashExpenseStats() {
    const total = this.recentExpenses.reduce((sum, e) => sum + e.amount, 0);
    const therapistPayments = this.recentExpenses.filter((e) => e.category === 'therapist_payment').reduce((sum, e) => sum + e.amount, 0);
    const operational = this.recentExpenses.filter((e) => e.category === 'operational').reduce((sum, e) => sum + e.amount, 0);
    return { total, therapistPayments, operational, other: total - therapistPayments - operational };
  }

  private checkDeepLinks() {
    const params = this.route.snapshot.queryParams;
    if (params['search_patient']) this.searchQuery = params['search_patient'];
    if (params['action'] === 'register') setTimeout(() => this.openRegisterModal(), 800);
  }

  private loadPaymentsData() { this.loadSedes(); this.loadPaymentsTherapists(); this.loadPaymentsDebtReport(); this.loadFinancialSummary(); this.loadPaymentHistory(); this.loadContractAlerts(); }

  private loadSedes() {
    this.subscriptions.add(this.adminService.getSedes().subscribe({ next: (list) => { this.sedes = list; this.cdr.markForCheck(); }, error: () => this.cdr.markForCheck() }));
  }

  private loadPaymentsTherapists() {
    this.subscriptions.add(this.adminService.getUsers('terapista').subscribe({ next: (res) => { if (res.success) this.therapistsList = res.users; this.cdr.markForCheck(); }, error: () => this.cdr.markForCheck() }));
  }

  private loadPaymentsDebtReport() {
    this.paymentsLoading = true;
    this.subscriptions.add(
      forkJoin({ patients: this.adminService.getUsers('jugador'), debt: this.adminService.getDebtReport('all') }).subscribe({
        next: ({ patients, debt }) => {
          const porSede: Record<string, any> = debt?.data?.por_sede || {};
          const debtByName = new Map<string, any>();
          Object.values(porSede).forEach((group: any) => (group.deudores || []).forEach((d: any) => {
            const key = (d.paciente || d.email || '').toLowerCase().trim();
            if (key) debtByName.set(key, d);
          }));
          this.patients = (patients.users || []).map((u: any) => {
            const nameKey = (u.username || u.email || '').toLowerCase().trim();
            const d = debtByName.get(nameKey) || {};
            return {
              id: u.id, username: u.username || 'Sin nombre', email: u.email || '', phone: u.phone,
              sede_name: d.sede_name || u.sede_name || '', therapist_name: d.therapist_name || '',
              plan_name: d.modality || u.plan_type || 'Sin plan', plan_frequency: d.frequency || u.payment_plan || '',
              payment_amount: d.monto || u.payment_amount || 0, sessions_total: u.sessions_total || 0,
              sessions_attended: u.sessions_attended || 0,
              sessions_remaining: u.sessions_remaining ?? ((u.sessions_total || 0) - (u.sessions_attended || 0)),
              next_due_date: d.fecha_vencimiento || u.payment_due_date, status: u.account_status || 'active',
              has_plan_config: !!(u.payment_plan || u.payment_amount),
            };
          });
          this.updateCharts();
          this.paymentsLoading = false;
          this.cdr.markForCheck();
        },
        error: () => { this.paymentsLoading = false; this.cdr.markForCheck(); },
      }),
    );
  }

  private loadFinancialSummary() {
    this.subscriptions.add(this.adminService.getFinancialSummary().subscribe({
      next: (res) => { if (res.success && res.data) { this.financials = res.data; this.updateCharts(); } this.cdr.markForCheck(); },
      error: () => this.cdr.markForCheck(),
    }));
  }

  private loadPaymentHistory() {
    this.historyLoading = true;
    this.subscriptions.add(this.adminService.getAllPayments().subscribe({
      next: (res) => {
        if (res.success && res.payments) {
          this.paymentHistory = res.payments.map((p: any) => ({
            id: p.id, patient_id: p.patient_id, patient_name: p.patient_name || '',
            amount: p.amount || 0, discount: p.discount || 0, method: p.method || '',
            reference: p.reference, date: p.date || '', status: p.status || 'completed',
            receipt_image_path: p.receipt_image_path, document_number: p.document_number, guardian_name: p.guardian_name,
          }));
        }
        this.historyLoading = false;
        this.genDashboardCharts();
        this.updateRevenueHistoryChart();
        this.cdr.markForCheck();
      },
        error: () => { this.historyLoading = false; this.cdr.markForCheck(); },
      }));
  }

  loadContractAlerts() {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const todayStr = today.toISOString().split('T')[0];

    this.subscriptions.add(
      forkJoin({
        due: this.adminService.getDueInstallments(),
        upcoming: this.adminService.getUpcomingInstallments(7),
      }).subscribe({
        next: ({ due, upcoming }) => {
          const alerts: any[] = [];
          const seen = new Set<string>();

          (due.installments || []).forEach((inst: any) => {
            const key = `${inst.contract_id}-${inst.id}`;
            if (seen.has(key)) return;
            seen.add(key);
            alerts.push({
              id: inst.id,
              patient_name: inst.patient_name || '',
              contract_name: inst.contract_name || '',
              installment_number: inst.number || 0,
              amount: inst.amount || 0,
              due_date: inst.due_date || '',
              type: 'overdue',
            });
          });

          (upcoming.installments || []).forEach((inst: any) => {
            const key = `${inst.contract_id}-${inst.id}`;
            if (seen.has(key)) return;
            seen.add(key);
            const dueDate = new Date(inst.due_date);
            dueDate.setHours(0, 0, 0, 0);
            const isToday = dueDate.getTime() === today.getTime();
            alerts.push({
              id: inst.id,
              patient_name: inst.patient_name || '',
              contract_name: inst.contract_name || '',
              installment_number: inst.number || 0,
              amount: inst.amount || 0,
              due_date: inst.due_date || '',
              type: isToday ? 'due_today' : 'upcoming',
            });
          });

          this.contractAlerts = alerts.slice(0, 5);
          this.cdr.markForCheck();
        },
        error: () => this.cdr.markForCheck(),
      })
    );
  }

  // ── Contratos ──────────────────────────────────────────────────────
  loadContracts() {
    this.contractsLoading = true;
    this.contracts = [];
    this.cdr.markForCheck();
    const params: any = {};
    if (this.contractFilter.search) params.search = this.contractFilter.search;
    if (this.contractFilter.status) params.status = this.contractFilter.status;
    if (this.contractFilter.month) params.month = this.contractFilter.month;
    if (this.contractFilter.year) params.year = this.contractFilter.year;
    if (this.contractFilter.sede_id) params.sede_id = this.contractFilter.sede_id;

    this.subscriptions.add(
      this.adminService.getContractsFiltered(params).subscribe({
        next: (res) => {
          this.contracts = (res.contracts || []) as any;
          this.contractsLoading = false;
          this.updateContractSummary();
          this.cdr.markForCheck();
        },
        error: () => {
          this.contractsLoading = false;
          this.cdr.markForCheck();
        }
      })
    );
  }

  get contractFilterMonthValue(): string {
    if (this.contractFilter.month && this.contractFilter.year) {
      return `${this.contractFilter.year}-${String(this.contractFilter.month).padStart(2, '0')}`;
    }
    return '';
  }

  onContractMonthChange(event: Event) {
    const val = (event.target as HTMLInputElement).value;
    if (val) {
      const [y, m] = val.split('-').map(Number);
      this.contractFilter.year = y;
      this.contractFilter.month = m;
    } else {
      this.contractFilter.year = null;
      this.contractFilter.month = null;
    }
    this.loadContracts();
  }

  clearContractFilters() {
    this.contractFilter = { search: '', status: '', month: null, year: null, sede_id: null };
    this.loadContracts();
  }

  updateContractSummary() {
    this.contractSummaryActive = this.contracts.filter(c => c.status === 'active').length;
    this.contractSummaryPending = this.contracts.filter(c => c.status === 'pending').length;
    this.contractSummaryOverdue = this.contracts.filter(c => c.status === 'overdue' || c.overdue_count > 0).length;
    this.contractSummaryCollected = this.contracts.reduce((sum, c) => sum + (c.paid_count * c.installment_amount), 0);
  }

  toggleContractDetail(contract: Contract) {
    if (this.expandedContractId === contract.id) {
      this.expandedContractId = null;
      this.contractDetail = null;
      return;
    }
    this.expandedContractId = contract.id;
    this.subscriptions.add(
      this.adminService.getContractDetail(contract.id).subscribe({
        next: (res) => {
          this.contractDetail = res.contract as any;
          this.cdr.markForCheck();
        },
        error: () => { this.expandedContractId = null; this.cdr.markForCheck(); }
      })
    );
  }

  openCreateContractModal() {
    console.log('[FINANZAS] openCreateContractModal called');
    this.createContractForm = {
      patient_id: null, total_amount: 0, billing_type: 'Mensual', currency: 'PEN',
      installment_count: 4, start_date: new Date().toISOString().substring(1, 10),
      implementation_cost: 0, billing_rule: 'standard', bonus_months: 0, name: '', notes: '',
    };
    this.createContractStatus = '';
    this.showCreateContractModal = true;
    console.log('[FINANZAS] showCreateContractModal set to', this.showCreateContractModal);
    this.cdr.markForCheck();
    this.loadPatientsList();
  }

  loadPatientsList() {
    this.subscriptions.add(
      this.adminService.getUsers('jugador').subscribe({
        next: (res) => { this.patientsList = res.users || []; this.cdr.markForCheck(); },
        error: () => this.cdr.markForCheck()
      })
    );
  }

  migrateExistingPatients() {
    if (this.migrating) return;
    this.migrating = true;
    this.cdr.markForCheck();
    this.http.post('/admin/api/contracts/migrate-existing', {}).subscribe({
      next: (res: any) => {
        this.migrating = false;
        if (res.success) {
          this.migrationDone = true;
          localStorage.setItem('contracts_migration_done', 'true');
          this.toastService.show(`Migración completada: ${res.created} contratos creados, ${res.skipped} ya existían`, 'success');
          this.loadContracts();
        } else {
          this.toastService.show('Error en la migración: ' + (res.error || 'Error desconocido'), 'error');
        }
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.migrating = false;
        console.error('[FINANZAS] Error en migrateExistingPatients:', err);
        this.toastService.show('Error de conexión al migrar: ' + (err.message || ''), 'error');
        this.cdr.markForCheck();
      }
    });
  }

  submitCreateContract() {
    if (!this.createContractForm.patient_id || this.createContractForm.total_amount <= 0) {
      this.createContractStatus = 'Selecciona un paciente y monto valido.';
      return;
    }
    this.createContractStatus = '';
    const isEdit = this.selectedPatientContract && this.selectedPatientContract.patient_id === this.createContractForm.patient_id;
    if (isEdit) {
      this.subscriptions.add(
        this.adminService.updateContract(this.selectedPatientContract!.id, {
          name: this.createContractForm.name,
          notes: this.createContractForm.notes,
          billing_type: this.createContractForm.billing_type,
          currency: this.createContractForm.currency,
          billing_rule: this.createContractForm.billing_rule,
        }).subscribe({
          next: (res) => {
            if (res.success) {
              this.showCreateContractModal = false;
              this.loadPatientContract(this.createContractForm.patient_id!);
              this.toastService.show('Contrato actualizado', 'success');
            } else {
              this.createContractStatus = res.error || 'Error al actualizar';
            }
            this.cdr.markForCheck();
          },
          error: (err) => {
            this.createContractStatus = err.error?.error || 'Error de conexion';
            this.cdr.markForCheck();
          }
        })
      );
    } else {
      this.subscriptions.add(
        this.adminService.createContract(this.createContractForm).subscribe({
          next: (res) => {
            if (res.success) {
              this.showCreateContractModal = false;
              this.loadPatientContract(this.createContractForm.patient_id!);
              this.toastService.show('Contrato creado', 'success');
            } else {
              this.createContractStatus = res.error || 'Error al crear contrato';
            }
            this.cdr.markForCheck();
          },
          error: (err) => {
            this.createContractStatus = err.error?.error || 'Error de conexion';
            this.cdr.markForCheck();
          }
        })
      );
    }
  }

  openPayInstallmentModal(installment: any, contract: Contract) {
    this.payInstallmentForm = {
      installment_id: installment.id,
      contract_id: contract.id,
      contract_name: contract.name,
      patient_name: contract.patient_name,
      installment_number: installment.number,
      due_date: installment.due_date,
      amount: installment.is_free_month ? 0 : (installment.real_amount || installment.amount),
      method: 'transfer',
      payment_date: '',
      reference: '',
      payment_notes: '',
      is_free_month: installment.is_free_month,
    };
    this.payInstallmentStatus = '';
    this.showPayInstallmentModal = true;
  }

  submitPayInstallment() {
    if (!this.payInstallmentForm.installment_id) return;
    this.payInstallmentStatus = '';
    const data = {
      amount: this.payInstallmentForm.amount,
      method: this.payInstallmentForm.method,
      reference: this.payInstallmentForm.reference,
      payment_notes: this.payInstallmentForm.payment_notes,
    };
    this.subscriptions.add(
      this.adminService.payInstallment(this.payInstallmentForm.installment_id!, data).subscribe({
        next: (res) => {
          if (res.success) {
            this.showPayInstallmentModal = false;
            this.loadContracts();
            if (this.expandedContractId) this.toggleContractDetail({ id: this.expandedContractId } as any);
          } else {
            this.payInstallmentStatus = res.error || 'Error al pagar cuota';
          }
          this.cdr.markForCheck();
        },
        error: (err) => {
          this.payInstallmentStatus = err.error?.error || 'Error de conexión';
          this.cdr.markForCheck();
        }
      })
    );
  }

  openCancelContractModal(contract: Contract) {
    this.cancelContractForm = {
      contract_id: contract.id,
      contract_name: contract.name,
      patient_name: contract.patient_name,
      cancellation_date: new Date().toISOString().split('T')[0],
      reason: '',
      comment: '',
      disposition: 'none',
    };
    this.cancelContractStatus = '';
    this.showCancelContractModal = true;
  }

  submitCancelContract() {
    if (!this.cancelContractForm.contract_id || !this.cancelContractForm.reason) {
      this.cancelContractStatus = 'Ingresa un motivo de cancelación.';
      return;
    }
    this.cancelContractStatus = '';
    const data = {
      reason: this.cancelContractForm.reason,
      cancellation_date: this.cancelContractForm.cancellation_date,
      comment: this.cancelContractForm.comment,
      disposition: this.cancelContractForm.disposition,
    };
    this.subscriptions.add(
      this.adminService.cancelContract(this.cancelContractForm.contract_id!, data).subscribe({
        next: (res) => {
          if (res.success) {
            this.showCancelContractModal = false;
            this.loadContracts();
          } else {
            this.cancelContractStatus = res.error || 'Error al cancelar contrato';
          }
          this.cdr.markForCheck();
        },
        error: (err) => {
          this.cancelContractStatus = err.error?.error || 'Error de conexión';
          this.cdr.markForCheck();
        }
      })
    );
  }

  openReactivateContractModal(contractId: number) {
    this.reactivateContractId = contractId;
    this.reactivateNextPaymentDate = '';
    this.reactivateStatus = '';
    this.showReactivateContractModal = true;
  }

  submitReactivateContract() {
    if (!this.reactivateContractId || !this.reactivateNextPaymentDate) {
      this.reactivateStatus = 'Selecciona fecha de próximo pago.';
      return;
    }
    this.reactivateStatus = '';
    this.subscriptions.add(
      this.adminService.reactivateContract(this.reactivateContractId, { next_payment_date: this.reactivateNextPaymentDate }).subscribe({
        next: (res) => {
          if (res.success) {
            this.showReactivateContractModal = false;
            this.loadContracts();
          } else {
            this.reactivateStatus = res.error || 'Error al reactivar';
          }
          this.cdr.markForCheck();
        },
        error: (err) => {
          this.reactivateStatus = err.error?.error || 'Error de conexión';
          this.cdr.markForCheck();
        }
      })
    );
  }

  getContractStatusColor(status: string): string {
    const colors: Record<string, string> = { active: '#75a83a', pending: '#f59e0b', overdue: '#dc2626', cancelled: '#9ca3af', completed: '#2563eb' };
    return colors[status] || '#9ca3af';
  }

  getContractStatusText(status: string): string {
    const labels: Record<string, string> = { active: 'Activo', pending: 'Pendiente', overdue: 'Vencido', cancelled: 'Cancelado', completed: 'Completado' };
    return labels[status] || status;
  }

  getInstallmentStatusColor(status: string): string {
    const colors: Record<string, string> = { paid: '#75a83a', pending: '#f59e0b', overdue: '#dc2626', free: '#6b7280' };
    return colors[status] || '#9ca3af';
  }

  getInstallmentStatusText(status: string): string {
    const labels: Record<string, string> = { paid: 'Pagado', pending: 'Pendiente', overdue: 'Vencido', free: 'Gratis' };
    return labels[status] || status;
  }

  get activeFilterCount(): number {
    let c = 0;
    if (this.searchQuery) c++;
    if (this.selectedSedeId) c++;
    if (this.selectedTherapistId) c++;
    if (this.selectedStatus) c++;
    if (this.selectedSort) c++;
    return c;
  }

  clearFilters() { this.searchQuery = ''; this.selectedSedeId = null; this.selectedTherapistId = null; this.selectedStatus = ''; this.selectedSort = ''; }

  trackPatient = (i: number, p: PatientRow): number => p.id;

  getPatientRowClass = (p: PatientRow, _i: number): string => {
    const classes: string[] = [];
    if (getPatientStatus(p) === 'deudor') classes.push('bg-error-container/10');
    if (getPatientStatus(p) === 'sin_plan') classes.push('bg-surface-container-high/40');
    if (isOverdue(p)) classes.push('border-l-2 border-l-error');
    return classes.join(' ');
  };

  get filteredPatients(): PatientRow[] {
    let result = [...this.patients];
    if (this.patientStatusFilter !== 'all') {
      result = result.filter(p => getPatientStatus(p) === this.patientStatusFilter);
    }
    if (this.searchQuery) { const q = this.searchQuery.toLowerCase(); result = result.filter((p) => p.username.toLowerCase().includes(q) || p.email.toLowerCase().includes(q)); }
    if (this.selectedSedeId) { const sn = this.sedes.find((s) => s.id === this.selectedSedeId)?.name || ''; result = result.filter((p) => p.sede_name === sn); }
    if (this.selectedTherapistId) { const tn = this.therapistsList.find((t) => t.id === this.selectedTherapistId)?.username || ''; result = result.filter((p) => p.therapist_name === tn); }
    if (this.selectedStatus) result = result.filter((p) => getPatientStatus(p) === this.selectedStatus);
    if (this.selectedSort) {
      switch (this.selectedSort) {
        case 'nombre': result.sort((a, b) => a.username.localeCompare(b.username)); break;
        case 'vencimiento_cercano': result.sort((a, b) => { if (!a.next_due_date) return 1; if (!b.next_due_date) return -1; return new Date(a.next_due_date).getTime() - new Date(b.next_due_date).getTime(); }); break;
        case 'vencimiento_lejano': result.sort((a, b) => { if (!a.next_due_date) return 1; if (!b.next_due_date) return -1; return new Date(b.next_due_date).getTime() - new Date(a.next_due_date).getTime(); }); break;
        case 'mayor_deuda': result.sort((a, b) => b.payment_amount - a.payment_amount); break;
      }
    }
    this.patientTotalPages = Math.max(1, Math.ceil(result.length / this.patientPageSize));
    if (this.patientPage > this.patientTotalPages) this.patientPage = 1;
    return result;
  }

  get paginatedPatients(): PatientRow[] {
    const start = (this.patientPage - 1) * this.patientPageSize;
    return this.filteredPatients.slice(start, start + this.patientPageSize);
  }

  get patientPageNumbers(): number[] {
    const pages: number[] = [];
    const total = this.patientTotalPages;
    const current = this.patientPage;
    const start = Math.max(1, current - 2);
    const end = Math.min(total, current + 2);
    for (let i = start; i <= end; i++) pages.push(i);
    return pages;
  }

  goToPatientPage(page: number) {
    if (page < 1 || page > this.patientTotalPages) return;
    this.patientPage = page;
    this.cdr.markForCheck();
  }

  setPatientStatusFilter(filter: 'all' | 'al_dia' | 'deudor' | 'sin_plan') {
    this.patientStatusFilter = filter;
    this.patientPage = 1;
    this.cdr.markForCheck();
  }

  togglePatientExpand(patient: PatientRow) {
    if (this.expandedPatientId === patient.id) {
      this.expandedPatientId = null;
      this.selectedPatientContract = null;
      this.cdr.markForCheck();
      return;
    }
    this.expandedPatientId = patient.id;
    this.selectedPatientContract = null;
    this.contractLoading = true;
    this.cdr.markForCheck();
    this.loadPatientContract(patient.id);
  }

  private loadPatientContract(patientId: number) {
    this.subscriptions.add(
      this.adminService.getContractsFiltered({ patient_id: patientId }).subscribe({
        next: (res) => {
          const contracts = (res.contracts || []) as any;
          const active = contracts.find((c: any) => c.status === 'active');
          if (active) {
            this.adminService.getContractDetail(active.id).subscribe({
              next: (detailRes) => {
                this.selectedPatientContract = detailRes.contract as any;
                this.contractLoading = false;
                this.cdr.markForCheck();
              },
              error: () => { this.contractLoading = false; this.cdr.markForCheck(); }
            });
          } else {
            this.contractLoading = false;
            this.cdr.markForCheck();
          }
        },
        error: () => { this.contractLoading = false; this.cdr.markForCheck(); }
      })
    );
  }

  openCreateContractForPatient(patient: PatientRow) {
    this.createContractForm = {
      patient_id: patient.id, total_amount: 0, billing_type: 'Mensual', currency: 'PEN',
      installment_count: 4, start_date: new Date().toISOString().substring(0, 10),
      implementation_cost: 0, billing_rule: 'standard', bonus_months: 0,
      name: `Plan ${patient.username}`, notes: '',
    };
    this.createContractStatus = '';
    this.showCreateContractModal = true;
    this.cdr.markForCheck();
  }

  openEditContractModal() {
    if (!this.selectedPatientContract) return;
    this.createContractForm = {
      patient_id: this.selectedPatientContract.patient_id,
      total_amount: this.selectedPatientContract.total_amount,
      billing_type: this.selectedPatientContract.billing_type,
      currency: this.selectedPatientContract.currency,
      installment_count: this.selectedPatientContract.installment_count,
      start_date: this.selectedPatientContract.start_date || '',
      implementation_cost: this.selectedPatientContract.implementation_cost,
      billing_rule: this.selectedPatientContract.billing_rule,
      bonus_months: 0,
      name: this.selectedPatientContract.name,
      notes: this.selectedPatientContract.notes || '',
    };
    this.createContractStatus = '';
    this.showCreateContractModal = true;
    this.cdr.markForCheck();
  }

  get filteredHistory(): PaymentHistoryRow[] {
    let r = [...this.paymentHistory];
    if (this.historyMonth) r = r.filter((p) => p.date && p.date.startsWith(this.historyMonth));
    return r;
  }

  get historyMonths(): string[] {
    const s = new Set<string>();
    this.paymentHistory.forEach((p) => { if (p.date) s.add(p.date.substring(0, 7)); });
    return Array.from(s).sort((a, b) => b.localeCompare(a));
  }

  get yapeTransactions(): PaymentHistoryRow[] { return this.paymentHistory.filter((p) => p.method === 'yape' || p.method === 'plin'); }
  get yapeTotal(): number { return this.yapeTransactions.reduce((sum, p) => sum + (p.amount - (p.discount || 0)), 0); }
  get yapeMonthlyTotal(): number { const cm = new Date().toISOString().substring(0, 7); return this.yapeTransactions.filter((p) => p.date && p.date.startsWith(cm)).reduce((sum, p) => sum + (p.amount - (p.discount || 0)), 0); }
  get yapeCount(): number { return this.yapeTransactions.length; }

  get totalIncomeReal(): number { return this.financials?.income_real || 0; }
  get totalPending(): number { return this.patients.filter((p) => p.payment_amount > 0).reduce((sum, p) => sum + p.payment_amount, 0); }
  get totalDebt(): number { return this.financials?.overdue_amount || 0; }
  get totalPatients(): number { return this.patients.length; }
  get progressPercent(): number { return this.financials?.income_expected > 0 ? (this.financials.income_real / this.financials.income_expected) * 100 : 0; }

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
    const alDia = this.patients.filter((p) => getPatientStatus(p) === 'al_dia').length;
    const deudor = this.patients.filter((p) => getPatientStatus(p) === 'deudor').length;
    const sinPlan = this.patients.filter((p) => getPatientStatus(p) === 'sin_plan').length;
    this.chartStatusDist = { labels: ['Al Día', 'Deudores', 'Sin Plan'], datasets: [{ data: [alDia, deudor, sinPlan], backgroundColor: ['#75a83a', '#ba1a1a', '#d9dbce'], borderWidth: 0, hoverOffset: 8 }] };
  }

  private updateDebtByLocationChart() {
    const debtBySede: Record<string, number> = {};
    this.patients.forEach((p) => { debtBySede[p.sede_name] = (debtBySede[p.sede_name] || 0) + p.payment_amount; });
    const labels = Object.keys(debtBySede);
    this.chartDebtByLocation = { labels, datasets: [{ label: 'Deuda (S/)', data: Object.values(debtBySede), backgroundColor: labels.map((_, i) => chartColors[i % chartColors.length]), borderRadius: 6, barPercentage: 0.5 }] };
  }

  private updatePaymentAgeChart() {
    const ranges = ['1-7 días', '8-15 días', '16-30 días', '31-60 días', '+60 días'];
    const counts = [0, 0, 0, 0, 0];
    const now = new Date();
    this.patients.forEach((p) => {
      if (!p.next_due_date) return;
      const diffDays = Math.floor((now.getTime() - new Date(p.next_due_date).getTime()) / (1000 * 60 * 60 * 24));
      if (diffDays <= 0) counts[0]++; else if (diffDays <= 7) counts[0]++; else if (diffDays <= 15) counts[1]++; else if (diffDays <= 30) counts[2]++; else if (diffDays <= 60) counts[3]++; else counts[4]++;
    });
    this.chartPaymentAge = { labels: ranges, datasets: [{ label: 'Pacientes', data: counts, backgroundColor: ['rgba(117, 168, 58, 0.8)', 'rgba(59, 130, 246, 0.8)', 'rgba(245, 158, 11, 0.8)', 'rgba(139, 92, 246, 0.8)', 'rgba(186, 26, 26, 0.8)'], borderRadius: 6, barPercentage: 0.6 }] };
  }

  private updateRevenueHistoryChart() {
    const incomeByMonth = getMonthlyIncome(this.paymentHistory);
    const monthKeys = getLast6MonthsKeys();
    const revenues = monthKeys.map((k) => incomeByMonth.get(k) || 0);
    const labels = monthKeys.map((k) => formatMonthLabel(k));
    this.chartRevenueHistory = { labels, datasets: [{ label: 'Ingresos (S/)', data: revenues, borderColor: '#75a83a', backgroundColor: 'rgba(117, 168, 58, 0.1)', fill: true, pointBackgroundColor: '#75a83a', pointBorderColor: '#fff', pointBorderWidth: 2 }] };
  }

  private updateRevenueByPlanChart() {
    const planMap: Record<string, number> = {};
    this.patients.forEach((p) => { const k = p.plan_name || 'Sin plan'; planMap[k] = (planMap[k] || 0) + p.payment_amount; });
    const labels = Object.keys(planMap);
    this.chartRevenueByPlan = { labels, datasets: [{ data: Object.values(planMap), backgroundColor: labels.map((_, i) => chartColors[i % chartColors.length]), borderWidth: 0, hoverOffset: 8 }] };
  }

  private updateProjVsRealChart() {
    this.chartProjVsReal = { labels: ['Este Mes'], datasets: [{ label: 'Proyectado', data: [this.financials?.income_expected || 0], backgroundColor: 'rgba(59, 130, 246, 0.85)', borderRadius: 6, barPercentage: 0.4 }, { label: 'Real', data: [this.financials?.income_real || 0], backgroundColor: 'rgba(117, 168, 58, 0.85)', borderRadius: 6, barPercentage: 0.4 }] };
  }

  private updateRevenueByLocationChart() {
    const sedeMap: Record<string, number> = {};
    this.patients.forEach((p) => { sedeMap[p.sede_name] = (sedeMap[p.sede_name] || 0) + p.payment_amount; });
    const labels = Object.keys(sedeMap);
    this.chartRevenueByLocation = { labels, datasets: [{ data: Object.values(sedeMap), backgroundColor: labels.map((_, i) => chartColors[i % chartColors.length]), borderWidth: 0, hoverOffset: 8 }] };
  }

  openRegisterModal(patient?: PatientRow) {
    this.registerForm = {
      patient_id: patient?.id || null, amount: patient?.payment_amount || 0, method: 'transfer', reference: '',
      next_due_date: '', payment_date: new Date().toISOString().substring(0, 10), discount: 0,
      document_number: '', guardian_name: '', guardian_dni: '', receipt: null,
    };
    this.analyzeResult = null;
    this.analyzingReceipt = false;
    this.registerStatus = '';
    this.showRegisterModal = true;
    this.cdr.markForCheck();
  }

  closeRegisterModal() { this.showRegisterModal = false; }

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
          error: () => { this.analyzingReceipt = false; this.cdr.markForCheck(); },
        }),
      );
    }
  }

  submitRegisterPayment() {
    this.registerStatus = 'Registrando...';
    const fd = new FormData();
    if (this.registerForm.patient_id) fd.append('patient_id', String(this.registerForm.patient_id));
    fd.append('amount', String(this.registerForm.amount));
    fd.append('method', this.registerForm.method);
    if (this.registerForm.reference) fd.append('reference', this.registerForm.reference);
    if (this.registerForm.next_due_date) fd.append('next_due_date', this.registerForm.next_due_date);
    if (this.registerForm.payment_date) fd.append('payment_date', this.registerForm.payment_date);
    fd.append('discount', String(this.registerForm.discount));
    if (this.registerForm.document_number) fd.append('document_number', this.registerForm.document_number);
    if (this.registerForm.guardian_name) fd.append('guardian_name', this.registerForm.guardian_name);
    if (this.registerForm.receipt) fd.append('receipt', this.registerForm.receipt);

    this.subscriptions.add(this.adminService.registerPayment(fd).subscribe({
      next: (res: any) => {
        if (res.success) {
          this.registerStatus = 'Pago registrado exitosamente';
          setTimeout(() => { this.closeRegisterModal(); this.loadPaymentsDebtReport(); this.loadPaymentHistory(); this.loadSummaryData(); }, 1500);
        } else {
          this.registerStatus = 'Error: ' + (res.message || res.error || 'Desconocido');
        }
        this.cdr.markForCheck();
      },
      error: () => { this.registerStatus = 'Error de conexión al servidor'; this.cdr.markForCheck(); },
    }));
  }

  get needsRecalculation(): boolean { return this.registerForm.amount > 0 && this.registerForm.discount > 0; }
  get hasMissingData(): boolean { return !this.registerForm.document_number || !this.registerForm.guardian_name; }

  openSettingsModal(patient: PatientRow) {
    this.settingsForm = {
      patient_id: patient.id, patient_name: patient.username,
      payment_plan: patient.plan_frequency || 'Mensual', payment_amount: patient.payment_amount,
      payment_due_date: patient.next_due_date || '',
    };
    this.settingsStatus = '';
    this.showSettingsModal = true;
  }

  closeSettingsModal() { this.showSettingsModal = false; }

  submitSettings() {
    this.settingsStatus = 'Guardando...';
    const data: any = {};
    if (this.settingsForm.payment_amount > 0) data.payment_amount = this.settingsForm.payment_amount;
    if (this.settingsForm.payment_due_date) data.payment_due_date = this.settingsForm.payment_due_date;
    if (this.settingsForm.payment_plan) data.payment_plan = this.settingsForm.payment_plan;

    this.subscriptions.add(this.adminService.updatePaymentSettings(this.settingsForm.patient_id!, data).subscribe({
      next: (res: any) => {
        if (res.success) { this.settingsStatus = 'Configuración guardada'; setTimeout(() => { this.closeSettingsModal(); this.loadPaymentsDebtReport(); }, 1500); }
        else { this.settingsStatus = 'Error: ' + (res.message || res.error || 'Desconocido'); }
        this.cdr.markForCheck();
      },
      error: () => { this.settingsStatus = 'Error de conexión'; this.cdr.markForCheck(); },
    }));
  }

  get incompletePlanPatients(): PatientRow[] { return this.patients.filter((p) => !p.has_plan_config); }

  async generateReport() {
    const c = await firstValueFrom(this.confirmService.confirm({ title: 'Generar Reporte', message: 'Esta operación puede tomar unos segundos. ¿Deseas continuar?', confirmText: 'Generar', cancelText: 'Cancelar', variant: 'warning' }));
    if (!c) return;
    this.subscriptions.add(this.adminService.exportPaymentsCsv().subscribe({
      next: (blob) => { const url = window.URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = `pagos_${new Date().toISOString().slice(0, 7)}.csv`; a.click(); window.URL.revokeObjectURL(url); this.cdr.markForCheck(); },
      error: () => { this.toastService.show('Error al generar el reporte', 'error'); this.cdr.markForCheck(); },
    }));
  }

  showHelp() {
    this.alertService.showHelp('Panel de Finanzas',
      'Panel de Finanzas\n\n• Dashboard: Resumen financiero del centro.\n• Pagos: Lista de pacientes con su estado de pago, plan y progreso.\n• Yape: Transacciones registradas vía Yape / Plin.\n• Gastos: Pagos a personal y gastos operativos.\n• Use los filtros para buscar por sede, terapeuta, o estado.');
  }

  async deletePayment(id: number) {
    const c = await firstValueFrom(this.confirmService.confirm({ title: 'Eliminar Pago', message: '¿Eliminar este pago?', confirmText: 'Eliminar', cancelText: 'Cancelar', variant: 'danger' }));
    if (!c) return;
    this.subscriptions.add(this.adminService.deletePayment(id).subscribe({ next: () => { this.paymentHistory = this.paymentHistory.filter((p) => p.id !== id); this.cdr.markForCheck(); }, error: () => this.cdr.markForCheck() }));
  }

  viewPatientHistory(patient: PatientRow) { window.open(`/admin/payments/history/${patient.id}`, '_blank'); }
  getPatientName(id: number): string { return this.patients.find((p) => p.id === id)?.username || ''; }
  sedeById(id: number): string { return this.sedes.find((s) => s.id === id)?.name || ''; }
  therapistById(id: number): string { return this.therapistsList.find((t) => t.id === id)?.username || ''; }
  trackById(_: number, item: any): number { return item.id || item.patient_id; }

  private loadExpensesData() {
    this.expensesLoading = true;
    this.subscriptions.add(this.adminService.getTherapistFinancials().subscribe({ next: (res) => { this.therapistFinancials = res.data; this.cdr.markForCheck(); }, error: () => this.cdr.markForCheck() }));
    this.subscriptions.add(this.adminService.getUsers('terapista').subscribe({ next: (res) => { this.expenseTherapists = res.users.map((u: any) => ({ ...u, is_active: true } as User)); this.cdr.markForCheck(); }, error: () => this.cdr.markForCheck() }));
    this.subscriptions.add(this.adminService.getExpenses().subscribe({ next: (res) => { this.recentExpenses = res.data; this.expensesLoading = false; this.genDashboardCharts(); this.cdr.markForCheck(); }, error: () => { this.expensesLoading = false; this.cdr.markForCheck(); } }));
  }

  openTherapistPaymentModal(therapist: TherapistFinancial) {
    this.expenseModalMode = 'therapist_payment';
    this.expenseForm = { category: 'therapist_payment', therapist_id: therapist.therapist.id, therapist_name: therapist.therapist.username, amount: therapist.balance > 0 ? therapist.balance : 0, method: 'transfer', date: new Date().toISOString().split('T')[0], description: `Pago a ${therapist.therapist.username}`, receipt: null };
    this.showExpenseModal = true;
  }

  openOperationalModal() {
    this.expenseModalMode = 'operational';
    this.expenseForm = { category: 'operational', therapist_id: null, therapist_name: '', amount: 0, method: 'transfer', date: new Date().toISOString().split('T')[0], description: '', receipt: null };
    this.showExpenseModal = true;
  }

  closeExpenseModal() { this.showExpenseModal = false; }

  onExpenseFileSelected(event: any) { const file = event.target.files[0]; if (file) this.expenseForm.receipt = file; }

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

    this.subscriptions.add(this.adminService.createExpense(fd).subscribe({
      next: () => { this.submitting = false; this.closeExpenseModal(); this.loadExpensesData(); this.loadSummaryData(); this.cdr.markForCheck(); },
      error: () => { this.submitting = false; this.cdr.markForCheck(); },
    }));
  }
}
