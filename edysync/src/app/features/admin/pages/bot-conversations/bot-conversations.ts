import { Component, ChangeDetectionStrategy, ChangeDetectorRef, ElementRef, OnDestroy, OnInit, ViewChild, computed, effect, inject, input, output, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { Subject, Subscription, interval, merge } from 'rxjs';
import { AdminService, BotConversation, BotMessage } from '../../../../core/services/admin.service';
import { LiveSyncService } from '../../../../core/services/live-sync.service';
import { ToastService } from '../../../../core/services/toast.service';
import { Switch } from '../../../../shared/components/switch/switch';

type ChannelFilter = '' | 'telegram' | 'whatsapp';

/**
 * Bandeja del bot: todas las conversaciones de Telegram y WhatsApp en vivo. El administrador puede leer el hilo,
 * tomar la conversación (el bot deja de contestar) y escribirle a la persona como si fuera el centro.
 * La lista y el hilo se actualizan solos cada pocos segundos; no hace falta recargar la página.
 */
@Component({
  selector: 'app-bot-conversations',
  standalone: true,
  imports: [FormsModule, FontAwesomeModule, Switch],
  templateUrl: './bot-conversations.html',
  styleUrl: './bot-conversations.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class BotConversations implements OnInit, OnDestroy {
  /** Si la intervención está apagada en la configuración, se puede leer pero no escribir. */
  interventionEnabled = input(true);
  unreadChange = output<number>();

  @ViewChild('scroller') scroller?: ElementRef<HTMLElement>;
  @ViewChild('composer') composerEl?: ElementRef<HTMLTextAreaElement>;

  private admin = inject(AdminService);
  private live = inject(LiveSyncService);
  private toast = inject(ToastService);
  private cdr = inject(ChangeDetectorRef);
  private subs = new Subscription();
  private refreshNow$ = new Subject<void>();

  conversations = signal<BotConversation[]>([]);
  selectedId = signal<number | null>(null);
  messages = signal<BotMessage[]>([]);
  loading = signal(true);
  threadLoading = signal(false);
  filter = signal<ChannelFilter>('');
  search = signal('');
  draft = '';
  sending = false;
  takeoverBusy = false;
  newBelow = false;
  mobileThread = false;

  selected = computed(() => this.conversations().find((c) => c.id === this.selectedId()) ?? null);
  unreadTotal = computed(() => this.conversations().reduce((n, c) => n + (c.unread || 0), 0));
  private lastMessageId = 0;

  constructor() {
    effect(() => this.unreadChange.emit(this.unreadTotal()));
  }

  ngOnInit() {
    this.loadList(true);
    // Lista: cada 4 s; hilo abierto: cada 2,5 s; y al instante cuando el servidor avisa de un cambio.
    this.subs.add(merge(interval(4000), this.refreshNow$).subscribe(() => this.loadList()));
    this.subs.add(interval(2500).subscribe(() => this.pollThread()));
    this.subs.add(this.live.watch(['conversations'], 3000).subscribe(() => { this.loadList(); this.pollThread(); }));
  }

  ngOnDestroy() {
    this.subs.unsubscribe();
  }

  // ── lista ────────────────────────────────────────────────────────────────
  loadList(first = false) {
    this.admin.getBotConversations({ channel: this.filter() || undefined, q: this.search() || undefined }).subscribe({
      next: (res) => {
        this.conversations.set(res.conversations);
        this.loading.set(false);
        if (first && !this.selectedId() && res.conversations.length && window.innerWidth >= 900) this.open(res.conversations[0].id, false);
        this.cdr.markForCheck();
      },
      error: () => { this.loading.set(false); this.cdr.markForCheck(); },
    });
  }

  setFilter(value: ChannelFilter) {
    this.filter.set(value);
    this.loadList();
  }

  onSearch(value: string) {
    this.search.set(value);
    this.refreshNow$.next();
  }

  // ── hilo ─────────────────────────────────────────────────────────────────
  open(id: number, showMobile = true) {
    this.selectedId.set(id);
    this.messages.set([]);
    this.lastMessageId = 0;
    this.threadLoading.set(true);
    this.newBelow = false;
    if (showMobile) this.mobileThread = true;
    this.admin.getBotThread(id, undefined, true).subscribe({
      next: (res) => {
        this.messages.set(res.messages);
        this.lastMessageId = res.messages.at(-1)?.id ?? 0;
        this.threadLoading.set(false);
        this.patchConversation(res.conversation);
        this.cdr.markForCheck();
        setTimeout(() => this.scrollToEnd(false));
      },
      error: () => { this.threadLoading.set(false); this.toast.show('No se pudo abrir la conversación.', 'error'); this.cdr.markForCheck(); },
    });
  }

  back() {
    this.mobileThread = false;
  }

  private pollThread() {
    const id = this.selectedId();
    if (!id || this.threadLoading()) return;
    this.admin.getBotThread(id, this.lastMessageId || undefined, true).subscribe({
      next: (res) => {
        this.patchConversation(res.conversation);
        if (!res.messages.length) return;
        const nearBottom = this.isNearBottom();
        this.messages.update((m) => [...m, ...res.messages.filter((x) => !m.some((y) => y.id === x.id))]);
        this.lastMessageId = res.messages.at(-1)!.id;
        this.cdr.markForCheck();
        if (nearBottom) setTimeout(() => this.scrollToEnd(true));
        else this.newBelow = true;
      },
      error: () => {},
    });
  }

  private patchConversation(conv: BotConversation) {
    this.conversations.update((list) => list.map((c) => (c.id === conv.id ? { ...c, ...conv, unread: 0 } : c)));
  }

  // ── acciones ─────────────────────────────────────────────────────────────
  toggleTakeover(enabled: boolean) {
    const conv = this.selected();
    if (!conv || this.takeoverBusy) return;
    this.takeoverBusy = true;
    this.patchConversation({ ...conv, human_takeover: enabled });
    this.admin.setBotTakeover(conv.id, enabled).subscribe({
      next: (res) => {
        this.takeoverBusy = false;
        this.patchConversation(res.conversation);
        this.toast.show(enabled ? 'Atiendes esta conversación: el bot no contestará.' : 'El bot vuelve a contestar esta conversación.', 'success');
        this.cdr.markForCheck();
        if (enabled) setTimeout(() => this.composerEl?.nativeElement.focus());
      },
      error: (err) => {
        this.takeoverBusy = false;
        this.patchConversation({ ...conv, human_takeover: !enabled });
        this.toast.show(err?.error?.error || 'No se pudo cambiar quién atiende.', 'error');
        this.cdr.markForCheck();
      },
    });
  }

  send() {
    const conv = this.selected();
    const text = this.draft.trim();
    if (!conv || !text || this.sending) return;
    this.sending = true;
    this.cdr.markForCheck();
    this.admin.sendBotMessage(conv.id, text).subscribe({
      next: (res) => {
        this.sending = false;
        this.draft = '';
        this.messages.update((m) => (m.some((x) => x.id === res.message.id) ? m : [...m, res.message]));
        this.lastMessageId = Math.max(this.lastMessageId, res.message.id);
        this.cdr.markForCheck();
        setTimeout(() => this.scrollToEnd(true));
      },
      error: (err) => {
        this.sending = false;
        this.toast.show(err?.error?.error || 'No se pudo enviar el mensaje.', 'error');
        // El intento fallido queda en el historial: se vuelve a leer para mostrarlo.
        this.pollThread();
        this.cdr.markForCheck();
      },
    });
  }

  onComposerKey(event: KeyboardEvent) {
    if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
      event.preventDefault();
      this.send();
    }
  }

  // ── scroll ───────────────────────────────────────────────────────────────
  private isNearBottom(): boolean {
    const el = this.scroller?.nativeElement;
    return !el || el.scrollHeight - el.scrollTop - el.clientHeight < 120;
  }

  scrollToEnd(smooth: boolean) {
    const el = this.scroller?.nativeElement;
    if (!el) return;
    el.scrollTo({ top: el.scrollHeight, behavior: smooth ? 'smooth' : 'auto' });
    this.newBelow = false;
    this.cdr.markForCheck();
  }

  onScroll() {
    if (this.newBelow && this.isNearBottom()) { this.newBelow = false; this.cdr.markForCheck(); }
  }

  // ── presentación ─────────────────────────────────────────────────────────
  channelIcon(c: BotConversation): [string, string] {
    return c.channel === 'whatsapp' ? ['fab', 'whatsapp'] : ['fab', 'telegram'];
  }

  time(iso: string | null): string {
    if (!iso) return '';
    const d = new Date(iso);
    const today = new Date();
    return d.toDateString() === today.toDateString()
      ? d.toLocaleTimeString('es-PE', { hour: '2-digit', minute: '2-digit' })
      : d.toLocaleDateString('es-PE', { day: '2-digit', month: 'short' });
  }

  dayLabel(iso: string): string {
    const d = new Date(iso);
    const today = new Date();
    const yesterday = new Date(Date.now() - 86400000);
    if (d.toDateString() === today.toDateString()) return 'Hoy';
    if (d.toDateString() === yesterday.toDateString()) return 'Ayer';
    return d.toLocaleDateString('es-PE', { weekday: 'long', day: 'numeric', month: 'long' });
  }

  showDay(index: number): boolean {
    const list = this.messages();
    if (index === 0) return true;
    return new Date(list[index].created_at).toDateString() !== new Date(list[index - 1].created_at).toDateString();
  }

  initials(name: string): string {
    return (name.trim().split(/\s+/).slice(0, 2).map((p) => p[0]).join('') || '?').toUpperCase();
  }

  trackMsg = (_: number, m: BotMessage) => m.id;
}
