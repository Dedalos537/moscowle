import { Component, OnInit, OnDestroy, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { ActivatedRoute, Router } from '@angular/router';
import { Subscription } from 'rxjs';
import { AdminService } from '../../../../core/services/admin.service';
import { Payment } from '../../../../core/models/payment';
import { fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter } from '../../../../core/animations';
import { firstValueFrom } from 'rxjs';
import { ConfirmService } from '../../../../core/services/confirm.service';
import { Button } from '../../../../shared/components/button/button';
import { Spinner } from '../../../../shared/components/spinner/spinner';

@Component({
  selector: 'app-payment-history',
  standalone: true,
  templateUrl: './payment-history.html',
  styleUrl: './payment-history.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
  animations: [fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter],
  imports: [CommonModule, FontAwesomeModule, Button, Spinner],
})
export class PaymentHistory implements OnInit, OnDestroy {
  userId!: number;
  patientName = '';
  payments: Payment[] = [];
  loading = true;
  error: string | null = null;
  private subscriptions: Subscription = new Subscription();

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private adminService: AdminService,
    private confirmService: ConfirmService,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit() {
    this.userId = Number(this.route.snapshot.paramMap.get('userId'));
    this.loadHistory();
  }

  ngOnDestroy() {
    this.subscriptions.unsubscribe();
  }

  loadHistory() {
    this.loading = true;
    this.error = null;
    this.subscriptions.add(
      this.adminService.getPaymentHistory(this.userId).subscribe({
        next: (res) => {
          if (res.success && res.payments) {
            this.payments = res.payments;
            this.patientName = res.patient?.username || 'Paciente';
          }
          this.loading = false;
          this.cdr.markForCheck();
        },
        error: (err) => { this.loading = false; this.error = err.error?.message || err.message || 'Error al cargar historial de pagos'; this.cdr.markForCheck(); },
      })
    );
  }

  get totalPaid(): number {
    return this.payments.filter((p) => p.status === 'completed').reduce((sum, p) => sum + (p.amount || 0), 0);
  }

  get totalDiscounts(): number {
    return this.payments.reduce((sum, p) => sum + (p.discount || 0), 0);
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
        next: () => { this.loadHistory(); this.cdr.markForCheck(); },
        error: (err) => { this.error = err.error?.message || err.message || 'Error al eliminar pago'; this.cdr.markForCheck(); },
      })
    );
  }

  getMethodIcon(method: string): string {
    const map: Record<string, string> = { yape: 'mobile-alt', plin: 'mobile-alt', transfer: 'exchange-alt', cash: 'money-bill', card: 'credit-card' };
    return map[method] || 'receipt';
  }

  goBack() {
    this.router.navigate(['/admin/payments']);
  }
}
