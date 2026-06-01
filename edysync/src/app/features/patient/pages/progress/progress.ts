import { Component, OnInit, OnDestroy, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { Subscription } from 'rxjs';
import { HeaderService } from '../../../../core/services/header.service';
import { PatientService, PatientProgress } from '../../../../core/services/patient.service';
import { fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter } from '../../../../core/animations';

@Component({
  selector: 'app-patient-progress',
  standalone: false,
  templateUrl: './progress.html',
  styleUrl: './progress.scss',
  animations: [fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class PatientProgressPage implements OnInit, OnDestroy {
  loading = true;
  data: PatientProgress | null = null;
  error: string | null = null;

  private subs = new Subscription();

  constructor(
    private headerService: HeaderService,
    private patientService: PatientService,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit() {
    this.headerService.setConfig({
      title: 'Mi Progreso',
      subtitle: 'Evolución de tu rendimiento',
      icon: ['fas', 'chart-line'],
    });
    this.loadProgress();
  }

  ngOnDestroy() {
    this.subs.unsubscribe();
  }

  private loadProgress() {
    this.subs.add(this.patientService.getProgress().subscribe({
      next: (res) => {
        if (res.success) this.data = res.data;
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
}
