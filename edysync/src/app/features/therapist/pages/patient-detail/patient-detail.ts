// DCE — Diego Centeno Estuvo Acá
import { Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { HeaderService } from '../../../../core/services/header.service';
import { TherapistService } from '../../../../core/services/therapist.service';
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

  // Weekly Report
  weeklyReport: any = null;
  weeklyReportLoading = false;
  weeklyReportGenerating = false;

  constructor(
    private route: ActivatedRoute,
    private headerService: HeaderService,
    private therapistService: TherapistService,
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

  generateWeeklyReport() {
    this.weeklyReportGenerating = true;
    this.weeklyReport = null;
    this.therapistService.generateWeeklyReport(this.patientId).subscribe({
      next: (res) => {
        this.weeklyReportGenerating = false;
        if (res.success) {
          this.weeklyReport = res.report;
          this.loadWeeklyReport();
        }
      },
      error: () => {
        this.weeklyReportGenerating = false;
      },
    });
  }

  loadWeeklyReport() {
    this.weeklyReportLoading = true;
    this.therapistService.getWeeklyReport(this.patientId).subscribe({
      next: (res) => {
        this.weeklyReportLoading = false;
        if (res.success && res.report) {
          this.weeklyReport = res.report;
        }
      },
      error: () => {
        this.weeklyReportLoading = false;
      },
    });
  }
}
