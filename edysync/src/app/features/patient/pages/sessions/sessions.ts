import { Component, OnInit } from '@angular/core';
import { HeaderService } from '../../../../core/services/header.service';
import { PatientService, PatientSession } from '../../../../core/services/patient.service';
import { fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter } from '../../../../core/animations';

@Component({
  selector: 'app-patient-sessions',
  standalone: false,
  templateUrl: './sessions.html',
  styleUrl: './sessions.scss',
  animations: [fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter]
})
export class PatientSessions implements OnInit {
  loading = true;
  sessions: PatientSession[] = [];

  constructor(
    private headerService: HeaderService,
    private patientService: PatientService
  ) {}

  ngOnInit() {
    this.headerService.setConfig({
      title: 'Mis Sesiones',
      subtitle: 'Historial de tus sesiones de terapia',
      icon: ['fas', 'calendar-alt'],
    });
    this.loadSessions();
  }

  private loadSessions() {
    this.patientService.getSessions().subscribe({
      next: (res) => {
        if (res.success) this.sessions = res.data;
        this.loading = false;
      },
      error: () => (this.loading = false),
    });
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
      scheduled: 'bg-blue-100 text-blue-700',
      completed: 'bg-green-100 text-green-700',
      cancelled: 'bg-gray-100 text-gray-500',
    };
    return map[status] || 'bg-gray-100 text-gray-500';
  }
}
