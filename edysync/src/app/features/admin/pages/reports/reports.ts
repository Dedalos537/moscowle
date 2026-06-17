import { Component, OnInit, OnDestroy, ViewChild, TemplateRef, ChangeDetectionStrategy, ChangeDetectorRef, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { BaseChartDirective } from 'ng2-charts';
import { Subscription } from 'rxjs';
import { AdminService } from '../../../../core/services/admin.service';
import { HeaderService } from '../../../../core/services/header.service';
import { ToastService } from '../../../../core/services/toast.service';
import { GlobalSettingsService } from '../../../../core/services/global-settings.service';
import { TherapistStats, PatientStats } from '../../../../core/models/expense';
import { Chart, registerables } from 'chart.js';
import type { ChartConfiguration, ChartData } from 'chart.js';
import { fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter } from '../../../../core/animations';
import { firstValueFrom } from 'rxjs';
import { ConfirmService } from '../../../../core/services/confirm.service';
import { SelectOption } from '../../../../shared/components/select/select';
import { Button } from '../../../../shared/components/button/button';
import { Spinner } from '../../../../shared/components/spinner/spinner';
import { Select } from '../../../../shared/components/select/select';
import { Modal } from '../../../../shared/components/modal/modal';
import DOMPurify from 'dompurify';

Chart.register(...registerables);

interface FinancialSummary {
  income_real: number;
  income_expected: number;
  overdue_amount: number;
  overdue_users_count: number;
  expenses: number;
  net_profit: number;
}

@Component({
  selector: 'app-reports',
  standalone: true,
  templateUrl: './reports.html',
  styleUrl: './reports.scss',
  animations: [fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter],
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [CommonModule, FormsModule, FontAwesomeModule, BaseChartDirective, Button, Spinner, Select, Modal],
})
export class Reports implements OnInit, OnDestroy {
  private settings = inject(GlobalSettingsService);
  hideCharts = this.settings.hideCharts;

  @ViewChild('headerActions', { static: true }) headerActions!: TemplateRef<any>;
  @ViewChild('financialChart') financialChart?: any;
  @ViewChild('therapistChart') therapistChart?: any;

  financials: FinancialSummary = {
    income_real: 0,
    income_expected: 0,
    overdue_amount: 0,
    overdue_users_count: 0,
    expenses: 0,
    net_profit: 0,
  };
  therapists: TherapistStats[] = [];
  patients: PatientStats[] = [];
  auditStats: any = { total: 0, avg_score: 0, recent: [], by_therapist: [] };

  overview: { therapists: number; patients: number; sessions_total: number; avg_accuracy: number } | null = null;

  // Weekly / Daily Reports
  weeklySummary: any = null;
  dailyReports: any[] = [];
  weeklySummaryLoading = false;
  dailyReportsLoading = false;
  reportsAccumulating = false;
  selectedWeekStart: string = '';
  dailyStartDate: string = '';
  dailyEndDate: string = '';

  // Monthly / Quarterly Reports
  activeReportTab: 'weekly' | 'monthly' | 'quarterly' = 'weekly';
  monthlySummary: any = null;
  quarterlySummary: any = null;
  monthlyLoading = false;
  quarterlyLoading = false;
  selectedMonth: number = new Date().getMonth() + 1;
  selectedYear: number = new Date().getFullYear();
  selectedQuarter: number = Math.floor(new Date().getMonth() / 3) + 1;

  monthOptions: SelectOption[] = [1,2,3,4,5,6,7,8,9,10,11,12].map(m => ({value: m, label: String(m).padStart(2, '0')}));

  get yearOptions(): SelectOption[] {
    const y = this.selectedYear;
    return [y-2, y-1, y, y+1].map(yy => ({value: yy, label: String(yy)}));
  }

  quarterOptions: SelectOption[] = [1,2,3,4].map(q => ({value: q, label: `Q${q}`}));

  // Efficiency
  therapistEfficiency: any = null;
  efficiencyLoading = false;

  loading = true;
  aiGenerating = false;
  reportSending = false;
  aiReport: string | null = null;

  readonly financialChartLabels = ['Proyectado', 'Recaudado', 'Gastos'];

  financialChartData: ChartData<'bar'> = {
    labels: this.financialChartLabels,
    datasets: [
      {
        label: 'Monto (S/)',
        data: [0, 0, 0],
        backgroundColor: [
          'rgba(59, 130, 246, 0.85)',
          'rgba(117, 168, 58, 0.85)',
          'rgba(186, 26, 26, 0.85)',
        ],
        borderColor: ['#3b82f6', '#75a83a', '#ba1a1a'],
        borderWidth: 1,
        borderRadius: 8,
        barPercentage: 0.6,
      },
    ],
  };

  financialChartOptions: ChartConfiguration<'bar'>['options'] = {
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
        displayColors: true,
        boxPadding: 6,
        callbacks: {
          label: (ctx) => `S/ ${Number(ctx.raw).toLocaleString('es-PE', { minimumFractionDigits: 2 })}`,
        },
      },
    },
    scales: {
      x: {
        grid: { display: false },
        ticks: {
          font: { family: 'Manrope', size: 12, weight: 600 },
          color: '#76796c',
        },
      },
      y: {
        grid: { color: 'rgba(217, 219, 206, 0.4)' },
        ticks: {
          font: { family: 'Manrope', size: 11, weight: 500 },
          color: '#76796c',
          callback: (val) => `S/${val}`,
        },
        beginAtZero: true,
      },
    },
  };

  readonly financialChartType = 'bar' as const;

  therapistChartLabels: string[] = [];

  therapistChartData: ChartData<'bar'> = {
    labels: [],
    datasets: [
      {
        label: 'Precisión (%)',
        data: [],
        backgroundColor: 'rgba(117, 168, 58, 0.8)',
        borderColor: '#75a83a',
        borderWidth: 1,
        borderRadius: 6,
        barPercentage: 0.5,
      },
    ],
  };

  therapistChartOptions: ChartConfiguration<'bar'>['options'] = {
    responsive: true,
    maintainAspectRatio: false,
    indexAxis: 'y',
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: 'rgba(26, 28, 22, 0.92)',
        titleFont: { family: 'Manrope', size: 12, weight: 700 },
        bodyFont: { family: 'Manrope', size: 13, weight: 600 },
        padding: { x: 14, y: 10 },
        cornerRadius: 10,
        callbacks: {
          label: (ctx) => `${ctx.raw}%`,
        },
      },
    },
    scales: {
      x: {
        grid: { color: 'rgba(217, 219, 206, 0.3)' },
        ticks: {
          font: { family: 'Manrope', size: 10, weight: 500 },
          color: '#76796c',
          callback: (val) => `${val}%`,
        },
        beginAtZero: true,
        max: 100,
      },
      y: {
        grid: { display: false },
        ticks: {
          font: { family: 'Manrope', size: 11, weight: 600 },
          color: '#1a1c16',
        },
      },
    },
  };

  readonly therapistChartType = 'bar' as const;

  private subscriptions = new Subscription();

  constructor(
    private adminService: AdminService,
    private headerService: HeaderService,
    private toastService: ToastService,
    private confirmService: ConfirmService,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit() {
    this.headerService.setConfig({
      title: 'Reportes y Finanzas',
      subtitle: 'Resumen operativo y financiero',
      icon: ['fas', 'chart-bar'],
      actionTemplate: this.headerActions,
    });
    this.initReportDateDefaults();
    this.loadData();
    this.loadWeeklySummary();
    this.loadDailyReports();
    this.loadEfficiency();
  }

  private initReportDateDefaults() {
    const today = new Date();
    const monday = new Date(today);
    const day = monday.getDay();
    const diff = day === 0 ? -6 : 1 - day;
    monday.setDate(monday.getDate() + diff);
    this.selectedWeekStart = monday.toISOString().split('T')[0];

    const weekAgo = new Date(today);
    weekAgo.setDate(today.getDate() - 6);
    this.dailyEndDate = today.toISOString().split('T')[0];
    this.dailyStartDate = weekAgo.toISOString().split('T')[0];
  }

  ngOnDestroy() {
    this.headerService.reset();
    this.subscriptions.unsubscribe();
  }

  private loadData() {
    this.subscriptions.add(
      this.adminService.getAdminOverview().subscribe({
        next: (res) => {
          if (res.success && res.data) {
            this.overview = res.data;
          }
          this.cdr.markForCheck();
        },
        error: () => this.cdr.markForCheck(),
      }),
    );

    this.subscriptions.add(
      this.adminService.getAuditStats().subscribe({
        next: (res: any) => {
          if (res.success && res.data) {
            this.auditStats = res.data;
          }
          this.cdr.markForCheck();
        },
        error: (err) => {
          console.error('Error cargando Stats Auditoria', err);
          this.cdr.markForCheck();
        },
      }),
    );

    this.subscriptions.add(
      this.adminService.getFinancialSummary().subscribe({
        next: (res) => {
          if (res.success && res.data) {
            this.financials = res.data;
            this.updateFinancialChart();
          }
          this.cdr.markForCheck();
        },
        error: () => this.cdr.markForCheck(),
      }),
    );

    this.subscriptions.add(
      this.adminService.getTherapistStats().subscribe({
        next: (res) => {
          this.therapists = res.data;
          this.updateTherapistChart();
          this.cdr.markForCheck();
        },
        error: () => this.cdr.markForCheck(),
      }),
    );

    this.subscriptions.add(
      this.adminService.getPatientStats().subscribe({
        next: (res) => {
          this.patients = res.data;
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

  private updateFinancialChart() {
    this.financialChartData = {
      ...this.financialChartData,
      datasets: [
        {
          ...this.financialChartData.datasets[0],
          data: [
            this.financials.income_expected,
            this.financials.income_real,
            this.financials.expenses,
          ],
        },
      ],
    };
  }

  private updateTherapistChart() {
    this.therapistChartLabels = this.therapists.map((t) => t.name);
    this.therapistChartData = {
      ...this.therapistChartData,
      labels: this.therapistChartLabels,
      datasets: [
        {
          ...this.therapistChartData.datasets[0],
          data: this.therapists.map((t) => t.avg_accuracy),
        },
      ],
    };
  }

  get executionPercent(): number {
    return this.financials.income_expected > 0
      ? (this.financials.income_real / this.financials.income_expected) * 100
      : 0;
  }

  get overduePercent(): number {
    return this.financials.income_expected > 0
      ? (this.financials.overdue_amount / this.financials.income_expected) * 100
      : 0;
  }

  generateAIReport() {
    this.aiGenerating = true;
    this.subscriptions.add(
      this.adminService.generateAIReport().subscribe({
        next: (res) => {
          this.aiGenerating = false;
          this.aiReport = res.report;
          this.cdr.markForCheck();
        },
        error: () => {
          this.aiGenerating = false;
          this.cdr.markForCheck();
        },
      }),
    );
  }

  sendWeeklyReport() {
    this.reportSending = true;
    this.subscriptions.add(
      this.adminService.sendWeeklyReport().subscribe({
        next: () => {
          this.reportSending = false;
          this.cdr.markForCheck();
        },
        error: () => {
          this.reportSending = false;
          this.cdr.markForCheck();
        },
      }),
    );
  }

  exportCSV() {
    this.subscriptions.add(
      this.adminService.exportPaymentsCsv().subscribe({
        next: (blob) => {
          const url = window.URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = 'pagos_export.csv';
          a.click();
          window.URL.revokeObjectURL(url);
          this.cdr.markForCheck();
        },
        error: () => this.cdr.markForCheck(),
      }),
    );
  }

  closeAIReport() {
    this.aiReport = null;
  }

  async generateReport() {
    const confirmed = await firstValueFrom(this.confirmService.confirm({
      title: 'Generar Reporte',
      message: 'Esta operación tomará 1-2 minutos y analizará las últimas notas transcritas. ¿Continuar?',
      confirmText: 'Generar',
      cancelText: 'Cancelar',
      variant: 'warning',
    }));
    if (!confirmed) return;

    this.aiGenerating = true;
    this.aiReport = null;

    this.subscriptions.add(
      this.adminService.generateIAReport().subscribe({
        next: (res: any) => {
          this.aiGenerating = false;
          if (res.success) {
          this.aiReport = DOMPurify.sanitize(res.report, { ALLOWED_TAGS: ['b', 'i', 'em', 'strong', 'a', 'ul', 'ol', 'li', 'br', 'p', 'h1', 'h2', 'h3', 'h4', 'pre', 'code', 'table', 'thead', 'tbody', 'tr', 'th', 'td', 'blockquote'], ALLOWED_ATTR: ['href'] });
          } else {
            this.toastService.show('Error: ' + res.error, 'error');
          }
          this.cdr.markForCheck();
        },
        error: (err) => {
          this.aiGenerating = false;
          this.toastService.show('Error de conexión al generar el reporte.', 'error');
          console.error(err);
          this.cdr.markForCheck();
        },
      }),
    );
  }

  get barMaxValue(): number {
    return Math.max(
      this.financials.income_expected,
      this.financials.income_real,
      this.financials.overdue_amount,
      1,
    );
  }

  // ─── Weekly / Daily Reports ────────────────────────────

  loadWeeklySummary() {
    this.weeklySummaryLoading = true;
    this.subscriptions.add(
      this.adminService.getWeeklySummary(this.selectedWeekStart || undefined).subscribe({
        next: (res) => {
          this.weeklySummaryLoading = false;
          if (res.success) {
            this.weeklySummary = res.data;
          }
          this.cdr.markForCheck();
        },
        error: () => {
          this.weeklySummaryLoading = false;
          this.cdr.markForCheck();
        },
      }),
    );
  }

  loadDailyReports() {
    this.dailyReportsLoading = true;
    this.subscriptions.add(
      this.adminService.getDailyReports(this.dailyStartDate || undefined, this.dailyEndDate || undefined).subscribe({
        next: (res) => {
          this.dailyReportsLoading = false;
          if (res.success) {
            this.dailyReports = res.data || [];
          }
          this.cdr.markForCheck();
        },
        error: () => {
          this.dailyReportsLoading = false;
          this.cdr.markForCheck();
        },
      }),
    );
  }

  accumulateReports() {
    this.reportsAccumulating = true;
    this.subscriptions.add(
      this.adminService.accumulateReports().subscribe({
        next: (res) => {
          this.reportsAccumulating = false;
          if (res.success) {
            this.toastService.show('Reportes acumulados correctamente.', 'success');
            this.loadWeeklySummary();
            this.loadDailyReports();
          }
          this.cdr.markForCheck();
        },
        error: () => {
          this.reportsAccumulating = false;
          this.toastService.show('Error al acumular reportes.', 'error');
          this.cdr.markForCheck();
        },
      }),
    );
  }

  loadEfficiency(therapistId?: number) {
    this.efficiencyLoading = true;
    this.subscriptions.add(
      this.adminService.getTherapistEfficiency(therapistId).subscribe({
        next: (res) => {
          this.efficiencyLoading = false;
          if (res.success) {
            this.therapistEfficiency = res;
          }
          this.cdr.markForCheck();
        },
        error: () => {
          this.efficiencyLoading = false;
          this.cdr.markForCheck();
        },
      }),
    );
  }

  setWeekStart(date: string) {
    this.selectedWeekStart = date;
    this.loadWeeklySummary();
  }

  accuracyColor(avg: number): string {
    if (avg >= 90) return 'text-success bg-success-container';
    if (avg >= 75) return 'text-warning bg-warning-container';
    return 'text-error bg-error-container';
  }

  get therapistWeeklyPatients(): any[] {
    const bt = this.weeklySummary?.by_therapist;
    if (!bt) return [];
    if (Array.isArray(bt)) return bt;
    return Object.entries(bt).map(([name, data]: [string, any]) => ({
      therapist_id: data.therapist_id,
      therapist_name: name,
      patients: data.patients || [],
      total_sessions: data.total_sessions || 0,
      avg_score: data.avg_score || 0,
    }));
  }

  // ─── Monthly / Quarterly Reports ────────────────────────

  setReportTab(tab: 'weekly' | 'monthly' | 'quarterly') {
    this.activeReportTab = tab;
    if (tab === 'monthly') this.loadMonthlySummary();
    if (tab === 'quarterly') this.loadQuarterlySummary();
  }

  loadMonthlySummary() {
    this.monthlyLoading = true;
    this.subscriptions.add(
      this.adminService.getMonthlySummary(this.selectedYear, this.selectedMonth).subscribe({
        next: (res) => {
          this.monthlyLoading = false;
          if (res.success) this.monthlySummary = res.summary;
          this.cdr.markForCheck();
        },
        error: () => {
          this.monthlyLoading = false;
          this.cdr.markForCheck();
        },
      }),
    );
  }

  loadQuarterlySummary() {
    this.quarterlyLoading = true;
    this.subscriptions.add(
      this.adminService.getQuarterlySummary(this.selectedYear, this.selectedQuarter).subscribe({
        next: (res) => {
          this.quarterlyLoading = false;
          if (res.success) this.quarterlySummary = res.summary;
          this.cdr.markForCheck();
        },
        error: () => {
          this.quarterlyLoading = false;
          this.cdr.markForCheck();
        },
      }),
    );
  }

  generateMonthlyReports() {
    this.monthlyLoading = true;
    this.subscriptions.add(
      this.adminService.generateMonthlyReports(this.selectedYear, this.selectedMonth).subscribe({
        next: (res) => {
          if (res.success) {
            this.toastService.show(`${res.count} reportes mensuales generados`, 'success');
            this.loadMonthlySummary();
          }
          this.cdr.markForCheck();
        },
        error: () => {
          this.monthlyLoading = false;
          this.toastService.show('Error al generar reportes mensuales', 'error');
          this.cdr.markForCheck();
        },
      }),
    );
  }

  generateQuarterlyReports() {
    this.quarterlyLoading = true;
    this.subscriptions.add(
      this.adminService.generateQuarterlyReports(this.selectedYear, this.selectedQuarter).subscribe({
        next: (res) => {
          if (res.success) {
            this.toastService.show(`${res.count} reportes trimestrales generados`, 'success');
            this.loadQuarterlySummary();
          }
          this.cdr.markForCheck();
        },
        error: () => {
          this.quarterlyLoading = false;
          this.toastService.show('Error al generar reportes trimestrales', 'error');
          this.cdr.markForCheck();
        },
      }),
    );
  }

  generateAllWeeklyReports() {
    this.weeklySummaryLoading = true;
    this.subscriptions.add(
      this.adminService.generateAllWeeklyReports(this.selectedWeekStart).subscribe({
        next: (res) => {
          if (res.success) {
            this.toastService.show(`${res.count} reportes semanales generados`, 'success');
            this.loadWeeklySummary();
          }
          this.cdr.markForCheck();
        },
        error: () => {
          this.weeklySummaryLoading = false;
          this.toastService.show('Error al generar reportes', 'error');
          this.cdr.markForCheck();
        },
      }),
    );
  }

  get monthlyTherapistPatients(): any[] {
    if (!this.monthlySummary?.by_therapist) return [];
    return Object.values(this.monthlySummary.by_therapist);
  }

  get quarterlyTherapistPatients(): any[] {
    if (!this.quarterlySummary?.by_therapist) return [];
    return Object.values(this.quarterlySummary.by_therapist);
  }
}
