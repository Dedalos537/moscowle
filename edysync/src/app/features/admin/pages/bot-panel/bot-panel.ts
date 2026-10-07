import { Component, OnInit, OnDestroy, Output, EventEmitter, ChangeDetectionStrategy, ChangeDetectorRef, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { Subject, Subscription, debounceTime, interval } from 'rxjs';
import { AdminService, type WebsiteFaqStatus } from '../../../../core/services/admin.service';
import { AuthService } from '../../../../core/services/auth.service';
import { Spinner } from '../../../../shared/components/spinner/spinner';
import { Button } from '../../../../shared/components/button/button';
import { Alert } from '../../../../shared/components/alert/alert';
import { Switch } from '../../../../shared/components/switch/switch';
import { LiveSyncService } from '../../../../core/services/live-sync.service';
import { BotConversations } from '../bot-conversations/bot-conversations';

interface BotForm {
  bot_name: string;
  bot_emoji: string;
  persona_message: string;
  system_prompt: string;
  auto_faq_enabled: boolean;
  auto_faq_threshold: number;
  mcp_prompt_enabled: boolean;
  notify_supervision_enabled: boolean;
  intervention_enabled: boolean;
}

const EMPTY_FORM: BotForm = {
  bot_name: '',
  bot_emoji: '',
  persona_message: '',
  system_prompt: '',
  auto_faq_enabled: true,
  auto_faq_threshold: 3,
  mcp_prompt_enabled: true,
  notify_supervision_enabled: true,
  intervention_enabled: true,
};

type TabId = 'dashboard' | 'conversations' | 'config' | 'telegram' | 'faq' | 'webhook' | 'test';

interface TabDef {
  id: TabId;
  label: string;
  icon: [string, string];
  badge?: number;
}

@Component({
  selector: 'app-bot-panel',
  standalone: true,
  imports: [CommonModule, FormsModule, FontAwesomeModule, Spinner, Button, Alert, Switch, BotConversations],
  templateUrl: './bot-panel.html',
  styleUrl: './bot-panel.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class BotPanel implements OnInit, OnDestroy {
  private admin = inject(AdminService);
  private auth = inject(AuthService);
  private cdr = inject(ChangeDetectorRef);
  private live = inject(LiveSyncService);
  private subs = new Subscription();
  private autosave$ = new Subject<void>();
  unreadConv = 0;

  loading = true;
  error: string | null = null;

  activeTab: TabId = 'dashboard';

  tabs: TabDef[] = [
    { id: 'dashboard', label: 'Resumen', icon: ['fas', 'gauge-high'] },
    { id: 'conversations', label: 'Conversaciones', icon: ['fas', 'comments'] },
    { id: 'config', label: 'Configuración', icon: ['fas', 'gear'] },
    { id: 'telegram', label: 'Telegram', icon: ['fab', 'telegram'] },
    { id: 'faq', label: 'FAQ', icon: ['fas', 'book'] },
    { id: 'webhook', label: 'Webhook', icon: ['fas', 'link'] },
    { id: 'test', label: 'Pruebas', icon: ['fas', 'flask'] },
  ];

  /** Salta a la pestaña Notificaciones del Centro de control, donde está el
   *  QR y el estado del número emisor de WhatsApp. */
  @Output() openNotifications = new EventEmitter<void>();

  // Bot data
  bot: any = null;
  channels: any = {};

  // Interruptor maestro del bot
  toggleSaving = false;
  toggleError = '';
  conversations: any[] = [];
  activity: any[] = [];

  // Configuración (identidad + opciones): un solo formulario, un solo guardado
  form: BotForm = { ...EMPTY_FORM };
  private savedForm: BotForm = { ...EMPTY_FORM };
  fieldErrors: Record<string, string> = {};
  saving = false;
  saveState: 'idle' | 'saving' | 'saved' | 'error' = 'idle';
  saveError = '';
  readonly limits = { persona: 1000, prompt: 20000 };

  // FAQ
  faqList: any[] = [];
  faqLoading = false;
  faqCategory = '';
  faqEditing: any = null;
  faqSaving = false;
  faqForm = { question: '', answer: '', category: 'general', keywords: '' };
  showFaqForm = false;

  // Webhook
  webhookStatus: any = null;
  webhookLoading = false;
  webhookSetupUrl = '';
  webhookSecret = '';

  // Test message
  testChatId = '';
  testMessage = '';
  testSending = false;
  testResponse = '';
  testError = '';

  // Linked accounts
  tgStatus: any = null;
  showLinkForm = false;
  linkCode = '';
  linking = false;
  linkError = '';
  linkSuccess = '';
  unlinking: number | false = false;

  // Filters
  activityFilter: 'all' | 'telegram' | 'api' | 'errors' = 'all';
  convFilter = 'all';
  convFilterOptions = ['all', 'web', 'telegram', 'whatsapp', 'instagram'];
  activityFilterOptions = ['all', 'telegram', 'api', 'errors'];

  // Intervention (reply as bot)
  replyOpen: number | null = null;
  replyText = '';
  replySending = false;
  replyMsg = '';
  replyErr = '';

  // Proposed (auto-grown) FAQs
  proposedFaqs: any[] = [];
  proposedLoading = false;
  webFaq: WebsiteFaqStatus | null = null;
  webFaqBusy = false;
  autogrowMsg = '';
  autogrowErr = '';

  ngOnInit() {
    this.loadDashboard();

    // Autoguardado: lo escrito se guarda solo a los 0,8 s sin teclear; los interruptores guardan al instante.
    this.subs.add(this.autosave$.pipe(debounceTime(800)).subscribe(() => this.saveConfig()));
    // Cambios hechos por otra persona/pestaña (o por el propio bot): la pantalla se recarga sola.
    this.subs.add(
      this.live.watch(['bot_config', 'faq']).subscribe((scope) => {
        if (scope === 'bot_config' && !this.dirty && !this.saving) this.loadDashboard(false);
        if (scope === 'faq') { this.loadProposedFaqs(); if (this.faqList.length) this.loadFaq(); this.refreshBotCounts(); }
      }),
    );
    // Insignia de mensajes sin leer en la pestaña Conversaciones.
    this.refreshUnread();
    this.subs.add(interval(8000).subscribe(() => { if (this.activeTab !== 'conversations') this.refreshUnread(); }));
  }

  private refreshUnread() {
    this.admin.getBotConversations({}).subscribe({ next: (r) => { this.unreadConv = r.unread_total; this.cdr.markForCheck(); }, error: () => {} });
  }

  private refreshBotCounts() {
    this.admin.getBotDashboard().subscribe({
      next: (res) => {
        if (this.bot) { this.bot.faq_count = res.bot?.faq_count; this.bot.proposed_faq_count = res.bot?.proposed_faq_count; }
        this.cdr.markForCheck();
      },
      error: () => {},
    });
  }

  ngOnDestroy() {
    this.subs.unsubscribe();
  }

  setTab(id: TabId) {
    this.activeTab = id;
    this.cdr.markForCheck();
    if (id === 'telegram' && !this.tgStatus) this.loadLinkedAccounts();
    if (id === 'webhook' && !this.webhookStatus) this.loadWebhookStatus();
    if (id === 'faq' && !this.webFaq) this.loadWebFaq();
    if (id === 'faq' && this.faqList.length === 0) this.loadFaq();
    if (id === 'faq' && this.proposedFaqs.length === 0) this.loadProposedFaqs();
    this.error = null;
  }

  loadDashboard(showLoading = true) {
    if (showLoading) {
      this.loading = true;
    }
    this.error = null;
    this.cdr.markForCheck();

    this.subs.add(
      this.admin.getBotDashboard().subscribe({
        next: (res) => {
          this.bot = res.bot;
          this.channels = res.channels || {};
          this.conversations = res.conversations || [];
          this.activity = res.activity || [];
          this.initForm();
          this.loading = false;
          this.cdr.markForCheck();
        },
        error: (err) => {
          const status = err?.status;
          let msg = '';
          if (status === 401 || status === 403) {
            msg = 'Sesión expirada. Por favor, vuelve a iniciar sesión.';
            this.triggerAuthRefresh();
          } else if (status === 0) {
            msg = 'No se puede conectar al servidor. Verifica tu conexión.';
          } else {
            msg = err?.error?.error || err?.message || err?.statusText || `Error ${status || ''}: al cargar dashboard del bot`;
          }
          this.error = msg;
          this.loading = false;
          this.cdr.markForCheck();
        },
      })
    );
  }

  private triggerAuthRefresh() {
    this.auth.refreshToken().subscribe({
      next: (res) => {
        if (res.access_token) {
          localStorage.setItem('access_token', res.access_token);
        }
        if (res.refresh_token) {
          localStorage.setItem('refresh_token', res.refresh_token);
        }
        this.loadDashboard(false);
      },
      error: (err) => {
        window.location.href = '/app/auth/login';
      },
    });
  }

  loadLinkedAccounts() {
    this.subs.add(
      this.admin.getTelegramStatus().subscribe({
        next: (res) => { this.tgStatus = res; this.cdr.markForCheck(); },
        error: () => this.cdr.markForCheck(),
      })
    );
  }

  loadWebhookStatus() {
    this.webhookLoading = true;
    this.cdr.markForCheck();
    this.subs.add(
      this.admin.getWebhookStatus().subscribe({
        next: (res) => { this.webhookStatus = res; this.webhookLoading = false; this.cdr.markForCheck(); },
        error: () => { this.webhookLoading = false; this.webhookStatus = { ok: false, error: 'Error' }; this.cdr.markForCheck(); },
      })
    );
  }

  setupWebhook() {
    if (!this.webhookSetupUrl.trim()) return;
    this.webhookLoading = true;
    this.cdr.markForCheck();
    this.subs.add(
      this.admin.setupWebhook(this.webhookSetupUrl, this.webhookSecret || undefined).subscribe({
        next: (res) => { this.webhookLoading = false; if (res.ok) this.loadWebhookStatus(); this.cdr.markForCheck(); },
        error: () => { this.webhookLoading = false; this.cdr.markForCheck(); },
      })
    );
  }

  deleteWebhook() {
    this.webhookLoading = true;
    this.cdr.markForCheck();
    this.subs.add(
      this.admin.deleteWebhook().subscribe({
        next: () => { this.webhookLoading = false; this.loadWebhookStatus(); this.cdr.markForCheck(); },
        error: () => { this.webhookLoading = false; this.cdr.markForCheck(); },
      })
    );
  }

  // ─── Configuración ──────────────────────────────────────────────────
  private initForm() {
    const cfg = this.bot?.config || {};
    this.form = {
      bot_name: this.bot?.name || '',
      bot_emoji: this.bot?.emoji || '',
      persona_message: this.bot?.persona_message || '',
      system_prompt: this.bot?.system_prompt || '',
      auto_faq_enabled: cfg.auto_faq_enabled ?? true,
      auto_faq_threshold: cfg.auto_faq_threshold ?? 3,
      mcp_prompt_enabled: cfg.mcp_prompt_enabled ?? true,
      notify_supervision_enabled: cfg.notify_supervision_enabled ?? true,
      intervention_enabled: cfg.intervention_enabled ?? true,
    };
    this.savedForm = { ...this.form };
    this.fieldErrors = {};
  }

  get dirty(): boolean {
    return (Object.keys(this.form) as (keyof BotForm)[]).some((k) => this.form[k] !== this.savedForm[k]);
  }

  /** Texto escrito: se guarda solo tras una pausa. */
  onType() {
    this.saveState = 'idle';
    this.saveError = '';
    this.autosave$.next();
  }

  /** Interruptores y selecciones: guardan al instante. */
  onToggle<K extends keyof BotForm>(key: K, value: BotForm[K]) {
    this.form[key] = value;
    this.saveConfig();
  }

  /** Lo que verá quien escriba /start: misma fórmula que el backend (identidad + presentación configuradas). */
  get previewName(): string {
    return this.form.bot_name.trim() || 'Asistente';
  }
  get previewEmoji(): string {
    return this.form.bot_emoji.trim() || '🤖';
  }
  get previewIntro(): string {
    return this.form.persona_message.trim() || 'Soy tu asistente inteligente para el Centro Juan Pablo II.';
  }

  saveConfig() {
    if (this.saving || !this.dirty) return;
    // Solo viaja lo que cambió: antes se reenviaba todo, incluido el texto heredado del entorno, y el servidor lo rechazaba.
    const payload: Record<string, unknown> = {};
    (Object.keys(this.form) as (keyof BotForm)[]).forEach((k) => {
      if (this.form[k] !== this.savedForm[k]) payload[k] = k === 'auto_faq_threshold' ? Math.max(1, Math.min(50, Math.round(Number(this.form[k]) || 3))) : this.form[k];
    });
    const sent = { ...this.form };
    this.saving = true;
    this.saveState = 'saving';
    this.saveError = '';
    this.fieldErrors = {};
    this.cdr.markForCheck();
    this.subs.add(
      this.admin.updateTelegramConfig(payload).subscribe({
        next: (res) => {
          const c = res?.config || {};
          this.bot = {
            ...this.bot,
            name: c.bot_name ?? sent.bot_name,
            emoji: c.bot_emoji ?? sent.bot_emoji,
            persona_message: c.persona_message ?? sent.persona_message,
            system_prompt: c.system_prompt ?? sent.system_prompt,
            config: {
              auto_faq_enabled: c.auto_faq_enabled ?? sent.auto_faq_enabled,
              auto_faq_threshold: c.auto_faq_threshold ?? sent.auto_faq_threshold,
              mcp_prompt_enabled: c.mcp_prompt_enabled ?? sent.mcp_prompt_enabled,
              notify_supervision_enabled: c.notify_supervision_enabled ?? sent.notify_supervision_enabled,
              intervention_enabled: c.intervention_enabled ?? sent.intervention_enabled,
            },
          };
          // Lo enviado pasa a ser «guardado»; lo que se escribió mientras tanto sigue pendiente.
          Object.keys(payload).forEach((k) => ((this.savedForm as any)[k] = (sent as any)[k]));
          this.saving = false;
          this.saveState = this.dirty ? 'idle' : 'saved';
          this.cdr.markForCheck();
          if (this.dirty) this.autosave$.next();
          else setTimeout(() => { if (this.saveState === 'saved') { this.saveState = 'idle'; this.cdr.markForCheck(); } }, 2200);
        },
        error: (err) => {
          this.saving = false;
          this.saveState = 'error';
          this.fieldErrors = err?.error?.fields || {};
          const fields = Object.values(this.fieldErrors);
          this.saveError = fields.length ? fields.join(' · ') : err?.error?.error || 'No se pudo guardar. Se reintentará al seguir editando.';
          this.cdr.markForCheck();
        },
      })
    );
  }

  // ─── FAQ ────────────────────────────────────────────────────────────
  loadWebFaq() {
    this.subs.add(this.admin.getWebsiteFaq().subscribe({ next: (r) => { this.webFaq = r; this.cdr.markForCheck(); } }));
  }

  syncWebFaq() {
    if (this.webFaqBusy) return;
    this.webFaqBusy = true;
    this.cdr.markForCheck();
    this.subs.add(
      this.admin.syncWebsiteFaq().subscribe({
        next: (r) => { this.webFaq = r; this.webFaqBusy = false; this.loadFaq(); this.cdr.markForCheck(); },
        error: (err) => {
          this.webFaq = { ...(err?.error ?? {}), url: err?.error?.url ?? this.webFaq?.url ?? '', ok: false, error: err?.error?.error ?? 'No se pudo leer la página' };
          this.webFaqBusy = false;
          this.cdr.markForCheck();
        },
      }),
    );
  }

  loadFaq() {
    this.faqLoading = true;
    this.cdr.markForCheck();
    this.subs.add(
      this.admin.getFaqList(this.faqCategory || undefined).subscribe({
        next: (res) => { this.faqList = res; this.faqLoading = false; this.cdr.markForCheck(); },
        error: () => { this.faqLoading = false; this.cdr.markForCheck(); },
      })
    );
  }

  startCreateFaq() {
    this.faqEditing = null;
    this.faqForm = { question: '', answer: '', category: 'general', keywords: '' };
    this.showFaqForm = true;
  }

  startEditFaq(faq: any) {
    this.faqEditing = faq.id;
    this.faqForm = { question: faq.question, answer: faq.answer, category: faq.category, keywords: faq.keywords || '' };
    this.showFaqForm = true;
  }

  saveFaq() {
    if (!this.faqForm.question || !this.faqForm.answer) return;
    this.faqSaving = true;
    this.cdr.markForCheck();
    const obs = this.faqEditing
      ? this.admin.updateFaq(this.faqEditing, this.faqForm)
      : this.admin.createFaq(this.faqForm);
    this.subs.add(
      obs.subscribe({
        next: () => {
          this.faqSaving = false;
          this.faqEditing = null;
          this.showFaqForm = false;
          this.faqForm = { question: '', answer: '', category: 'general', keywords: '' };
          this.loadFaq();
          this.cdr.markForCheck();
        },
        error: () => { this.faqSaving = false; this.cdr.markForCheck(); },
      })
    );
  }

  deleteFaq(id: number) {
    this.subs.add(
      this.admin.deleteFaq(id).subscribe({ next: () => this.loadFaq() })
    );
  }

  cancelFaqEdit() {
    this.faqEditing = null;
    this.showFaqForm = false;
    this.faqForm = { question: '', answer: '', category: 'general', keywords: '' };
  }

  // ─── Test message ───────────────────────────────────────────────────
  sendTestMessage() {
    if (!this.testChatId || !this.testMessage) return;
    this.testSending = true;
    this.testResponse = '';
    this.testError = '';
    this.cdr.markForCheck();
    this.subs.add(
      this.admin.sendTestMessage(Number(this.testChatId), this.testMessage).subscribe({
        next: (res) => {
          this.testSending = false;
          this.testResponse = res?.message || 'Mensaje enviado';
          this.testMessage = '';
          this.cdr.markForCheck();
        },
        error: (err) => {
          this.testSending = false;
          this.testError = err.error?.error || err.message || 'Error al enviar';
          this.cdr.markForCheck();
        },
      })
    );
  }

  // ─── Link / Unlink ──────────────────────────────────────────────────
  linkTelegram() {
    const code = this.linkCode.trim().toUpperCase();
    if (!code || code.length < 4) {
      this.linkError = 'Ingresa el código de 6 caracteres que te dio el bot.';
      return;
    }
    this.linking = true;
    this.linkError = '';
    this.linkSuccess = '';
    this.cdr.markForCheck();
    this.subs.add(
      this.admin.linkTelegram(code).subscribe({
        next: (res) => {
          this.linking = false;
          if (res.status === 'linked') {
            this.linkSuccess = 'Telegram vinculado exitosamente.';
            this.linkCode = '';
            this.showLinkForm = false;
            this.loadDashboard();
            this.loadLinkedAccounts();
          } else if (res.error) {
            this.linkError = res.error;
          } else {
            this.linkError = 'No se pudo vincular.';
          }
          this.cdr.markForCheck();
        },
        error: (err) => {
          this.linking = false;
          this.linkError = err.error?.error || err.message || 'Error al vincular';
          this.cdr.markForCheck();
        },
      })
    );
  }

  unlinkTelegram(chatId: number) {
    this.unlinking = chatId;
    this.cdr.markForCheck();
    this.subs.add(
      this.admin.unlinkTelegram(chatId).subscribe({
        next: () => { this.unlinking = false; this.loadDashboard(); this.loadLinkedAccounts(); this.cdr.markForCheck(); },
        error: () => { this.unlinking = false; this.cdr.markForCheck(); },
      })
    );
  }

  toggleNotifications(chatId: number, enabled: boolean) {
    this.subs.add(
      this.admin.toggleTelegramNotifications(chatId, enabled).subscribe({
        next: () => { this.loadLinkedAccounts(); this.cdr.markForCheck(); },
        error: () => this.cdr.markForCheck(),
      })
    );
  }

  // ─── Filters ────────────────────────────────────────────────────────
  setConvFilter(f: string) { this.convFilter = f; }
  setActivityFilter(f: string) { this.activityFilter = f as any; }

  filteredActivity(): any[] {
    if (this.activityFilter === 'all') return this.activity;
    return this.activity.filter(a => a.type === this.activityFilter);
  }

  filteredConversations(): any[] {
    if (this.convFilter === 'all') return this.conversations;
    return this.conversations.filter(c => c.channel === this.convFilter);
  }

  // ─── Intervention: reply as bot ─────────────────────────────────────
  toggleReply(conv: any) {
    this.replyOpen = this.replyOpen === conv.chat_id ? null : conv.chat_id;
    this.replyText = '';
    this.replyMsg = '';
    this.replyErr = '';
    this.cdr.markForCheck();
  }

  canReply(conv: any): boolean {
    return conv.channel === 'telegram' && !!conv.chat_id && this.bot?.config?.intervention_enabled !== false;
  }

  sendReply(conv: any) {
    const text = this.replyText.trim();
    if (!text) return;
    this.replySending = true;
    this.replyMsg = '';
    this.replyErr = '';
    this.cdr.markForCheck();
    this.subs.add(
      this.admin.replyToChat(Number(conv.chat_id), text).subscribe({
        next: (res) => {
          this.replySending = false;
          this.replyMsg = res?.message || 'Respondido';
          this.replyText = '';
          this.cdr.markForCheck();
        },
        error: (err) => {
          this.replySending = false;
          this.replyErr = err.error?.error || err.message || 'Error al enviar';
          this.cdr.markForCheck();
        },
      })
    );
  }

  // ─── Proposed (auto-grown) FAQ ──────────────────────────────────────
  loadProposedFaqs() {
    this.proposedLoading = true;
    this.autogrowMsg = '';
    this.autogrowErr = '';
    this.cdr.markForCheck();
    this.subs.add(
      this.admin.getProposedFaqs().subscribe({
        next: (res) => { this.proposedFaqs = res || []; this.proposedLoading = false; this.cdr.markForCheck(); },
        error: () => { this.proposedFaqs = []; this.proposedLoading = false; this.cdr.markForCheck(); },
      })
    );
  }

  triggerAutoGrow() {
    this.autogrowErr = '';
    this.autogrowMsg = '';
    this.cdr.markForCheck();
    this.subs.add(
      this.admin.triggerAutoGrow().subscribe({
        next: (res) => { this.autogrowMsg = `Generadas ${res?.proposed || 0} propuestas nuevas`; this.loadProposedFaqs(); this.cdr.markForCheck(); },
        error: (err) => { this.autogrowErr = err.error?.error || err.message || 'Error'; this.cdr.markForCheck(); },
      })
    );
  }

  approveFaq(faqId: number) {
    this.subs.add(
      this.admin.approveFaq(faqId).subscribe({
        next: () => { this.proposedFaqs = this.proposedFaqs.filter(f => f.id !== faqId); this.loadFaq(); this.cdr.markForCheck(); },
        error: () => { this.cdr.markForCheck(); },
      })
    );
  }

  rejectFaq(faqId: number) {
    this.subs.add(
      this.admin.deleteFaq(faqId).subscribe({
        next: () => { this.proposedFaqs = this.proposedFaqs.filter(f => f.id !== faqId); this.cdr.markForCheck(); },
        error: () => { this.cdr.markForCheck(); },
      })
    );
  }

  // ─── Helpers ────────────────────────────────────────────────────────
  formatDate(s: string | null | undefined): string {
    if (!s) return '—';
    try { return new Date(s).toLocaleString('es-PE', { dateStyle: 'short', timeStyle: 'short' }); }
    catch { return s; }
  }

  channelIcon(ch: string): string {
    return this.channelIconDef(ch)[1];
  }

  channelIconDef(ch: string): [string, string] {
    const brands: Record<string, string> = { telegram: 'telegram', whatsapp: 'whatsapp', instagram: 'instagram' };
    const solid: Record<string, string> = { web: 'globe' };
    if (brands[ch]) return ['fab', brands[ch]];
    if (solid[ch]) return ['fas', solid[ch]];
    return ['fas', 'circle'];
  }

  channelColor(ch: string): string {
    const colors: Record<string, string> = {
      web: '#22c55e', telegram: '#229ED9', whatsapp: '#25D366', instagram: '#E4405F',
    };
    return colors[ch] || '#94a3b8';
  }

  get whatsappChannel(): any {
    return this.channels?.['whatsapp'] || null;
  }

  /** Enciende o apaga el bot sin tocar el token. */
  toggleEnabled(value: boolean) {
    if (this.toggleSaving) return;
    this.toggleSaving = true;
    this.toggleError = '';
    this.cdr.markForCheck();
    this.subs.add(
      this.admin.updateTelegramConfig({ enabled: value }).subscribe({
        next: (res) => {
          const cfg = res?.config;
          if (this.bot && cfg) {
            this.bot.enabled = !!cfg.enabled;
            this.bot.is_active = !!(this.bot.configured && cfg.enabled);
          }
          this.toggleSaving = false;
          this.cdr.markForCheck();
        },
        error: (err) => {
          this.toggleSaving = false;
          this.toggleError = err?.error?.error || 'No se pudo cambiar el estado del bot';
          this.cdr.markForCheck();
        },
      })
    );
  }

  formatUptime(seconds?: number): string {
    const s = Math.max(0, Math.floor(seconds || 0));
    if (s < 60) return `${s}s`;
    const m = Math.floor(s / 60);
    if (m < 60) return `${m} min`;
    return `${Math.floor(m / 60)}h ${m % 60} min`;
  }

  formatWaPhone(phone?: string): string {
    const digits = String(phone || '').replace(/\D/g, '');
    return digits ? `+${digits}` : '';
  }

  channelLabel(ch: string): string {
    const labels: Record<string, string> = { web: 'Web', telegram: 'Telegram', whatsapp: 'WhatsApp', instagram: 'Instagram' };
    return labels[ch] || ch;
  }

  activityIcon(type: string): string {
    const icons: Record<string, string> = { telegram: 'telegram', api: 'code', error: 'exclamation-triangle', system: 'cog' };
    return icons[type] || 'circle';
  }

  activityIconDef(type: string): [string, string] {
    if (type === 'telegram') return ['fab', 'telegram'];
    const icons: Record<string, string> = { api: 'code', error: 'exclamation-triangle', system: 'cog' };
    return ['fas', icons[type] || 'circle'];
  }

  activityColor(type: string): string {
    const colors: Record<string, string> = { telegram: '#229ED9', api: '#3b82f6', error: '#ef4444', system: '#94a3b8' };
    return colors[type] || '#94a3b8';
  }
}
