import { Component, OnInit } from '@angular/core';
import { HeaderService } from '../../../../core/services/header.service';
import { PatientService, PatientProgress } from '../../../../core/services/patient.service';
import { fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter } from '../../../../core/animations';

@Component({
  selector: 'app-patient-progress',
  standalone: false,
  templateUrl: './progress.html',
  styleUrl: './progress.scss',
  animations: [fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter]
})
export class PatientProgressPage implements OnInit {
  loading = true;
  data: PatientProgress | null = null;

  constructor(
    private headerService: HeaderService,
    private patientService: PatientService
  ) {}

  ngOnInit() {
    this.headerService.setConfig({
      title: 'Mi Progreso',
      subtitle: 'Evolución de tu rendimiento',
      icon: ['fas', 'chart-line'],
    });
    this.loadProgress();
  }

  private loadProgress() {
    this.patientService.getProgress().subscribe({
      next: (res) => {
        if (res.success) this.data = res.data;
        this.loading = false;
      },
      error: () => (this.loading = false),
    });
  }
}
