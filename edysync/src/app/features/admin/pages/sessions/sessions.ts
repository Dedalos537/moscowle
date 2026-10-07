import { Component, OnInit, OnDestroy, ViewChild, TemplateRef, ChangeDetectionStrategy, ChangeDetectorRef, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { Subject, Subscription, forkJoin, of, firstValueFrom } from 'rxjs';
import { catchError, switchMap, tap } from 'rxjs/operators';
import { AdminService } from '../../../../core/services/admin.service';
import { HeaderService } from '../../../../core/services/header.service';
import { ConfirmService } from '../../../../core/services/confirm.service';
import { ToastService } from '../../../../core/services/toast.service';
import { CalendarWidgetEvent, CalendarWidget } from '../../../../shared/components/calendar-widget/calendar-widget';
import { MultiDatePicker } from '../../../../shared/components/multi-date-picker/multi-date-picker';
import { Button } from '../../../../shared/components/button/button';
import { Spinner } from '../../../../shared/components/spinner/spinner';
import { Select, SelectOption } from '../../../../shared/components/select/select';
import { Modal } from '../../../../shared/components/modal/modal';
import { Sede } from '../../../../core/models/sede';
import { timeFromISO, dateFromISO, toLocalDateString } from '../../../../core/utils/date.util';

type SessionStatus = 'scheduled' | 'in_progress' | 'completed' | 'cancelled';

export const SESSION_STATUS: Record<string, { label: string; badge: string }> = {
  scheduled: { label: 'Programada', badge: 'badge--info' },
  in_progress: { label: 'En curso', badge: 'badge--warning' },
  completed: { label: 'Completada', badge: 'badge--success' },
  cancelled: { label: 'Cancelada', badge: 'badge--error' },
};

interface Conflict {
  date: string;
  patient_id: number;
  reason: string;
}

interface CreateResult {
  created: number;
  conflicts: Conflict[];
  holidays: string[];
  message: string;
  failed: boolean;
}

@Component({
  selector: 'app-sessions',
  standalone: true,
  templateUrl: './sessions.html',
  styleUrl: './sessions.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, FontAwesomeModule, Button, Spinner, Select, Modal, CalendarWidget, MultiDatePicker],
})
export class Sessions implements OnInit, OnDestroy {
  @ViewChild('headerActions', { static: true }) headerActions!: TemplateRef<unknown>;
  @ViewChild(CalendarWidget) calendarWidget?: CalendarWidget;

  private adminService = inject(AdminService);
  private headerService = inject(HeaderService);
  private confirmService = inject(ConfirmService);
  private toastService = inject(ToastService);
  private cdr = inject(ChangeDetectorRef);
  private subs = new Subscription();

  readonly statusMeta = SESSION_STATUS;
  readonly skeletonCells = Array.from({ length: 35 }, (_, i) => i);

  // ── datos ────────────────────────────────────────────────────────────────
  therapists: { id: number; username: string }[] = [];
  allPatients: { id: number; username: string }[] = [];
  patients: { id: number; username: string }[] = [];
  patientGroups: any[] = [];
  sedes: Sede[] = [];
  holidaysMap = new Map<string, string>();

  rawEvents: any[] = [];
  widgetEvents: CalendarWidgetEvent[] = [];

  // ── filtros / carga ──────────────────────────────────────────────────────
  selectedTherapistId: number | null = null;
  selectedPatientId: number | null = null;
  loading = true; // primera carga (el calendario aún no existe)
  refreshing = false; // recargas posteriores: el calendario sigue montado
  loadError = false;
  private viewMonth = new Date();
  private load$ = new Subject<void>();

  // ── modales ──────────────────────────────────────────────────────────────
  showCreateModal = false;
  showEditModal = false;
  showDetailModal = false;
  showBulkProgramModal = false;

  // crear
  createForm = { therapist_id: '', patient_id: '', title: '', sede: '', session_type: 'individual', start_time: '', end_time: '', notes: '' };
  createDates: string[] = [];
  dayNotes: Record<string, string> = {};
  selectedGroupId: number | null = null;
  unlockPastDates = false;
  createProgramFile: File | null = null;
  patientsLoading = false;
  submitting = false;
  submitted = false;
  createProgress = 0;
  createResult: CreateResult | null = null;

  // editar
  editForm = { id: 0, title: '', date: '', start_time: '', end_time: '', status: 'scheduled' as string, notes: '', therapist: '', patient: '' };
  editConflict: string | null = null;
  auditState: { has_program?: boolean; planned_text_preview?: string } | null = null;
  programUploading = false;
  programDeleting = false;
  programError: string | null = null;
  programSuccessMessage: string | null = null;
  deleting = false;

  // detalle
  detailSession: any = null;
  detailLoading = false;
  detailShowProgram = false;

  // selección múltiple
  multiSelectMode = false;
  selectedSessionIds = new Set<number>();
  bulkProgramFile: File | null = null;
  bulkProgramUploading = false;
  bulkProgramError: string | null = null;

  // ── opciones de selects ─────────────────────────────────────────────────
  get therapistOptions(): SelectOption[] {
    return [{ value: null, label: 'Todos los terapeutas' }, ...this.therapists.map((t) => ({ value: t.id, label: t.username }))];
  }
  get patientFilterOptions(): SelectOption[] {
    return [{ value: null, label: 'Todos los alumnos' }, ...this.allPatients.map((p) => ({ value: p.id, label: p.username }))];
  }
  get therapistCreateOptions(): SelectOption[] {
    return [{ value: null, label: 'Seleccionar terapeuta' }, ...this.therapists.map((t) => ({ value: t.id, label: t.username }))];
  }
  get patientCreateOptions(): SelectOption[] {
    return [{ value: null, label: 'Seleccionar paciente' }, ...this.patients.map((p) => ({ value: p.id, label: p.username }))];
  }
  get sedeCreateOptions(): SelectOption[] {
    return [{ value: null, label: 'Sin sede' }, ...this.sedes.map((s) => ({ value: s.name, label: s.name }))];
  }
  get groupSelectOptions(): SelectOption[] {
    return [{ value: null, label: 'Seleccionar grupo' }, ...this.patientGroups.map((g) => ({ value: g.id, label: `${g.name} (${g.member_count} pac.)` }))];
  }
  readonly statusOptions: SelectOption[] = Object.entries(SESSION_STATUS).map(([value, m]) => ({ value, label: m.label }));
  readonly sessionTypeOptions: SelectOption[] = [
    { value: 'individual', label: 'Individual' },
    { value: 'grupal', label: 'Grupal' },
    { value: 'evaluacion', label: 'Evaluación' },
  ];

  get hasFilters(): boolean {
    return !!(this.selectedTherapistId || this.selectedPatientId);
  }
  get selectedGroup(): any | null {
    return this.patientGroups.find((g) => g.id === this.selectedGroupId) || null;
  }
  get isGroupCreate(): boolean {
    return this.createForm.session_type === 'grupal';
  }

  // ── ciclo de vida ───────────────────────────────────────────────────────
  ngOnInit() {
    this.headerService.setConfig({
      title: 'Calendario global de sesiones',
      subtitle: 'Gestiona las sesiones de todos los terapeutas',
      icon: ['fas', 'calendar-days'],
      actionTemplate: this.headerActions,
    });

    // Una sola tubería de carga: si el usuario cambia de mes o de filtro rápido, la respuesta vieja se descarta.
    this.subs.add(
      this.load$
        .pipe(
          tap(() => {
            this.refreshing = true;
            this.loadError = false;
            this.cdr.markForCheck();
          }),
          switchMap(() => {
            const { start, end } = this.visibleRange();
            return this.adminService
              .getSessions(start, end, this.selectedTherapistId ?? undefined, this.selectedPatientId ?? undefined)
              .pipe(catchError(() => of(null)));
          }),
        )
        .subscribe((events) => {
          if (events) this.applyEvents(events);
          else {
            this.loadError = true;
            this.toastService.show('No se pudieron cargar las sesiones.', 'error');
          }
          this.loading = false;
          this.refreshing = false;
          this.cdr.markForCheck();
        }),
    );

    this.loadLookups();
    this.requestLoad();
  }

  ngOnDestroy() {
    this.subs.unsubscribe();
    this.headerService.reset();
  }

  private loadLookups() {
    this.subs.add(
      forkJoin({
        therapists: this.adminService.getUsers('terapista').pipe(catchError(() => of({ users: [] }))),
        patients: this.adminService.getUsers('jugador').pipe(catchError(() => of({ users: [] }))),
        sedes: this.adminService.getSedes().pipe(catchError(() => of([] as Sede[]))),
        groups: this.adminService.getPatientGroups().pipe(catchError(() => of({ groups: [] }))),
        holidays: this.adminService.getHolidays().pipe(catchError(() => of({ holidays: [] }))),
      }).subscribe((r: any) => {
        // Una respuesta inesperada de un catálogo no debe romper el resto de la página.
        const list = <T>(v: unknown): T[] => (Array.isArray(v) ? (v as T[]) : []);
        this.therapists = list<any>(r.therapists?.users).map((u) => ({ id: u.id, username: u.username }));
        this.allPatients = list<any>(r.patients?.users).map((u) => ({ id: u.id, username: u.username }));
        this.sedes = list<Sede>(r.sedes).filter((s) => s.active !== false);
        this.patientGroups = list<any>(r.groups?.groups);
        this.holidaysMap = new Map(list<any>(r.holidays?.holidays).map((h) => [h.date, h.name] as [string, string]));
        this.cdr.markForCheck();
      }),
    );
  }

  // ── carga de sesiones ───────────────────────────────────────────────────
  /** Mes visible ± 7 días: la cuadrícula muestra también días de los meses vecinos. */
  private visibleRange(): { start: string; end: string } {
    const m = this.viewMonth;
    const start = new Date(m.getFullYear(), m.getMonth(), 1 - 7);
    const end = new Date(m.getFullYear(), m.getMonth() + 1, 7);
    return { start: toLocalDateString(start), end: toLocalDateString(end) };
  }

  requestLoad() {
    this.load$.next();
  }

  private applyEvents(events: any[]) {
    this.rawEvents = events;
    this.widgetEvents = events.map((e: any) => ({
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
  }

  onMonthChange(month: Date) {
    this.viewMonth = new Date(month.getFullYear(), month.getMonth(), 1);
    this.requestLoad();
  }

  onFilterChange() {
    this.requestLoad();
  }

  clearFilters() {
    this.selectedTherapistId = null;
    this.selectedPatientId = null;
    this.requestLoad();
  }

  // ── calendario → modales ────────────────────────────────────────────────
  onDayDblClick(date: Date) {
    this.openCreateModal();
    this.createDates = [toLocalDateString(date)];
  }

  onRangeDblClick(range: { start: Date; end: Date }) {
    this.openCreateModal();
    const dates: string[] = [];
    for (const d = new Date(range.start); d <= range.end && dates.length < 10; d.setDate(d.getDate() + 1)) {
      const key = toLocalDateString(d);
      if (!this.holidaysMap.has(key)) dates.push(key);
    }
    this.createDates = dates;
  }

  onEventClick(event: CalendarWidgetEvent) {
    this.openDetailModal(event);
  }

  // ── detalle ─────────────────────────────────────────────────────────────
  openDetailModal(event: CalendarWidgetEvent) {
    const raw = this.rawEvents.find((e) => e.id === event.id);
    this.detailLoading = true;
    this.detailSession = null;
    this.detailShowProgram = false;
    this.showDetailModal = true;

    this.subs.add(
      forkJoin({
        audit: this.adminService.getSessionAudit(event.id).pipe(catchError(() => of(null))),
        program: this.adminService.getSessionProgram(event.id).pipe(catchError(() => of(null))),
      }).subscribe(({ audit, program }) => {
        this.detailSession = {
          id: event.id,
          title: raw?.title || event.title,
          status: raw?.extendedProps?.status || event.status,
          date: toLocalDateString(event.date),
          time: event.time,
          endTime: event.endTime,
          therapist: raw?.extendedProps?.therapist || event.therapist,
          patient: raw?.extendedProps?.patient || event.patient,
          location: raw?.extendedProps?.location || null,
          sessionType: raw?.extendedProps?.session_type || null,
          notes: raw?.extendedProps?.notes || null,
          audit: audit?.audit || null,
          auditExists: !!audit?.exists,
          programText: program?.program_text || null,
          hasProgram: !!program?.has_program,
        };
        this.detailLoading = false;
        this.cdr.markForCheck();
      }),
    );
  }

  closeDetailModal() {
    this.showDetailModal = false;
    this.detailSession = null;
    this.detailShowProgram = false;
  }

  editFromDetail() {
    const d = this.detailSession;
    if (!d) return;
    this.closeDetailModal();
    this.openEditModal({
      id: d.id,
      title: d.title,
      date: new Date(d.date + 'T12:00:00'),
      time: d.time,
      endTime: d.endTime,
      status: d.status,
      therapist: d.therapist,
      patient: d.patient,
    });
  }

  // ── editar ──────────────────────────────────────────────────────────────
  openEditModal(event: CalendarWidgetEvent) {
    const raw = this.rawEvents.find((e) => e.id === event.id);
    this.editForm = {
      id: event.id,
      title: raw?.title || event.title,
      date: toLocalDateString(event.date),
      start_time: event.time || '',
      end_time: event.endTime || '',
      status: raw?.extendedProps?.status || event.status,
      notes: raw?.extendedProps?.notes || '',
      therapist: raw?.extendedProps?.therapist || event.therapist || '',
      patient: raw?.extendedProps?.patient || event.patient || '',
    };
    this.editConflict = null;
    this.auditState = null;
    this.programError = null;
    this.programSuccessMessage = null;
    this.showEditModal = true;
    this.cdr.markForCheck();

    this.subs.add(
      this.adminService.getSessionAudit(event.id).pipe(catchError(() => of(null))).subscribe((data: any) => {
        if (data?.success && data.exists && data.audit?.has_program) this.auditState = data.audit;
        this.cdr.markForCheck();
      }),
    );
  }

  closeEditModal() {
    this.showEditModal = false;
    this.submitting = false;
    this.editConflict = null;
    this.auditState = null;
  }

  get editTimesInvalid(): boolean {
    const f = this.editForm;
    return !!f.start_time && !!f.end_time && f.end_time <= f.start_time;
  }

  submitEdit(force = false) {
    const f = this.editForm;
    if (!f.date || !f.start_time || !f.end_time || this.editTimesInvalid) return;
    this.submitting = true;
    this.editConflict = null;
    this.subs.add(
      this.adminService
        .updateSession(f.id, {
          title: f.title,
          notes: f.notes,
          start_time: `${f.date}T${f.start_time}`,
          end_time: `${f.date}T${f.end_time}`,
          status: f.status,
          ...(force ? { force: true } : {}),
        } as any)
        .subscribe({
          next: () => {
            this.submitting = false;
            this.closeEditModal();
            this.requestLoad();
            this.toastService.show('Sesión actualizada', 'success');
            this.cdr.markForCheck();
          },
          error: (err) => {
            this.submitting = false;
            if (err?.status === 409) this.editConflict = err.error?.error || 'La sesión choca con otra ya programada.';
            else this.toastService.show(err?.error?.error || 'No se pudo actualizar la sesión.', 'error');
            this.cdr.markForCheck();
          },
        }),
    );
  }

  async deleteSession() {
    const ok = await firstValueFrom(
      this.confirmService.confirm({
        title: 'Eliminar sesión',
        message: `Se eliminará «${this.editForm.title || 'esta sesión'}». Esta acción no se puede deshacer.`,
        confirmText: 'Eliminar',
        variant: 'danger',
      }),
    );
    if (!ok) return;
    this.deleting = true;
    this.subs.add(
      this.adminService.deleteSession(this.editForm.id).subscribe({
        next: () => {
          this.deleting = false;
          this.closeEditModal();
          this.requestLoad();
          this.toastService.show('Sesión eliminada', 'success');
          this.cdr.markForCheck();
        },
        error: () => {
          this.deleting = false;
          this.toastService.show('No se pudo eliminar la sesión.', 'error');
          this.cdr.markForCheck();
        },
      }),
    );
  }

  onProgramSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    input.value = '';
    if (!file || !this.editForm.id) return;
    if (!file.name.toLowerCase().endsWith('.docx')) {
      this.programError = 'Solo se permiten archivos .docx';
      return;
    }
    this.programUploading = true;
    this.programError = null;
    this.programSuccessMessage = null;
    this.subs.add(
      this.adminService.uploadSessionProgram(this.editForm.id, file).subscribe({
        next: (res: any) => {
          this.programUploading = false;
          if (res.success) {
            this.programSuccessMessage = 'Programación subida.';
            this.auditState = { has_program: true, planned_text_preview: res.planned_text_preview };
          } else this.programError = res.error || 'No se pudo procesar el documento.';
          this.cdr.markForCheck();
        },
        error: (err) => {
          this.programUploading = false;
          this.programError = err?.error?.error || 'No se pudo subir el documento.';
          this.cdr.markForCheck();
        },
      }),
    );
  }

  async deleteProgram() {
    const ok = await firstValueFrom(
      this.confirmService.confirm({ title: 'Quitar programación', message: '¿Quitar el documento de programación de esta sesión?', confirmText: 'Quitar', variant: 'danger' }),
    );
    if (!ok) return;
    this.programDeleting = true;
    this.subs.add(
      this.adminService.deleteSessionProgram(this.editForm.id).subscribe({
        next: (res: any) => {
          this.programDeleting = false;
          if (res.success) {
            this.auditState = null;
            this.programSuccessMessage = 'Programación quitada.';
          } else this.programError = res.error || 'No se pudo quitar.';
          this.cdr.markForCheck();
        },
        error: () => {
          this.programDeleting = false;
          this.programError = 'No se pudo quitar la programación.';
          this.cdr.markForCheck();
        },
      }),
    );
  }

  // ── crear ───────────────────────────────────────────────────────────────
  openCreateModal() {
    this.createForm = { therapist_id: '', patient_id: '', title: '', sede: '', session_type: 'individual', start_time: '', end_time: '', notes: '' };
    this.createDates = [];
    this.dayNotes = {};
    this.selectedGroupId = null;
    this.unlockPastDates = false;
    this.createProgramFile = null;
    this.patients = [];
    this.submitted = false;
    this.submitting = false;
    this.createProgress = 0;
    this.createResult = null;
    this.showCreateModal = true;
    this.cdr.markForCheck();
  }

  closeCreateModal() {
    this.showCreateModal = false;
    this.submitting = false;
    this.createResult = null;
  }

  onTherapistSelectCreate() {
    const id = parseInt(this.createForm.therapist_id, 10);
    this.createForm.patient_id = '';
    if (!id) {
      this.patients = [];
      return;
    }
    this.patientsLoading = true;
    this.subs.add(
      this.adminService.getPatientsByTherapist(id).subscribe({
        next: (list) => {
          this.patients = list;
          this.patientsLoading = false;
          this.cdr.markForCheck();
        },
        error: () => {
          this.patients = [];
          this.patientsLoading = false;
          this.toastService.show('No se pudieron cargar los pacientes del terapeuta.', 'error');
          this.cdr.markForCheck();
        },
      }),
    );
  }

  onGroupSelect(groupId: number | null) {
    this.selectedGroupId = groupId;
    const group = this.selectedGroup;
    if (!group) return;
    if (group.start_time) this.createForm.start_time = group.start_time;
    if (group.end_time) this.createForm.end_time = group.end_time;
    const sede = this.sedes.find((s) => s.id === group.sede_id);
    if (sede) this.createForm.sede = sede.name;
    const dates: string[] = Array.isArray(group.session_dates) ? group.session_dates.filter(Boolean).slice(0, 10) : [];
    if (dates.length) this.createDates = dates;
    this.cdr.markForCheck();
  }

  /** Errores del formulario: se muestran junto al campo tras el primer intento de enviar. */
  get createErrors(): Record<string, string> {
    const f = this.createForm;
    const e: Record<string, string> = {};
    if (!f.therapist_id) e['therapist'] = 'Elige un terapeuta.';
    if (this.isGroupCreate ? !this.selectedGroup?.member_ids?.length : !f.patient_id) {
      e['patient'] = this.isGroupCreate ? 'Elige un grupo con pacientes.' : 'Elige un paciente.';
    }
    if (!this.createDates.length) e['dates'] = 'Elige al menos una fecha.';
    if (!f.start_time) e['start'] = 'Indica la hora de inicio.';
    if (!f.end_time) e['end'] = 'Indica la hora de fin.';
    else if (f.start_time && f.end_time <= f.start_time) e['end'] = 'Debe ser posterior al inicio.';
    return e;
  }

  get createCount(): number {
    const patients = this.isGroupCreate ? this.selectedGroup?.member_count || 0 : this.createForm.patient_id ? 1 : 0;
    return this.createDates.length * patients;
  }

  get hasErrors(): boolean {
    return Object.keys(this.createErrors).length > 0;
  }

  async submitCreate() {
    this.submitted = true;
    if (this.hasErrors || this.submitting) return;
    if (this.createCount >= 20) {
      const ok = await firstValueFrom(
        this.confirmService.confirm({ title: 'Programar muchas sesiones', message: `Se crearán ${this.createCount} sesiones. ¿Continuar?`, confirmText: 'Crear', variant: 'primary' }),
      );
      if (!ok) return;
    }
    const f = this.createForm;
    const group = this.isGroupCreate ? this.selectedGroup : null;
    const payload: any = {
      therapist_id: parseInt(f.therapist_id, 10),
      title_prefix: f.title,
      sede: f.sede || '',
      session_type: f.session_type,
      dates: this.createDates,
      start_time: f.start_time,
      end_time: f.end_time,
      unlock_past_dates: this.unlockPastDates,
      notes: f.notes,
      day_notes: this.dayNotes,
    };
    if (group) {
      payload.patient_ids = group.member_ids;
      payload.group_id = group.id;
    } else payload.patient_id = parseInt(f.patient_id, 10);

    this.submitting = true;
    this.createProgress = 15;
    this.cdr.markForCheck();
    this.subs.add(
      this.adminService.batchCreateSessions(payload).subscribe({
        next: (res: any) => this.afterCreate(res),
        error: (err) => {
          this.submitting = false;
          this.createProgress = 0;
          if (err?.status === 409 && err.error?.conflicts) {
            this.createResult = { created: 0, conflicts: err.error.conflicts, holidays: err.error.skipped_holidays || [], message: err.error.error, failed: true };
          } else this.toastService.show(err?.error?.error || 'No se pudieron crear las sesiones.', 'error');
          this.cdr.markForCheck();
        },
      }),
    );
  }

  private afterCreate(res: any) {
    const ids: number[] = res?.session_ids || [];
    const finish = (programOk: boolean) => {
      this.createProgress = 100;
      this.submitting = false;
      this.createResult = {
        created: res?.created ?? ids.length,
        conflicts: res?.conflicts || [],
        holidays: res?.skipped_holidays || [],
        message: res?.message || '',
        failed: false,
      };
      if (!programOk) this.toastService.show('Las sesiones se crearon, pero no se pudo asignar la programación.', 'warning');
      this.requestLoad();
      this.cdr.markForCheck();
      // Sin nada que leer: se muestra la confirmación un instante y se cierra sola.
      if (!this.createResult.conflicts.length && !this.createResult.holidays.length) setTimeout(() => this.showCreateModal && this.closeCreateModal() , 1100);
    };
    if (this.createProgramFile && ids.length) {
      this.createProgress = 55;
      this.cdr.markForCheck();
      this.subs.add(this.adminService.bulkAssignProgram(ids, this.createProgramFile).subscribe({ next: () => finish(true), error: () => finish(false) }));
    } else finish(true);
  }

  onCreateFileSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0] || null;
    input.value = '';
    this.createProgramFile = file && file.name.toLowerCase().endsWith('.docx') ? file : null;
    if (file && !this.createProgramFile) this.toastService.show('Solo se permiten archivos .docx', 'error');
  }

  conflictLabel(c: Conflict): string {
    const name = this.allPatients.find((p) => p.id === c.patient_id)?.username;
    return `${c.date}${name ? ' · ' + name : ''}`;
  }

  // ── selección múltiple + programación en lote ───────────────────────────
  toggleMultiSelect() {
    this.multiSelectMode = !this.multiSelectMode;
    if (!this.multiSelectMode) this.selectedSessionIds = new Set();
    this.cdr.markForCheck();
  }

  onSelectionChange(ids: number[]) {
    this.selectedSessionIds = new Set(ids);
    this.cdr.markForCheck();
  }

  openBulkProgramModal() {
    if (!this.selectedSessionIds.size) return;
    this.bulkProgramFile = null;
    this.bulkProgramError = null;
    this.showBulkProgramModal = true;
  }

  closeBulkProgramModal() {
    this.showBulkProgramModal = false;
    this.bulkProgramFile = null;
    this.bulkProgramError = null;
  }

  onBulkFileSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    input.value = '';
    if (!file) return;
    if (!file.name.toLowerCase().endsWith('.docx')) {
      this.bulkProgramError = 'Solo se permiten archivos .docx';
      return;
    }
    this.bulkProgramFile = file;
    this.bulkProgramError = null;
  }

  submitBulkProgram() {
    if (!this.bulkProgramFile || !this.selectedSessionIds.size) return;
    this.bulkProgramUploading = true;
    this.bulkProgramError = null;
    this.subs.add(
      this.adminService.bulkAssignProgram([...this.selectedSessionIds], this.bulkProgramFile).subscribe({
        next: (res) => {
          this.bulkProgramUploading = false;
          this.closeBulkProgramModal();
          this.selectedSessionIds = new Set();
          this.multiSelectMode = false;
          this.toastService.show(`Programación asignada a ${res.updated} sesión(es)`, 'success');
          this.requestLoad();
          this.cdr.markForCheck();
        },
        error: (err) => {
          this.bulkProgramUploading = false;
          this.bulkProgramError = err?.error?.error || 'No se pudo asignar la programación.';
          this.cdr.markForCheck();
        },
      }),
    );
  }

  // ── helpers de plantilla ────────────────────────────────────────────────
  statusOf(status: string) {
    return this.statusMeta[status] || { label: status, badge: 'badge--neutral' };
  }
}

export type { SessionStatus };
