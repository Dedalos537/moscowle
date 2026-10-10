import { ChangeDetectionStrategy, Component, OnDestroy, OnInit, TemplateRef, ViewChild, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { Subscription, interval } from 'rxjs';
import { ActionRequest, ActionRequestService, REQUEST_KIND_LABEL, RequestStatus } from '../../../../core/services/action-request.service';
import { HeaderService } from '../../../../core/services/header.service';
import { ToastService } from '../../../../core/services/toast.service';

type Filter = RequestStatus | 'all';
interface Field {
  label: string;
  value: string;
}

/** Solicitudes de terapeutas (sesiones, altas, grupos): revisar y aprobar o rechazar con motivo. */
@Component({
  selector: 'app-admin-requests',
  standalone: true,
  imports: [FormsModule, FontAwesomeModule],
  templateUrl: './requests.html',
  styleUrl: './requests.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AdminRequests implements OnInit, OnDestroy {
  @ViewChild('headerActions', { static: true }) headerActions!: TemplateRef<unknown>;
  private service = inject(ActionRequestService);
  private header = inject(HeaderService);
  private toast = inject(ToastService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private subs = new Subscription();

  readonly labels = REQUEST_KIND_LABEL;
  readonly filter = signal<Filter>('pending');
  readonly items = signal<ActionRequest[]>([]);
  readonly pending = signal(0);
  readonly loading = signal(true);
  readonly selectedId = signal<number | null>(null);
  readonly busy = signal(false);
  readonly rejecting = signal(false);
  rejectNote = '';

  readonly selected = computed(() => this.items().find((i) => i.id === this.selectedId()) ?? null);
  readonly fields = computed<Field[]>(() => {
    const r = this.selected();
    return r ? this.describe(r) : [];
  });

  ngOnInit() {
    this.header.setConfig({ title: 'Solicitudes', subtitle: 'Pedidos de los terapeutas', icon: ['fas', 'paper-plane'], actionTemplate: this.headerActions });
    const id = Number(this.route.snapshot.queryParamMap.get('id'));
    if (id) this.selectedId.set(id);
    this.load();
    this.subs.add(interval(30_000).subscribe(() => this.load(true)));
  }

  ngOnDestroy() {
    this.header.reset();
    this.subs.unsubscribe();
  }

  load(silent = false) {
    if (!silent) this.loading.set(true);
    const f = this.filter();
    this.subs.add(
      this.service.list(f === 'all' ? undefined : f).subscribe({
        next: (r) => {
          this.items.set(r.requests);
          this.pending.set(r.pending);
          this.loading.set(false);
          if (this.selectedId() && !r.requests.some((x) => x.id === this.selectedId()) && !silent) {
            // Llegó por un aviso con ?id= de una ya resuelta: se muestran todas para encontrarla.
            if (f !== 'all') {
              this.filter.set('all');
              this.load();
            }
          }
        },
        error: () => this.loading.set(false),
      }),
    );
  }

  setFilter(f: Filter) {
    if (f === this.filter()) return;
    this.filter.set(f);
    this.selectedId.set(null);
    this.load();
  }

  select(r: ActionRequest) {
    this.selectedId.set(r.id);
    this.rejecting.set(false);
    this.rejectNote = '';
    this.router.navigate([], { queryParams: { id: r.id }, queryParamsHandling: 'merge', replaceUrl: true });
  }

  approve() {
    const r = this.selected();
    if (!r) return;
    this.busy.set(true);
    this.subs.add(
      this.service.approve(r.id).subscribe({
        next: (res) => {
          this.busy.set(false);
          this.replace(res.request);
          this.toast.show('Solicitud aprobada y aplicada. El terapeuta ya fue avisado.', 'success');
        },
        error: (e) => {
          this.busy.set(false);
          const msg = e?.error?.error || 'No se pudo aplicar la solicitud.';
          this.items.update((list) => list.map((x) => (x.id === r.id ? { ...x, last_error: msg } : x)));
          this.toast.show(msg, 'error');
        },
      }),
    );
  }

  reject() {
    const r = this.selected();
    const note = this.rejectNote.trim();
    if (!r || !note) return;
    this.busy.set(true);
    this.subs.add(
      this.service.reject(r.id, note).subscribe({
        next: (res) => {
          this.busy.set(false);
          this.rejecting.set(false);
          this.replace(res.request);
          this.toast.show('Solicitud rechazada. El terapeuta verá el motivo.', 'success');
        },
        error: (e) => {
          this.busy.set(false);
          this.toast.show(e?.error?.error || 'No se pudo rechazar.', 'error');
        },
      }),
    );
  }

  private replace(updated: ActionRequest) {
    this.items.update((list) => list.map((x) => (x.id === updated.id ? updated : x)));
    this.pending.update((n) => Math.max(0, n - 1));
  }

  status(s: string) {
    return ({ pending: 'Pendiente', approved: 'Aprobada', rejected: 'Rechazada' } as Record<string, string>)[s] ?? s;
  }

  when(iso: string | null) {
    if (!iso) return '';
    return new Date(iso).toLocaleString('es-PE', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
  }

  /** El formulario del terapeuta en palabras, para revisarlo sin abrir otra pantalla. */
  private describe(r: ActionRequest): Field[] {
    const p = r.payload as Record<string, any>;
    const out: Field[] = [];
    const add = (label: string, value: unknown) => {
      if (value !== null && value !== undefined && String(value).trim() !== '') out.push({ label, value: String(value) });
    };
    if (r.kind === 'sessions') {
      add('Tipo', { individual: 'Individual', grupal: 'Grupal', evaluacion: 'Evaluación' }[p['session_type'] as string] ?? p['session_type']);
      add('Nombre de la sesión', p['title_prefix']);
      add('Fechas', (p['dates'] as string[]).join(', '));
      add('Horario', `${p['start_time']} – ${p['end_time']}`);
      add('Sede', p['sede']);
      add('Comentario general', p['notes']);
      Object.entries((p['day_notes'] || {}) as Record<string, string>).forEach(([d, n]) => add(`Nota del ${d}`, n));
    } else if (r.kind === 'patient') {
      add('Nombre', p['username']);
      add('Correo', p['email'] || 'Sin correo (se creará sin acceso hasta que se agregue)');
      add('Teléfono', p['phone']);
      add('Apoderado', p['guardian_name']);
      add('Contacto del apoderado', p['guardian_contact']);
      add('Motivo o comentarios', p['notes']);
    } else {
      add('Nombre del grupo', p['name']);
      add('Pacientes', `${(p['member_ids'] as number[]).length}`);
      if (p['start_time']) add('Horario', `${p['start_time']} – ${p['end_time'] || ''}`);
      add('Comentarios', p['notes']);
    }
    return out;
  }
}
