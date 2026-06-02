import { Component, OnInit, OnDestroy, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { Subscription } from 'rxjs';
import { HeaderService } from '../../../../core/services/header.service';
import { PatientService, PatientDashboardData } from '../../../../core/services/patient.service';
import { fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter } from '../../../../core/animations';
import { Spinner } from '../../../../shared/components/spinner/spinner';
import { Card } from '../../../../shared/components/card/card';

@Component({
  selector: 'app-patient-dashboard',
  standalone: true,
  imports: [CommonModule, RouterModule, FontAwesomeModule, Spinner, Card],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.scss',
  animations: [fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class PatientDashboard implements OnInit, OnDestroy {
  loading = true;
  data: PatientDashboardData | null = null;
  error: string | null = null;

  private subs = new Subscription();

  constructor(
    private headerService: HeaderService,
    private patientService: PatientService,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit() {
    this.headerService.setConfig({
      title: 'Mi Panel',
      subtitle: 'Resumen de tus actividades',
      icon: ['fas', 'home'],
    });
    this.loadData();
  }

  ngOnDestroy() {
    this.subs.unsubscribe();
  }

  private loadData() {
    this.subs.add(this.patientService.getDashboard().subscribe({
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
