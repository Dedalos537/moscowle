import { Component, OnInit, OnDestroy, ChangeDetectionStrategy, computed, inject, signal, TemplateRef, ViewChild } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { Subscription } from 'rxjs';
import { Incident, IncidentDetail, IncidentService } from '../../../core/services/incident.service';
import { HeaderService } from '../../../core/services/header.service';
import { AuthService } from '../../../core/services/auth.service';
import { ToastService } from '../../../core/services/toast.service';
import { Modal } from '../modal/modal';
import { Button } from '../button/button';

type Filter = 'open' | 'done' | 'all';

const ESTADO: Record<string, string> = {
  NUEVO: 'Recibida',
  EN_CURSO: 'En atención',
  PENDIENTE_PROVEEDOR: 'En espera de un tercero',
  RESUELTO: 'Resuelta',
  CERRADO: 'Cerrada',
};
const CATEGORIA: Record<string, string> = {
  SOFTWARE: 'Plataforma o app',
  HARDWARE: 'Equipos del centro',
  RED: 'Conexión a internet',
  ACCESOS: 'Acceso a la cuenta',
  OPERACIONES: 'Atención y operación del centro',
};
const NEXT: Record<string, { estado: string; label: string }[]> = {
  NUEVO: [{ estado: 'EN_CURSO', label: 'Empezar a atender' }, { estado: 'RESUELTO', label: 'Marcar como resuelta' }],
  EN_CURSO: [{ estado: 'PENDIENTE_PROVEEDOR', label: 'En espera de un tercero' }, { estado: 'RESUELTO', label: 'Marcar como resuelta' }],
  PENDIENTE_PROVEEDOR: [{ estado: 'EN_CURSO', label: 'Retomar' }, { estado: 'RESUELTO', label: 'Marcar como resuelta' }],
  RESUELTO: [{ estado: 'CERRADO', label: 'Cerrar' }],
};

interface TimelineEntry {
  key: string;
  kind: 'status' | 'comment';
  at: string | null;
  who: string | null;
  text: string;
  internal?: boolean;
  mine?: boolean;
}

/**
 * Incidencias de terapeutas y pacientes: reportar, ver el estado, quién la atiende, el historial y responder.
 * Antes cada tarjeta enlazaba a /admin/incidents/:id, bloqueada para estos roles: se podía reportar pero nunca
 * ver la respuesta. Los avisos llegan con ?id=N y abren la incidencia directamente.
 */
@Component({
  selector: 'app-incidents-list',
  standalone: true,
  imports: [FormsModule, FontAwesomeModule, Modal, Button],
  templateUrl: './incidents-list.html',
  styleUrl: './incidents-list.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class IncidentsList implements OnInit, OnDestroy {
  @ViewChild('headerActions', { static: true }) headerActions!: TemplateRef<unknown>;

  private incidentService = inject(IncidentService);
  private headerService = inject(HeaderService);
  private toast = inject(ToastService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private subs = new Subscription();
  private user = toSignal(inject(AuthService).currentUser$, { initialValue: null });

  readonly categories = Object.entries(CATEGORIA).map(([value, label]) => ({ value, label }));
  readonly items = signal<Incident[]>([]);
  readonly loading = signal(true);
  readonly loadError = signal<string | null>(null);
  readonly filter = signal<Filter>('open');
  readonly selectedId = signal<number | null>(null);
  readonly detail = signal<IncidentDetail | null>(null);
  readonly detailLoading = signal(false);
  readonly reply = signal('');
  readonly sending = signal(false);
  readonly changing = signal(false);

  readonly creating = signal(false);
  readonly showCreate = signal(false);
  readonly createError = signal<string | null>(null);
  form = { titulo: '', descripcion: '', categoria: 'SOFTWARE', impacto: 1, urgencia: 2 };

  readonly isPatient = computed(() => this.user()?.role === 'jugador');
  readonly myId = computed<number | null>(() => (this.user()?.id != null ? Number(this.user().id) : null));

  readonly counts = computed(() => {
    const list = this.items();
    const done = list.filter((i) => i.estado === 'RESUELTO' || i.estado === 'CERRADO').length;
    return { open: list.length - done, done, all: list.length };
  });

  readonly visible = computed(() => {
    const f = this.filter();
    return this.items().filter((i) => {
      const done = i.estado === 'RESUELTO' || i.estado === 'CERRADO';
      return f === 'all' || (f === 'done' ? done : !done);
    });
  });

  /** Solo el responsable asignado cambia el estado desde aquí (coordinación lo hace desde su panel). */
  readonly actions = computed(() => {
    const d = this.detail();
    if (!d || d.responsable_id == null || d.responsable_id !== this.myId()) return [];
    return NEXT[d.estado] ?? [];
  });

  readonly timeline = computed<TimelineEntry[]>(() => {
    const d = this.detail();
    if (!d) return [];
    const me = this.user()?.username;
    const entries: TimelineEntry[] = [
      ...(d.historial ?? []).map((h) => ({
        key: `h${h.id}`,
        kind: 'status' as const,
        at: h.changed_at,
        who: h.changed_by,
        text: h.estado_anterior
          ? `${ESTADO[h.estado_anterior] ?? h.estado_anterior} → ${ESTADO[h.estado_nuevo] ?? h.estado_nuevo}${h.comentario ? ' · ' + h.comentario : ''}`
          : 'Reportada',
      })),
      ...(d.comentarios ?? []).map((c) => ({
        key: `c${c.id}`,
        kind: 'comment' as const,
        at: c.created_at,
        who: c.autor,
        text: c.contenido,
        internal: c.es_interno,
        mine: !!me && c.autor === me,
      })),
    ];
    return entries.sort((a, b) => (a.at ?? '').localeCompare(b.at ?? ''));
  });

  ngOnInit() {
    this.headerService.setConfig({
      title: 'Incidencias',
      subtitle: 'Reporta un problema y sigue su atención',
      icon: ['fas', 'triangle-exclamation'],
      actionTemplate: this.headerActions,
    });
    this.load();
    this.subs.add(
      this.route.queryParamMap.subscribe((q) => {
        const id = Number(q.get('id'));
        if (id && id !== this.selectedId()) this.open(id, false);
      }),
    );
  }

  ngOnDestroy() {
    this.headerService.reset();
    this.subs.unsubscribe();
  }

  load() {
    this.loading.set(true);
    this.loadError.set(null);
    this.subs.add(
      this.incidentService.getMyIncidents(1, 100).subscribe({
        next: (res) => {
          this.items.set(res.incidentes);
          this.loading.set(false);
        },
        error: () => {
          this.loading.set(false);
          this.loadError.set('No se pudieron cargar tus incidencias.');
        },
      }),
    );
  }

  open(id: number, updateUrl = true) {
    this.selectedId.set(id);
    this.reply.set('');
    this.detailLoading.set(true);
    if (updateUrl) this.router.navigate([], { queryParams: { id }, queryParamsHandling: 'merge', replaceUrl: true });
    this.subs.add(
      this.incidentService.getIncident(id).subscribe({
        next: (d) => {
          this.detail.set(d);
          this.detailLoading.set(false);
          const done = d.estado === 'RESUELTO' || d.estado === 'CERRADO';
          if (done && this.filter() === 'open') this.filter.set('all');
        },
        error: (e) => {
          this.detailLoading.set(false);
          this.detail.set(null);
          this.selectedId.set(null);
          this.toast.show(e?.status === 403 ? 'No tienes acceso a esa incidencia.' : 'No se pudo abrir la incidencia.', 'error');
        },
      }),
    );
  }

  close() {
    this.selectedId.set(null);
    this.detail.set(null);
    this.router.navigate([], { queryParams: { id: null }, queryParamsHandling: 'merge', replaceUrl: true });
  }

  sendReply() {
    const d = this.detail();
    const text = this.reply().trim();
    if (!d || text.length < 2) return;
    this.sending.set(true);
    this.subs.add(
      this.incidentService.addComment(d.id, text).subscribe({
        next: () => {
          this.sending.set(false);
          this.reply.set('');
          this.open(d.id, false);
        },
        error: (e) => {
          this.sending.set(false);
          this.toast.show(e?.error?.error || 'No se pudo enviar la respuesta.', 'error');
        },
      }),
    );
  }

  changeStatus(estado: string) {
    const d = this.detail();
    if (!d) return;
    this.changing.set(true);
    this.subs.add(
      this.incidentService.updateStatus(d.id, estado).subscribe({
        next: (updated) => {
          this.changing.set(false);
          this.detail.set(updated);
          this.items.update((list) => list.map((i) => (i.id === updated.id ? { ...i, estado: updated.estado } : i)));
          this.toast.show(`Incidencia ${ESTADO[estado]?.toLowerCase() ?? 'actualizada'}`, 'success');
        },
        error: (e) => {
          this.changing.set(false);
          this.toast.show(e?.error?.error || 'No se pudo cambiar el estado.', 'error');
        },
      }),
    );
  }

  openCreate() {
    this.form = { titulo: '', descripcion: '', categoria: this.isPatient() ? 'OPERACIONES' : 'SOFTWARE', impacto: 1, urgencia: 2 };
    this.createError.set(null);
    this.showCreate.set(true);
  }

  create() {
    const f = this.form;
    if (f.titulo.trim().length < 5) {
      this.createError.set('Escribe un título de al menos 5 letras.');
      return;
    }
    if (f.descripcion.trim().length < 10) {
      this.createError.set('Cuenta un poco más qué pasó (al menos 10 letras).');
      return;
    }
    this.creating.set(true);
    this.createError.set(null);
    this.subs.add(
      this.incidentService
        .createIncident({ titulo: f.titulo.trim(), descripcion: f.descripcion.trim(), categoria: f.categoria, impacto: f.impacto, urgencia: f.urgencia })
        .subscribe({
          next: (d) => {
            this.creating.set(false);
            this.showCreate.set(false);
            this.toast.show('Incidencia enviada. Coordinación ya fue avisada.', 'success');
            this.items.update((list) => [d, ...list]);
            this.filter.set('open');
            this.open(d.id);
          },
          error: (e) => {
            this.creating.set(false);
            const details = e?.error?.details;
            this.createError.set(
              e?.status === 401
                ? 'Tu sesión expiró. Recarga la página e inicia sesión.'
                : details
                  ? Object.values(details).flat().join(' ')
                  : e?.error?.error || 'No se pudo enviar la incidencia.',
            );
          },
        }),
    );
  }

  estado(e: string) {
    return ESTADO[e] ?? e;
  }

  categoria(c: string) {
    return CATEGORIA[c] ?? c;
  }

  prioridad(p: number) {
    return p >= 6 ? 'Alta' : p >= 3 ? 'Media' : 'Baja';
  }

  when(iso: string | null) {
    if (!iso) return '';
    const d = new Date(iso.endsWith('Z') || iso.includes('+') ? iso : iso + 'Z');
    const mins = Math.round((Date.now() - d.getTime()) / 60000);
    if (mins < 1) return 'ahora';
    if (mins < 60) return `hace ${mins} min`;
    const h = Math.floor(mins / 60);
    if (h < 24) return `hace ${h} h`;
    const days = Math.floor(h / 24);
    if (days < 7) return `hace ${days} ${days === 1 ? 'día' : 'días'}`;
    return d.toLocaleDateString('es-PE', { day: 'numeric', month: 'short' });
  }

  sla(d: Incident) {
    if (d.estado === 'RESUELTO' || d.estado === 'CERRADO') return null;
    if (d.esta_vencido) return { text: 'Plazo de atención vencido', late: true };
    if (d.horas_restantes_sla == null) return null;
    const h = d.horas_restantes_sla;
    return { text: h < 1 ? 'Menos de 1 h para atenderla' : `Plazo de atención: ${Math.round(h)} h`, late: false };
  }
}
