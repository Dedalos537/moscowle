import { Component, OnInit, OnDestroy, ViewChild, TemplateRef } from '@angular/core';
import { CalendarOptions, EventClickArg } from '@fullcalendar/core';
import { FullCalendarComponent } from '@fullcalendar/angular';
import dayGridPlugin from '@fullcalendar/daygrid';
import timeGridPlugin from '@fullcalendar/timegrid';
import interactionPlugin from '@fullcalendar/interaction';
import esLocale from '@fullcalendar/core/locales/es';
import { AdminService } from '../../../../core/services/admin.service';
import { HeaderService } from '../../../../core/services/header.service';

@Component({
  selector: 'app-sessions',
  standalone: false,
  templateUrl: './sessions.html',
  styleUrl: './sessions.scss',
})
export class Sessions implements OnInit, OnDestroy {
  @ViewChild('headerActions', { static: true }) headerActions!: TemplateRef<any>;
  @ViewChild(FullCalendarComponent) calendarComponent!: FullCalendarComponent;

  therapists: { id: number; username: string }[] = [];
  selectedTherapistId = 'all';
  calendarOptions: CalendarOptions;
  showCreateModal = false;
  showEditModal = false;
  activeTab: 'single' | 'batch' = 'single';
  patients: { id: number; username: string }[] = [];
  patientsLoading = false;

  singleForm = {
    therapist_id: '',
    patient_id: '',
    title: '',
    dates: '',
    start_time: '',
    end_time: '',
    status: 'scheduled',
    location: '',
    notes: '',
    is_past_session: false,
  };

  batchForm = {
    therapist_id: '',
    patient_id: '',
    title: '',
    start_date: '',
    start_time: '',
    end_time: '',
    weeks: 4,
    days: [] as number[],
    is_past_session: false,
  };

  editForm = {
    id: 0,
    title: '',
    date: '',
    start_time: '',
    end_time: '',
    status: 'scheduled' as string,
    therapist: '',
    patient: '',
  };

  submitting = false;

  // --- PROGRAM UPLOADS / AUDITS ---
  auditState: any = null;
  programUploading = false;
  programError: string | null = null;
  programSuccessMessage: string | null = null;


  constructor(
    private adminService: AdminService,
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
      title: 'Calendario Global de Sesiones',
      subtitle: 'Gestiona las sesiones de todos los terapeutas',
      icon: ['fas', 'calendar-alt'],
      actionTemplate: this.headerActions,
    });
    this.loadTherapists();
  }

  ngOnDestroy() {
    this.headerService.reset();
  }

  private loadTherapists() {
    this.adminService.getUsers('terapista').subscribe({
      next: (res) => {
        this.therapists = res.users.map((u) => ({ id: u.id, username: u.username }));
      },
    });
  }

  private loadEvents(fetchInfo: any, successCallback: (events: any[]) => void, failureCallback: (error: any) => void) {
    const therapistId = this.selectedTherapistId !== 'all' ? parseInt(this.selectedTherapistId) : undefined;
    this.adminService.getSessions(fetchInfo.startStr, fetchInfo.endStr, therapistId).subscribe({
      next: (events) => successCallback(events),
      error: (err) => failureCallback(err),
    });
  }

  onTherapistFilterChange() {
    this.calendarComponent?.getApi().refetchEvents();
  }

  openCreateModal() {
    this.activeTab = 'single';
    this.showCreateModal = true;
    this.resetForms();
  }

  closeCreateModal() {
    this.showCreateModal = false;
  }

  switchTab(tab: 'single' | 'batch') {
    this.activeTab = tab;
  }

  onTherapistSelect(formType: 'single' | 'batch') {
    const therapistId = parseInt(formType === 'single' ? this.singleForm.therapist_id : this.batchForm.therapist_id);
    if (!therapistId) {
      this.patients = [];
      return;
    }
    this.patientsLoading = true;
    this.adminService.getPatientsByTherapist(therapistId).subscribe({
      next: (list) => {
        this.patients = list;
        this.patientsLoading = false;
      },
      error: () => {
        this.patients = [];
        this.patientsLoading = false;
      },
    });
  }

  toggleDay(day: number) {
    const idx = this.batchForm.days.indexOf(day);
    if (idx >= 0) {
      this.batchForm.days.splice(idx, 1);
    } else {
      this.batchForm.days.push(day);
    }
  }

  submitCreate() {
    if (this.activeTab === 'single') {
      this.submitSingle();
    } else {
      this.submitBatch();
    }
  }

  private submitSingle() {
    const f = this.singleForm;
    if (!f.therapist_id || !f.patient_id || !f.dates || !f.start_time || !f.end_time) {
      return;
    }

    this.submitting = true;
    const dateList = f.dates.split(', ');

    let successCount = 0;
    const errors: string[] = [];
    let completed = 0;

    for (const dateStr of dateList) {
      const dObj = new Date(dateStr + 'T00:00:00');
      const pyDay = (dObj.getDay() + 6) % 7;

      const payload = {
        therapist_id: parseInt(f.therapist_id),
        patient_id: parseInt(f.patient_id),
        title_prefix: f.title,
        start_date: dateStr,
        start_time: f.start_time,
        end_time: f.end_time,
        weeks: 1,
        days: [pyDay],
      };

      this.adminService.batchCreateSessions(payload).subscribe({
        next: () => {
          successCount++;
          completed++;
          this.checkCreateDone(completed, dateList.length, successCount, errors);
        },
        error: () => {
          errors.push(dateStr);
          completed++;
          this.checkCreateDone(completed, dateList.length, successCount, errors);
        },
      });
    }
  }

  private checkCreateDone(completed: number, total: number, successCount: number, errors: string[]) {
    if (completed < total) return;
    this.submitting = false;
    this.closeCreateModal();
    this.refreshCalendar();
  }

  private submitBatch() {
    const f = this.batchForm;
    if (!f.therapist_id || !f.patient_id || !f.start_date || !f.start_time || !f.end_time || f.days.length === 0) {
      return;
    }

    this.submitting = true;
    const payload = {
      therapist_id: parseInt(f.therapist_id),
      patient_id: parseInt(f.patient_id),
      title_prefix: f.title,
      start_date: f.start_date,
      start_time: f.start_time,
      end_time: f.end_time,
      weeks: f.weeks,
      days: f.days,
    };

    this.adminService.batchCreateSessions(payload).subscribe({
      next: () => {
        this.submitting = false;
        this.closeCreateModal();
        this.refreshCalendar();
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
      therapist: (ext['therapist'] as string) || '',
      patient: (ext['patient'] as string) || '',
    };
    
    // Reset states
    this.auditState = null;
    this.programError = null;
    this.programSuccessMessage = null;
    
    // Load audit state
    this.adminService.getSessionAudit(this.editForm.id).subscribe({
      next: (data: any) => {
        if (data && data.success && data.exists && data.audit.has_program) {
            this.auditState = data.audit;
        }
      },
      error: () => {}
    });

    this.showEditModal = true;
  }

  closeEditModal() {
    this.showEditModal = false;
    this.auditState = null;
    this.programError = null;
    this.programSuccessMessage = null;
  }

  submitEdit() {
    const f = this.editForm;
    this.submitting = true;
    this.adminService
      .updateSession(f.id, {
        title: f.title,
        start_time: `${f.date}T${f.start_time}`,
        end_time: `${f.date}T${f.end_time}`,
        status: f.status as any,
      })
      .subscribe({
        next: () => {
          this.submitting = false;
          this.closeEditModal();
          this.refreshCalendar();
        },
        error: () => {
          this.submitting = false;
        },
      });
  }

  deleteSession() {
    if (!confirm('¿Estás seguro de que deseas eliminar esta sesión? Esta acción no se puede deshacer.')) return;

    this.adminService.deleteSession(this.editForm.id).subscribe({
      next: () => {
        this.closeEditModal();
        this.refreshCalendar();
      },
    });
  }

  private refreshCalendar() {
    this.calendarComponent?.getApi().refetchEvents();
  }

  private resetForms() {
    this.singleForm = {
      therapist_id: '',
      patient_id: '',
      title: '',
      dates: '',
      start_time: '',
      end_time: '',
      status: 'scheduled',
      location: '',
      notes: '',
      is_past_session: false,
    };
    this.batchForm = {
      therapist_id: '',
      patient_id: '',
      title: '',
      start_date: '',
      start_time: '',
      end_time: '',
      weeks: 4,
      days: [],
      is_past_session: false,
    };
    this.patients = [];
  }
  onFileSelected(event: any) {
    const file: File = event.target.files[0];
    if (file && this.editForm.id) {
      this.programUploading = true;
      this.programError = null;
      this.programSuccessMessage = null;
      
      this.adminService.uploadSessionProgram(this.editForm.id, file).subscribe({
        next: (res: any) => {
          this.programUploading = false;
          if (res.success) {
            this.programSuccessMessage = 'Programación subida correctamente.';
            this.auditState = { has_program: true, planned_text_preview: res.planned_text_preview };
          } else {
            this.programError = res.error || 'Error desconocido';
          }
          event.target.value = null;
        },
        error: (err) => {
          this.programUploading = false;
          this.programError = 'Error de conexión al subir.';
          event.target.value = null;
        }
      });
    }
  }

  deleteProgram() {
    if (confirm('¿Eliminar la programación de esta sesión?')) {
      this.adminService.deleteSessionProgram(this.editForm.id).subscribe({
        next: (res: any) => {
          if (res.success) {
            this.auditState = null;
            this.programSuccessMessage = 'Programación eliminada.';
          } else {
            this.programError = res.error || 'Error al eliminar';
          }
        },
        error: () => {
          this.programError = 'Error de conexión al eliminar.';
        }
      });
    }
  }
}