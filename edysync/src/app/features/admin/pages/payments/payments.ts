import { Component, OnInit, OnDestroy, ViewChild, TemplateRef } from '@angular/core';
import { AdminService } from '../../../../core/services/admin.service';
import { HeaderService } from '../../../../core/services/header.service';
import { Sede } from '../../../../core/models/sede';

interface PaymentInfo {
  id: number;
  patient_id: number;
  amount: number;
  discount: number;
  method: string;
  reference?: string;
  date: string;
  status: string;
  patient?: { id: number; username: string };
}

interface PatientStatus {
  id: number;
  username: string;
  email: string;
  sede_name: string;
  payment_amount: number;
  sessions_total: number;
  sessions_attended: number;
  sessions_remaining: number;
  status: string;
  phone?: string;
}

@Component({
  selector: 'app-payments',
  standalone: false,
  templateUrl: './payments.html',
  styleUrl: './payments.scss',
})
export class Payments implements OnInit, OnDestroy {
  @ViewChild('headerActions', { static: true }) headerActions!: TemplateRef<any>;

  patients: PatientStatus[] = [];
  paymentHistory: PaymentInfo[] = [];
  sedes: Sede[] = [];
  loading = true;
  searchQuery = '';
  selectedSedeId: number | null = null;

  showRegisterModal = false;
  registerForm = { patient_id: null as number | null, amount: 0, method: 'transfer', reference: '', next_due_date: '', discount: 0, receipt: null as File | null };
  registerStatus = '';
  analyzeResult: any = null;

  constructor(
    private adminService: AdminService,
    private headerService: HeaderService,
  ) {}

  ngOnInit() {
    this.headerService.setConfig({
      title: 'Pagos y Finanzas',
      subtitle: 'Control de ingresos, deudores y estadísticas',
      icon: ['fas', 'credit-card'],
      actionTemplate: this.headerActions,
    });
    this.loadSedes();
    this.loadData();
  }

  ngOnDestroy() {
    this.headerService.reset();
  }

  private loadSedes() {
    this.adminService.getSedes().subscribe({
      next: (list) => (this.sedes = list),
    });
  }

  private loadData() {
    this.adminService.getDebtReport('all').subscribe({
      next: (res) => {
        if (res.success && res.data) {
          const porSede: Record<string, any> = res.data.por_sede || {};
          const list: PatientStatus[] = [];
          Object.values(porSede).forEach((group: any) => {
            (group.deudores || []).forEach((d: any) => {
              list.push({
                id: d.id || 0,
                username: d.paciente || d.email || 'Sin nombre',
                email: d.email || '',
                sede_name: group.sede_name || '',
                payment_amount: d.monto || 0,
                sessions_total: d.sessions_total || 0,
                sessions_attended: d.sessions_attended || 0,
                sessions_remaining: (d.sessions_total || 0) - (d.sessions_attended || 0),
                status: d.estado || 'active',
                phone: d.phone,
              });
            });
          });
          this.patients = list;
        }
        this.loading = false;
      },
      error: () => (this.loading = false),
    });
  }

  get filteredPatients(): PatientStatus[] {
    let result = [...this.patients];
    if (this.searchQuery) {
      const q = this.searchQuery.toLowerCase();
      result = result.filter((p) => p.username.toLowerCase().includes(q) || p.email.toLowerCase().includes(q));
    }
    if (this.selectedSedeId) {
      result = result.filter((p) => p.sede_name === this.sedes.find((s) => s.id === this.selectedSedeId)?.name);
    }
    return result;
  }

  get totalIncomeReal(): number {
    return this.paymentHistory.filter((p) => p.status === 'completed').reduce((sum, p) => sum + p.amount - (p.discount || 0), 0);
  }

  get totalPending(): number {
    return this.patients.filter((p) => p.payment_amount > 0).reduce((sum, p) => sum + p.payment_amount, 0);
  }

  onFileSelected(event: Event) {
    const file = (event.target as HTMLInputElement).files?.[0] || null;
    this.registerForm.receipt = file;
    if (file) {
      this.adminService.analyzeReceipt(file).subscribe({
        next: (res) => {
          this.analyzeResult = res;
          if (res.amount) this.registerForm.amount = parseFloat(res.amount);
          if (res.reference) this.registerForm.reference = res.reference;
          if (res.method) this.registerForm.method = res.method;
        },
        error: () => {},
      });
    }
  }

  openRegisterModal(patient?: PatientStatus) {
    this.registerForm = { patient_id: patient?.id || null, amount: patient?.payment_amount || 0, method: 'transfer', reference: '', next_due_date: '', discount: 0, receipt: null };
    this.analyzeResult = null;
    this.registerStatus = '';
    this.showRegisterModal = true;
  }

  closeRegisterModal() {
    this.showRegisterModal = false;
  }

  submitPayment() {
    this.registerStatus = 'Registrando...';
    const formData = new FormData();
    if (this.registerForm.patient_id) formData.append('patient_id', String(this.registerForm.patient_id));
    formData.append('amount', String(this.registerForm.amount));
    formData.append('method', this.registerForm.method);
    if (this.registerForm.reference) formData.append('reference', this.registerForm.reference);
    if (this.registerForm.next_due_date) formData.append('next_due_date', this.registerForm.next_due_date);
    formData.append('discount', String(this.registerForm.discount));
    if (this.registerForm.receipt) formData.append('receipt', this.registerForm.receipt);

    this.adminService.registerPayment(formData).subscribe({
      next: (res: any) => {
        if (res.success) {
          this.registerStatus = 'Pago registrado exitosamente';
          setTimeout(() => {
            this.closeRegisterModal();
            this.loadData();
          }, 1500);
        } else {
          this.registerStatus = 'Error: ' + (res.message || res.error || 'Desconocido');
        }
      },
      error: () => {
        this.registerStatus = 'Error de conexión al servidor';
      },
    });
  }

  deletePayment(id: number) {
    if (!confirm('¿Eliminar este pago?')) return;
    this.adminService.deletePayment(id).subscribe({
      next: () => this.loadData(),
    });
  }

  getMethodIcon(method: string): string {
    const map: Record<string, string> = { yape: 'mobile-alt', plin: 'mobile-alt', transfer: 'exchange-alt', cash: 'money-bill', card: 'credit-card' };
    return map[method] || 'receipt';
  }

  onSedeChange(value: string) {
    this.selectedSedeId = value ? parseInt(value) : null;
  }

  sedeById(id: number): string {
    return this.sedes.find((s) => s.id === id)?.name || '';
  }

  getInitials(name: string): string {
    return name?.slice(0, 2).toUpperCase() || 'PA';
  }

  trackById(_: number, item: any): number {
    return item.id || item.patient_id;
  }
}
