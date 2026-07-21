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
import { ToastService } from '../../../../core/services/toast.service';
import { SelectOption } from '../../../../shared/components/select/select';
import { Button } from '../../../../shared/components/button/button';
import { Spinner } from '../../../../shared/components/spinner/spinner';
import { Select } from '../../../../shared/components/select/select';
import { Modal } from '../../../../shared/components/modal/modal';
import { ProgressBar } from '../../../../shared/components/progress-bar/progress-bar';
import { Sede } from '../../../../core/models/sede';
import { timeFromISO, dateFromISO } from '../../../../core/utils/date.util';

@Component({
  selector: 'app-sessions',
  standalone: true,
  templateUrl: './sessions.html',
  styleUrl: './sessions.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
  animations: [fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter],
  imports: [CommonModule, FormsModule, FontAwesomeModule, Button, Spinner, Select, Modal, CalendarWidget, ProgressBar],
})
export class Sessions implements OnInit, OnDestroy {
  @ViewChild('headerActions', { static: true }) headerActions!: TemplateRef<any>;
  @ViewChild(CalendarWidget) calendarWidget!: CalendarWidget;

  therapists: { id: number; username: string }[] = [];
  selectedTherapistId: number | null = null;
  patients: { id: number; username: string }[] = [];
  allPatients: { id: number; username: string }[] = [];
  patientsLoading = false;
  selectedPatientId: number | null = null;
  loading = true;
  private subscriptions: Subscription = new Subscription();

  patientGroups: any[] = [];
  selectedGroupId: number | null = null;

  rawEvents: any[] = [];
  widgetEvents: CalendarWidgetEvent[] = [];

  showCreateModal = false;
  showEditModal = false;
  showMoveModal = false;
  showDetailModal = false;

  moveSessionId = 0;
  moveNewDate = '';
  moveSessionTitle = '';

  detailSession: any = null;
  detailLoading = false;
  detailShowProgram = false;

  sedes: Sede[] = [];
  sedesLoading = false;

  shiftRangeStart: string | null = null;
  rangeMode = false;
  rangeStartStr: string | null = null;

  get therapistOptions(): SelectOption[] {
    return [{value: null, label: 'Todos'}, ...this.therapists.map(t => ({value: t.id, label: t.username}))];
  }

  get patientFilterOptions(): SelectOption[] {
    return [{value: null, label: 'Todos los alumnos'}, ...this.allPatients.map(p => ({value: p.id, label: p.username}))];
  }

  get therapistCreateOptions(): SelectOption[] {
    return [{value: null, label: 'Seleccionar terapeuta'}, ...this.therapists.map(t => ({value: t.id, label: t.username}))];
  }

  get patientCreateOptions(): SelectOption[] {
    return [{value: null, label: 'Seleccionar paciente'}, ...this.patients.map(p => ({value: p.id, label: p.username}))];
  }

  get sedeCreateOptions(): SelectOption[] {
    return [{value: null, label: 'Seleccionar sede'}, ...this.sedes.map(s => ({value: s.name, label: s.name}))];
  }

  get groupSelectOptions(): SelectOption[] {
    return [{value: null, label: 'Seleccionar grupo'}, ...this.patientGroups.map((g: any) => ({value: g.id, label: `${g.name} (${g.member_count} pac.)`}))];
  }

  getGroupById(id: number): any {
    return this.patientGroups.find((g: any) => g.id === id) || null;
  }

  statusOptions: SelectOption[] = [
    {value: 'scheduled', label: 'Programada'},
    {value: 'completed', label: 'Completada'},
    {value: 'cancelled', label: 'Cancelada'},
  ];

  sessionTypeOptions: SelectOption[] = [
    {value: 'individual', label: 'Individual'},
    {value: 'grupal', label: 'Grupal'},
  ];

  months = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Setiembre', 'Octubre', 'Noviembre', 'Diciembre'];

  createForm = {
    therapist_id: '',
    patient_id: '',
    title: '',
    sede: '',
    session_type: 'individual',
    dates: [] as string[],
    start_time: '',
    end_time: '',
    notes: '',
    dayNotes: {} as Record<string, string>,
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
  unlockPastDates = false;

  auditState: any = null;
  programUploading = false;
  programDeleting = false;
  deleting = false;
  programError: string | null = null;
  programSuccessMessage: string | null = null;
  createProgramFile: File | null = null;
  programUploadingCreate = false;
  createProgress = 0;

  multiSelectMode = false;
  selectedSessionIds = new Set<number>();
  showBulkProgramModal = false;
  bulkProgramFile: File | null = null;
  bulkProgramUploading = false;
  bulkProgramError: string | null = null;
  bulkProgramSuccess: string | null = null;

  constructor(
    private adminService: AdminService,
    private headerService: HeaderService,
    private confirmService: ConfirmService,
    private toastService: ToastService,
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
    this.loadAllPatients();
    this.loadSedes();
    this.loadSessions();
    this.loadPatientGroups();
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

  private loadAllPatients() {
    this.subscriptions.add(
      this.adminService.getUsers('jugador').subscribe({
        next: (res) => {
          this.allPatients = res.users.map((u) => ({ id: u.id, username: u.username }));
          this.cdr.markForCheck();
        },
        error: () => { this.cdr.markForCheck(); },
      })
    );
  }

  private loadSedes() {
    this.sedesLoading = true;
    this.subscriptions.add(
      this.adminService.getSedes().subscribe({
        next: (res) => {
          this.sedes = res.filter(s => s.active);
          this.sedesLoading = false;
          this.cdr.markForCheck();
        },
        error: () => {
          this.sedesLoading = false;
          this.cdr.markForCheck();
        },
      })
    );
  }

  private loadPatientGroups() {
    this.subscriptions.add(
      this.adminService.getPatientGroups().subscribe({
        next: (res: any) => {
          this.patientGroups = res.groups || [];
          this.cdr.markForCheck();
        },
        error: () => this.cdr.markForCheck(),
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
          let filtered = events;
          if (this.selectedPatientId) {
            filtered = events.filter((e: any) => e.extendedProps?.patient_id === this.selectedPatientId);
          }
          this.rawEvents = filtered;
          this.widgetEvents = filtered.map((e: any) => ({
            id: e.id,
            title: e.title,
            date: new Date(dateFromISO(e.start) + 'T12:00:00'),
            time: timeFromISO(e.start),
            endTime: timeFromISO(e.end),
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
    this.loadSessions();
  }

  onPatientFilterChange() {
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
        const isPast = cursor.getTime() < today.getTime() && cursor.getMonth() === month && !this.unlockPastDates;
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
      delete this.createForm.dayNotes[dateStr];
    } else if (this.createForm.dates.length < 10) {
      this.createForm.dates = [...this.createForm.dates, dateStr];
    }
    this.buildCalendarGrid();
  }

  toggleCalendarDate(day: { date: Date; day: number; selected: boolean; disabled: boolean }) {
    if (day.disabled) return;
    const dateStr = day.date.toISOString().split('T')[0];

    if (this.rangeMode) {
      if (!this.rangeStartStr) {
        this.rangeStartStr = dateStr;
        this.toggleDate(dateStr);
      } else {
        const start = new Date(this.rangeStartStr);
        const end = new Date(dateStr);
        const minDate = start < end ? this.rangeStartStr : dateStr;
        const maxDate = start < end ? dateStr : this.rangeStartStr;
        const current = new Date(minDate);
        while (current <= new Date(maxDate)) {
          const ds = current.toISOString().split('T')[0];
          if (!this.createForm.dates.includes(ds) && this.createForm.dates.length < 10) {
            this.createForm.dates = [...this.createForm.dates, ds];
          }
          current.setDate(current.getDate() + 1);
        }
        this.rangeStartStr = null;
        this.rangeMode = false;
        this.buildCalendarGrid();
      }
    } else {
      this.toggleDate(dateStr);
    }
  }

  toggleRangeMode() {
    this.rangeMode = !this.rangeMode;
    this.rangeStartStr = null;
  }

  toggleUnlockPast() {
    this.unlockPastDates = !this.unlockPastDates;
    this.buildCalendarGrid();
  }

  clearRangeSelection() {
    this.rangeMode = false;
    this.rangeStartStr = null;
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
    this.submitting = false;
    this.createProgress = 0;
    this.programUploadingCreate = false;
    this.selectedGroupId = null;
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

  onGroupSelect(groupId: number | null) {
    if (!groupId) {
      this.selectedGroupId = null;
      return;
    }
    this.selectedGroupId = groupId;
    const group = this.patientGroups.find((g: any) => g.id === groupId);
    if (!group) return;

    if (group.start_time) this.createForm.start_time = group.start_time;
    if (group.end_time) this.createForm.end_time = group.end_time;
    if (group.sede_id) {
      const sede = this.sedes.find(s => s.id === group.sede_id);
      if (sede) this.createForm.sede = sede.name;
    }
    this.cdr.markForCheck();
  }

  async submitCreate() {
    const f = this.createForm;
    const isGroup = f.session_type === 'grupal' && this.selectedGroupId;
    if (!f.therapist_id || (!isGroup && !f.patient_id) || !f.dates.length || !f.start_time || !f.end_time) return;
    if (isGroup && (!group || !group.member_ids?.length)) return;

    const group = isGroup ? this.patientGroups.find((g: any) => g.id === this.selectedGroupId) : null;
    const patientCount = isGroup ? (group?.member_count || 0) : 1;

    const confirmed = await firstValueFrom(this.confirmService.confirm({
      title: 'Programar sesiones',
      message: isGroup
        ? `Se crearán ${f.dates.length} sesión(es) × ${patientCount} pacientes del grupo "${group?.name}". Total: ${f.dates.length * patientCount}. ¿Estás seguro?`
        : `Se crearán ${f.dates.length} sesión(es). ¿Estás seguro?`,
      confirmText: 'Crear',
      cancelText: 'Cancelar',
      variant: 'primary',
    }));
    if (!confirmed) return;

    this.submitting = true;
    this.createProgress = 10;

    const payload: any = {
      therapist_id: parseInt(f.therapist_id),
      title_prefix: f.title,
      sede: f.sede,
      session_type: f.session_type,
      dates: f.dates,
      start_time: f.start_time,
      end_time: f.end_time,
      unlock_past_dates: this.unlockPastDates,
    };

    if (isGroup && group) {
      payload.patient_ids = group.member_ids || [];
    } else if (f.patient_id) {
      payload.patient_id = parseInt(f.patient_id);
    }

    this.subscriptions.add(
      this.adminService.batchCreateSessions(payload).subscribe({
        next: (res: any) => {
          const sessionIds: number[] = res?.session_ids || [];
          if (this.createProgramFile && sessionIds.length > 0) {
            this.createProgress = 40;
            this.programUploadingCreate = true;
            let uploaded = 0;
            const total = sessionIds.length;
            const finishCreate = (msg: string, type: 'success' | 'warning') => {
              this.createProgress = 100;
              this.programUploadingCreate = false;
              this.createProgramFile = null;
              this.submitting = false;
              this.closeCreateModal();
              this.refreshEvents();
              this.toastService.show(msg, type);
              this.cdr.markForCheck();
            };
            sessionIds.forEach((id) => {
              this.subscriptions.add(
                this.adminService.uploadSessionProgram(id, this.createProgramFile!).subscribe({
                  next: () => {
                    uploaded++;
                    this.createProgress = 40 + Math.round((uploaded / total) * 50);
                    this.cdr.markForCheck();
                    if (uploaded === total) {
                      finishCreate(`${total} sesiones creadas con programación`, 'success');
                    }
                  },
                  error: () => {
                    uploaded++;
                    this.createProgress = 40 + Math.round((uploaded / total) * 50);
                    this.cdr.markForCheck();
                    if (uploaded === total) {
                      finishCreate(`${total} sesiones creadas (con errores en algunas programaciones)`, 'warning');
                    }
                  },
                })
              );
            });
          } else {
            this.createProgress = 100;
            this.submitting = false;
            this.createProgramFile = null;
            this.closeCreateModal();
            this.refreshEvents();
            this.toastService.show(`${f.dates.length} sesiones creadas correctamente`, 'success');
            this.cdr.markForCheck();
          }
        },
        error: (err: any) => {
          this.submitting = false;
          this.programUploadingCreate = false;
          this.createProgress = 0;
          const msg = err?.error?.error || err?.error?.message || 'Error al crear sesiones';
          this.toastService.show(msg, 'error');
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
    this.submitting = false;
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
            this.toastService.show('Sesión actualizada correctamente', 'success');
            this.cdr.markForCheck();
          },
          error: () => {
            this.submitting = false;
            this.toastService.show('Error al actualizar sesión', 'error');
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
          this.toastService.show('Sesión eliminada correctamente', 'success');
          this.cdr.markForCheck();
        },
        error: () => {
          this.deleting = false;
          this.toastService.show('Error al eliminar sesión', 'error');
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
      session_type: 'individual',
      dates: [],
      start_time: '',
      end_time: '',
      notes: '',
      dayNotes: {},
    };
    this.shiftRangeStart = null;
    this.rangeMode = false;
    this.rangeStartStr = null;
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

  openMoveModal(event: {id: number; title: string; date: Date; time?: string; endTime?: string; status: string; therapist?: string; patient?: string}) {
    this.moveSessionId = event.id;
    this.moveSessionTitle = event.title;
    this.moveNewDate = event.date.toISOString().split('T')[0];
    this.showMoveModal = true;
    this.cdr.markForCheck();
  }

  closeMoveModal() {
    this.showMoveModal = false;
    this.moveSessionId = 0;
    this.moveNewDate = '';
  }

  async submitMove() {
    if (!this.moveNewDate || !this.moveSessionId) return;
    const confirmed = await firstValueFrom(this.confirmService.confirm({
      title: 'Mover sesion',
      message: `Mover "${this.moveSessionTitle}" al ${this.moveNewDate}?`,
      confirmText: 'Mover',
      cancelText: 'Cancelar',
      variant: 'primary',
    }));
    if (!confirmed) return;

    const raw = this.rawEvents.find((e: any) => e.id === this.moveSessionId);
    if (!raw) return;

    const startTime = timeFromISO(raw.start);
    const endTime = timeFromISO(raw.end);

    this.subscriptions.add(
      this.adminService.updateSession(this.moveSessionId, {
        start_time: `${this.moveNewDate}T${startTime}`,
        end_time: `${this.moveNewDate}T${endTime}`,
      }).subscribe({
        next: () => {
          this.closeMoveModal();
          this.refreshEvents();
          this.toastService.show('Sesion movida correctamente', 'success');
          this.cdr.markForCheck();
        },
        error: () => {
          this.toastService.show('Error al mover sesion', 'error');
          this.cdr.markForCheck();
        },
      })
    );
  }

  openDetailModal(event: {id: number; title: string; date: Date; time?: string; endTime?: string; status: string; therapist?: string; patient?: string}) {
    this.detailLoading = true;
    this.detailSession = null;
    this.showDetailModal = true;
    this.cdr.markForCheck();

    let auditData: any = null;
    let programData: any = null;
    let loaded = 0;
    const total = 2;

    const buildSession = () => {
      this.detailSession = {
        id: event.id,
        title: event.title,
        status: event.status,
        date: event.date.toISOString().split('T')[0],
        time: event.time,
        endTime: event.endTime,
        therapist: event.therapist,
        patient: event.patient,
        audit: auditData?.audit || null,
        auditExists: auditData?.exists || false,
        programText: programData?.program_text || null,
        hasProgram: programData?.has_program || false,
      };
      this.detailLoading = false;
      this.cdr.markForCheck();
    };

    this.subscriptions.add(
      this.adminService.getSessionAudit(event.id).subscribe({
        next: (data: any) => { auditData = data; loaded++; if (loaded >= total) buildSession(); },
        error: () => { loaded++; if (loaded >= total) buildSession(); },
      })
    );

    this.subscriptions.add(
      this.adminService.getSessionProgram(event.id).subscribe({
        next: (data: any) => { programData = data; loaded++; if (loaded >= total) buildSession(); },
        error: () => { loaded++; if (loaded >= total) buildSession(); },
      })
    );
  }

  closeDetailModal() {
    this.showDetailModal = false;
    this.detailSession = null;
    this.detailShowProgram = false;
  }

  toDateStr(date: string): Date {
    return new Date(date + 'T12:00:00');
  }

  toggleMultiSelect() {
    this.multiSelectMode = !this.multiSelectMode;
    if (!this.multiSelectMode) {
      this.selectedSessionIds = new Set();
    }
    this.cdr.markForCheck();
  }

  onSelectionChange(ids: number[]) {
    this.selectedSessionIds = new Set(ids);
    this.cdr.markForCheck();
  }

  openBulkProgramModal() {
    if (this.selectedSessionIds.size === 0) return;
    this.showBulkProgramModal = true;
    this.bulkProgramFile = null;
    this.bulkProgramError = null;
    this.bulkProgramSuccess = null;
    this.cdr.markForCheck();
  }

  closeBulkProgramModal() {
    this.showBulkProgramModal = false;
    this.bulkProgramFile = null;
    this.bulkProgramError = null;
    this.bulkProgramSuccess = null;
  }

  onBulkFileSelected(event: any) {
    const file: File = event.target.files[0];
    if (file) {
      if (!file.name.endsWith('.docx')) {
        this.bulkProgramError = 'Solo se permiten archivos .docx';
        return;
      }
      this.bulkProgramFile = file;
      this.bulkProgramError = null;
    }
  }

  submitBulkProgram() {
    if (!this.bulkProgramFile || this.selectedSessionIds.size === 0) return;
    this.bulkProgramUploading = true;
    this.bulkProgramError = null;
    this.bulkProgramSuccess = null;

    const ids = Array.from(this.selectedSessionIds);
    let completed = 0;
    let errors = 0;

    ids.forEach(sessionId => {
      this.adminService.uploadSessionProgram(sessionId, this.bulkProgramFile!).subscribe({
        next: () => {
          completed++;
          if (completed + errors === ids.length) {
            this.bulkProgramUploading = false;
            if (errors > 0) {
              this.bulkProgramError = `${completed} exitosas, ${errors} fallidas`;
            } else {
              this.bulkProgramSuccess = `Programación asignada a ${completed} sesión(es) exitosamente`;
              setTimeout(() => {
                this.closeBulkProgramModal();
                this.loadSessions();
              }, 1500);
            }
            this.cdr.markForCheck();
          }
        },
        error: () => {
          errors++;
          if (completed + errors === ids.length) {
            this.bulkProgramUploading = false;
            this.bulkProgramError = `${completed} exitosas, ${errors} fallidas`;
            this.cdr.markForCheck();
          }
        }
      });
    });
  }
}
