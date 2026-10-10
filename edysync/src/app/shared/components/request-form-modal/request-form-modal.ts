import { ChangeDetectionStrategy, Component, computed, effect, inject, input, output, signal, untracked } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { ActionRequest, ActionRequestService, REQUEST_KIND_LABEL, RequestKind, RequestOptions } from '../../../core/services/action-request.service';
import { Modal } from '../modal/modal';
import { Select, SelectOption } from '../select/select';
import { MultiDatePicker } from '../multi-date-picker/multi-date-picker';

/**
 * Formulario de solicitud del terapeuta: los mismos campos que usa la coordinación para programar sesiones, dar de
 * alta un paciente o crear un grupo, pero en vez de ejecutarse se envía para aprobación (como el cambio de clave).
 */
@Component({
  selector: 'app-request-form-modal',
  standalone: true,
  imports: [FormsModule, FontAwesomeModule, Modal, Select, MultiDatePicker],
  templateUrl: './request-form-modal.html',
  styleUrl: './request-form-modal.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class RequestFormModal {
  private service = inject(ActionRequestService);

  kind = input<RequestKind | null>(null);
  closed = output<void>();
  sent = output<ActionRequest>();

  readonly labels = REQUEST_KIND_LABEL;
  readonly options = signal<RequestOptions | null>(null);
  readonly loadingOptions = signal(false);
  readonly sending = signal(false);
  readonly submitted = signal(false);
  readonly serverError = signal<string | null>(null);
  readonly done = signal<ActionRequest | null>(null);

  // Sesiones (mismos campos que el modal de la coordinación)
  s = { session_type: 'individual', patient_id: '' as string | number, group_id: null as number | null, title_prefix: '', sede: '', start_time: '', end_time: '', notes: '' };
  dates: string[] = [];
  dayNotes: Record<string, string> = {};
  // Paciente
  p = { username: '', email: '', phone: '', guardian_name: '', guardian_contact: '', sede_id: null as number | null, notes: '' };
  // Grupo
  g = { name: '', member_ids: [] as number[], sede_id: null as number | null, start_time: '', end_time: '', notes: '' };

  readonly typeOptions: SelectOption[] = [
    { value: 'individual', label: 'Individual' },
    { value: 'grupal', label: 'Grupal' },
    { value: 'evaluacion', label: 'Evaluación' },
  ];

  readonly patientOptions = computed<SelectOption[]>(() => (this.options()?.patients ?? []).map((x) => ({ value: x.id, label: x.username })));
  readonly groupOptions = computed<SelectOption[]>(() =>
    (this.options()?.groups ?? []).map((x) => ({ value: x.id, label: `${x.name} · ${x.member_count} ${x.member_count === 1 ? 'paciente' : 'pacientes'}` })),
  );
  readonly sedeNameOptions = computed<SelectOption[]>(() => (this.options()?.sedes ?? []).map((x) => ({ value: x.name, label: x.name })));
  readonly sedeIdOptions = computed<SelectOption[]>(() => (this.options()?.sedes ?? []).map((x) => ({ value: x.id, label: x.name })));

  constructor() {
    effect(() => {
      const k = this.kind();
      if (!k) return;
      // Solo reacciona a que se abra el formulario; leer las opciones aquí lo reiniciaría al terminar de cargarlas.
      untracked(() => this.open());
    });
  }

  /** Cada vez que se abre: formulario limpio y opciones frescas (un paciente recién aprobado ya aparece). */
  private open() {
    this.reset();
    this.loadingOptions.set(true);
    this.service.options().subscribe({
      next: (o) => {
        this.options.set(o);
        this.loadingOptions.set(false);
      },
      error: () => {
        this.loadingOptions.set(false);
        this.serverError.set('No se pudieron cargar tus pacientes. Cierra y vuelve a intentar.');
      },
    });
  }

  get isGroupSession(): boolean {
    return this.s.session_type === 'grupal';
  }

  get errors(): Record<string, string> {
    const e: Record<string, string> = {};
    const k = this.kind();
    if (k === 'sessions') {
      if (this.isGroupSession ? !this.s.group_id : !this.s.patient_id) e['who'] = this.isGroupSession ? 'Elige uno de tus grupos.' : 'Elige un paciente.';
      if (!this.dates.length) e['dates'] = 'Elige al menos una fecha.';
      if (!this.s.start_time) e['start'] = 'Indica la hora de inicio.';
      if (!this.s.end_time) e['end'] = 'Indica la hora de fin.';
      else if (this.s.start_time && this.s.end_time <= this.s.start_time) e['end'] = 'Debe ser posterior al inicio.';
    } else if (k === 'patient') {
      if (this.p.username.trim().length < 3) e['name'] = 'Escribe el nombre completo.';
      if (this.p.email && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(this.p.email.trim())) e['email'] = 'Revisa el correo.';
    } else if (k === 'group') {
      if (this.g.name.trim().length < 2) e['name'] = 'Escribe el nombre del grupo.';
      if (!this.g.member_ids.length) e['members'] = 'Elige al menos un paciente.';
      if (this.g.start_time && this.g.end_time && this.g.end_time <= this.g.start_time) e['end'] = 'Debe ser posterior al inicio.';
    }
    return e;
  }

  get count(): number {
    if (this.kind() !== 'sessions') return 0;
    const members = this.isGroupSession ? this.options()?.groups.find((x) => x.id === this.s.group_id)?.member_count || 0 : this.s.patient_id ? 1 : 0;
    return this.dates.length * members;
  }

  onGroupChange(id: number | null) {
    this.s.group_id = id;
    const grp = this.options()?.groups.find((x) => x.id === id);
    if (grp?.start_time) this.s.start_time = grp.start_time;
    if (grp?.end_time) this.s.end_time = grp.end_time;
  }

  setDayNote(date: string, value: string) {
    this.dayNotes = { ...this.dayNotes, [date]: value };
  }

  submit() {
    this.submitted.set(true);
    this.serverError.set(null);
    const k = this.kind();
    if (!k || Object.keys(this.errors).length || this.sending()) return;
    let payload: Record<string, unknown>;
    if (k === 'sessions') {
      payload = {
        ...this.s,
        patient_id: this.isGroupSession ? null : Number(this.s.patient_id),
        group_id: this.isGroupSession ? this.s.group_id : null,
        dates: this.dates,
        day_notes: Object.fromEntries(Object.entries(this.dayNotes).filter(([d, v]) => this.dates.includes(d) && v.trim())),
      };
    } else if (k === 'patient') payload = { ...this.p, username: this.p.username.trim(), email: this.p.email.trim() };
    else payload = { ...this.g, name: this.g.name.trim() };
    this.sending.set(true);
    this.service.create(k, payload).subscribe({
      next: (r) => {
        this.sending.set(false);
        this.done.set(r.request);
        this.sent.emit(r.request);
      },
      error: (e) => {
        this.sending.set(false);
        this.serverError.set(e?.error?.error || 'No se pudo enviar la solicitud. Revisa tu conexión.');
      },
    });
  }

  close() {
    this.closed.emit();
  }

  private reset() {
    this.submitted.set(false);
    this.serverError.set(null);
    this.done.set(null);
    this.s = { session_type: 'individual', patient_id: '', group_id: null, title_prefix: '', sede: '', start_time: '', end_time: '', notes: '' };
    this.dates = [];
    this.dayNotes = {};
    this.p = { username: '', email: '', phone: '', guardian_name: '', guardian_contact: '', sede_id: null, notes: '' };
    this.g = { name: '', member_ids: [], sede_id: null, start_time: '', end_time: '', notes: '' };
  }
}
