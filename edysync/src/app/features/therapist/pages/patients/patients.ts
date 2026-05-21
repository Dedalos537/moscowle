// DCE — Diego Centeno Estuvo Acá
import { Component, OnInit } from '@angular/core';
import { HeaderService } from '../../../../core/services/header.service';
import { TherapistService, PatientInfo } from '../../../../core/services/therapist.service';
import { HttpClient } from '@angular/common/http';
import { fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter } from '../../../../core/animations';

@Component({
  selector: 'app-therapist-patients',
  standalone: false,
  templateUrl: './patients.html',
  styleUrl: './patients.scss',
  animations: [fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter]
})
export class TherapistPatients implements OnInit {
  loading = true;
  patients: (PatientInfo & { status_label?: string; status_color?: string })[] = [];

  constructor(
    private headerService: HeaderService,
    private therapistService: TherapistService,
    private http: HttpClient
  ) {}

  ngOnInit() {
    this.headerService.setConfig({
      title: 'Mis Pacientes',
      subtitle: 'Gestiona tus pacientes asignados',
      icon: ['fas', 'user-friends'],
    });
    this.loadPatients();
  }

  private loadPatients() {
    this.therapistService.getPatients().subscribe({
      next: (list) => {
        this.patients = list.map((p) => ({
          ...p,
          status_label: 'Activo',
          status_color: 'bg-green-100 text-green-700',
        }));
        this.loading = false;
      },
      error: () => (this.loading = false),
    });
  }
}
