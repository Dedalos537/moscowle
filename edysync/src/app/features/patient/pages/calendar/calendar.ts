import { Component, OnInit } from '@angular/core';
import { HeaderService } from '../../../../core/services/header.service';
import { PatientService } from '../../../../core/services/patient.service';
import { CalendarWidgetEvent } from '../../../../shared/components/calendar-widget/calendar-widget';
import { fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter } from '../../../../core/animations';

@Component({
  selector: 'app-patient-calendar',
  standalone: false,
  templateUrl: './calendar.html',
  styleUrl: './calendar.scss',
  animations: [fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter]
})
export class PatientCalendar implements OnInit {
  loading = true;
  widgetEvents: CalendarWidgetEvent[] = [];

  constructor(
    private headerService: HeaderService,
    private patientService: PatientService,
  ) {}

  ngOnInit() {
    this.headerService.setConfig({
      title: 'Calendario',
      subtitle: 'Tus sesiones programadas',
      icon: ['fas', 'calendar-day'],
    });
    this.loadSessions();
  }

  private loadSessions() {
    this.patientService.getSessions().subscribe({
      next: (res) => {
        if (res.success) {
          this.widgetEvents = res.data.map((s) => ({
            id: s.id,
            title: s.title,
            date: new Date(s.start_time),
            time: s.start_time ? new Date(s.start_time).toTimeString().substring(0, 5) : undefined,
            endTime: s.end_time ? new Date(s.end_time).toTimeString().substring(0, 5) : undefined,
            status: (s.status as 'scheduled' | 'completed' | 'cancelled') || 'scheduled',
          }));
        }
        this.loading = false;
      },
      error: () => (this.loading = false),
    });
  }
}
