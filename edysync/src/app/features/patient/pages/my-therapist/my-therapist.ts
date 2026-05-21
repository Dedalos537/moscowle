// DCE — Diego Centeno Estuvo Acá
import { Component, OnInit } from '@angular/core';
import { HeaderService } from '../../../../core/services/header.service';
import { PatientService, MyTherapistInfo } from '../../../../core/services/patient.service';
import { fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter } from '../../../../core/animations';

@Component({
  selector: 'app-patient-my-therapist',
  standalone: false,
  templateUrl: './my-therapist.html',
  styleUrl: './my-therapist.scss',
  animations: [fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter]
})
export class PatientMyTherapist implements OnInit {
  loading = true;
  therapist: MyTherapistInfo | null = null;

  constructor(
    private headerService: HeaderService,
    private patientService: PatientService
  ) {}

  ngOnInit() {
    this.headerService.setConfig({
      title: 'Mi Terapeuta',
      subtitle: 'Información de tu terapeuta asignado',
      icon: ['fas', 'user-md'],
    });
    this.loadTherapist();
  }

  private loadTherapist() {
    this.patientService.getMyTherapist().subscribe({
      next: (res) => {
        if (res.success) this.therapist = res.data;
        this.loading = false;
      },
      error: () => (this.loading = false),
    });
  }
}
