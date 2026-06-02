import { Component, OnInit, OnDestroy, ViewChild, TemplateRef, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { Subscription } from 'rxjs';
import { AdminService } from '../../../../core/services/admin.service';
import { HeaderService } from '../../../../core/services/header.service';
import { CalendarWidgetEvent, CalendarWidget } from '../../../../shared/components/calendar-widget/calendar-widget';
import { fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter } from '../../../../core/animations';
import { firstValueFrom } from 'rxjs';
import { ConfirmService } from '../../../../core/services/confirm.service';
import { SelectOption } from '../../../../shared/components/select/select';
import { Button } from '../../../../shared/components/button/button';
import { Spinner } from '../../../../shared/components/spinner/spinner';
import { Select } from '../../../../shared/components/select/select';
import { Modal } from '../../../../shared/components/modal/modal';

@Component({
  selector: 'app-sessions',
  standalone: true,
  templateUrl: './sessions.html',
  styleUrl: './sessions.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
  animations: [fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter],
  imports: [CommonModule, FormsModule, FontAwesomeModule, Button, Spinner, Select, Modal, CalendarWidget],
})
export class Sessions implements OnInit, OnDestroy {
  @ViewChild('headerActions', { static: true }) headerActions!: TemplateRef<any>;
  @ViewChild(CalendarWidget) calendarWidget!: CalendarWidget;

  therapists: { id: number; username: string }[] = [];
  selectedTherapistId: number | null = null;
  patients: { id: number; username: string }[] = [];
  patientsLoading = false;
  loading = true;
  private subscriptions: Subscription = new Subscription();

  rawEvents: any[] = [];
  widgetEvents: CalendarWidgetEvent[] = [];

  showCreateModal = false;
  showEditModal = false;

  sedes = ['Piura', 'Talara'];

  get therapistOptions(): SelectOption[] {
    return [{value: null, label: 'Todos'}, ...this.therapists.map(t => ({value: t.id, label: t.username}))];
  }

  get therapistCreateOptions(): SelectOption[] {
    return [{value: null, label: 'Seleccionar terapeuta'}, ...this.therapists.map(t => ({value: t.id, label: t.username}))];
  }

  get patientCreateOptions(): SelectOption[] {
    return [{value: null, label: 'Seleccionar paciente'}, ...this.patients.map(p => ({value: p.id, label: p.username}))];
  }

  get sedeCreateOptions(): SelectOption[] {
    return [{value: null, label: 'Seleccionar sede'}, ...this.sedes.map(s => ({value: s, label: s}))];
  }

  statusOptions: SelectOption[] = [
    {value: 'scheduled', label: 'Programada'},
    {value: 'completed', label: 'Completada'},
    {value: 'cancelled', label: 'Cancelada'},
  ];

  months = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Setiembre', 'Octubre', 'Noviembre', 'Diciembre'];

  createForm = {
    therapist_id: '',
    patient_id: '',
    title: '',
    sede: '',
    dates: [] as string[],
    start_time: '',
    end_time: '',
    notes: '',
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

  calendarMonth: Date = new Date();
  calendarDays: { date: Date; day: number; selected: boolean; disabled: boolean }[][] = [];

  auditState: any = null;
  programUploading = false;
  programDeleting = false;
  deleting = false;
  programError: string | null = null;
  programSuccessMessage: string | null = null;
  createProgramFile: File | null = null;
  programUploadingCreate = false;

  constructor(
    private adminService: AdminService,
    private headerService: HeaderService,
    private confirmService: ConfirmService,
    private cdr: ChangeDetectorRef,
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
    this.buildCalendarGrid();
  }

  ngOnDestroy() {
    this.subscriptions.unsubscribe();
    this.headerService.reset();
  }

  private loadTherapists() {
    this.subscriptions.add(
      this.adminService.getUsers('terapista').subscribe({
        next: (res) => {
          this.therapists = res.users.map((u) => ({ id: u.id, username: u.username }));
          this.cdr.markForCheck();
        },
        error: () => { this.cdr.markForCheck(); },
      })
    );
  }

  private loadSessions() {
    const now = new Date();
    const start = new Date(now.getFullYear(), now.getMonth() - 1, 1).toISOString().split('T')[0];
    const end = new Date(now.getFullYear(), now.getMonth() + 2, 0).toISOString().split('T')[0];
    const therapistId = this.selectedTherapistId ?? undefined;

    this.subscriptions.add(
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
          this.cdr.markForCheck();
        },
        error: () => { this.loading = false; this.cdr.markForCheck(); },
      })
    );
  }

  onTherapistFilterChange() {
    this.loading = true;
    this.loadSessions();
  }

  onDayDblClick(date: Date) {
    const dateStr = date.toISOString().split('T')[0];
    this.openCreateModal();
    this.toggleDate(dateStr);
  }

  onRangeDblClick(range: { start: Date; end: Date }) {
    this.openCreateModal();
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

    this.subscriptions.add(
      this.adminService.getSessionAudit(this.editForm.id).subscribe({
        next: (data: any) => {
          if (data && data.success && data.exists && data.audit.has_program) {
            this.auditState = data.audit;
          }
          this.cdr.markForCheck();
        },
        error: () => { this.cdr.markForCheck(); },
      })
    );

    this.showEditModal = true;
  }

  private buildCalendarGrid() {
    const year = this.calendarMonth.getFullYear();
    const month = this.calendarMonth.getMonth();
    const firstDay = new Date(year, month, 1);
    const startOfWeek = new Date(firstDay);
    startOfWeek.setDate(startOfWeek.getDate() - ((startOfWeek.getDay() + 6) % 7));

    const today = new Date();
    today.setHours(0, 0, 0, 0);

    const weeks: { date: Date; day: number; selected: boolean; disabled: boolean }[][] = [];
    let cursor = new Date(startOfWeek);

    for (let w = 0; w < 6; w++) {
      const week: { date: Date; day: number; selected: boolean; disabled: boolean }[] = [];
      for (let d = 0; d < 7; d++) {
        const dateStr = cursor.toISOString().split('T')[0];
        const isPast = cursor.getTime() < today.getTime() && cursor.getMonth() === month;
        week.push({
          date: new Date(cursor),
          day: cursor.getDate(),
          selected: this.createForm.dates.includes(dateStr),
          disabled: isPast,
        });
        cursor.setDate(cursor.getDate() + 1);
      }
      weeks.push(week);
      if (cursor.getMonth() !== month && weeks.length >= 4) break;
    }

    this.calendarDays = weeks;
  }

  prevMonth() {
    this.calendarMonth = new Date(this.calendarMonth.getFullYear(), this.calendarMonth.getMonth() - 1, 1);
    this.buildCalendarGrid();
  }

  nextMonth() {
    this.calendarMonth = new Date(this.calendarMonth.getFullYear(), this.calendarMonth.getMonth() + 1, 1);
    this.buildCalendarGrid();
  }

  toggleDate(dateStr: string) {
    const idx = this.createForm.dates.indexOf(dateStr);
    if (idx >= 0) {
      this.createForm.dates = this.createForm.dates.filter(d => d !== dateStr);
    } else if (this.createForm.dates.length < 5) {
      this.createForm.dates = [...this.createForm.dates, dateStr];
    }
    this.buildCalendarGrid();
  }

  toggleCalendarDate(day: { date: Date; day: number; selected: boolean; disabled: boolean }) {
    if (day.disabled) return;
    const dateStr = day.date.toISOString().split('T')[0];
    this.toggleDate(dateStr);
  }

  removeDate(dateStr: string) {
    this.createForm.dates = this.createForm.dates.filter(d => d !== dateStr);
    this.buildCalendarGrid();
  }

  get calendarLabel(): string {
    return `${this.months[this.calendarMonth.getMonth()]} ${this.calendarMonth.getFullYear()}`;
  }

  openCreateModal() {
    this.showCreateModal = true;
    this.resetForms();
    this.cdr.markForCheck();
  }

  closeCreateModal() {
    this.showCreateModal = false;
  }

  onTherapistSelectCreate() {
    const therapistId = parseInt(this.createForm.therapist_id);
    if (!therapistId) {
      this.patients = [];
      return;
    }
    this.patientsLoading = true;
    this.subscriptions.add(
      this.adminService.getPatientsByTherapist(therapistId).subscribe({
        next: (list) => {
          this.patients = list;
          this.patientsLoading = false;
          this.cdr.markForCheck();
        },
        error: () => {
          this.patients = [];
          this.patientsLoading = false;
          this.cdr.markForCheck();
        },
      })
    );
  }

  async submitCreate() {
    const f = this.createForm;
    if (!f.therapist_id || !f.patient_id || !f.dates.length || !f.start_time || !f.end_time) return;

    const confirmed = await firstValueFrom(this.confirmService.confirm({
      title: 'Programar sesiones',
      message: `Se crearán ${f.dates.length} sesión(es). ¿Estás seguro?`,
      confirmText: 'Crear',
      cancelText: 'Cancelar',
      variant: 'primary',
    }));
    if (!confirmed) return;

    this.submitting = true;
    const payload = {
      therapist_id: parseInt(f.therapist_id),
      patient_id: parseInt(f.patient_id),
      title_prefix: f.title,
      sede: f.sede,
      dates: f.dates,
      start_time: f.start_time,
      end_time: f.end_time,
    };

    this.subscriptions.add(
      this.adminService.batchCreateSessions(payload).subscribe({
        next: (res: any) => {
          const sessionIds: number[] = res?.session_ids || [];
          if (this.createProgramFile && sessionIds.length > 0) {
            this.programUploadingCreate = true;
            let uploaded = 0;
            sessionIds.forEach((id) => {
              this.subscriptions.add(
                this.adminService.uploadSessionProgram(id, this.createProgramFile!).subscribe({
                  next: () => {
                    uploaded++;
                    if (uploaded === sessionIds.length) {
                      this.programUploadingCreate = false;
                      this.createProgramFile = null;
                      this.submitting = false;
                      this.closeCreateModal();
                      this.refreshEvents();
                      this.cdr.markForCheck();
                    }
                  },
                  error: () => {
                    uploaded++;
                    if (uploaded === sessionIds.length) {
                      this.programUploadingCreate = false;
                      this.createProgramFile = null;
                      this.submitting = false;
                      this.closeCreateModal();
                      this.refreshEvents();
                      this.cdr.markForCheck();
                    }
                  },
                })
              );
            });
          } else {
            this.submitting = false;
            this.createProgramFile = null;
            this.closeCreateModal();
            this.refreshEvents();
            this.cdr.markForCheck();
          }
        },
        error: () => {
          this.submitting = false;
          this.programUploadingCreate = false;
          this.cdr.markForCheck();
        },
      })
    );
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
    this.subscriptions.add(
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
            this.cdr.markForCheck();
          },
          error: () => {
            this.submitting = false;
            this.cdr.markForCheck();
          },
        })
    );
  }

  async deleteSession() {
    const confirmed = await firstValueFrom(this.confirmService.confirm({
      title: 'Eliminar Sesión',
      message: '¿Estás seguro de que deseas eliminar esta sesión? Esta acción no se puede deshacer.',
      confirmText: 'Eliminar',
      cancelText: 'Cancelar',
      variant: 'danger',
    }));
    if (!confirmed) return;
    this.deleting = true;
    this.subscriptions.add(
      this.adminService.deleteSession(this.editForm.id).subscribe({
        next: () => {
          this.deleting = false;
          this.closeEditModal();
          this.refreshEvents();
          this.cdr.markForCheck();
        },
        error: () => {
          this.deleting = false;
          this.cdr.markForCheck();
        },
      })
    );
  }

  private resetForms() {
    this.createForm = {
      therapist_id: '',
      patient_id: '',
      title: '',
      sede: '',
      dates: [],
      start_time: '',
      end_time: '',
      notes: '',
    };
    this.createProgramFile = null;
    this.patients = [];
    this.calendarMonth = new Date();
    this.buildCalendarGrid();
  }

  onFileSelected(event: any) {
    const file: File = event.target.files[0];
    if (file && this.editForm.id) {
      this.programUploading = true;
      this.programError = null;
      this.programSuccessMessage = null;

      this.subscriptions.add(
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
            this.cdr.markForCheck();
          },
          error: () => {
            this.programUploading = false;
            this.programError = 'Error de conexión al subir.';
            event.target.value = null;
            this.cdr.markForCheck();
          },
        })
      );
    }
  }

  onCreateFileSelected(event: any) {
    this.createProgramFile = event.target.files[0] || null;
  }

  async deleteProgram() {
    const confirmed = await firstValueFrom(this.confirmService.confirm({
      title: 'Eliminar Programación',
      message: '¿Eliminar la programación de esta sesión?',
      confirmText: 'Eliminar',
      cancelText: 'Cancelar',
      variant: 'danger',
    }));
    if (!confirmed) return;
    this.programDeleting = true;
    this.subscriptions.add(
      this.adminService.deleteSessionProgram(this.editForm.id).subscribe({
        next: (res: any) => {
          this.programDeleting = false;
          if (res.success) {
            this.auditState = null;
            this.programSuccessMessage = 'Programación eliminada.';
          } else {
            this.programError = res.error || 'Error al eliminar';
          }
          this.cdr.markForCheck();
        },
        error: () => {
          this.programDeleting = false;
          this.programError = 'Error de conexión al eliminar.';
          this.cdr.markForCheck();
        },
      })
    );
  }
}
