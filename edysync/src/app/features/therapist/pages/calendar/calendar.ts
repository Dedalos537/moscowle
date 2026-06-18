import { CommonModule } from '@angular/common';
import { Component, OnInit, OnDestroy, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { Subscription } from 'rxjs';
import { HeaderService } from '../../../../core/services/header.service';
import { TherapistService } from '../../../../core/services/therapist.service';
import { CalendarWidgetEvent } from '../../../../shared/components/calendar-widget/calendar-widget';
import { fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter } from '../../../../core/animations';
import { Spinner } from '../../../../shared/components/spinner/spinner';
import { CalendarWidget } from '../../../../shared/components/calendar-widget/calendar-widget';
import { toLocalDateString } from '../../../../core/utils/date.util';

@Component({
  selector: 'app-therapist-calendar',
  standalone: true,
  imports: [CommonModule, Spinner, CalendarWidget],
  templateUrl: './calendar.html',
  styleUrl: './calendar.scss',
  animations: [fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class TherapistCalendarPage implements OnInit, OnDestroy {
  loading = true;
  widgetEvents: CalendarWidgetEvent[] = [];
  error: string | null = null;

  private subs = new Subscription();

  constructor(
    private headerService: HeaderService,
    private therapistService: TherapistService,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit() {
    this.headerService.setConfig({
      title: 'Calendario',
      subtitle: 'Vista general de tus sesiones',
      icon: ['fas', 'calendar-alt'],
    });
    this.loadSessions();
  }

  ngOnDestroy() {
    this.subs.unsubscribe();
  }

  private loadSessions() {
    const now = new Date();
    const start = toLocalDateString(new Date(now.getFullYear(), now.getMonth() - 1, 1));
    const end = toLocalDateString(new Date(now.getFullYear(), now.getMonth() + 2, 0));

    this.subs.add(this.therapistService.getSessions(start, end).subscribe({
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
