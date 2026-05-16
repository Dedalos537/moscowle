import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { AdminService } from '../../../../core/services/admin.service';
import { Payment } from '../../../../core/models/payment';
import { fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter } from '../../../../core/animations';

@Component({
  selector: 'app-payment-history',
  standalone: false,
  templateUrl: './payment-history.html',
  styleUrl: './payment-history.scss',
  animations: [fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter]
})
export class PaymentHistory implements OnInit {
  userId!: number;
  patientName = '';
  payments: Payment[] = [];
  loading = true;

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private adminService: AdminService,
  ) {}

  ngOnInit() {
    this.userId = Number(this.route.snapshot.paramMap.get('userId'));
    this.loadHistory();
  }

  private loadHistory() {
    this.loading = true;
    this.adminService.getPaymentHistory(this.userId).subscribe({
      next: (res) => {
        if (res.success && res.payments) {
          this.payments = res.payments;
          this.patientName = res.patient?.username || 'Paciente';
        }
        this.loading = false;
      },
      error: () => (this.loading = false),
    });
  }

  get totalPaid(): number {
    return this.payments.filter((p) => p.status === 'completed').reduce((sum, p) => sum + (p.amount || 0), 0);
  }

  get totalDiscounts(): number {
    return this.payments.reduce((sum, p) => sum + (p.discount || 0), 0);
  }

  deletePayment(id: number) {
    if (!confirm('¿Eliminar este pago?')) return;
    this.adminService.deletePayment(id).subscribe({
      next: () => this.loadHistory(),
    });
  }

  getMethodIcon(method: string): string {
    const map: Record<string, string> = { yape: 'mobile-alt', plin: 'mobile-alt', transfer: 'exchange-alt', cash: 'money-bill', card: 'credit-card' };
    return map[method] || 'receipt';
  }

  goBack() {
    this.router.navigate(['/admin/payments']);
  }
}
