import { Component, OnInit, OnDestroy, ViewChild, TemplateRef } from '@angular/core';
import { AdminService } from '../../../../core/services/admin.service';
import { HeaderService } from '../../../../core/services/header.service';
import { TherapistStats, PatientStats } from '../../../../core/models/expense';

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
})
export class Reports implements OnInit, OnDestroy {
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
  // --- AUDITORIA IA ---
  auditStats: any = { total: 0, avg_score: 0, recent: [], by_therapist: [] };

  loading = true;
  aiGenerating = false;
  reportSending = false;
  aiReport: string | null = null;

  constructor(
    private adminService: AdminService,
    private headerService: HeaderService,
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
    
    this.adminService.getAuditStats().subscribe({
      next: (res: any) => {
        if (res.success && res.data) {
          this.auditStats = res.data;
        }
      },
      error: (err) => console.error("Error cargando Stats Auditoria", err)
    });

    this.adminService.getFinancialSummary().subscribe({
      next: (res) => {
        if (res.success && res.data) {
          this.financials = res.data;
        }
      },
    });

    this.adminService.getTherapistStats().subscribe({
      next: (res) => (this.therapists = res.data),
    });

    this.adminService.getPatientStats().subscribe({
      next: (res) => {
        this.patients = res.data;
        this.loading = false;
      },
      error: () => (this.loading = false),
    });
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
    if (!confirm('Esta operación tomará 1-2 minutos y analizará las últimas notas transcritas. ¿Continuar?')) {
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
          alert('Error: ' + res.error);
        }
      },
      error: (err) => {
        this.aiGenerating = false;
        alert('Error de conexión al generar el reporte.');
        console.error(err);
      }
    })
  }

}