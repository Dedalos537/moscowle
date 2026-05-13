import { Component, OnInit, OnDestroy, ViewChild, TemplateRef } from '@angular/core';
import { CalendarOptions, EventClickArg } from '@fullcalendar/core';
import { FullCalendarComponent } from '@fullcalendar/angular';
import dayGridPlugin from '@fullcalendar/daygrid';
import timeGridPlugin from '@fullcalendar/timegrid';
import interactionPlugin from '@fullcalendar/interaction';
import esLocale from '@fullcalendar/core/locales/es';
import { TherapistService } from '../../../../core/services/therapist.service';
import { HeaderService } from '../../../../core/services/header.service';

@Component({
  selector: 'app-therapist-sessions',
  standalone: false,
  templateUrl: './therapist-sessions.html',
  styleUrl: './therapist-sessions.scss',
})
export class TherapistSessions implements OnInit, OnDestroy {
  @ViewChild('headerActions', { static: true }) headerActions!: TemplateRef<any>;
  @ViewChild(FullCalendarComponent) calendarComponent!: FullCalendarComponent;

  calendarOptions: CalendarOptions;
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
  ) {
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
      events: this.loadEvents.bind(this),
      eventClick: this.handleEventClick.bind(this),
      height: 'auto',
    };
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

  private loadEvents(fetchInfo: any, successCallback: (events: any[]) => void, failureCallback: (error: any) => void) {
    this.therapistService.getSessions(fetchInfo.startStr, fetchInfo.endStr).subscribe({
      next: (events) => successCallback(events),
      error: (err) => failureCallback(err),
    });
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
        this.refreshCalendar();
        this.loadStats();
      },
      error: () => {
        this.submitting = false;
      },
    });
  }

  private handleEventClick(arg: EventClickArg) {
    const ext = arg.event.extendedProps;
    this.editForm = {
      id: parseInt(arg.event.id),
      title: arg.event.title,
      date: arg.event.start?.toISOString().split('T')[0] || '',
      start_time: arg.event.start?.toTimeString().substring(0, 5) || '',
      end_time: arg.event.end?.toTimeString().substring(0, 5) || '',
      status: (ext['status'] as string) || 'scheduled',
      patient: (ext['patient'] as string) || '',
    };
    this.showEditModal = true;
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
        this.refreshCalendar();
        this.loadStats();
      },
      error: () => {
        this.submitting = false;
      },
    });
  }

  deleteSession() {
    if (!confirm('¿Estás seguro de eliminar esta sesión?')) return;
    this.therapistService.deleteSession(this.editForm.id).subscribe({
      next: () => {
        this.closeEditModal();
        this.refreshCalendar();
        this.loadStats();
      },
    });
  }

  private refreshCalendar() {
    this.calendarComponent?.getApi().refetchEvents();
  }
}
