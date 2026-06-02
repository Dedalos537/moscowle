import { CommonModule } from '@angular/common';
import { Component, OnInit, OnDestroy, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { Subscription } from 'rxjs';
import { HeaderService } from '../../../../core/services/header.service';
import { TherapistService } from '../../../../core/services/therapist.service';
import { HttpClient } from '@angular/common/http';
import { fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter } from '../../../../core/animations';
import { Spinner } from '../../../../shared/components/spinner/spinner';
import { Button } from '../../../../shared/components/button/button';

@Component({
  selector: 'app-therapist-patient-detail',
  standalone: true,
  imports: [CommonModule, FontAwesomeModule, Spinner, Button],
  templateUrl: './patient-detail.html',
  styleUrl: './patient-detail.scss',
  animations: [fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class TherapistPatientDetail implements OnInit, OnDestroy {
  loading = true;
  patientId!: number;
  patient: any = null;
  sessions: any[] = [];
  error: string | null = null;

  weeklyReport: any = null;
  weeklyReportLoading = false;
  weeklyReportGenerating = false;

  private subs = new Subscription();

  constructor(
    private route: ActivatedRoute,
    private headerService: HeaderService,
    private therapistService: TherapistService,
    private http: HttpClient,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit() {
    this.patientId = Number(this.route.snapshot.paramMap.get('id'));
    this.loadPatientData();
  }

  ngOnDestroy() {
    this.subs.unsubscribe();
  }

  private loadPatientData() {
    this.subs.add(this.http.get(`/therapist/patients/${this.patientId}`).subscribe({
      next: (res: any) => {
        this.headerService.setConfig({
          title: res.patient?.username || 'Paciente',
          subtitle: 'Detalle completo del paciente',
          icon: ['fas', 'user'],
        });
        this.patient = res.patient;
        this.sessions = res.recent_sessions || [];
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

  generateWeeklyReport() {
    this.weeklyReportGenerating = true;
    this.weeklyReport = null;
    this.cdr.markForCheck();
    this.subs.add(this.therapistService.generateWeeklyReport(this.patientId).subscribe({
      next: (res) => {
        this.weeklyReportGenerating = false;
        if (res.success) {
          this.weeklyReport = res.report;
          this.loadWeeklyReport();
        }
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.weeklyReportGenerating = false;
        this.error = err.message;
        this.cdr.markForCheck();
      },
    }));
  }

  loadWeeklyReport() {
    this.weeklyReportLoading = true;
    this.cdr.markForCheck();
    this.subs.add(this.therapistService.getWeeklyReport(this.patientId).subscribe({
      next: (res) => {
        this.weeklyReportLoading = false;
        if (res.success && res.report) {
          this.weeklyReport = res.report;
        }
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.weeklyReportLoading = false;
        this.error = err.message;
        this.cdr.markForCheck();
      },
    }));
  }
}
