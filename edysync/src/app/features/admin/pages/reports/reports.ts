import { Component, OnInit, OnDestroy, ViewChild, TemplateRef } from '@angular/core';
import { AdminService } from '../../../../core/services/admin.service';
import { HeaderService } from '../../../../core/services/header.service';
import { AlertService } from '../../../../core/services/alert.service';
import { TherapistStats, PatientStats } from '../../../../core/models/expense';
import { Chart, registerables } from 'chart.js';
import type { ChartConfiguration, ChartData } from 'chart.js';
import { fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter } from '../../../../core/animations';

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
  standalone: false,
  templateUrl: './reports.html',
  styleUrl: './reports.scss',
  animations: [fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter]
})
export class Reports implements OnInit, OnDestroy {
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

  constructor(
    private adminService: AdminService,
    private headerService: HeaderService,
    private alertService: AlertService,
  ) {}

  ngOnInit() {
    this.headerService.setConfig({
      title: 'Reportes y Finanzas',
      subtitle: 'Resumen operativo y financiero',
      icon: ['fas', 'chart-bar'],
      actionTemplate: this.headerActions,
    });
    this.loadData();
  }

  ngOnDestroy() {
    this.headerService.reset();
  }

  private loadData() {
    this.adminService.getAdminOverview().subscribe({
      next: (res) => {
        if (res.success && res.data) {
          this.overview = res.data;
        }
      },
    });

    this.adminService.getAuditStats().subscribe({
      next: (res: any) => {
        if (res.success && res.data) {
          this.auditStats = res.data;
        }
      },
      error: (err) => console.error('Error cargando Stats Auditoria', err),
    });

    this.adminService.getFinancialSummary().subscribe({
      next: (res) => {
        if (res.success && res.data) {
          this.financials = res.data;
          this.updateFinancialChart();
        }
      },
    });

    this.adminService.getTherapistStats().subscribe({
      next: (res) => {
        this.therapists = res.data;
        this.updateTherapistChart();
      },
    });

    this.adminService.getPatientStats().subscribe({
      next: (res) => {
        this.patients = res.data;
        this.loading = false;
      },
      error: () => (this.loading = false),
    });
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
    this.adminService.generateAIReport().subscribe({
      next: (res) => {
        this.aiGenerating = false;
        this.aiReport = res.report;
      },
      error: () => (this.aiGenerating = false),
    });
  }

  sendWeeklyReport() {
    this.reportSending = true;
    this.adminService.sendWeeklyReport().subscribe({
      next: () => (this.reportSending = false),
      error: () => (this.reportSending = false),
    });
  }

  exportCSV() {
    this.adminService.exportPaymentsCsv().subscribe({
      next: (blob) => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'pagos_export.csv';
        a.click();
        window.URL.revokeObjectURL(url);
      },
    });
  }

  closeAIReport() {
    this.aiReport = null;
  }

  generateReport() {
    if (
      !confirm(
        'Esta operación tomará 1-2 minutos y analizará las últimas notas transcritas. ¿Continuar?',
      )
    ) {
      return;
    }

    this.aiGenerating = true;
    this.aiReport = null;

    this.adminService.generateIAReport().subscribe({
      next: (res: any) => {
        this.aiGenerating = false;
        if (res.success) {
          this.aiReport = res.report;
        } else {
          this.alertService.show('Error: ' + res.error, 'error');
        }
      },
      error: (err) => {
        this.aiGenerating = false;
        this.alertService.show('Error de conexión al generar el reporte.', 'error');
        console.error(err);
      },
    });
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
    this.adminService.getWeeklySummary(this.selectedWeekStart || undefined).subscribe({
      next: (res) => {
        this.weeklySummaryLoading = false;
        if (res.success) {
          this.weeklySummary = res.data;
        }
      },
      error: () => {
        this.weeklySummaryLoading = false;
      },
    });
  }

  loadDailyReports() {
    this.dailyReportsLoading = true;
    this.adminService.getDailyReports(this.dailyStartDate || undefined, this.dailyEndDate || undefined).subscribe({
      next: (res) => {
        this.dailyReportsLoading = false;
        if (res.success) {
          this.dailyReports = res.data || [];
        }
      },
      error: () => {
        this.dailyReportsLoading = false;
      },
    });
  }

  accumulateReports() {
    this.reportsAccumulating = true;
    this.adminService.accumulateReports().subscribe({
      next: (res) => {
        this.reportsAccumulating = false;
        if (res.success) {
          this.alertService.show('Reportes acumulados correctamente.', 'success');
          this.loadWeeklySummary();
          this.loadDailyReports();
        }
      },
      error: () => {
        this.reportsAccumulating = false;
        this.alertService.show('Error al acumular reportes.', 'error');
      },
    });
  }

  loadEfficiency(therapistId?: number) {
    this.efficiencyLoading = true;
    this.adminService.getTherapistEfficiency(therapistId).subscribe({
      next: (res) => {
        this.efficiencyLoading = false;
        if (res.success) {
          this.therapistEfficiency = res;
        }
      },
      error: () => {
        this.efficiencyLoading = false;
      },
    });
  }

  setWeekStart(date: string) {
    this.selectedWeekStart = date;
    this.loadWeeklySummary();
  }

  accuracyColor(avg: number): string {
    if (avg >= 90) return 'text-emerald-600 bg-emerald-100';
    if (avg >= 75) return 'text-amber-600 bg-amber-100';
    return 'text-red-600 bg-red-100';
  }

  get therapistWeeklyPatients(): any[] {
    if (!this.weeklySummary?.by_therapist) return [];
    return this.weeklySummary.by_therapist;
  }

  // ─── Monthly / Quarterly Reports ────────────────────────

  setReportTab(tab: 'weekly' | 'monthly' | 'quarterly') {
    this.activeReportTab = tab;
    if (tab === 'monthly') this.loadMonthlySummary();
    if (tab === 'quarterly') this.loadQuarterlySummary();
  }

  loadMonthlySummary() {
    this.monthlyLoading = true;
    this.adminService.getMonthlySummary(this.selectedYear, this.selectedMonth).subscribe({
      next: (res) => {
        this.monthlyLoading = false;
        if (res.success) this.monthlySummary = res.summary;
      },
      error: () => this.monthlyLoading = false,
    });
  }

  loadQuarterlySummary() {
    this.quarterlyLoading = true;
    this.adminService.getQuarterlySummary(this.selectedYear, this.selectedQuarter).subscribe({
      next: (res) => {
        this.quarterlyLoading = false;
        if (res.success) this.quarterlySummary = res.summary;
      },
      error: () => this.quarterlyLoading = false,
    });
  }

  generateMonthlyReports() {
    this.monthlyLoading = true;
    this.adminService.generateMonthlyReports(this.selectedYear, this.selectedMonth).subscribe({
      next: (res) => {
        if (res.success) {
          this.alertService.show(`${res.count} reportes mensuales generados`, 'success');
          this.loadMonthlySummary();
        }
      },
      error: () => {
        this.monthlyLoading = false;
        this.alertService.show('Error al generar reportes mensuales', 'error');
      },
    });
  }

  generateQuarterlyReports() {
    this.quarterlyLoading = true;
    this.adminService.generateQuarterlyReports(this.selectedYear, this.selectedQuarter).subscribe({
      next: (res) => {
        if (res.success) {
          this.alertService.show(`${res.count} reportes trimestrales generados`, 'success');
          this.loadQuarterlySummary();
        }
      },
      error: () => {
        this.quarterlyLoading = false;
        this.alertService.show('Error al generar reportes trimestrales', 'error');
      },
    });
  }

  generateAllWeeklyReports() {
    this.weeklySummaryLoading = true;
    this.adminService.generateAllWeeklyReports(this.selectedWeekStart).subscribe({
      next: (res) => {
        if (res.success) {
          this.alertService.show(`${res.count} reportes semanales generados`, 'success');
          this.loadWeeklySummary();
        }
      },
      error: () => {
        this.weeklySummaryLoading = false;
        this.alertService.show('Error al generar reportes', 'error');
      },
    });
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
