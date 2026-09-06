import { Component, OnInit, OnDestroy, ChangeDetectionStrategy, ChangeDetectorRef, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { Subscription } from 'rxjs';
import { AdminService } from '../../../../core/services/admin.service';
import { AuthService } from '../../../../core/services/auth.service';
import { Spinner } from '../../../../shared/components/spinner/spinner';
import { Button } from '../../../../shared/components/button/button';
import { Alert } from '../../../../shared/components/alert/alert';
import { Logo } from '../../../../shared/components/logo/logo';

type TabId = 'dashboard' | 'config' | 'telegram' | 'faq' | 'webhook' | 'test';

interface TabDef {
  id: TabId;
  label: string;
  icon: [string, string];
  badge?: number;
}

@Component({
  selector: 'app-bot-panel',
  standalone: true,
  imports: [CommonModule, FormsModule, FontAwesomeModule, Spinner, Button, Alert, Logo],
  templateUrl: './bot-panel.html',
  styleUrl: './bot-panel.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class BotPanel implements OnInit, OnDestroy {
  private admin = inject(AdminService);
  private auth = inject(AuthService);
  private cdr = inject(ChangeDetectorRef);
  private subs = new Subscription();

  loading = true;
  error: string | null = null;
  debugLog: string[] = [];

  private log(msg: string, data?: any) {
    const entry = `[${new Date().toISOString()}] ${msg}`;
    this.debugLog.push(entry);
    console.log('[BotPanel DEBUG]', entry, data ?? '');
    if (data) console.log(data);
  }

  activeTab: TabId = 'dashboard';

  tabs: TabDef[] = [
    { id: 'dashboard', label: 'Resumen', icon: ['fas', 'gauge-high'] },
    { id: 'config', label: 'Configuración', icon: ['fas', 'gear'] },
    { id: 'telegram', label: 'Telegram', icon: ['fab', 'telegram'] },
    { id: 'faq', label: 'FAQ', icon: ['fas', 'book'] },
    { id: 'webhook', label: 'Webhook', icon: ['fas', 'link'] },
    { id: 'test', label: 'Pruebas', icon: ['fas', 'flask'] },
  ];

  // Bot data
  bot: any = null;
  channels: any = {};
  conversations: any[] = [];
  activity: any[] = [];

  // Config editing
  editing = false;
  editForm: any = {};
  saving = false;
  saveSuccess = '';
  saveError = '';

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
  autogrowMsg = '';
  autogrowErr = '';

  // Config toggles
  cfgAutoFaq = true;
  cfgFaqThreshold = 3;
  cfgMcpPrompt = true;
  cfgNotifySupervision = true;
  cfgIntervention = true;

  ngOnInit() {
    this.log('ngOnInit started');
    try {
      this.loadDashboard();
      this.checkAuth();
      this.log('ngOnInit completed');
    } catch (e: any) {
      this.log('ngOnInit SYNC ERROR', e);
      this.error = 'Error crítico en inicialización: ' + (e?.message || String(e));
      this.loading = false;
      this.cdr.markForCheck();
    }
  }

  ngOnDestroy() {
    this.subs.unsubscribe();
  }

  setTab(id: TabId) {
    this.activeTab = id;
    this.cdr.markForCheck();
    if (id === 'telegram' && !this.tgStatus) this.loadLinkedAccounts();
    if (id === 'webhook' && !this.webhookStatus) this.loadWebhookStatus();
    if (id === 'faq' && this.faqList.length === 0) this.loadFaq();
    if (id === 'faq' && this.proposedFaqs.length === 0) this.loadProposedFaqs();
    this.error = null;
  }

  private checkAuth() {
    const token = localStorage.getItem('access_token') || sessionStorage.getItem('access_token');
    if (!token) {
      console.warn('[BotPanel] No auth token found');
    }
  }

  loadDashboard(showLoading = true) {
    this.log('loadDashboard called', { showLoading });
    if (showLoading) {
      this.loading = true;
    }
    this.error = null;
    this.cdr.markForCheck();

    this.subs.add(
      this.admin.getBotDashboard().subscribe({
        next: (res) => {
          this.log('Dashboard loaded successfully', res);
          this.bot = res.bot;
          this.channels = res.channels || {};
          this.conversations = res.conversations || [];
          this.activity = res.activity || [];
          this.log('Data assigned', { bot: !!this.bot, channels: Object.keys(this.channels), convCount: this.conversations.length, activityCount: this.activity.length });
          const cfg = res.bot?.config;
          if (cfg) {
            this.cfgAutoFaq = cfg.auto_faq_enabled;
            this.cfgFaqThreshold = cfg.auto_faq_threshold;
            this.cfgMcpPrompt = cfg.mcp_prompt_enabled;
            this.cfgNotifySupervision = cfg.notify_supervision_enabled;
            this.cfgIntervention = cfg.intervention_enabled;
            this.log('Config toggles set', cfg);
          }
          this.loading = false;
          this.cdr.markForCheck();
          this.log('Dashboard loading complete');
        },
        error: (err) => {
          this.log('Dashboard load ERROR', { status: err?.status, statusText: err?.statusText, message: err?.message, error: err?.error });
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
    this.log('Attempting token refresh...');
    this.auth.refreshToken().subscribe({
      next: (res) => {
        this.log('Token refresh response', res);
        if (res.access_token) {
          localStorage.setItem('access_token', res.access_token);
        }
        if (res.refresh_token) {
          localStorage.setItem('refresh_token', res.refresh_token);
        }
        this.log('Token refreshed, retrying dashboard load...');
        this.loadDashboard(false);
      },
      error: (err) => {
        this.log('Token refresh failed', err);
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

  // ─── Config editing ────────────────────────────────────────────────
  startEdit() {
    this.editing = true;
    this.editForm = {
      bot_name: this.bot?.name || '',
      bot_emoji: this.bot?.emoji || '',
      persona_message: this.bot?.persona_message || '',
      system_prompt: this.bot?.system_prompt || '',
    };
    this.saveSuccess = '';
    this.saveError = '';
  }

  cancelEdit() {
    this.editing = false;
    this.editForm = {};
  }

  saveConfig() {
    this.saving = true;
    this.saveSuccess = '';
    this.saveError = '';
    this.cdr.markForCheck();
    this.subs.add(
      this.admin.updateTelegramConfig({
        bot_name: this.editForm.bot_name,
        bot_emoji: this.editForm.bot_emoji,
        persona_message: this.editForm.persona_message,
        system_prompt: this.editForm.system_prompt,
      }).subscribe({
        next: () => {
          this.bot = { ...this.bot, ...this.editForm };
          this.saving = false;
          this.editing = false;
          this.saveSuccess = 'Configuración guardada';
          this.cdr.markForCheck();
        },
        error: (err) => { this.saving = false; this.saveError = err.error?.error || 'Error al guardar'; this.cdr.markForCheck(); },
      })
    );
  }

  // ─── FAQ ────────────────────────────────────────────────────────────
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
    return conv.channel === 'telegram' && !!conv.chat_id;
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

  // ─── Config toggles save ────────────────────────────────────────────
  saveConfigToggles() {
    this.saving = true;
    this.saveSuccess = '';
    this.saveError = '';
    this.cdr.markForCheck();
    this.subs.add(
      this.admin.updateTelegramConfig({
        auto_faq_enabled: this.cfgAutoFaq,
        auto_faq_threshold: this.cfgFaqThreshold,
        mcp_prompt_enabled: this.cfgMcpPrompt,
        notify_supervision_enabled: this.cfgNotifySupervision,
        intervention_enabled: this.cfgIntervention,
      }).subscribe({
        next: () => { this.saving = false; this.saveSuccess = 'Opciones guardadas'; this.saveError = ''; this.cdr.markForCheck(); },
        error: (err) => { this.saving = false; this.saveError = err.error?.error || 'Error al guardar'; this.cdr.markForCheck(); },
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
