import { Component, OnInit } from '@angular/core';
import { HeaderService } from '../../../../core/services/header.service';
import { PatientService, PatientPayment } from '../../../../core/services/patient.service';
import { fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter } from '../../../../core/animations';

@Component({
  selector: 'app-patient-payments',
  standalone: false,
  templateUrl: './payments.html',
  styleUrl: './payments.scss',
  animations: [fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter]
})
export class PatientPayments implements OnInit {
  loading = true;
  payments: PatientPayment[] = [];

  constructor(
    private headerService: HeaderService,
    private patientService: PatientService
  ) {}

  ngOnInit() {
    this.headerService.setConfig({
      title: 'Mis Pagos',
      subtitle: 'Historial de tus pagos',
      icon: ['fas', 'file-invoice-dollar'],
    });
    this.loadPayments();
  }

  private loadPayments() {
    this.patientService.getPayments().subscribe({
      next: (res) => {
        if (res.success) this.payments = res.data;
        this.loading = false;
      },
      error: () => (this.loading = false),
    });
  }

  getStatusClass(status: string): string {
    const map: Record<string, string> = {
      completed: 'bg-green-100 text-green-700',
      pending: 'bg-amber-100 text-amber-700',
      cancelled: 'bg-red-100 text-red-700',
    };
    return map[status] || 'bg-gray-100 text-gray-500';
  }
}
