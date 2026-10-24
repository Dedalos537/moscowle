import { ChangeDetectionStrategy, Component, ElementRef, HostListener, OnDestroy, OnInit, TemplateRef, ViewChild, computed, effect, inject, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { Subscription } from 'rxjs';
import { ActionBlock, ActionField, AssistantMessage, AssistantModels, AssistantSchedule, AssistantService, AssistantThread, AssistantUpload, FileBlock } from '../../../../core/services/assistant';
import { HeaderService } from '../../../../core/services/header.service';
import { AssistantVisibilityService } from '../../../../core/services/assistant-visibility';
import { ToastService } from '../../../../core/services/toast.service';
import { ConfirmService } from '../../../../core/services/confirm.service';
import { Modal } from '../../../../shared/components/modal/modal';
import { Select, SelectOption } from '../../../../shared/components/select/select';
import { MessageBlocks } from './components/message-blocks/message-blocks';

const LAST_KEY = 'moscowle_assistant_last';
const MODEL_KEY = 'moscowle_assistant_model';
const ACCEPT = '.jpg,.jpeg,.png,.webp,.pdf,.docx,.xlsx,.txt,.csv,.md';
const SUBTITLE = 'Pregunta por el centro: cifras, comparativos y tendencias';

/** Comandos rápidos del cuadro de texto («/» y elegir). */
const COMMANDS = [
  { cmd: '/resumen', text: '¿Cómo vamos este mes?' },
  { cmd: '/sedes', text: 'Compara las sedes este trimestre' },
  { cmd: '/equipo', text: '¿Cómo están los terapeutas este mes?' },
  { cmd: '/deudores', text: '¿Quiénes deben cuotas vencidas?' },
  { cmd: '/riesgo', text: 'Pacientes en riesgo de dejar el centro' },
  { cmd: '/tendencia', text: 'Tendencia de ingresos y sesiones' },
  { cmd: '/pagos', text: 'Pagos por método este mes' },
  { cmd: '/altas', text: 'Altas y bajas de pacientes' },
];

/**
 * Asistente del centro (PRP 015): pantalla de inicio del admin y del supervisor (este, limitado a su sede).
 * Conversaciones guardadas y compartibles; cada respuesta trae texto, indicadores, gráficas y tablas con los
 * mismos números del Dashboard, y se puede programar para recibirla por correo o Telegram.
 */
@Component({
  selector: 'app-assistant',
  standalone: true,
  imports: [DatePipe, FormsModule, FontAwesomeModule, Modal, Select, MessageBlocks],
  templateUrl: './assistant.html',
  styleUrl: './assistant.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Assistant implements OnInit, OnDestroy {
  private api = inject(AssistantService);
  private header = inject(HeaderService);
  private toast = inject(ToastService);
  private confirm = inject(ConfirmService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private floating = inject(AssistantVisibilityService);
  private subs = new Subscription();
  @ViewChild('thread') threadEl?: ElementRef<HTMLElement>;
  @ViewChild('headerActions', { static: true }) headerActions!: TemplateRef<unknown>;
  @ViewChild('composer') composerEl?: ElementRef<HTMLTextAreaElement>;

  readonly threads = signal<AssistantThread[]>([]);
  readonly current = signal<AssistantThread | null>(null);
  readonly messages = signal<AssistantMessage[]>([]);
  readonly suggestions = signal<string[]>([]);
  readonly loadingThread = signal(false);
  readonly asking = signal<string | null>(null);
  /** Lo que va haciendo MiMo mientras responde (pasos y herramientas MCP), en vivo. */
  readonly steps = signal<string[]>([]);

  // Modelo que responde: «auto» = MiMo y su respaldo; o uno de la cadena (Groq, Gemini…) si MiMo no tiene cuota.
  readonly models = signal<AssistantModels | null>(null);
  readonly model = signal<string>(this.readModel());
  readonly modelOptions = computed<SelectOption[]>(() =>
    (this.models()?.models ?? [{ key: 'auto', label: 'MiMo (automático)', blocked: false }]).map((m) => ({
      value: m.key,
      label: m.blocked && m.key !== 'auto' ? `${m.label} (en pausa)` : m.label,
    })),
  );
  /** MiMo no está (sin cuota o caído) y se está usando «automático»: se ofrece cambiar de modelo, como Gemini. */
  readonly mimoDown = computed(() => {
    const m = this.models()?.mimo;
    return !!m && m.enabled && !m.available && this.model() === 'auto';
  });
  readonly mimoBack = computed(() => {
    const secs = this.models()?.mimo.blocked_for ?? 0;
    return secs > 0 ? `vuelve en ~${Math.max(1, Math.round(secs / 60))} min` : 'se reintenta en la próxima pregunta';
  });

  // Adjunto (foto o documento) que va con la próxima pregunta.
  readonly accept = ACCEPT;
  readonly attachment = signal<AssistantUpload | null>(null);
  readonly uploading = signal<string | null>(null);
  private modelsTimer: ReturnType<typeof setInterval> | null = null;
  private askSub: Subscription | null = null;
  readonly listOpen = signal(false);
  /** Lista de conversaciones oculta (en PC); se recuerda en este navegador. */
  readonly collapsed = signal(this.readCollapsed());
  readonly search = signal('');
  draft = '';

  /** El nombre de la conversación abierta va como subtítulo de la barra superior. */
  private readonly remember = effect(() => {
    const id = this.current()?.id;
    if (id) this.store('set', id);
  });
  private readonly headerTitle = effect(() => this.header.setConfig({ subtitle: this.current()?.title || SUBTITLE }));

  readonly pinned = computed(() => this.filtered().filter((t) => t.pinned));
  readonly mine = computed(() => this.filtered().filter((t) => !t.pinned && t.mine));
  readonly shared = computed(() => this.filtered().filter((t) => !t.pinned && !t.mine));
  readonly commands = computed(() => {
    const d = this.draftSignal();
    return d.startsWith('/') ? COMMANDS.filter((c) => c.cmd.startsWith(d.split(' ')[0].toLowerCase())) : [];
  });
  private readonly draftSignal = signal('');

  // Acción propuesta por la IA (formulario + confirmar)
  readonly action = signal<{ message: AssistantMessage; block: ActionBlock } | null>(null);
  readonly runningAction = signal(false);
  readonly actionError = signal<string | null>(null);
  actionForm: Record<string, unknown> = {};
  readonly yesNo: SelectOption[] = [
    { value: true, label: 'Sí' },
    { value: false, label: 'No' },
  ];

  // Renombrar (modal del sistema, no el prompt del navegador)
  readonly renameOpen = signal(false);
  renameValue = '';
  private renameTarget: AssistantThread | null = null;

  // Programar reporte
  readonly scheduleOpen = signal(false);
  private scheduleTarget: AssistantThread | null = null;
  scheduleForm = { question: '', cadence: 'weekly', weekday: 0, hour: 8, channel: 'email' };
  readonly cadenceOptions: SelectOption[] = [
    { value: 'weekly', label: 'Cada semana' },
    { value: 'daily', label: 'Cada día' },
  ];
  readonly weekdayOptions: SelectOption[] = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'].map((l, i) => ({ value: i, label: l }));
  readonly hourOptions: SelectOption[] = Array.from({ length: 16 }, (_, i) => i + 6).map((h) => ({ value: h, label: `${String(h).padStart(2, '0')}:00` }));
  readonly channelOptions: SelectOption[] = [
    { value: 'email', label: 'Correo' },
    { value: 'telegram', label: 'Telegram' },
    { value: 'both', label: 'Correo y Telegram' },
  ];

  toggleCollapsed(): void {
    this.collapsed.update((v) => !v);
    try {
      localStorage.setItem('moscowle_assistant_collapsed', this.collapsed() ? '1' : '0');
    } catch {
      /* sin almacenamiento: vale solo para esta visita */
    }
  }

  private readCollapsed(): boolean {
    try {
      return localStorage.getItem('moscowle_assistant_collapsed') === '1';
    } catch {
      return false;
    }
  }

  private filtered() {
    const q = this.search().trim().toLowerCase();
    return q ? this.threads().filter((t) => t.title.toLowerCase().includes(q)) : this.threads();
  }

  ngOnInit(): void {
    this.floating.suppressed.set(true);
    this.header.setConfig({ title: 'Asistente', subtitle: SUBTITLE, icon: ['fas', 'brain'], actionTemplate: this.headerActions });
    this.subs.add(this.api.home().subscribe({ next: (r) => this.suggestions.set(r.suggestions), error: () => {} }));
    this.loadThreads();
    this.loadModels();
    this.modelsTimer = setInterval(() => this.loadModels(), 60_000);
    // Al volver de otra pantalla (p. ej. Sedes) sin ?t=, se retoma la última conversación abierta.
    const last = this.route.snapshot.queryParamMap.get('t') ? null : this.store('get');
    if (last) void this.router.navigate([], { relativeTo: this.route, queryParams: { t: last }, replaceUrl: true });
    this.subs.add(
      this.route.queryParamMap.subscribe((p) => {
        const id = Number(p.get('t'));
        if (id) this.open(id, String(id) === last);
        else {
          this.current.set(null);
          this.messages.set([]);
        }
      }),
    );
  }

  ngOnDestroy(): void {
    if (this.modelsTimer) clearInterval(this.modelsTimer);
    this.floating.suppressed.set(false);
    this.subs.unsubscribe();
    this.header.reset();
  }

  loadThreads(): void {
    this.subs.add(this.api.threads().subscribe({ next: (r) => this.threads.set(r.threads), error: () => {} }));
  }

  loadModels(): void {
    this.subs.add(this.api.models().subscribe({ next: (m) => this.models.set(m), error: () => {} }));
  }

  private readModel(): string {
    try {
      return localStorage.getItem(MODEL_KEY) || 'auto';
    } catch {
      return 'auto';
    }
  }

  setModel(key: string): void {
    this.model.set(key || 'auto');
    try {
      localStorage.setItem(MODEL_KEY, this.model());
    } catch {
      /* solo esta visita */
    }
  }

  pickFile(input: HTMLInputElement): void {
    const file = input.files?.[0];
    input.value = '';
    if (!file) return;
    this.uploading.set(file.name);
    this.subs.add(
      this.api.upload(file).subscribe({
        next: (up) => {
          this.uploading.set(null);
          this.attachment.set(up);
          this.composerEl?.nativeElement.focus();
        },
        error: (err) => {
          this.uploading.set(null);
          this.toast.show(err?.error?.message || 'No se pudo subir el archivo.', 'error');
        },
      }),
    );
  }

  downloadFile(f: FileBlock): void {
    this.subs.add(
      this.api.download(f.path).subscribe({
        next: (blob) => {
          const url = URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = f.name;
          a.click();
          setTimeout(() => URL.revokeObjectURL(url), 2000);
        },
        error: () => this.toast.show('No se pudo descargar el archivo.', 'error'),
      }),
    );
  }

  /** Última conversación abierta en este navegador. */
  private store(op: 'get' | 'set' | 'clear', id?: number): string | null {
    try {
      if (op === 'get') return localStorage.getItem(LAST_KEY);
      if (op === 'set') localStorage.setItem(LAST_KEY, String(id));
      else localStorage.removeItem(LAST_KEY);
    } catch {
      /* sin almacenamiento: no se recuerda */
    }
    return null;
  }

  select(t: AssistantThread | null): void {
    this.listOpen.set(false);
    if (!t) this.store('clear');
    void this.router.navigate([], { relativeTo: this.route, queryParams: { t: t?.id ?? null } });
  }

  private open(id: number, restoring = false): void {
    if (this.current()?.id === id && this.messages().length) return;
    this.loadingThread.set(true);
    this.subs.add(
      this.api.thread(id).subscribe({
        next: (t) => {
          this.current.set(t);
          this.messages.set(t.messages ?? []);
          this.loadingThread.set(false);
          this.scrollDown();
        },
        error: () => {
          this.loadingThread.set(false);
          if (!restoring) this.toast.show('No se encontró esa conversación.', 'error');
          this.select(null);
        },
      }),
    );
  }

  onDraft(value: string): void {
    this.draft = value;
    this.draftSignal.set(value);
  }

  useCommand(text: string): void {
    this.onDraft(text);
    this.send();
  }

  onKey(e: KeyboardEvent): void {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      const cmd = this.commands()[0];
      if (cmd && this.draft.trim().startsWith('/')) this.onDraft(cmd.text);
      this.send();
    }
  }

  send(text?: string): void {
    const question = (text ?? this.draft).trim();
    const attachment = this.attachment();
    if ((!question && !attachment) || this.asking() || this.uploading()) return;
    const shown = attachment ? `📎 ${attachment.name}${question ? ' — ' + question : ''}` : question;
    this.asking.set(shown);
    this.attachment.set(null);
    this.steps.set([]);
    this.onDraft('');
    const threadId = this.current()?.mine === false ? null : (this.current()?.id ?? null);
    this.scrollDown();
    this.askSub = this.api.askStream(question, threadId, { model: this.model(), attachment }).subscribe({
      next: (ev) => {
        if (ev.type === 'step') {
          this.steps.update((l) => (l[l.length - 1] === ev.text ? l : [...l, ev.text].slice(-6)));
          this.scrollDown();
          return;
        }
        if (ev.type === 'error') {
          this.asking.set(null);
          this.onDraft(question);
          this.toast.show(ev.message || 'No pude responder ahora. Intenta de nuevo.', 'error');
          return;
        }
        const { thread, message } = ev;
        this.loadModels();
          const user: AssistantMessage = { id: -Date.now(), role: 'user', text: shown, blocks: [], sources: [], model: null, question: null, feedback: null, created_at: new Date().toISOString() };
          if (this.current()?.id === thread.id) {
            this.messages.update((m) => [...m, user, message]);
            this.current.set({ ...this.current()!, ...thread });
          } else {
            this.current.set(thread);
            this.messages.set([user, message]);
            void this.router.navigate([], { relativeTo: this.route, queryParams: { t: thread.id }, replaceUrl: true });
          }
          this.asking.set(null);
          this.loadThreads();
          this.scrollDown();
      },
      error: (err) => {
        this.asking.set(null);
        this.onDraft(question);
        this.toast.show(err?.message || 'No pude responder ahora. Intenta de nuevo.', 'error');
      },
    });
    this.subs.add(this.askSub);
  }

  /** Deja de esperar la respuesta (lo que MiMo ya hizo queda hecho). */
  stop(): void {
    this.askSub?.unsubscribe();
    this.askSub = null;
    const q = this.asking();
    this.asking.set(null);
    if (q) this.onDraft(q);
  }

  refresh(m: AssistantMessage): void {
    this.subs.add(
      this.api.refresh(m.id).subscribe({
        next: (fresh) => {
          this.messages.update((list) => list.map((x) => (x.id === m.id ? fresh : x)));
          this.toast.show('Actualizado con los datos de hoy.', 'success');
        },
        error: (err) => this.toast.show(err?.error?.message || 'No se pudo actualizar.', 'error'),
      }),
    );
  }

  feedback(m: AssistantMessage, value: 1 | -1): void {
    const next = m.feedback === value ? 0 : value;
    this.subs.add(this.api.feedback(m.id, next).subscribe({ next: (fresh) => this.messages.update((l) => l.map((x) => (x.id === m.id ? fresh : x))) }));
  }

  copy(m: AssistantMessage): void {
    void navigator.clipboard?.writeText((m.text || '').replace(/\*\*/g, '')).then(() => this.toast.show('Copiado.', 'success'));
  }

  // Menú ⋯ de cada conversación: tarjeta flotante al costado (la lista recorta lo que se sale de ella)
  readonly menu = signal<{ thread: AssistantThread; top: number; left: number } | null>(null);

  openMenu(ev: MouseEvent, t: AssistantThread): void {
    ev.stopPropagation();
    if (this.menu()?.thread.id === t.id) return this.menu.set(null);
    const r = (ev.currentTarget as HTMLElement).getBoundingClientRect();
    const w = 216, h = 236;
    const left = window.innerWidth - r.right > w + 12 ? r.right + 6 : Math.max(8, r.right - w);
    const top = Math.min(r.top - 4, window.innerHeight - h - 8);
    this.menu.set({ thread: t, top: Math.max(8, top), left });
  }

  menuAct(act: 'pinned' | 'shared' | 'schedule' | 'rename' | 'remove'): void {
    const t = this.menu()?.thread;
    this.menu.set(null);
    if (!t) return;
    if (act === 'pinned' || act === 'shared') this.toggle(act, t);
    else if (act === 'rename') this.rename(t);
    else if (act === 'remove') this.remove(t);
    else this.openSchedule(undefined, t);
  }

  @HostListener('document:keydown.escape')
  closeMenu(): void {
    this.menu.set(null);
  }

  /** Si la conversación tocada es la abierta, refleja el cambio arriba. */
  private patchCurrent(t: AssistantThread, fresh: Partial<AssistantThread>): void {
    const c = this.current();
    if (c?.id === t.id) this.current.set({ ...c, ...fresh });
  }

  toggle(key: 'pinned' | 'shared', t: AssistantThread | null = this.current()): void {
    if (!t?.mine) return;
    this.subs.add(
      this.api.updateThread(t.id, { [key]: !t[key] }).subscribe({
        next: (fresh) => {
          this.patchCurrent(t, fresh);
          this.loadThreads();
          if (key === 'shared') this.toast.show(fresh.shared ? 'Compartida con el equipo de administración.' : 'Ahora es solo tuya.', 'success');
        },
      }),
    );
  }

  rename(t: AssistantThread | null = this.current()): void {
    if (!t?.mine) return;
    this.renameTarget = t;
    this.renameValue = t.title;
    this.renameOpen.set(true);
  }

  saveRename(): void {
    const t = this.renameTarget;
    const title = this.renameValue.trim();
    if (!t || !title) return;
    this.renameOpen.set(false);
    this.subs.add(this.api.updateThread(t.id, { title }).subscribe({ next: (fresh) => { this.patchCurrent(t, fresh); this.loadThreads(); } }));
  }

  openAction(message: AssistantMessage, block: ActionBlock): void {
    this.actionForm = {};
    for (const f of block.fields) {
      const v = block.args[f.key];
      if (f.type === 'list' && f.options) this.actionForm[f.key] = Array.isArray(v) ? v : v != null ? [v] : [];
      else if (f.input === 'datetime' && typeof v === 'string') this.actionForm[f.key] = v.replace(' ', 'T').slice(0, 16);
      else this.actionForm[f.key] = Array.isArray(v) ? v.join(', ') : (v ?? (f.type === 'boolean' ? null : ''));
    }
    this.actionError.set(null);
    this.action.set({ message, block });
  }

  enumOptions(f: ActionField): SelectOption[] {
    return (f.options ?? []).map((o) => ({ value: o.value, label: o.label }));
  }

  /** Campos que aplican con lo elegido (p. ej. el plan solo si es paciente), como en el panel de Usuarios. */
  visibleFields(): ActionField[] {
    const a = this.action();
    if (!a) return [];
    return a.block.fields.filter((f) => !f.show_if || Object.entries(f.show_if).every(([k, vals]) => vals.includes(this.actionForm[k])));
  }

  /** ¿Este campo abre un grupo nuevo del formulario? */
  startsSection(f: ActionField, i: number): boolean {
    const list = this.visibleFields();
    return !!f.section && (i === 0 || list[i - 1].section !== f.section);
  }

  actionReady(): boolean {
    if (!this.action()) return false;
    const empty = (v: unknown) => v === '' || v === null || v === undefined || (Array.isArray(v) && !v.length);
    return this.visibleFields().every((f) => !f.required || !empty(this.actionForm[f.key]));
  }

  confirmAction(): void {
    const a = this.action();
    if (!a || !this.actionReady() || this.runningAction()) return;
    const args: Record<string, unknown> = {};
    for (const f of this.visibleFields()) {
      const raw = this.actionForm[f.key];
      if (raw === '' || raw === null || raw === undefined || (Array.isArray(raw) && !raw.length)) continue;
      if (f.type === 'integer') args[f.key] = parseInt(String(raw), 10);
      else if (f.type === 'number') args[f.key] = Number(raw);
      else if (f.type === 'list') args[f.key] = Array.isArray(raw) ? raw : String(raw).split(',').map((x) => x.trim()).filter(Boolean);
      else if (f.input === 'datetime') args[f.key] = String(raw).replace('T', ' ');
      else args[f.key] = raw;
    }
    const index = a.message.blocks.indexOf(a.block);
    this.runningAction.set(true);
    this.actionError.set(null);
    this.subs.add(
      this.api.runAction(a.message.id, args, index >= 0 ? index : undefined).subscribe({
        next: ({ message, reply }) => {
          this.runningAction.set(false);
          this.action.set(null);
          this.messages.update((l) => [...l.map((x) => (x.id === message.id ? message : x)), reply]);
          this.scrollDown();
        },
        error: (err) => {
          this.runningAction.set(false);
          this.actionError.set(err?.error?.message || 'No se pudo hacer. Revisa los datos.');
        },
      }),
    );
  }

  remove(t: AssistantThread | null = this.current()): void {
    if (!t?.mine) return;
    this.subs.add(
      this.confirm.confirm({ title: 'Borrar conversación', message: `«${t.title}» se borrará para todos.`, confirmText: 'Borrar', variant: 'danger' }).subscribe((ok) => {
        if (!ok) return;
        this.api.deleteThread(t.id).subscribe({ next: () => { if (this.current()?.id === t.id) this.select(null); this.loadThreads(); } });
      }),
    );
  }

  openSchedule(m?: AssistantMessage, t: AssistantThread | null = this.current()): void {
    this.scheduleTarget = t;
    const here = t?.id === this.current()?.id;
    const last = m?.question || (here ? [...this.messages()].reverse().find((x) => x.role === 'assistant')?.question : t?.title) || '';
    this.scheduleForm = { question: last, cadence: 'weekly', weekday: 0, hour: 8, channel: 'email' };
    this.scheduleOpen.set(true);
  }

  saveSchedule(): void {
    const t = this.scheduleTarget;
    this.subs.add(
      this.api.schedule({ ...(this.scheduleForm as Partial<AssistantSchedule> & { question: string }), thread_id: t?.mine ? t.id : null }).subscribe({
        next: (s) => {
          this.scheduleOpen.set(false);
          this.toast.show(`Listo: te llegará ${s.label}.`, 'success');
          const c = this.current();
          if (t && c?.id === t.id) this.current.set({ ...c, schedules: [...(c.schedules ?? []), s] });
        },
        error: (err) => this.toast.show(err?.error?.message || 'No se pudo programar.', 'error'),
      }),
    );
  }

  unschedule(s: AssistantSchedule): void {
    const t = this.current();
    this.subs.add(this.api.deleteSchedule(s.id).subscribe({ next: () => t && this.current.set({ ...t, schedules: (t.schedules ?? []).filter((x) => x.id !== s.id) }) }));
  }

  private scrollDown(): void {
    setTimeout(() => this.threadEl?.nativeElement.scrollTo({ top: this.threadEl.nativeElement.scrollHeight, behavior: 'smooth' }), 60);
  }
}
