import { Component, OnInit, OnDestroy, ViewChild, TemplateRef, ChangeDetectionStrategy, ChangeDetectorRef, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { Subscription } from 'rxjs';
import { AdminService } from '../../../../core/services/admin.service';
import { HeaderService } from '../../../../core/services/header.service';
import { ToastService } from '../../../../core/services/toast.service';
import { GlobalSettingsService } from '../../../../core/services/global-settings.service';
import { TherapistStats, PatientStats } from '../../../../core/models/expense';
import { fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter } from '../../../../core/animations';
import { firstValueFrom } from 'rxjs';
import { ConfirmService } from '../../../../core/services/confirm.service';
import { SelectOption } from '../../../../shared/components/select/select';
import { Button } from '../../../../shared/components/button/button';
import { Spinner } from '../../../../shared/components/spinner/spinner';
import { Select } from '../../../../shared/components/select/select';
import { Modal } from '../../../../shared/components/modal/modal';
import DOMPurify from 'dompurify';
import { markdownSections, type MdSection } from '../../../../core/utils/markdown';

interface StrategicMetrics {
  period: string;
  general: { therapists: number; patients: number; total_sessions: number; sessions_this_month: number };
  financial: { income_30d: number; expenses_30d: number; balance_30d: number; total_debt: number; debtors: number };
  top_therapists: { name: string; sessions: number }[];
  weekly_sessions: { week_start: string; sessions: number }[];
  notes_count: number;
}


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
  imports: [CommonModule, FormsModule, FontAwesomeModule, Button, Spinner, Select, Modal],
})
export class Reports implements OnInit, OnDestroy {
  private settings = inject(GlobalSettingsService);
  hideCharts = this.settings.hideCharts;

  @ViewChild('headerActions', { static: true }) headerActions!: TemplateRef<any>;

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

  // Accordion state
  expandedTherapists = new Set<string>();

  loading = true;
  aiGenerating = false;
  reportSending = false;
  /** Informe estratégico (texto, en la ventana) y de auditoría (HTML saneado, dentro de la página): antes compartían variable y salían duplicados. */
  strategicReport: string | null = null;
  strategicMetrics: StrategicMetrics | null = null;
  strategicSections: MdSection[] = [];
  weekHover: number | null = null;
  auditReport: string | null = null;
  strategicGenerating = false;
  exporting = false;


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
      title: 'Reportes',
      subtitle: 'Operación, cobranza y calidad de las sesiones',
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

  get executionPercent(): number {
    return this.financials.income_expected > 0
      ? (this.financials.income_real / this.financials.income_expected) * 100
      : 0;
  }

  generateAIReport() {
    if (this.strategicGenerating) return;
    this.strategicGenerating = true;
    this.cdr.markForCheck();
    this.subscriptions.add(
      this.adminService.generateAIReport().subscribe({
        next: (res) => {
          this.strategicGenerating = false;
          // Se muestra como texto (interpolación): nada de la respuesta del modelo se interpreta como HTML.
          this.strategicReport = (res?.report || '').trim() || null;
          this.strategicMetrics = (res as { metrics?: StrategicMetrics }).metrics ?? null;
          // Lo que ya se ve en las gráficas no se repite como texto: quedan el análisis, notas y recomendaciones.
          const shown = this.strategicMetrics ? /resumen|financ|top\s*terap|indicadores/i : /^$/;
          this.strategicSections = markdownSections(this.strategicReport || '').filter((sec) => !shown.test(sec.title));
          if (!this.strategicReport && !this.strategicMetrics) this.toastService.show('La IA no devolvió un análisis. Inténtalo de nuevo.', 'warning');
          this.cdr.markForCheck();
        },
        error: () => {
          this.strategicGenerating = false;
          this.toastService.show('No se pudo generar el análisis con IA.', 'error');
          this.cdr.markForCheck();
        },
      }),
    );
  }

  sendWeeklyReport() {
    if (this.reportSending) return;
    this.reportSending = true;
    this.cdr.markForCheck();
    this.subscriptions.add(
      this.adminService.sendWeeklyReport().subscribe({
        next: () => {
          this.reportSending = false;
          this.toastService.show('Reporte semanal enviado.', 'success');
          this.cdr.markForCheck();
        },
        error: () => {
          this.reportSending = false;
          this.toastService.show('No se pudo enviar el reporte semanal.', 'error');
          this.cdr.markForCheck();
        },
      }),
    );
  }

  exportCSV() {
    if (this.exporting) return;
    this.exporting = true;
    this.cdr.markForCheck();
    this.subscriptions.add(
      this.adminService.exportPaymentsCsv().subscribe({
        next: (blob) => {
          const url = window.URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = `pagos_${new Date().toISOString().slice(0, 10)}.csv`;
          a.click();
          setTimeout(() => window.URL.revokeObjectURL(url), 4000);
          this.exporting = false;
          this.cdr.markForCheck();
        },
        error: () => {
          this.exporting = false;
          this.toastService.show('No se pudo exportar el CSV de pagos.', 'error');
          this.cdr.markForCheck();
        },
      }),
    );
  }

  closeAIReport() {
    this.strategicReport = null;
    this.strategicMetrics = null;
    this.strategicSections = [];
  }

  // ── gráficas del análisis ─────────────────────────────────────────
  get weekMax() {
    return Math.max(1, ...(this.strategicMetrics?.weekly_sessions ?? []).map((w) => w.sessions));
  }

  weekLabel(iso: string) {
    const d = new Date(iso + 'T12:00:00');
    return d.toLocaleDateString('es-PE', { day: 'numeric', month: 'short' }).replace('.', '');
  }

  weeksSummary() {
    return (this.strategicMetrics?.weekly_sessions ?? []).map((w) => `${this.weekLabel(w.week_start)}: ${w.sessions}`).join(', ');
  }

  get topMax() {
    return Math.max(1, ...(this.strategicMetrics?.top_therapists ?? []).map((t) => t.sessions));
  }

  get moneyMax() {
    const f = this.strategicMetrics?.financial;
    return Math.max(1, f?.income_30d ?? 0, f?.expenses_30d ?? 0);
  }

  // ─── Formato en español y semáforo de precisión ───────────────
  private readonly nf = new Intl.NumberFormat('es-PE');
  private readonly mf = new Intl.NumberFormat('es-PE', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  private readonly pf = new Intl.NumberFormat('es-PE', { maximumFractionDigits: 1 });

  num(n: number | null | undefined) {
    return this.nf.format(n ?? 0);
  }

  money(n: number | null | undefined) {
    return `S/ ${this.mf.format(n ?? 0)}`;
  }

  pct(n: number | null | undefined) {
    return `${this.pf.format(n ?? 0)} %`;
  }

  /** Un solo criterio en toda la página (antes cada bloque usaba umbrales distintos y uno estaba en escala de 0 a 10). */
  level(n: number | null | undefined): 'good' | 'warn' | 'bad' {
    const v = n ?? 0;
    return v >= 85 ? 'good' : v >= 70 ? 'warn' : 'bad';
  }

  min100(n: number) {
    return Math.max(0, Math.min(100, n || 0));
  }

  max0(n: number) {
    return Math.max(0, n || 0);
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
    this.auditReport = null;

    this.subscriptions.add(
      this.adminService.generateIAReport().subscribe({
        next: (res: any) => {
          this.aiGenerating = false;
          if (res.success) {
          this.auditReport = DOMPurify.sanitize(res.report, { ALLOWED_TAGS: ['b', 'i', 'em', 'strong', 'a', 'ul', 'ol', 'li', 'br', 'p', 'h1', 'h2', 'h3', 'h4', 'pre', 'code', 'table', 'thead', 'tbody', 'tr', 'th', 'td', 'blockquote'], ALLOWED_ATTR: ['href'] });
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
          this.toastService.show('No se pudieron cargar los reportes diarios.', 'error');
          this.cdr.markForCheck();
        },
      }),
    );
  }

  accumulateReports() {
    this.reportsAccumulating = true;
    this.subscriptions.add(
      this.adminService.accumulateReports(this.selectedWeekStart || undefined).subscribe({
        next: (res) => {
          this.reportsAccumulating = false;
          if (res.success) {
            this.toastService.show(res.message, res.pairs ? 'success' : 'info');
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

  toggleTherapist(key: string) {
    if (this.expandedTherapists.has(key)) {
      this.expandedTherapists.delete(key);
    } else {
      this.expandedTherapists.add(key);
    }
  }

  isTherapistExpanded(key: string): boolean {
    return this.expandedTherapists.has(key);
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
