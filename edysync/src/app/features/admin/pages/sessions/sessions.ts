import { Component, OnInit, OnDestroy, ViewChild, TemplateRef } from '@angular/core';
import { AdminService } from '../../../../core/services/admin.service';
import { HeaderService } from '../../../../core/services/header.service';
import { CalendarWidgetEvent, CalendarWidget } from '../../../../shared/components/calendar-widget/calendar-widget';
import { fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter } from '../../../../core/animations';

@Component({
  selector: 'app-sessions',
  standalone: false,
  templateUrl: './sessions.html',
  styleUrl: './sessions.scss',
  animations: [fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter]
})
export class Sessions implements OnInit, OnDestroy {
  @ViewChild('headerActions', { static: true }) headerActions!: TemplateRef<any>;
  @ViewChild(CalendarWidget) calendarWidget!: CalendarWidget;

  therapists: { id: number; username: string }[] = [];
  selectedTherapistId = 'all';
  patients: { id: number; username: string }[] = [];
  patientsLoading = false;
  loading = true;

  rawEvents: any[] = [];
  widgetEvents: CalendarWidgetEvent[] = [];

  showCreateModal = false;
  showEditModal = false;
  activeTab: 'single' | 'batch' = 'single';

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
  programDeleting = false;
  deleting = false;
  programError: string | null = null;
  programSuccessMessage: string | null = null;

  constructor(
    private adminService: AdminService,
    private headerService: HeaderService,
  ) {}

  ngOnInit() {
    this.headerService.setConfig({
      title: 'Calendario Global de Sesiones',
      subtitle: 'Gestiona las sesiones de todos los terapeutas',
      icon: ['fas', 'calendar-alt'],
      actionTemplate: this.headerActions,
    });
    this.loadTherapists();
    this.loadSessions();
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

  private loadSessions() {
    const now = new Date();
    const start = new Date(now.getFullYear(), now.getMonth() - 1, 1).toISOString().split('T')[0];
    const end = new Date(now.getFullYear(), now.getMonth() + 2, 0).toISOString().split('T')[0];
    const therapistId = this.selectedTherapistId !== 'all' ? parseInt(this.selectedTherapistId) : undefined;

    this.adminService.getSessions(start, end, therapistId).subscribe({
      next: (events) => {
        this.rawEvents = events;
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

  onTherapistFilterChange() {
    this.loading = true;
    this.loadSessions();
  }

  onDayDblClick(date: Date) {
    this.openCreateModal();
    this.singleForm.dates = date.toISOString().split('T')[0];
  }

  onRangeDblClick(range: { start: Date; end: Date }) {
    this.openCreateModal();
    this.singleForm.dates = range.start.toISOString().split('T')[0];
  }

  onEventClick(event: CalendarWidgetEvent) {
    const raw = this.rawEvents.find((e: any) => e.id === event.id);

    this.editForm = {
      id: event.id,
      title: raw?.title || event.title,
      date: event.date.toISOString().split('T')[0],
      start_time: event.time || '',
      end_time: event.endTime || '',
      status: raw?.extendedProps?.status || event.status,
      therapist: raw?.extendedProps?.therapist || event.therapist || '',
      patient: raw?.extendedProps?.patient || event.patient || '',
    };

    this.auditState = null;
    this.programError = null;
    this.programSuccessMessage = null;

    this.adminService.getSessionAudit(this.editForm.id).subscribe({
      next: (data: any) => {
        if (data && data.success && data.exists && data.audit.has_program) {
          this.auditState = data.audit;
        }
      },
      error: () => {},
    });

    this.showEditModal = true;
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
    if (!f.therapist_id || !f.patient_id || !f.dates || !f.start_time || !f.end_time) return;

    this.submitting = true;
    const dObj = new Date(f.dates + 'T00:00:00');
    const pyDay = (dObj.getDay() + 6) % 7;

    const payload = {
      therapist_id: parseInt(f.therapist_id),
      patient_id: parseInt(f.patient_id),
      title_prefix: f.title,
      start_date: f.dates,
      start_time: f.start_time,
      end_time: f.end_time,
      weeks: 1,
      days: [pyDay],
    };

    this.adminService.batchCreateSessions(payload).subscribe({
      next: () => {
        this.submitting = false;
        this.closeCreateModal();
        this.refreshEvents();
      },
      error: () => {
        this.submitting = false;
      },
    });
  }

  private submitBatch() {
    const f = this.batchForm;
    if (!f.therapist_id || !f.patient_id || !f.start_date || !f.start_time || !f.end_time || f.days.length === 0) return;

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
        this.refreshEvents();
      },
      error: () => {
        this.submitting = false;
      },
    });
  }

  private refreshEvents() {
    this.loading = true;
    this.loadSessions();
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
          this.refreshEvents();
        },
        error: () => {
          this.submitting = false;
        },
      });
  }

  deleteSession() {
    if (!confirm('¿Estás seguro de que deseas eliminar esta sesión? Esta acción no se puede deshacer.')) return;
    this.deleting = true;
    this.adminService.deleteSession(this.editForm.id).subscribe({
      next: () => {
        this.deleting = false;
        this.closeEditModal();
        this.refreshEvents();
      },
      error: () => {
        this.deleting = false;
      },
    });
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
        error: () => {
          this.programUploading = false;
          this.programError = 'Error de conexión al subir.';
          event.target.value = null;
        },
      });
    }
  }

  deleteProgram() {
    if (!confirm('¿Eliminar la programación de esta sesión?')) return;
    this.programDeleting = true;
    this.adminService.deleteSessionProgram(this.editForm.id).subscribe({
      next: (res: any) => {
        this.programDeleting = false;
        if (res.success) {
          this.auditState = null;
          this.programSuccessMessage = 'Programación eliminada.';
        } else {
          this.programError = res.error || 'Error al eliminar';
        }
      },
      error: () => {
        this.programDeleting = false;
        this.programError = 'Error de conexión al eliminar.';
      },
    });
  }
}
