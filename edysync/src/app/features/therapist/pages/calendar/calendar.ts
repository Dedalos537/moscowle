import { Component, OnInit } from '@angular/core';
import { HeaderService } from '../../../../core/services/header.service';
import { TherapistService } from '../../../../core/services/therapist.service';
import { CalendarWidgetEvent } from '../../../../shared/components/calendar-widget/calendar-widget';
import { fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter } from '../../../../core/animations';

@Component({
  selector: 'app-therapist-calendar',
  standalone: false,
  templateUrl: './calendar.html',
  styleUrl: './calendar.scss',
  animations: [fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter]
})
export class TherapistCalendarPage implements OnInit {
  loading = true;
  widgetEvents: CalendarWidgetEvent[] = [];

  constructor(
    private headerService: HeaderService,
    private therapistService: TherapistService,
  ) {}

  ngOnInit() {
    this.headerService.setConfig({
      title: 'Calendario',
      subtitle: 'Vista general de tus sesiones',
      icon: ['fas', 'calendar-alt'],
    });
    this.loadSessions();
  }

  private loadSessions() {
    const now = new Date();
    const start = new Date(now.getFullYear(), now.getMonth() - 1, 1).toISOString().split('T')[0];
    const end = new Date(now.getFullYear(), now.getMonth() + 2, 0).toISOString().split('T')[0];

    this.therapistService.getSessions(start, end).subscribe({
      next: (events) => {
        this.widgetEvents = events.map((e: any) => ({
          id: e.id,
          title: e.title,
          date: new Date(e.start),
          time: e.start ? new Date(e.start).toTimeString().substring(0, 5) : undefined,
          endTime: e.end ? new Date(e.end).toTimeString().substring(0, 5) : undefined,
          status: e.extendedProps?.status || 'scheduled',
          therapist: e.extendedProps?.therapist,
          patient: e.extendedProps?.patient,
        }));
        this.loading = false;
      },
      error: () => (this.loading = false),
    });
  }
}
