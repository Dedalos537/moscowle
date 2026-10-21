import { ChangeDetectionStrategy, Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { Subject, debounceTime } from 'rxjs';
import {
  ActivityDetail,
  ActivityEventRow,
  ActivityPending,
  ActivityUserRow,
  AdminService,
} from '../../../../core/services/admin.service';
import { ConfirmService } from '../../../../core/services/confirm.service';
import { ToastService } from '../../../../core/services/toast.service';
import { PersonLabelPipe } from '../../../../shared/pipes/person-label.pipe';

type Tab = 'pending' | 'done';

const ROLE_LABEL: Record<string, string> = {
  admin: 'Admin',
  supervisor: 'Supervisor',
  terapista: 'Terapeuta',
  jugador: 'Paciente',
};

const TYPE_LABEL: Record<string, string> = {
  login: 'Accesos',
  session: 'Sesiones',
  session_created: 'Sesiones creadas',
  payment: 'Pagos',
  expense: 'Gastos',
  task: 'Tareas',
  incident: 'Incidencias',
  incident_resolved: 'Incidencias resueltas',
  request: 'Solicitudes',
  request_reviewed: 'Revisiones',
  print: 'Impresiones',
  ai: 'Asistente',
  status: 'Estados de cuenta',
  edit: 'Ediciones',
};

/** Revisión de actividad por usuario (PRP 012): lista con pendientes y detalle «Pendiente / Hecho». Solo admin. */
@Component({
  selector: 'app-activity-review',
  imports: [FormsModule, FontAwesomeModule, PersonLabelPipe],
  templateUrl: './activity-review.html',
  styleUrl: './activity-review.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ActivityReview {
  private api = inject(AdminService);
  private router = inject(Router);
  private toast = inject(ToastService);
  private confirm = inject(ConfirmService);
  private destroyRef = inject(DestroyRef);
  private search$ = new Subject<void>();

  readonly roles = [
    { value: '', label: 'Todos los roles' },
    { value: 'terapista', label: 'Terapeutas' },
    { value: 'jugador', label: 'Pacientes' },
    { value: 'admin', label: 'Admins' },
    { value: 'supervisor', label: 'Supervisores' },
  ];
  readonly typeLabels = TYPE_LABEL;

  role = '';
  query = '';
  onlyPending = false;

  readonly loading = signal(true);
  readonly users = signal<ActivityUserRow[]>([]);
  readonly selected = signal<ActivityUserRow | null>(null);
  readonly detail = signal<ActivityDetail | null>(null);
  readonly tab = signal<Tab>('pending');
  readonly events = signal<ActivityEventRow[]>([]);
  readonly eventsTotal = signal(0);
  readonly page = signal(1);
  readonly loadingEvents = signal(false);
  readonly typeFilter = signal<string>('');
  rangeDays = 30;

  readonly totals = computed(() => {
    const list = this.users();
    return {
      people: list.length,
      withPending: list.filter((u) => u.pending > 0).length,
      high: list.reduce((a, u) => a + u.pending_high, 0),
    };
  });

  readonly sparkMax = computed(() => Math.max(1, ...(this.detail()?.daily ?? []).map((d) => d.n)));
  readonly eventTypes = computed(() => [...new Set(this.events().map((e) => e.type))]);
  readonly hasMore = computed(() => this.events().length < this.eventsTotal());

  constructor() {
    this.search$.pipe(debounceTime(250), takeUntilDestroyed(this.destroyRef)).subscribe(() => this.load());
    this.load();
  }

  roleLabel(role: string) {
    return ROLE_LABEL[role] ?? role;
  }

  onFilter() {
    this.search$.next();
  }

  load() {
    this.loading.set(true);
    this.api
      .activityUsers({ role: this.role || undefined, only_pending: this.onlyPending, q: this.query.trim() || undefined })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (r) => {
          this.users.set(r.users);
          this.loading.set(false);
        },
        error: () => {
          this.loading.set(false);
          this.toast.show('No se pudo cargar la actividad.', 'error');
        },
      });
  }

  open(u: ActivityUserRow) {
    this.selected.set(u);
    this.detail.set(null);
    this.tab.set(u.pending ? 'pending' : 'done');
    this.events.set([]);
    this.page.set(1);
    this.typeFilter.set('');
    this.api
      .activityDetail(u.id)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({ next: (d) => this.detail.set(d), error: () => this.toast.show('No se pudo abrir el detalle.', 'error') });
    this.loadEvents(true);
  }

  close() {
    this.selected.set(null);
    this.detail.set(null);
  }

  private rangeFrom() {
    const d = new Date();
    d.setDate(d.getDate() - this.rangeDays);
    return d.toISOString().slice(0, 19);
  }

  loadEvents(reset = false) {
    const u = this.selected();
    if (!u) return;
    if (reset) this.page.set(1);
    this.loadingEvents.set(true);
    const types = this.typeFilter() ? [this.typeFilter()] : undefined;
    this.api
      .activityTimeline(u.id, { from: this.rangeFrom(), types, page: this.page() })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (t) => {
          this.events.set(reset ? t.events : [...this.events(), ...t.events]);
          this.eventsTotal.set(t.total);
          this.loadingEvents.set(false);
        },
        error: () => this.loadingEvents.set(false),
      });
  }

  more() {
    this.page.update((p) => p + 1);
    this.loadEvents();
  }

  setType(t: string) {
    this.typeFilter.set(t);
    this.loadEvents(true);
  }

  setRange(days: number) {
    this.rangeDays = days;
    this.loadEvents(true);
  }

  go(link: string | null) {
    if (link) void this.router.navigateByUrl(link);
  }

  severityLabel(p: ActivityPending) {
    return p.severity === 'high' ? 'Urgente' : p.severity === 'medium' ? 'Atender' : 'Menor';
  }

  dayKey(iso: string) {
    return new Date(iso).toLocaleDateString('es-PE', { weekday: 'long', day: 'numeric', month: 'long' });
  }

  time(iso: string) {
    return new Date(iso).toLocaleTimeString('es-PE', { hour: '2-digit', minute: '2-digit' });
  }

  ago(iso: string | null) {
    if (!iso) return 'Nunca';
    const mins = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
    if (mins < 60) return `hace ${Math.max(1, mins)} min`;
    const h = Math.round(mins / 60);
    if (h < 24) return `hace ${h} h`;
    const d = Math.round(h / 24);
    return d === 1 ? 'ayer' : `hace ${d} días`;
  }

  /** Agrupa la línea de tiempo por día para pintar encabezados. */
  readonly grouped = computed(() => {
    const out: { day: string; items: ActivityEventRow[] }[] = [];
    for (const e of this.events()) {
      const day = this.dayKey(e.at);
      const last = out[out.length - 1];
      if (last && last.day === day) last.items.push(e);
      else out.push({ day, items: [e] });
    }
    return out;
  });

  async revoke() {
    const u = this.selected();
    if (!u) return;
    const ok = await new Promise<boolean>((resolve) =>
      this.confirm
        .confirm({
          title: 'Cerrar sus sesiones',
          message: `${u.name} tendrá que volver a iniciar sesión en todos sus dispositivos.`,
          confirmText: 'Cerrar sesiones',
          variant: 'danger',
        })
        .subscribe(resolve),
    );
    if (!ok) return;
    this.api.revokeUserSessions(u.id).subscribe({
      next: (r) => {
        this.toast.show(`Se cerraron ${r.revoked} sesión(es).`, 'success');
        this.open(u);
      },
      error: (e) => this.toast.show(e?.error?.error || 'No se pudieron cerrar las sesiones.', 'error'),
    });
  }

  export(all = false) {
    const u = this.selected();
    this.api.exportActivity({ user_id: all ? undefined : u?.id, from: this.rangeFrom() }).subscribe({
      next: (blob) => {
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = `actividad${!all && u ? '-' + u.id : ''}.xlsx`;
        a.click();
        setTimeout(() => URL.revokeObjectURL(a.href), 1000);
      },
      error: () => this.toast.show('No se pudo exportar.', 'error'),
    });
  }
}
