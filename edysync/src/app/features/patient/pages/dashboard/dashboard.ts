// DCE — Diego Centeno Estuvo Acá
import { Component, OnInit } from '@angular/core';
import { HeaderService } from '../../../../core/services/header.service';
import { PatientService, PatientDashboardData } from '../../../../core/services/patient.service';
import { fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter } from '../../../../core/animations';

@Component({
  selector: 'app-patient-dashboard',
  standalone: false,
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.scss',
  animations: [fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter]
})
export class PatientDashboard implements OnInit {
  loading = true;
  data: PatientDashboardData | null = null;

  constructor(
    private headerService: HeaderService,
    private patientService: PatientService
  ) {}

  ngOnInit() {
    this.headerService.setConfig({
      title: 'Mi Panel',
      subtitle: 'Resumen de tus actividades',
      icon: ['fas', 'home'],
    });
    this.loadData();
  }

  private loadData() {
    this.patientService.getDashboard().subscribe({
      next: (res) => {
        if (res.success) this.data = res.data;
        this.loading = false;
      },
      error: () => (this.loading = false),
    });
  }
}
