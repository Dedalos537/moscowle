import { Component, OnInit, OnDestroy } from '@angular/core';
import { Router } from '@angular/router';
import { CalendarOptions, EventClickArg } from '@fullcalendar/core';
import dayGridPlugin from '@fullcalendar/daygrid';
import timeGridPlugin from '@fullcalendar/timegrid';
import interactionPlugin from '@fullcalendar/interaction';
import esLocale from '@fullcalendar/core/locales/es';
import { firstValueFrom } from 'rxjs';
import { TherapistService } from '../../../../core/services/therapist.service';
import { HeaderService } from '../../../../core/services/header.service';
import { ConfirmService } from '../../../../core/services/confirm.service';
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
  loading = true;
  widgetEvents: CalendarWidgetEvent[] = [];
  agendaEvents: any[] = [];
  showEditModal = false;
  submitting = false;
  deleting = false;
  activeView: string = 'timeGridDay';

  stats = {
    sessions_today: 0,
    completed_sessions: 0,
    pending_sessions: 0,
    active_patients: 0,
  };

  calendarOptions: CalendarOptions = {};

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
    private confirmService: ConfirmService,
  ) {
    this.initCalendar();
  }

  private initCalendar() {
    this.calendarOptions = {
      plugins: [dayGridPlugin, timeGridPlugin, interactionPlugin],
      initialView: 'timeGridDay',
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
      nowIndicator: true,
      slotMinTime: '06:00:00',
      slotMaxTime: '20:00:00',
      allDaySlot: false,
    };
  }

  cambiarVista(vista: string) {
    this.activeView = vista;
    if ((this.calendarOptions as any).initialView !== vista) {
      (this.calendarOptions as any).initialView = vista;
      this.calendarOptions = { ...this.calendarOptions };
    }
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
    });
    this.loadStats();
    this.loadSessions();
    this.cargarAgenda();
  }

  ngOnDestroy() {
    this.headerService.reset();
  }

  private loadStats() {
    this.therapistService.getDashboardStats().subscribe({
      next: (res) => (this.stats = res),
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

  cargarAgenda() {
    const hoy = new Date().toISOString().split('T')[0];
    this.therapistService.getSessions(hoy, hoy).subscribe({
      next: (events) => {
        this.agendaEvents = events;
      }
    });
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

  closeEditModal() {
    this.showEditModal = false;
  }

  async submitEdit() {
    const f = this.editForm;

    const confirmed = await firstValueFrom(this.confirmService.confirm({
      title: 'Guardar cambios',
      message: '¿Estás seguro de guardar los cambios?',
      confirmText: 'Guardar',
      cancelText: 'Cancelar',
      variant: 'primary',
    }));
    if (!confirmed) return;

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

  async deleteSession() {
    const confirmed = await firstValueFrom(this.confirmService.confirm({
      title: 'Eliminar sesión',
      message: '¿Estás seguro de eliminar esta sesión?',
      confirmText: 'Eliminar',
      cancelText: 'Cancelar',
      variant: 'danger',
    }));
    if (!confirmed) return;
    this.deleting = true;
    this.therapistService.deleteSession(this.editForm.id).subscribe({
      next: () => {
        this.deleting = false;
        this.closeEditModal();
        this.refreshEvents();
        this.loadStats();
      },
      error: () => {
        this.deleting = false;
      },
    });
  }

  irSesion(id: number) {
    this.router.navigate(['/therapist/sessions', id, 'review']);
  }

  private refreshEvents() {
    this.loading = true;
    this.loadSessions();
  }

  statusColor(status: string): string {
    const map: any = {
      scheduled: '#3b82f6',
      completed: '#22c55e',
      cancelled: '#ef4444',
      in_progress: '#f59e0b',
    };
    return map[status] || '#6b7280';
  }
}
