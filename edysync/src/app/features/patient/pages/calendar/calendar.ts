import { Component, OnInit, OnDestroy, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Subscription } from 'rxjs';
import { HeaderService } from '../../../../core/services/header.service';
import { PatientService } from '../../../../core/services/patient.service';
import { CalendarWidget, CalendarWidgetEvent } from '../../../../shared/components/calendar-widget/calendar-widget';
import { fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter } from '../../../../core/animations';
import { Spinner } from '../../../../shared/components/spinner/spinner';
import { timeFromISO, dateFromISO } from '../../../../core/utils/date.util';

@Component({
  selector: 'app-patient-calendar',
  standalone: true,
  imports: [CommonModule, Spinner, CalendarWidget],
  templateUrl: './calendar.html',
  styleUrl: './calendar.scss',
  animations: [fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class PatientCalendar implements OnInit, OnDestroy {
  loading = true;
  widgetEvents: CalendarWidgetEvent[] = [];
  error: string | null = null;

  private subs = new Subscription();

  constructor(
    private headerService: HeaderService,
    private patientService: PatientService,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit() {
    this.headerService.setConfig({
      title: 'Calendario',
      subtitle: 'Tus sesiones programadas',
      icon: ['fas', 'calendar-day'],
    });
    this.loadSessions();
  }

  ngOnDestroy() {
    this.subs.unsubscribe();
  }

  private loadSessions() {
    this.subs.add(this.patientService.getSessions().subscribe({
      next: (res) => {
        if (res.success) {
          this.widgetEvents = res.data.map((s) => ({
            id: s.id,
            title: s.title,
            date: new Date(dateFromISO(s.start_time) + 'T12:00:00'),
            time: timeFromISO(s.start_time),
            endTime: timeFromISO(s.end_time),
            status: (s.status as 'scheduled' | 'completed' | 'cancelled') || 'scheduled',
          }));
        }
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
