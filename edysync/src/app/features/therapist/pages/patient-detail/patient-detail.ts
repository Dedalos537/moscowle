import { Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { HeaderService } from '../../../../core/services/header.service';
import { HttpClient } from '@angular/common/http';
import { fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter } from '../../../../core/animations';

@Component({
  selector: 'app-therapist-patient-detail',
  standalone: false,
  templateUrl: './patient-detail.html',
  styleUrl: './patient-detail.scss',
  animations: [fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter]
})
export class TherapistPatientDetail implements OnInit {
  loading = true;
  patientId!: number;
  patient: any = null;
  sessions: any[] = [];

  constructor(
    private route: ActivatedRoute,
    private headerService: HeaderService,
    private http: HttpClient
  ) {}

  ngOnInit() {
    this.patientId = Number(this.route.snapshot.paramMap.get('id'));
    this.loadPatientData();
  }

  private loadPatientData() {
    this.http.get(`/therapist/patients/${this.patientId}`).subscribe({
      next: (res: any) => {
        this.headerService.setConfig({
          title: res.patient?.username || 'Paciente',
          subtitle: 'Detalle completo del paciente',
          icon: ['fas', 'user'],
        });
        this.patient = res.patient;
        this.sessions = res.recent_sessions || [];
        this.loading = false;
      },
      error: () => (this.loading = false),
    });
  }
}
