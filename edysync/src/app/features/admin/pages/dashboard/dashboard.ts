import { Component, OnInit, OnDestroy, ViewChild, TemplateRef } from '@angular/core';
import { AdminService } from '../../../../core/services/admin.service';
import { HeaderService } from '../../../../core/services/header.service';
import { Sede } from '../../../../core/models/sede';

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
  standalone: false,
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.scss',
  animations: []
})
export class Dashboard implements OnInit, OnDestroy {
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
  today = new Date();
  showGuidanceModal = false;
  showDailyModal = false;

  constructor(
    private adminService: AdminService,
    private headerService: HeaderService,
  ) {}

  ngOnInit() {
    this.headerService.setConfig({
      title: 'Panel de Administración',
      subtitle: 'Control integral de terapeutas y pacientes',
      icon: ['fas', 'shield-alt'],
      actionTemplate: this.headerActions,
    });
    this.loadAll();
  }

  ngOnDestroy() {
    this.headerService.reset();
  }

  private loadAll() {
    this.loadUserCounts();
    this.loadSedes();
    this.loadDebtData();
  }
  
  private setFinancialSummary() {
    this.adminService.getFinancialSummary().subscribe({
      next: (res) => {
        if (res.success && res.data && this.financials) {
          this.financials.income_real = res.data.income_real;
        }
      },
    });
  }

  private loadUserCounts() {
    this.adminService.getOverview().subscribe({
      next: (res) => {
        if (res.success && res.users) {
          this.therapistCount = res.users.filter((u) => u.role === 'terapista').length;
          this.patientCount = res.users.filter((u) => u.role === 'jugador').length;
          this.summary = { therapists: this.therapistCount, patients: this.patientCount, sessions_total: '-', avg_accuracy: '-' };
        }
        this.loading = false;
      },
      error: () => {
        this.loading = false;
      },
    });
    this.adminService.getAdminOverview().subscribe({
      next: (res) => {
        if (res.success && res.data) {
          this.avgAuditCompliance = res.data.avg_audit_compliance;
          this.auditsCount = res.data.audits_count;
          this.summary.sessions_total = res.data.sessions_total;
        }
      },
    });
  }

  private loadSedes() {
    this.adminService.getSedes().subscribe({
      next: (list) => {
        this.sedes = list;
      },
    });
  }

  private loadDebtData() {
    this.adminService.getDebtReport('all').subscribe({
      next: (res) => {
        if (!res.success || !res.data) return;
        const porSede: Record<string, any> = res.data.por_sede || {};
        const todayDay = this.today.getDate();

        let incomeReal = 0;
        let incomeExpected = 0;
        let overdueAmount = 0;
        let overdueCount = 0;
        const stats: SedeStat[] = [];
        const incomplete: IncompletePatient[] = [];
        const daily: DailyPending[] = [];

        Object.values(porSede).forEach((group: any) => {
          const sedeName = group.sede_name || '';
          const deudores: any[] = group.deudores || [];
          stats.push({ id: group.sede_id || 0, name: sedeName, count: deudores.length });

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
        this.sedesStats = stats;
        this.incompletePatients = incomplete;
        this.dailyPendings = daily;
        
        this.setFinancialSummary();

        if (incomplete.length > 5) {
          setTimeout(() => (this.showGuidanceModal = true), 2000);
        }
        if (daily.length > 0 && incomplete.length <= 5) {
          setTimeout(() => (this.showDailyModal = true), 2000);
        }
      },
    });
  }

  private loadFinancialSummary() {
    this.adminService.getFinancialSummary().subscribe({
      next: (res) => {
        if (res.success && res.data && this.financials) {
          this.financials.income_real = res.data.income_real;
        }
      },
    });
  }

  onPaymentCompleted() {
    this.loadAll();
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
