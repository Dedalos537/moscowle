import { ChangeDetectionStrategy, ChangeDetectorRef, Component, OnDestroy, OnInit, computed, inject, signal } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import type { IconProp } from '@fortawesome/fontawesome-svg-core';
import { Subscription, interval } from 'rxjs';
import {
  LandingAdminService,
  type LandingContent,
  type LandingLead,
  type LandingStats,
  type LandingVersion,
  type LeadStatus,
} from '../../../../core/services/landing-admin.service';
import { AuthService } from '../../../../core/services/auth.service';
import { ToastService } from '../../../../core/services/toast.service';

/** Dirección de la landing publicada. Mientras se revisa la versión nueva vive en /nuevo/. */
export const LANDING_URL = 'https://centrojuanpabloii.com/nuevo/';

interface FieldDef {
  key: string;
  label: string;
  max: number;
  kind?: 'text' | 'textarea' | 'url' | 'tel';
  required?: boolean;
  hint?: string;
  placeholder?: string;
}

interface ListDef {
  path: string[];
  label: string;
  itemLabel: string;
  summary: string;
  fields: FieldDef[];
  min: number;
  max: number;
}

interface GroupDef {
  id: string;
  label: string;
  icon: IconProp;
  intro?: string;
  objects?: { path: string[]; fields: FieldDef[] }[];
  lists?: ListDef[];
}

const T = (key: string, label: string, max: number, extra: Partial<FieldDef> = {}): FieldDef => ({ key, label, max, required: true, ...extra });
const O = (key: string, label: string, max: number, extra: Partial<FieldDef> = {}): FieldDef => ({ key, label, max, required: false, ...extra });

/** Lo que se puede editar de la landing. Los límites coinciden con los del backend (landing_content.SCHEMA). */
const GROUPS: GroupDef[] = [
  {
    id: 'contact',
    label: 'Contacto y WhatsApp',
    icon: ['fab', 'whatsapp'],
    intro: 'El número de WhatsApp y el teléfono que usan los botones para agendar la evaluación.',
    objects: [
      {
        path: ['contact'],
        fields: [
          T('whatsapp', 'Número de WhatsApp', 15, { kind: 'tel', hint: 'Con código de país y solo dígitos, ej. 51987277835.', placeholder: '51987277835' }),
          T('phone', 'Teléfono para llamadas', 25, { kind: 'tel', placeholder: '+51 987 277 835' }),
          O('phone_hours', 'Horario de llamadas', 120),
          O('email', 'Correo', 120),
          T('address', 'Dirección', 120),
          T('city', 'Ciudad', 80),
          O('maps_url', 'Enlace de Google Maps', 400, { kind: 'url', hint: 'Debe empezar por https://' }),
          O('hours_note', 'Nota de horario', 80, { placeholder: 'Atención con cita previa' }),
        ],
      },
    ],
    lists: [
      {
        path: ['contact', 'hours'],
        label: 'Horario de atención',
        itemLabel: 'Horario',
        summary: 'days',
        min: 0,
        max: 7,
        fields: [T('days', 'Días', 40), T('time', 'Horas', 60)],
      },
    ],
  },
  {
    id: 'hero',
    label: 'Portada',
    icon: ['fas', 'home'],
    intro: 'Lo primero que ve una familia al entrar.',
    objects: [
      {
        path: ['hero'],
        fields: [
          T('title', 'Titular', 90),
          O('highlight', 'Segunda línea (en verde lima)', 90),
          T('subtitle', 'Texto de presentación', 320, { kind: 'textarea' }),
          T('cta_primary', 'Botón principal', 32),
          O('cta_secondary', 'Enlace a las terapias', 32),
        ],
      },
    ],
  },
  {
    id: 'evaluation',
    label: 'Evaluación',
    icon: ['fas', 'map-signs'],
    intro: 'El recorrido animado: cada paso es una estación del camino 3D.',
    objects: [
      {
        path: ['evaluation'],
        fields: [
          T('title', 'Título', 90),
          T('subtitle', 'Texto', 320, { kind: 'textarea' }),
          T('whatsapp_message', 'Mensaje inicial de WhatsApp', 300, {
            kind: 'textarea',
            hint: 'Primera línea del mensaje que se abre en WhatsApp. Debajo se agregan solos el nombre, la edad, el área y el horario que llenó la familia.',
          }),
        ],
      },
    ],
    lists: [
      {
        path: ['evaluation', 'steps'],
        label: 'Pasos',
        itemLabel: 'Paso',
        summary: 'title',
        min: 2,
        max: 6,
        fields: [T('title', 'Título', 60), T('body', 'Descripción', 220, { kind: 'textarea' })],
      },
    ],
  },
  {
    id: 'services',
    label: 'Terapias',
    icon: ['fas', 'layer-group'],
    intro: 'Se agrupan por categoría en el orden en que aparecen. La foto es opcional.',
    objects: [{ path: ['services_intro'], fields: [T('title', 'Título de la sección', 90), O('subtitle', 'Texto', 260, { kind: 'textarea' })] }],
    lists: [
      {
        path: ['services'],
        label: 'Terapias y servicios',
        itemLabel: 'Terapia',
        summary: 'title',
        min: 1,
        max: 40,
        fields: [
          T('title', 'Nombre', 60),
          T('category', 'Categoría', 40, { hint: 'Ej. Terapias, Terapias integrales, Apoyo virtual, Material didáctico.' }),
          T('body', 'Descripción', 400, { kind: 'textarea' }),
          O('image', 'Foto (enlace)', 400, { kind: 'url', hint: 'Opcional. Enlace https:// a una foto real del centro.' }),
        ],
      },
    ],
  },
  {
    id: 'stats',
    label: 'Cifras',
    icon: ['fas', 'chart-simple'],
    intro: 'La torre de bloques: hasta cuatro datos, el primero va abajo.',
    lists: [
      {
        path: ['stats'],
        label: 'Cifras',
        itemLabel: 'Cifra',
        summary: 'label',
        min: 0,
        max: 4,
        fields: [T('value', 'Valor', 10, { placeholder: '20+' }), T('label', 'Descripción', 40)],
      },
    ],
  },
  {
    id: 'about',
    label: 'Nosotros',
    icon: ['fas', 'heart'],
    objects: [{ path: ['about'], fields: [T('title', 'Título', 90), T('body', 'Texto', 700, { kind: 'textarea' })] }],
    lists: [
      {
        path: ['about', 'values'],
        label: 'Valores',
        itemLabel: 'Valor',
        summary: 'title',
        min: 0,
        max: 8,
        fields: [T('title', 'Valor', 40), T('body', 'Descripción', 200, { kind: 'textarea' })],
      },
    ],
  },
  {
    id: 'testimonials',
    label: 'Testimonios',
    icon: ['fas', 'quote-left'],
    objects: [{ path: ['testimonials_intro'], fields: [T('title', 'Título', 90), O('subtitle', 'Texto', 260)] }],
    lists: [
      {
        path: ['testimonials'],
        label: 'Testimonios',
        itemLabel: 'Testimonio',
        summary: 'author',
        min: 0,
        max: 12,
        fields: [T('quote', 'Testimonio', 500, { kind: 'textarea' }), T('author', 'Nombre', 60), O('relation', 'Relación', 60, { placeholder: 'Madre de familia' })],
      },
    ],
  },
  {
    id: 'faq',
    label: 'Preguntas',
    icon: ['fas', 'circle-question'],
    lists: [
      {
        path: ['faq'],
        label: 'Preguntas frecuentes',
        itemLabel: 'Pregunta',
        summary: 'q',
        min: 0,
        max: 12,
        fields: [T('q', 'Pregunta', 160), T('a', 'Respuesta', 600, { kind: 'textarea' })],
      },
    ],
  },
  {
    id: 'seo',
    label: 'Buscadores',
    icon: ['fas', 'magnifying-glass'],
    intro: 'Cómo aparece el centro en Google y al compartir el enlace.',
    objects: [
      { path: ['seo'], fields: [T('title', 'Título en Google', 70), T('description', 'Descripción en Google', 170, { kind: 'textarea' })] },
      { path: ['brand'], fields: [T('name', 'Nombre del centro', 80), T('short', 'Nombre corto (barra superior)', 40)] },
    ],
  },
];

type View = 'leads' | 'content' | 'history';
type LeadFilter = 'open' | 'scheduled' | 'discarded' | 'all';

export const LEAD_STATUS_LABEL: Record<LeadStatus, string> = {
  new: 'Por atender',
  contacted: 'Contactada',
  scheduled: 'Evaluación agendada',
  discarded: 'Descartada',
};

const CHANNEL: Record<string, { label: string; icon: IconProp }> = {
  form: { label: 'Pidió que la llamen', icon: ['fas', 'phone'] },
  whatsapp: { label: 'Abrió WhatsApp', icon: ['fab', 'whatsapp'] },
  call: { label: 'Llamó', icon: ['fas', 'phone'] },
};

const TIME_LABEL: Record<string, string> = { manana: 'Mañana', tarde: 'Tarde', cualquiera: 'Cualquier horario' };

/** Sitio web: solicitudes de evaluación que llegan de la landing y edición de su contenido. */
@Component({
  selector: 'app-website',
  standalone: true,
  imports: [FormsModule, FontAwesomeModule],
  templateUrl: './website.html',
  styleUrl: './website.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Website implements OnInit, OnDestroy {
  private api = inject(LandingAdminService);
  private toast = inject(ToastService);
  private route = inject(ActivatedRoute);
  private auth = inject(AuthService);
  private cdr = inject(ChangeDetectorRef);
  private subs = new Subscription();

  readonly groups = GROUPS;
  readonly landingUrl = LANDING_URL;
  readonly statusLabel = LEAD_STATUS_LABEL;
  readonly statuses = Object.keys(LEAD_STATUS_LABEL) as LeadStatus[];
  readonly channel = CHANNEL;
  readonly timeLabel = TIME_LABEL;
  /** El supervisor ve todo pero no publica ni cambia estados (el backend también lo impide). */
  canWrite = false;

  readonly view = signal<View>('leads');

  // ── Solicitudes ──
  readonly filter = signal<LeadFilter>('open');
  readonly leads = signal<LandingLead[]>([]);
  readonly total = signal(0);
  readonly loadingLeads = signal(true);
  readonly openLead = signal<number | null>(null);
  readonly stats = signal<LandingStats | null>(null);
  search = '';
  notes: Record<number, string> = {};

  readonly statsLine = computed(() => {
    const s = this.stats()?.last_30_days;
    if (!s) return '';
    const parts = [
      `${s.whatsapp} ${s.whatsapp === 1 ? 'apertura' : 'aperturas'} de WhatsApp`,
      `${s.call} ${s.call === 1 ? 'llamada' : 'llamadas'}`,
      `${s.form} ${s.form === 1 ? 'pedido' : 'pedidos'} de llamada`,
    ];
    return `Últimos 30 días: ${parts.join(' · ')}.`;
  });

  // ── Contenido ──
  readonly group = signal(GROUPS[0].id);
  readonly loadingContent = signal(true);
  readonly publishing = signal(false);
  readonly publishError = signal<string | null>(null);
  readonly versions = signal<LandingVersion[]>([]);
  draft: LandingContent = {};
  private published = '';
  private defaults: LandingContent = {};
  version = 0;
  note = '';
  openItems = new Set<string>();

  readonly current = computed(() => GROUPS.find((g) => g.id === this.group()) ?? GROUPS[0]);

  ngOnInit() {
    this.subs.add(this.auth.currentUser$.subscribe((u) => (this.canWrite = u?.role === 'admin')));
    const lead = Number(this.route.snapshot.queryParamMap.get('lead'));
    if (lead) {
      this.openLead.set(lead);
      this.filter.set('all');
    }
    this.loadLeads();
    this.loadContent();
    this.subs.add(interval(60_000).subscribe(() => this.loadLeads(true)));
  }

  ngOnDestroy() {
    this.subs.unsubscribe();
  }

  // ───────────────────────────── solicitudes ─────────────────────────────

  setFilter(f: LeadFilter) {
    this.filter.set(f);
    this.loadLeads();
  }

  loadLeads(quiet = false) {
    if (!quiet) this.loadingLeads.set(true);
    const f = this.filter();
    this.api.leads({ status: f === 'all' ? undefined : f, q: this.search.trim() || undefined }).subscribe({
      next: (r) => {
        this.leads.set(r.leads);
        this.total.set(r.total);
        this.loadingLeads.set(false);
      },
      error: () => {
        this.loadingLeads.set(false);
        if (!quiet) this.toast.show('No se pudieron cargar las solicitudes', 'error');
      },
    });
    this.api.stats().subscribe({ next: (s) => this.stats.set(s), error: () => {} });
  }

  toggleLead(l: LandingLead) {
    this.openLead.set(this.openLead() === l.id ? null : l.id);
    if (this.notes[l.id] === undefined) this.notes[l.id] = l.staff_note ?? '';
  }

  setStatus(l: LandingLead, status: LeadStatus) {
    this.api.updateLead(l.id, { status }).subscribe({
      next: (r) => {
        this.replaceLead(r.lead);
        this.toast.show(`Marcada como «${LEAD_STATUS_LABEL[status].toLowerCase()}»`, 'success');
        this.api.stats().subscribe({ next: (s) => this.stats.set(s), error: () => {} });
      },
      error: () => this.toast.show('No se pudo cambiar el estado', 'error'),
    });
  }

  saveNote(l: LandingLead) {
    this.api.updateLead(l.id, { staff_note: this.notes[l.id] ?? '' }).subscribe({
      next: (r) => {
        this.replaceLead(r.lead);
        this.toast.show('Nota guardada', 'success');
      },
      error: () => this.toast.show('No se pudo guardar la nota', 'error'),
    });
  }

  private replaceLead(lead: LandingLead) {
    // En «Por atender», una solicitud agendada o descartada sale de la lista.
    const keep = this.filter() === 'all' || (this.filter() === 'open' ? ['new', 'contacted'].includes(lead.status) : lead.status === this.filter());
    this.leads.update((list) => (keep ? list.map((x) => (x.id === lead.id ? lead : x)) : list.filter((x) => x.id !== lead.id)));
    if (!keep) this.total.update((t) => Math.max(0, t - 1));
  }

  /** Enlace para escribirle a la familia: los celulares peruanos de 9 dígitos llevan el 51 delante. */
  waTo(phone: string | null): string | null {
    const digits = (phone ?? '').replace(/\D/g, '');
    if (digits.length < 8) return null;
    const full = digits.length === 9 && digits.startsWith('9') ? `51${digits}` : digits;
    return `https://wa.me/${full}`;
  }

  telTo(phone: string | null): string | null {
    const clean = (phone ?? '').replace(/[^\d+]/g, '');
    return clean.length >= 6 ? `tel:${clean}` : null;
  }

  when(iso: string | null): string {
    if (!iso) return '';
    const d = new Date(iso.endsWith('Z') || iso.includes('+') ? iso : `${iso}Z`);
    const mins = Math.round((Date.now() - d.getTime()) / 60000);
    if (mins < 1) return 'ahora';
    if (mins < 60) return `hace ${mins} min`;
    const hours = Math.round(mins / 60);
    if (hours < 24) return `hace ${hours} h`;
    return d.toLocaleDateString('es-PE', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
  }

  // ───────────────────────────── contenido ─────────────────────────────

  loadContent() {
    this.loadingContent.set(true);
    this.api.content().subscribe({
      next: (r) => {
        this.applyContent(r.content, r.version);
        this.defaults = r.default ?? {};
        this.versions.set(r.versions);
        this.loadingContent.set(false);
      },
      error: () => {
        this.loadingContent.set(false);
        this.toast.show('No se pudo cargar el contenido del sitio', 'error');
      },
    });
  }

  private applyContent(content: LandingContent, version: number) {
    this.draft = structuredClone(content);
    this.published = JSON.stringify(content);
    this.version = version;
    this.publishError.set(null);
    this.cdr.markForCheck();
  }

  get dirty(): boolean {
    return !!this.published && JSON.stringify(this.draft) !== this.published;
  }

  at(path: string[]): any {
    return path.reduce((o, k) => (o == null ? o : o[k]), this.draft);
  }

  items(list: ListDef): Record<string, string>[] {
    return (this.at(list.path) as Record<string, string>[]) ?? [];
  }

  len(value: unknown): number {
    return String(value ?? '').trim().length;
  }

  /** Problemas que el backend rechazaría: obligatorio vacío o texto demasiado largo. */
  readonly issues = (): string[] => {
    const out: string[] = [];
    for (const g of GROUPS) {
      for (const o of g.objects ?? []) {
        const obj = this.at(o.path) ?? {};
        for (const f of o.fields) this.check(out, g.label, f, obj[f.key]);
      }
      for (const l of g.lists ?? []) {
        const rows = this.items(l);
        if (rows.length < l.min) out.push(`${g.label}: al menos ${l.min} ${l.itemLabel.toLowerCase()}s`);
        rows.forEach((row, i) => l.fields.forEach((f) => this.check(out, `${g.label} › ${l.itemLabel} ${i + 1}`, f, row[f.key])));
      }
    }
    return out;
  };

  private check(out: string[], where: string, f: FieldDef, value: unknown) {
    const n = this.len(value);
    if (f.required && !n) out.push(`${where}: «${f.label}» es obligatorio`);
    else if (n > f.max) out.push(`${where}: «${f.label}» tiene ${n} de ${f.max} caracteres`);
  }

  groupIssues(g: GroupDef): number {
    return this.issues().filter((i) => i.startsWith(g.label)).length;
  }

  itemKey(list: ListDef, i: number) {
    return `${list.path.join('.')}#${i}`;
  }

  toggleItem(list: ListDef, i: number) {
    const k = this.itemKey(list, i);
    if (this.openItems.has(k)) this.openItems.delete(k);
    else this.openItems.add(k);
  }

  addItem(list: ListDef) {
    const rows = this.items(list);
    if (rows.length >= list.max) return;
    rows.push(Object.fromEntries(list.fields.map((f) => [f.key, ''])));
    this.openItems.add(this.itemKey(list, rows.length - 1));
  }

  removeItem(list: ListDef, i: number) {
    const rows = this.items(list);
    if (rows.length <= list.min) return;
    const label = rows[i]?.[list.summary] || `${list.itemLabel} ${i + 1}`;
    if (!confirm(`¿Quitar «${label}»? El cambio se aplica al publicar.`)) return;
    rows.splice(i, 1);
    this.openItems.clear();
  }

  moveItem(list: ListDef, i: number, delta: number) {
    const rows = this.items(list);
    const j = i + delta;
    if (j < 0 || j >= rows.length) return;
    [rows[i], rows[j]] = [rows[j], rows[i]];
    const a = this.itemKey(list, i);
    const b = this.itemKey(list, j);
    const aOpen = this.openItems.has(a);
    const bOpen = this.openItems.has(b);
    this.openItems.delete(a);
    this.openItems.delete(b);
    if (aOpen) this.openItems.add(b);
    if (bOpen) this.openItems.add(a);
  }

  discard() {
    if (!confirm('¿Descartar los cambios sin publicar?')) return;
    this.applyContent(JSON.parse(this.published), this.version);
  }

  resetGroupToDefault(g: GroupDef) {
    if (!confirm(`¿Volver «${g.label}» al texto original? El cambio se aplica al publicar.`)) return;
    for (const o of g.objects ?? []) this.copyDefault(o.path);
    for (const l of g.lists ?? []) this.copyDefault(l.path);
    this.openItems.clear();
  }

  private copyDefault(path: string[]) {
    const value = path.reduce((o, k) => (o == null ? o : o[k]), this.defaults as any);
    if (value === undefined) return;
    const parent = path.slice(0, -1).reduce((o, k) => (o[k] ??= {}), this.draft);
    parent[path[path.length - 1]] = structuredClone(value);
  }

  publish() {
    if (this.issues().length || this.publishing()) return;
    this.publishing.set(true);
    this.publishError.set(null);
    this.api.publish(this.draft, this.version, this.note.trim()).subscribe({
      next: (r) => {
        this.applyContent(r.content, r.version);
        this.versions.set(r.versions);
        this.note = '';
        this.publishing.set(false);
        this.toast.show('Publicado. La landing se actualiza en un minuto.', 'success');
      },
      error: (e: HttpErrorResponse) => {
        this.publishing.set(false);
        this.publishError.set(e.error?.error || 'No se pudo publicar. Revisa tu conexión e inténtalo de nuevo.');
      },
    });
  }

  restore(v: LandingVersion) {
    if (this.dirty && !confirm('Tienes cambios sin publicar que se perderán. ¿Continuar?')) return;
    if (!confirm(`¿Volver a publicar la versión del ${this.when(v.created_at)}?`)) return;
    this.api.restore(v.id).subscribe({
      next: (r) => {
        this.applyContent(r.content, r.version);
        this.versions.set(r.versions);
        this.toast.show('Versión restaurada y publicada', 'success');
      },
      error: (e: HttpErrorResponse) => this.toast.show(e.error?.error || 'No se pudo restaurar', 'error'),
    });
  }
}
