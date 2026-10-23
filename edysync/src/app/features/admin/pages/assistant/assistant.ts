import { ChangeDetectionStrategy, Component, ElementRef, OnDestroy, OnInit, ViewChild, computed, inject, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { Subscription } from 'rxjs';
import { AssistantMessage, AssistantSchedule, AssistantService, AssistantThread } from '../../../../core/services/assistant';
import { HeaderService } from '../../../../core/services/header.service';
import { AssistantVisibilityService } from '../../../../core/services/assistant-visibility';
import { ToastService } from '../../../../core/services/toast.service';
import { ConfirmService } from '../../../../core/services/confirm.service';
import { Modal } from '../../../../shared/components/modal/modal';
import { Select, SelectOption } from '../../../../shared/components/select/select';
import { MessageBlocks } from './components/message-blocks/message-blocks';

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
  @ViewChild('composer') composerEl?: ElementRef<HTMLTextAreaElement>;

  readonly threads = signal<AssistantThread[]>([]);
  readonly current = signal<AssistantThread | null>(null);
  readonly messages = signal<AssistantMessage[]>([]);
  readonly suggestions = signal<string[]>([]);
  readonly loadingThread = signal(false);
  readonly asking = signal<string | null>(null);
  readonly listOpen = signal(false);
  readonly search = signal('');
  draft = '';

  readonly pinned = computed(() => this.filtered().filter((t) => t.pinned));
  readonly mine = computed(() => this.filtered().filter((t) => !t.pinned && t.mine));
  readonly shared = computed(() => this.filtered().filter((t) => !t.pinned && !t.mine));
  readonly commands = computed(() => {
    const d = this.draftSignal();
    return d.startsWith('/') ? COMMANDS.filter((c) => c.cmd.startsWith(d.split(' ')[0].toLowerCase())) : [];
  });
  private readonly draftSignal = signal('');

  // Programar reporte
  readonly scheduleOpen = signal(false);
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

  private filtered() {
    const q = this.search().trim().toLowerCase();
    return q ? this.threads().filter((t) => t.title.toLowerCase().includes(q)) : this.threads();
  }

  ngOnInit(): void {
    this.floating.suppressed.set(true);
    this.header.setConfig({ title: 'Asistente', subtitle: 'Pregunta por el centro: cifras, comparativos y tendencias', icon: ['fas', 'brain'] });
    this.subs.add(this.api.home().subscribe({ next: (r) => this.suggestions.set(r.suggestions), error: () => {} }));
    this.loadThreads();
    this.subs.add(
      this.route.queryParamMap.subscribe((p) => {
        const id = Number(p.get('t'));
        if (id) this.open(id);
        else {
          this.current.set(null);
          this.messages.set([]);
        }
      }),
    );
  }

  ngOnDestroy(): void {
    this.floating.suppressed.set(false);
    this.subs.unsubscribe();
    this.header.reset();
  }

  loadThreads(): void {
    this.subs.add(this.api.threads().subscribe({ next: (r) => this.threads.set(r.threads), error: () => {} }));
  }

  select(t: AssistantThread | null): void {
    this.listOpen.set(false);
    void this.router.navigate([], { relativeTo: this.route, queryParams: { t: t?.id ?? null } });
  }

  private open(id: number): void {
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
          this.toast.show('No se encontró esa conversación.', 'error');
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
    if (!question || this.asking()) return;
    this.asking.set(question);
    this.onDraft('');
    const threadId = this.current()?.mine === false ? null : (this.current()?.id ?? null);
    this.scrollDown();
    this.subs.add(
      this.api.ask(question, threadId).subscribe({
        next: ({ thread, message }) => {
          const user: AssistantMessage = { id: -Date.now(), role: 'user', text: question, blocks: [], sources: [], model: null, question: null, feedback: null, created_at: new Date().toISOString() };
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
          this.toast.show(err?.error?.message || 'No pude responder ahora. Intenta de nuevo.', 'error');
        },
      }),
    );
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

  toggle(key: 'pinned' | 'shared'): void {
    const t = this.current();
    if (!t?.mine) return;
    this.subs.add(
      this.api.updateThread(t.id, { [key]: !t[key] }).subscribe({
        next: (fresh) => {
          this.current.set({ ...t, ...fresh });
          this.loadThreads();
          if (key === 'shared') this.toast.show(fresh.shared ? 'Compartida con el equipo de administración.' : 'Ahora es solo tuya.', 'success');
        },
      }),
    );
  }

  rename(): void {
    const t = this.current();
    if (!t?.mine) return;
    const title = window.prompt('Nombre de la conversación', t.title)?.trim();
    if (!title) return;
    this.subs.add(this.api.updateThread(t.id, { title }).subscribe({ next: (fresh) => { this.current.set({ ...t, ...fresh }); this.loadThreads(); } }));
  }

  remove(): void {
    const t = this.current();
    if (!t?.mine) return;
    this.subs.add(
      this.confirm.confirm({ title: 'Borrar conversación', message: `«${t.title}» se borrará para todos.`, confirmText: 'Borrar', variant: 'danger' }).subscribe((ok) => {
        if (!ok) return;
        this.api.deleteThread(t.id).subscribe({ next: () => { this.select(null); this.loadThreads(); } });
      }),
    );
  }

  openSchedule(m?: AssistantMessage): void {
    const last = m?.question || [...this.messages()].reverse().find((x) => x.role === 'assistant')?.question || '';
    this.scheduleForm = { question: last, cadence: 'weekly', weekday: 0, hour: 8, channel: 'email' };
    this.scheduleOpen.set(true);
  }

  saveSchedule(): void {
    const t = this.current();
    this.subs.add(
      this.api.schedule({ ...(this.scheduleForm as Partial<AssistantSchedule> & { question: string }), thread_id: t?.mine ? t.id : null }).subscribe({
        next: (s) => {
          this.scheduleOpen.set(false);
          this.toast.show(`Listo: te llegará ${s.label}.`, 'success');
          if (t) this.current.set({ ...t, schedules: [...(t.schedules ?? []), s] });
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
