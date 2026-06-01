import { Component, OnInit, OnDestroy, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { Subscription } from 'rxjs';
import { HeaderService } from '../../../../core/services/header.service';
import { PatientService, MyTherapistInfo } from '../../../../core/services/patient.service';
import { fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter } from '../../../../core/animations';

@Component({
  selector: 'app-patient-my-therapist',
  standalone: false,
  templateUrl: './my-therapist.html',
  styleUrl: './my-therapist.scss',
  animations: [fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class PatientMyTherapist implements OnInit, OnDestroy {
  loading = true;
  therapist: MyTherapistInfo | null = null;
  error: string | null = null;

  private subs = new Subscription();

  constructor(
    private headerService: HeaderService,
    private patientService: PatientService,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit() {
    this.headerService.setConfig({
      title: 'Mi Terapeuta',
      subtitle: 'Información de tu terapeuta asignado',
      icon: ['fas', 'user-md'],
    });
    this.loadTherapist();
  }

  ngOnDestroy() {
    this.subs.unsubscribe();
  }

  private loadTherapist() {
    this.subs.add(this.patientService.getMyTherapist().subscribe({
      next: (res) => {
        if (res.success) this.therapist = res.data;
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
