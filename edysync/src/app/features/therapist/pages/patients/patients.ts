import { CommonModule } from '@angular/common';
import { Component, OnInit, OnDestroy, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { RouterModule } from '@angular/router';
import { Subscription } from 'rxjs';
import { HeaderService } from '../../../../core/services/header.service';
import { TherapistService, PatientInfo } from '../../../../core/services/therapist.service';
import { fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter } from '../../../../core/animations';
import { Spinner } from '../../../../shared/components/spinner/spinner';

@Component({
  selector: 'app-therapist-patients',
  standalone: true,
  imports: [CommonModule, RouterModule, FontAwesomeModule, Spinner],
  templateUrl: './patients.html',
  styleUrl: './patients.scss',
  animations: [fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class TherapistPatients implements OnInit, OnDestroy {
  loading = true;
  error: string | null = null;
  patients: (PatientInfo & { status_label?: string; status_color?: string })[] = [];

  private subs = new Subscription();

  constructor(
    private headerService: HeaderService,
    private therapistService: TherapistService,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit() {
    this.headerService.setConfig({
      title: 'Mis Pacientes',
      subtitle: 'Gestiona tus pacientes asignados',
      icon: ['fas', 'user-friends'],
    });
    this.loadPatients();
  }

  ngOnDestroy() {
    this.subs.unsubscribe();
  }

  private loadPatients() {
    this.subs.add(this.therapistService.getPatients().subscribe({
      next: (list) => {
        this.patients = list.map((p) => ({
          ...p,
          status_label: 'Activo',
          status_color: 'bg-success-container text-success',
        }));
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
