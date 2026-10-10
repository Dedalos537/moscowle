import { ChangeDetectionStrategy, Component, OnDestroy, OnInit, TemplateRef, ViewChild, computed, inject, signal } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { IconProp } from '@fortawesome/fontawesome-svg-core';
import { Subscription, interval } from 'rxjs';
import { ActionRequest, ActionRequestService, REQUEST_KIND_LABEL, RequestKind } from '../../../../core/services/action-request.service';
import { HeaderService } from '../../../../core/services/header.service';
import { RequestFormModal } from '../../../../shared/components/request-form-modal/request-form-modal';

const STATUS: Record<string, string> = { pending: 'En revisión', approved: 'Aprobada', rejected: 'Rechazada' };

/** Solicitudes del terapeuta a la coordinación: pedir sesiones, altas de pacientes y grupos, y ver su estado. */
@Component({
  selector: 'app-therapist-requests',
  standalone: true,
  imports: [FontAwesomeModule, RequestFormModal],
  templateUrl: './requests.html',
  styleUrl: './requests.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class TherapistRequests implements OnInit, OnDestroy {
  @ViewChild('headerActions', { static: true }) headerActions!: TemplateRef<unknown>;
  private service = inject(ActionRequestService);
  private header = inject(HeaderService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private subs = new Subscription();

  readonly labels = REQUEST_KIND_LABEL;
  readonly items = signal<ActionRequest[]>([]);
  readonly loading = signal(true);
  readonly error = signal<string | null>(null);
  readonly formKind = signal<RequestKind | null>(null);
  readonly highlight = signal<number | null>(null);
  readonly pendingCount = computed(() => this.items().filter((i) => i.status === 'pending').length);

  readonly kinds: { key: RequestKind; icon: IconProp; hint: string }[] = [
    { key: 'sessions', icon: ['fas', 'calendar-plus'], hint: 'Fechas, horario y comentarios para uno de tus pacientes o grupos.' },
    { key: 'patient', icon: ['fas', 'user-plus'], hint: 'Datos del paciente y del apoderado; queda asignado a ti.' },
    { key: 'group', icon: ['fas', 'people-group'], hint: 'Reúne a varios de tus pacientes con un horario común.' },
  ];

  ngOnInit() {
    this.header.setConfig({ title: 'Solicitudes', subtitle: 'Pide a coordinación sesiones, altas y grupos', icon: ['fas', 'paper-plane'], actionTemplate: this.headerActions });
    const q = this.route.snapshot.queryParamMap;
    const nk = q.get('new') as RequestKind | null;
    if (nk && nk in REQUEST_KIND_LABEL) this.formKind.set(nk);
    const id = Number(q.get('id'));
    if (id) this.highlight.set(id);
    this.load();
    // Mientras haya algo en revisión, el estado se actualiza solo (sin recargar la página).
    this.subs.add(interval(30_000).subscribe(() => this.pendingCount() && this.load(true)));
  }

  ngOnDestroy() {
    this.header.reset();
    this.subs.unsubscribe();
  }

  load(silent = false) {
    if (!silent) this.loading.set(true);
    this.subs.add(
      this.service.mine().subscribe({
        next: (r) => {
          this.items.set(r.requests);
          this.loading.set(false);
          this.error.set(null);
        },
        error: () => {
          this.loading.set(false);
          if (!silent) this.error.set('No se pudieron cargar tus solicitudes.');
        },
      }),
    );
  }

  open(kind: RequestKind) {
    this.formKind.set(kind);
  }

  closeForm() {
    this.formKind.set(null);
    if (this.route.snapshot.queryParamMap.get('new')) this.router.navigate([], { queryParams: { new: null }, queryParamsHandling: 'merge', replaceUrl: true });
  }

  onSent(r: ActionRequest) {
    this.items.update((list) => [r, ...list]);
    this.highlight.set(r.id);
  }

  status(s: string) {
    return STATUS[s] ?? s;
  }

  when(iso: string | null) {
    if (!iso) return '';
    const d = new Date(iso);
    const mins = Math.round((Date.now() - d.getTime()) / 60000);
    if (mins < 1) return 'ahora';
    if (mins < 60) return `hace ${mins} min`;
    const h = Math.floor(mins / 60);
    if (h < 24) return `hace ${h} h`;
    return d.toLocaleDateString('es-PE', { day: 'numeric', month: 'short' });
  }

  resultText(r: ActionRequest): string {
    const res = r.result as Record<string, unknown> | null;
    if (!res) return '';
    if (r.kind === 'sessions') return String(res['message'] || `${res['created']} sesiones creadas`);
    if (r.kind === 'patient') return `Paciente creado${res['has_email'] ? ' y avisado por correo' : ''}.`;
    return `Grupo «${res['name']}» creado.`;
  }

  goToResult(r: ActionRequest) {
    const res = (r.result || {}) as Record<string, unknown>;
    if (r.kind === 'sessions') this.router.navigate(['/therapist/sessions']);
    else if (r.kind === 'patient' && res['user_id']) this.router.navigate(['/therapist/patients', res['user_id']]);
    else this.router.navigate(['/therapist/patients']);
  }
}
