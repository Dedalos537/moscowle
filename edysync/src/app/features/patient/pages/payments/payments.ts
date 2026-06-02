import { Component, OnInit, OnDestroy, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { Subscription } from 'rxjs';
import { HeaderService } from '../../../../core/services/header.service';
import { PatientService, PatientPayment } from '../../../../core/services/patient.service';
import { fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter } from '../../../../core/animations';
import { Spinner } from '../../../../shared/components/spinner/spinner';

@Component({
  selector: 'app-patient-payments',
  standalone: true,
  imports: [CommonModule, FontAwesomeModule, Spinner],
  templateUrl: './payments.html',
  styleUrl: './payments.scss',
  animations: [fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class PatientPayments implements OnInit, OnDestroy {
  loading = true;
  payments: PatientPayment[] = [];
  error: string | null = null;

  private subs = new Subscription();

  constructor(
    private headerService: HeaderService,
    private patientService: PatientService,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit() {
    this.headerService.setConfig({
      title: 'Mis Pagos',
      subtitle: 'Historial de tus pagos',
      icon: ['fas', 'file-invoice-dollar'],
    });
    this.loadPayments();
  }

  ngOnDestroy() {
    this.subs.unsubscribe();
  }

  private loadPayments() {
    this.subs.add(this.patientService.getPayments().subscribe({
      next: (res) => {
        if (res.success) this.payments = res.data;
        this.loading = false;
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.loading = false;
        this.error = err.message;
        this.cdr.markForCheck();
      },
    }));
  }

  getStatusClass(status: string): string {
    const map: Record<string, string> = {
      completed: 'bg-success-container text-success',
      pending: 'bg-warning-container text-warning',
      cancelled: 'bg-error-container text-on-error-container',
    };
    return map[status] || 'bg-surface-container-high text-on-surface-variant';
  }
}
