import { Component, OnInit, OnDestroy, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { Subscription } from 'rxjs';
import { HeaderService } from '../../../../core/services/header.service';
import { PatientService, PatientSession } from '../../../../core/services/patient.service';
import { fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter } from '../../../../core/animations';

@Component({
  selector: 'app-patient-sessions',
  standalone: false,
  templateUrl: './sessions.html',
  styleUrl: './sessions.scss',
  animations: [fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class PatientSessions implements OnInit, OnDestroy {
  loading = true;
  sessions: PatientSession[] = [];
  error: string | null = null;

  private subs = new Subscription();

  constructor(
    private headerService: HeaderService,
    private patientService: PatientService,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit() {
    this.headerService.setConfig({
      title: 'Mis Sesiones',
      subtitle: 'Historial de tus sesiones de terapia',
      icon: ['fas', 'calendar-alt'],
    });
    this.loadSessions();
  }

  ngOnDestroy() {
    this.subs.unsubscribe();
  }

  private loadSessions() {
    this.subs.add(this.patientService.getSessions().subscribe({
      next: (res) => {
        if (res.success) this.sessions = res.data;
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

  getStatusLabel(status: string): string {
    const map: Record<string, string> = {
      scheduled: 'Programada',
      completed: 'Completada',
      cancelled: 'Cancelada',
    };
    return map[status] || status;
  }

  getStatusClass(status: string): string {
    const map: Record<string, string> = {
      scheduled: 'bg-info-container text-info',
      completed: 'bg-success-container text-success',
      cancelled: 'bg-surface-container-high text-on-surface-variant',
    };
    return map[status] || 'bg-surface-container-high text-on-surface-variant';
  }
}
