import { Component, OnInit, OnDestroy, ViewChild, TemplateRef } from '@angular/core';
import { Router } from '@angular/router';
import { CalendarOptions, EventClickArg } from '@fullcalendar/core';
import { FullCalendarComponent } from '@fullcalendar/angular';
import dayGridPlugin from '@fullcalendar/daygrid';
import timeGridPlugin from '@fullcalendar/timegrid';
import interactionPlugin from '@fullcalendar/interaction';
import esLocale from '@fullcalendar/core/locales/es';
import { TherapistService } from '../../../../core/services/therapist.service';
import { HeaderService } from '../../../../core/services/header.service';
import { CalendarWidgetEvent } from '../../../../shared/components/calendar-widget/calendar-widget';
import { fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter } from '../../../../core/animations';

@Component({
  selector: 'app-therapist-sessions',
  standalone: false,
  templateUrl: './therapist-sessions.html',
  styleUrl: './therapist-sessions.scss',
  animations: [fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter]
})
export class TherapistSessions implements OnInit, OnDestroy {
  @ViewChild('headerActions', { static: true }) headerActions!: TemplateRef<any>;

  loading = true;
  widgetEvents: CalendarWidgetEvent[] = [];
  showCreateModal = false;
  showEditModal = false;
  patients: { id: number; username: string }[] = [];
  submitting = false;

  stats = {
    sessions_today: 0,
    completed_sessions: 0,
    pending_sessions: 0,
    active_patients: 0,
  };

  calendarOptions: CalendarOptions = {};

  createForm = {
    patient_id: '',
    title: '',
    date: '',
    start_time: '',
    end_time: '',
    status: 'scheduled',
    notes: '',
  };

  editForm = {
    id: 0,
    title: '',
    date: '',
    start_time: '',
    end_time: '',
    status: 'scheduled' as string,
    patient: '',
  };

  constructor(
    private therapistService: TherapistService,
    private headerService: HeaderService,
    private router: Router,
  ) {
    this.initCalendar();
  }

  private initCalendar() {
    this.calendarOptions = {
      plugins: [dayGridPlugin, timeGridPlugin, interactionPlugin],
      initialView: 'dayGridMonth',
      locale: esLocale,
      headerToolbar: {
        left: 'prev,next today',
        center: 'title',
        right: 'dayGridMonth,timeGridWeek,timeGridDay',
      },
      navLinks: true,
      events: this.loadFullCalendarEvents.bind(this),
      eventClick: this.onFullCalendarEventClick.bind(this),
      height: 'auto',
    };
  }

  private loadFullCalendarEvents(fetchInfo: any, successCallback: Function, failureCallback: Function) {
    const start = fetchInfo.start.toISOString().split('T')[0];
    const end = fetchInfo.end.toISOString().split('T')[0];
    this.therapistService.getSessions(start, end).subscribe({
      next: (events) => {
        successCallback(events);
      },
      error: () => failureCallback(),
    });
  }

  onFullCalendarEventClick(info: EventClickArg) {
    const event = info.event;
    this.onEventClick({
      id: event.id ? parseInt(event.id) : 0,
      title: event.title,
      date: event.start || new Date(),
      time: event.start ? event.start.toTimeString().substring(0, 5) : undefined,
      endTime: event.end ? event.end.toTimeString().substring(0, 5) : undefined,
      status: event.extendedProps?.['status'] || 'scheduled',
      therapist: event.extendedProps?.['therapist'],
      patient: event.extendedProps?.['patient'],
      therapistId: event.extendedProps?.['therapist_id'],
      patientId: event.extendedProps?.['patient_id'],
    });
  }

  ngOnInit() {
    this.headerService.setConfig({
      title: 'Mis Sesiones',
      subtitle: 'Gestiona tus sesiones con pacientes',
      icon: ['fas', 'calendar-alt'],
      actionTemplate: this.headerActions,
    });
    this.loadStats();
    this.loadPatients();
    this.loadSessions();
  }

  ngOnDestroy() {
    this.headerService.reset();
  }

  private loadStats() {
    this.therapistService.getDashboardStats().subscribe({
      next: (res) => (this.stats = res),
    });
  }

  private loadPatients() {
    this.therapistService.getPatients().subscribe({
      next: (list) => {
        this.patients = list.map((p) => ({ id: p.id, username: p.username }));
      },
    });
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
          therapistId: e.extendedProps?.therapist_id,
          patientId: e.extendedProps?.patient_id,
        }));
        this.loading = false;
      },
      error: () => (this.loading = false),
    });
  }

  onDayDblClick(date: Date) {
    this.createForm.date = date.toISOString().split('T')[0];
    this.openCreateModal();
  }

  onRangeDblClick(range: { start: Date; end: Date }) {
    this.createForm.date = range.start.toISOString().split('T')[0];
    this.openCreateModal();
  }

  onEventClick(event: CalendarWidgetEvent) {
    this.editForm = {
      id: event.id,
      title: event.title,
      date: event.date.toISOString().split('T')[0],
      start_time: event.time || '',
      end_time: event.endTime || '',
      status: event.status,
      patient: event.patient || '',
    };
    this.showEditModal = true;
  }

  openCreateModal() {
    this.showCreateModal = true;
    this.resetForm();
  }

  closeCreateModal() {
    this.showCreateModal = false;
  }

  private resetForm() {
    this.createForm = {
      patient_id: '',
      title: '',
      date: '',
      start_time: '',
      end_time: '',
      status: 'scheduled',
      notes: '',
    };
  }

  submitCreate() {
    const f = this.createForm;
    if (!f.patient_id || !f.date || !f.start_time || !f.end_time) return;

    this.submitting = true;
    const startTime = `${f.date}T${f.start_time}`;
    const endTime = `${f.date}T${f.end_time}`;

    this.therapistService.createSession({
      patient_id: parseInt(f.patient_id),
      title: f.title || 'Sesión',
      start_time: startTime,
      end_time: endTime,
      status: f.status,
      notes: f.notes,
    }).subscribe({
      next: () => {
        this.submitting = false;
        this.closeCreateModal();
        this.refreshEvents();
        this.loadStats();
      },
      error: () => {
        this.submitting = false;
      },
    });
  }

  closeEditModal() {
    this.showEditModal = false;
  }

  submitEdit() {
    const f = this.editForm;
    this.submitting = true;
    this.therapistService.updateSession(f.id, {
      title: f.title,
      start_time: `${f.date}T${f.start_time}`,
      end_time: `${f.date}T${f.end_time}`,
      status: f.status as any,
    }).subscribe({
      next: () => {
        this.submitting = false;
        this.closeEditModal();
        this.refreshEvents();
        this.loadStats();
      },
      error: () => {
        this.submitting = false;
      },
    });
  }

  navigateToReview() {
    this.closeEditModal();
    this.router.navigate(['/therapist/sessions', this.editForm.id, 'review']);
  }

  deleteSession() {
    if (!confirm('¿Estás seguro de eliminar esta sesión?')) return;
    this.therapistService.deleteSession(this.editForm.id).subscribe({
      next: () => {
        this.closeEditModal();
        this.refreshEvents();
        this.loadStats();
      },
    });
  }

  private refreshEvents() {
    this.loading = true;
    this.loadSessions();
  }
}
