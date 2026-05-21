// DCE — Diego Centeno Estuvo Acá
import { Component, OnInit, OnDestroy, ViewChild, TemplateRef } from '@angular/core';
import { AdminService } from '../../../../core/services/admin.service';
import { HeaderService } from '../../../../core/services/header.service';
import { fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter } from '../../../../core/animations';

interface DebtGroup {
  sede_name: string;
  deudores: DebtorItem[];
  total_deuda: number;
}

interface DebtorItem {
  paciente: string;
  email: string;
  phone?: string;
  monto: number;
  modality?: string;
  fecha_vencimiento?: string;
  payment_day?: number;
  sede?: string;
}

@Component({
  selector: 'app-debtors',
  standalone: false,
  templateUrl: './debtors.html',
  styleUrl: './debtors.scss',
  animations: [fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter]
})
export class Debtors implements OnInit, OnDestroy {
  @ViewChild('headerActions', { static: true }) headerActions!: TemplateRef<any>;

  groups: DebtGroup[] = [];
  loading = true;
  selectedMonth = 'current';
  filterText = '';

  showPaymentModal = false;
  paymentForm = { patient_id: 0, patient_name: '', amount: 0, method: 'transfer', reference: '' };
  paymentStatus = '';

  constructor(
    private adminService: AdminService,
    private headerService: HeaderService,
  ) {}

  ngOnInit() {
    this.headerService.setConfig({
      title: 'Deudores',
      subtitle: 'Gestiona pagos pendientes por sede',
      icon: ['fas', 'credit-card'],
      actionTemplate: this.headerActions,
    });
    this.loadData();
  }

  ngOnDestroy() {
    this.headerService.reset();
  }

  loadData() {
    this.loading = true;
    this.adminService.getDebtReport(this.selectedMonth).subscribe({
      next: (res) => {
        if (res.success && res.data) {
          const porSede: Record<string, any> = res.data.por_sede || {};
          this.groups = Object.values(porSede).map((g: any) => ({
            sede_name: g.sede_name || 'Sin sede',
            deudores: (g.deudores || []).map((d: any) => ({
              paciente: d.paciente || d.email || 'Desconocido',
              email: d.email || '',
              phone: d.phone,
              monto: d.monto || 0,
              modality: d.modality || 'Sin Modalidad',
              fecha_vencimiento: d.fecha_vencimiento || 'N/A',
              payment_day: d.payment_day,
            })),
            total_deuda: g.deudores ? g.deudores.reduce((sum: number, d: any) => sum + (d.monto || 0), 0) : 0,
          }));
        }
        this.loading = false;
      },
      error: () => (this.loading = false),
    });
  }

  get filteredGroups(): DebtGroup[] {
    if (!this.filterText) return this.groups;
    const q = this.filterText.toLowerCase();
    return this.groups
      .map((g) => ({
        ...g,
        deudores: g.deudores.filter((d) => d.paciente.toLowerCase().includes(q)),
      }))
      .filter((g) => g.deudores.length > 0);
  }

  get totalDeuda(): number {
    return this.groups.reduce((sum, g) => sum + g.total_deuda, 0);
  }

  get totalDeudores(): number {
    return this.groups.reduce((sum, g) => sum + g.deudores.length, 0);
  }

  openPaymentModal(item: DebtorItem) {
    this.paymentForm = { patient_id: 0, patient_name: item.paciente, amount: item.monto, method: 'transfer', reference: '' };
    this.paymentStatus = '';
    this.showPaymentModal = true;
  }

  closePaymentModal() {
    this.showPaymentModal = false;
  }

  submitPayment() {
    this.paymentStatus = 'Registrando...';
    const formData = new FormData();
    formData.append('patient_id', String(this.paymentForm.patient_id || 0));
    formData.append('amount', String(this.paymentForm.amount));
    formData.append('method', this.paymentForm.method);
    formData.append('reference', this.paymentForm.reference);

    this.adminService.registerPayment(formData).subscribe({
      next: (res: any) => {
        if (res.success) {
          this.paymentStatus = 'Pago registrado';
          setTimeout(() => {
            this.closePaymentModal();
            this.loadData();
          }, 1500);
        } else {
          this.paymentStatus = 'Error: ' + (res.message || '');
        }
      },
      error: () => {
        this.paymentStatus = 'Error de conexión';
      },
    });
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

  onMonthChange(month: string) {
    this.selectedMonth = month;
    this.loadData();
  }
}
