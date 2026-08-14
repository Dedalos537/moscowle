import { CommonModule } from '@angular/common';
import {
  Component, ElementRef, ViewChild, HostBinding, HostListener,
  AfterViewChecked, OnDestroy, ChangeDetectionStrategy, ChangeDetectorRef, inject,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { IconProp } from '@fortawesome/fontawesome-svg-core';
import { Subscription } from 'rxjs';
import { AdminService } from '../../../core/services/admin.service';
import { WizardService } from '../../contextual-help/services/wizard.service';
import { FloatingUiService } from '../../../core/services/floating-ui.service';
import { McpChatService, McpChip, McpPendingConfirm, McpStreamEvent } from '../../../core/services/mcp-chat.service';
import { ChatSessionService, ChatSession, ChatSessionMessage } from '../../../core/services/chat-session.service';
import { ChatConfirmDialog, PendingAction } from '../chat-confirm-dialog/chat-confirm-dialog';
import { environment } from '../../../../environments/environment';
import DOMPurify from 'dompurify';

const ALLOWED_REDIRECT_PREFIXES = ['/', '/admin/', '/therapist/', '/patient/', '/auth/'];

interface ChatMsg {
  id?: number;
  role: 'user' | 'assistant';
  content: string;
  intent?: string;
  error?: boolean;
  filePreview?: string;
  toolCalls?: ToolCallResult[];
}

interface ToolCallResult {
  name: string;
  args: Record<string, unknown>;
  result: string;
  success: boolean;
}

type VoiceState = 'idle' | 'recording' | 'transcribing' | 'unsupported';

const FA_ICON_MAP: Record<string, string> = {
  'chart-line': 'chart-line',
  users: 'users',
  calendar: 'calendar',
  'chart-bar': 'chart-bar',
  'dollar-sign': 'dollar-sign',
  receipt: 'receipt',
  mobile: 'mobile-alt',
  'question-circle': 'question-circle',
  'exclamation-circle': 'exclamation-circle',
  'info-circle': 'info-circle',
  history: 'history',
  'user-plus': 'user-plus',
  'user-doctor': 'user-md',
  user: 'user',
  building: 'building',
  'calendar-plus': 'calendar-plus',
  'file-alt': 'file-alt',
  download: 'download',
  'paper-plane': 'paper-plane',
  gamepad: 'gamepad',
  'exclamation-triangle': 'exclamation-triangle',
  upload: 'upload',
  key: 'key',
  check: 'check',
  times: 'times',
  spinner: 'spinner',
  search: 'search',
  plus: 'plus',
  trash: 'trash',
  edit: 'edit',
  envelope: 'envelope',
  ban: 'ban',
  'toggle-on': 'toggle-on',
  wallet: 'wallet',
  wrench: 'wrench',
};

@Component({
  selector: 'app-ai-chat',
  standalone: true,
  imports: [CommonModule, FormsModule, FontAwesomeModule, ChatConfirmDialog],
  templateUrl: './ai-chat.html',
  styleUrl: './ai-chat.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AiChat implements AfterViewChecked, OnDestroy {
  @ViewChild('scrollContainer') scrollContainer!: ElementRef;
  @ViewChild('inputEl') inputEl!: ElementRef;
  @ViewChild('confirmDialog') confirmDialog!: ChatConfirmDialog;

  private wizardService = inject(WizardService);
  private floatingUi = inject(FloatingUiService);
  private mcpChat = inject(McpChatService);
  private sessionStore = inject(ChatSessionService);
  private abortCtrl: AbortController | null = null;
  private streamSub: Subscription | null = null;

  isOpen = false;
  fullScreen = false;
  messages: ChatMsg[] = [];
  inputMessage = '';
  loading = false;
  hasUnread = false;
  error: string | null = null;
  processingAction = false;
  uploading = false;
  actionFeedback: { type: 'success' | 'error' | 'info'; message: string } | null = null;
  thinkingText = '';

  voiceState: VoiceState = 'idle';
  recordingTime = 0;
  private mediaRecorder: MediaRecorder | null = null;
  private audioChunks: Blob[] = [];
  private mediaStream: MediaStream | null = null;
  private recordingTimer: ReturnType<typeof setInterval> | null = null;

  suggestions: string[] = [];
  actionChips: McpChip[] = [];
  currentPage = 'dashboard';
  welcomeMessage = '¡Hola! Soy tu asistente IA';

  sessions: ChatSession[] = [];
  activeSessionId: string | null = null;
  showSessionList = false;

  pendingAction: McpPendingConfirm | null = null;

  private lastRequest: { message: string; history: { role: string; content: string }[] } | null = null;
  private assistantText = '';
  private streamToolCalls: ToolCallResult[] = [];

  private pendingFilePreview: string | null = null;
  private subs = new Subscription();

  constructor(
    private admin: AdminService,
    private cdr: ChangeDetectorRef,
  ) {
    // NOTE: no auto-close effect on floatingUi.hidden(). The chat's own confirm
    // dialog (an <app-modal> child) would flip hidden=true and destroy this panel
    // mid-confirmation. Visual hiding is handled by the .floating-ui--hidden CSS
    // class when OTHER overlays cover the screen; state is preserved.
    const state = this.sessionStore.load();
    this.sessions = state.sessions;
    this.activeSessionId = state.activeId;
  }

  get currentMode(): 'chiquito' | 'grande' {
    return this.fullScreen ? 'grande' : 'chiquito';
  }

  sanitize(html: string): string {
    const rendered = this.markdownToHtml(html);
    return DOMPurify.sanitize(rendered, {
      ALLOWED_TAGS: ['b', 'i', 'em', 'strong', 'a', 'ul', 'ol', 'li', 'br', 'p', 'h3', 'h4'],
      ALLOWED_ATTR: ['href'],
    });
  }

  private markdownToHtml(text: string): string {
    if (!text) return '';
    let html = text
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.+?)\*/g, '<em>$1</em>')
      .replace(/`(.+?)`/g, '<code>$1</code>');
    const lines = html.split('\n');
    const processed: string[] = [];
    let inList = false;
    for (const line of lines) {
      const trimmed = line.trim();
      if (/^[-•]\s/.test(trimmed)) {
        if (!inList) { processed.push('<ul>'); inList = true; }
        processed.push(`<li>${trimmed.replace(/^[-•]\s+/, '')}</li>`);
      } else {
        if (inList) { processed.push('</ul>'); inList = false; }
        processed.push(trimmed ? `<p>${trimmed}</p>` : '');
      }
    }
    if (inList) processed.push('</ul>');
    return processed.join('');
  }

  getIcon(iconName: string): IconProp {
    const mapped = FA_ICON_MAP[iconName] || iconName;
    return ['fas', mapped] as IconProp;
  }

  ngAfterViewChecked() {
    this.scrollToBottom();
  }

  ngOnDestroy() {
    this.persistCurrentSession();
    this.subs.unsubscribe();
    this.streamSub?.unsubscribe();
    this.abortCtrl?.abort();
    this.clearRecordingTimer();
    this.stopMediaTracks();
    if (this.mediaRecorder) {
      this.mediaRecorder.onstop = null;
      try { this.mediaRecorder.stop(); } catch { /* ignore */ }
      this.mediaRecorder = null;
    }
  }

  @HostBinding('class.fullscreen') get fullScreenClass() {
    return this.fullScreen;
  }
  @HostBinding('class.floating-ui') readonly floatingUiClass = true;
  @HostBinding('class.floating-ui--hidden') get floatingHidden() {
    return this.floatingUi.hidden();
  }
  @HostBinding('style.bottom.px') get hostBottom() {
    return this.fullScreen ? null : this.floatingUi.rightBaseBottom();
  }
  @HostBinding('style.right.px') get hostRight() {
    return this.fullScreen ? null : this.floatingUi.rightInset();
  }

  @HostListener('document:keydown.escape')
  onEscape() {
    if (this.fullScreen) {
      this.fullScreen = false;
      this.cdr.markForCheck();
    } else if (this.isOpen) {
      this.togglePanel();
    }
  }

  toggleFullScreen() {
    this.fullScreen = !this.fullScreen;
    this.cdr.markForCheck();
  }

  togglePanel() {
    this.isOpen = !this.isOpen;
    this.hasUnread = false;
    if (!this.isOpen) {
      this.fullScreen = false;
      this.showSessionList = false;
      this.persistCurrentSession();
    }
    if (this.isOpen) {
      this.currentPage = this.detectCurrentPage();
      this.ensureActiveSession();
      this.restoreActiveSession();
      if (this.messages.length === 0) {
        this.loadInitialContext();
      } else {
        this.suggestions = this.pageSuggestions();
      }
    }
    this.cdr.markForCheck();
    setTimeout(() => this.inputEl?.nativeElement?.focus(), 300);
  }

  private detectCurrentPage(): string {
    const url = window.location.pathname;
    if (url.includes('/finanzas')) return 'finanzas';
    if (url.includes('/payments')) return 'payments';
    if (url.includes('/users')) return 'users';
    if (url.includes('/sessions')) return 'sessions';
    if (url.includes('/reports')) return 'reports';
    if (url.includes('/games')) return 'games';
    return 'dashboard';
  }

  private getApiUrl(): string {
    return environment.apiBaseUrl;
  }

  private loadInitialContext() {
    this.currentPage = this.detectCurrentPage();
    this.suggestions = this.pageSuggestions();
    this.welcomeMessage = '¡Hola! Soy tu asistente IA';
    this.cdr.markForCheck();
  }

  private pageSuggestions(): string[] {
    switch (this.currentPage) {
      case 'finanzas':
        return ['Resumen financiero del mes', 'Mostrar deudores del mes', 'Comparar este mes con el anterior'];
      case 'payments':
        return ['Ver historial de pagos de un paciente', 'Registrar un pago', 'Mostrar deudores del mes'];
      case 'users':
        return ['Buscar un paciente', 'Crear un usuario', 'Listar usuarios por rol'];
      case 'sessions':
        return ['¿Cuántas sesiones hay hoy?', 'Crear sesión para un paciente', 'Sesiones de esta semana'];
      case 'reports':
        return ['Generar reporte semanal', 'Ver reporte del mes', 'Eficiencia de terapeutas'];
      case 'games':
        return ['Ver juegos disponibles', 'Progreso de un paciente'];
      default:
        return ['¿Cuántas sesiones hay hoy?', 'Ver incidencias abiertas', 'Resumen financiero del mes', 'Buscar un paciente'];
    }
  }

  sendSuggestion(text: string) {
    this.inputMessage = text;
    this.sendMessage();
  }

  private showFeedback(type: 'success' | 'error' | 'info', message: string) {
    this.actionFeedback = { type, message };
    this.cdr.markForCheck();
    setTimeout(() => {
      this.actionFeedback = null;
      this.cdr.markForCheck();
    }, 4000);
  }

  handleActionChip(chip: McpChip) {
    if (this.processingAction) return;

    switch (chip.type) {
      case 'navigation':
        if (chip.target && ALLOWED_REDIRECT_PREFIXES.some((p) => chip.target!.startsWith(p))) {
          setTimeout(() => {
            window.location.href = chip.target!;
          }, 300);
        }
        break;
      case 'wizard':
        this.isOpen = false;
        this.cdr.markForCheck();
        setTimeout(() => {
          this.wizardService.resetAll();
          this.wizardService.start();
          setTimeout(() => {
            this.isOpen = true;
            this.cdr.markForCheck();
          }, 1500);
        }, 400);
        break;
      case 'scroll': {
        const el = document.querySelector(chip.target!);
        if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
        break;
      }
      case 'action':
        this.inputMessage = chip.label || chip.target || '';
        if (this.inputMessage) this.sendMessage();
        break;
      case 'confirm':
        this.inputMessage = chip.label || 'Sí, confirmar';
        this.sendMessage();
        break;
      case 'cancel':
        this.pushAssistant('Acción cancelada. ¿Necesitas ayuda con algo más?');
        break;
      default:
        this.inputMessage = chip.label || chip.target || '';
        if (this.inputMessage) this.sendMessage();
        break;
    }
    this.cdr.markForCheck();
  }

  private pushAssistant(content: string, toolCalls?: ToolCallResult[]) {
    this.messages.push({ role: 'assistant', content, toolCalls });
    this.persistCurrentSession();
    this.cdr.markForCheck();
  }

  private updateThinking(text: string) {
    this.thinkingText = text;
    this.cdr.markForCheck();
  }

  private clearThinking() {
    this.thinkingText = '';
    this.cdr.markForCheck();
  }

  private ensureActiveSession() {
    if (this.activeSessionId && this.sessions.some((s) => s.id === this.activeSessionId)) return;
    const session = this.sessionStore.createSession();
    this.sessions.unshift(session);
    this.activeSessionId = session.id;
    this.persistSessionList();
  }

  private restoreActiveSession() {
    const active = this.sessions.find((s) => s.id === this.activeSessionId);
    this.messages = active ? active.messages.map((m) => ({ ...m })) : [];
  }

  toggleSessionList() {
    if (this.loading || this.processingAction) return;
    this.showSessionList = !this.showSessionList;
    if (this.showSessionList) {
      this.persistCurrentSession();
    }
    this.cdr.markForCheck();
  }

  newSession() {
    if (this.loading || this.processingAction) return;
    this.resetChatState();
    this.activeSessionId = null;
    this.ensureActiveSession();
    this.showSessionList = false;
    this.loadInitialContext();
    this.cdr.markForCheck();
  }

  switchSession(id: string) {
    if (id === this.activeSessionId) {
      this.showSessionList = false;
      this.cdr.markForCheck();
      return;
    }
    if (this.loading || this.processingAction) return;
    this.persistCurrentSession();
    this.resetChatState();
    this.activeSessionId = id;
    this.restoreActiveSession();
    this.suggestions = this.pageSuggestions();
    this.showSessionList = false;
    this.cdr.markForCheck();
  }

  deleteSession(event: Event, id: string) {
    event.stopPropagation();
    if (this.loading || this.processingAction) return;
    this.sessions = this.sessions.filter((s) => s.id !== id);
    if (this.activeSessionId === id) {
      this.resetChatState();
      this.activeSessionId = this.sessions[0]?.id ?? null;
      this.restoreActiveSession();
      if (this.messages.length === 0) this.loadInitialContext();
    }
    this.persistSessionList();
    this.cdr.markForCheck();
  }

  private resetChatState() {
    this.streamSub?.unsubscribe();
    this.abortCtrl?.abort();
    this.messages = [];
    this.inputMessage = '';
    this.actionChips = [];
    this.error = null;
    this.loading = false;
    this.processingAction = false;
    this.pendingAction = null;
    this.assistantText = '';
    this.streamToolCalls = [];
    this.thinkingText = '';
  }

  private persistCurrentSession() {
    const session = this.sessions.find((s) => s.id === this.activeSessionId);
    if (!session) return;
    const messages: ChatSessionMessage[] = this.messages.map((m) => ({
      role: m.role,
      content: m.content,
      ...(m.intent ? { intent: m.intent } : {}),
      ...(m.error ? { error: m.error } : {}),
      ...(m.filePreview ? { filePreview: m.filePreview } : {}),
      ...(m.toolCalls && m.toolCalls.length > 0 ? { toolCalls: m.toolCalls } : {}),
    }));
    session.messages = messages;
    session.updatedAt = Date.now();
    if (!session.title || session.title === 'Nueva conversación') {
      const firstUser = messages.find((m) => m.role === 'user');
      if (firstUser) session.title = this.makeSessionTitle(firstUser.content);
    }
    this.persistSessionList();
  }

  private makeSessionTitle(content: string): string {
    const clean = content.replace(/\s+/g, ' ').trim();
    return clean.length > 40 ? clean.slice(0, 40) + '…' : clean;
  }

  private persistSessionList() {
    this.sessionStore.save({ sessions: this.sessions, activeId: this.activeSessionId });
  }

  sendMessage() {
    const msg = this.inputMessage.trim();
    if (!msg || this.loading || this.processingAction) return;

    this.messages.push({ role: 'user', content: msg });
    this.inputMessage = '';
    this.persistCurrentSession();
    const history = this.messages.slice(0, -1).slice(-8).map((m) => ({ role: m.role, content: m.content }));
    this.lastRequest = { message: msg, history };
    this.streamToServer(msg, history, undefined);
  }

  private streamToServer(message: string, history: { role: string; content: string }[], confirmed?: McpPendingConfirm) {
    this.loading = true;
    this.error = null;
    this.actionChips = [];
    this.assistantText = '';
    this.streamToolCalls = [];
    this.cdr.markForCheck();

    this.streamSub?.unsubscribe();
    this.abortCtrl?.abort();
    this.abortCtrl = new AbortController();

    this.streamSub = this.mcpChat
      .stream({
        message,
        mode: this.currentMode,
        history,
        confirmed_tool: confirmed,
        conversation_id: this.activeSessionId || undefined,
        signal: this.abortCtrl.signal,
      })
      .subscribe({
        next: (event) => this.handleStreamEvent(event),
      });
  }

  private handleStreamEvent(event: McpStreamEvent) {
    switch (event.type) {
      case 'thinking':
        this.updateThinking(event.content || 'Procesando...');
        break;

      case 'chunk':
      case 'text':
        if (event.content) {
          this.assistantText += event.content;
          this.clearThinking();
          this.updateLastAssistant(this.assistantText, this.streamToolCalls);
        }
        break;

      case 'tool_call':
        this.streamToolCalls.push({
          name: event.name || '',
          args: event.args || {},
          result: '',
          success: false,
        });
        this.updateLastAssistant(this.assistantText, this.streamToolCalls);
        break;

      case 'tool_result':
        if (this.streamToolCalls.length > 0) {
          const tc = this.streamToolCalls[this.streamToolCalls.length - 1];
          tc.result = event.result || '';
          tc.success = event.success !== false;
        }
        this.updateLastAssistant(this.assistantText, this.streamToolCalls);
        break;

      case 'chips':
        this.actionChips = event.chips || [];
        this.cdr.markForCheck();
        break;

      case 'confirm': {
        const pending = event.pending_confirm || {
          name: event.name || '',
          args: event.args || {},
          tool_call_text: event.tool_call_text,
        };
        if (pending?.name) {
          this.loading = false;
          this.processingAction = true;
          this.pendingAction = pending;
          this.cdr.markForCheck();
          setTimeout(() => this.confirmDialog?.open(pending));
        }
        break;
      }

      case 'done':
        this.loading = false;
        this.clearThinking();
        if (event.pending_confirm?.name && !this.processingAction) {
          this.processingAction = true;
          this.pendingAction = event.pending_confirm;
          this.cdr.markForCheck();
          setTimeout(() => this.confirmDialog?.open(event.pending_confirm!));
        }
        this.assistantText = '';
        this.streamToolCalls = [];
        this.persistCurrentSession();
        this.cdr.markForCheck();
        break;

      case 'error':
        this.loading = false;
        this.clearThinking();
        this.error = event.error || 'Error desconocido';
        this.pushAssistant('Error: ' + (event.error || 'Error desconocido'));
        this.persistCurrentSession();
        break;
    }
  }

  onConfirmAction(action: PendingAction) {
    this.processingAction = false;
    this.pendingAction = null;
    this.cdr.markForCheck();
    if (this.lastRequest) {
      this.streamToServer(this.lastRequest.message, this.lastRequest.history, action);
    }
  }

  onCancelConfirm() {
    this.processingAction = false;
    this.pendingAction = null;
    this.pushAssistant('Acción cancelada. ¿Necesitas ayuda con algo más?');
    this.cdr.markForCheck();
  }

  private updateLastAssistant(content: string, toolCalls: ToolCallResult[]) {
    const last = this.messages[this.messages.length - 1];
    if (last && last.role === 'assistant') {
      last.content = content;
      last.toolCalls = toolCalls.length > 0 ? [...toolCalls] : undefined;
    } else {
      this.messages.push({
        role: 'assistant',
        content,
        toolCalls: toolCalls.length > 0 ? [...toolCalls] : undefined,
      });
    }
    this.cdr.markForCheck();
  }

  onFileSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    if (!input.files || input.files.length === 0) return;
    const file = input.files[0];

    this.uploading = true;
    this.cdr.markForCheck();

    const formData = new FormData();
    formData.append('file', file);

    const apiUrl = this.getApiUrl();
    fetch(`${apiUrl}/mcp/upload`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('access_token') || ''}`,
      },
      body: formData,
    })
      .then(resp => resp.json())
      .then(data => {
        this.uploading = false;
        if (data.success) {
          if (data.ocr) {
            const o = data.ocr;
            const parts = [];
            if (o.patient_hint) parts.push(`Paciente: ${o.patient_hint}`);
            if (o.amount) parts.push(`Monto: S/${o.amount}`);
            if (o.method) parts.push(`Método: ${o.method}`);
            if (o.date) parts.push(`Fecha: ${o.date}`);
            if (o.reference) parts.push(`Ref: ${o.reference}`);
            const ocrText = parts.length > 0 ? parts.join(' - ') : 'No se pudieron leer datos';
            this.inputMessage = `Voucher detectado: ${ocrText}. Imagen: ${data.url}. ¿Registrar este pago? Si los datos son incorrectos, indíqueme los correctos.`;
          } else {
            this.inputMessage = `Imagen subida: ${data.url}. No pude leer el comprobante. Por favor indique: paciente, monto, método y fecha.`;
          }
          this.sendMessage();
        } else {
          this.inputMessage = `Error al subir: ${data.error}`;
        }
        this.cdr.markForCheck();
      })
      .catch(err => {
        this.uploading = false;
        this.inputMessage = `Error de red al subir archivo`;
        this.cdr.markForCheck();
      });

    input.value = '';
  }

  toggleVoice() {
    if (this.voiceState === 'recording') {
      this.stopVoice();
    } else if (this.voiceState === 'idle' || this.voiceState === 'unsupported') {
      this.startVoice();
    }
  }

  startVoice() {
    if (typeof MediaRecorder === 'undefined' || !navigator.mediaDevices?.getUserMedia) {
      this.voiceState = 'unsupported';
      this.showFeedback('error', 'Tu navegador no soporta grabación de voz');
      this.cdr.markForCheck();
      return;
    }

    navigator.mediaDevices.getUserMedia({ audio: true })
      .then(stream => {
        this.mediaStream = stream;
        this.mediaRecorder = new MediaRecorder(stream);
        this.audioChunks = [];
        this.recordingTime = 0;
        this.voiceState = 'recording';
        this.mediaRecorder.ondataavailable = (event) => {
          if (event.data.size > 0) {
            this.audioChunks.push(event.data);
          }
        };
        this.mediaRecorder.start();
        this.showFeedback('info', 'Grabando... Habla ahora');
        this.recordingTimer = setInterval(() => {
          this.recordingTime++;
          this.cdr.markForCheck();
        }, 1000);
        this.cdr.markForCheck();
      })
      .catch(() => {
        this.voiceState = 'unsupported';
        this.showFeedback('error', 'Tu navegador no soporta grabación de voz');
        this.cdr.markForCheck();
      });
  }

  stopVoice() {
    if (this.voiceState !== 'recording' || !this.mediaRecorder) return;

    const recorder = this.mediaRecorder;
    this.voiceState = 'transcribing';
    this.cdr.markForCheck();

    recorder.onstop = () => {
      const blob = new Blob(this.audioChunks, { type: recorder.mimeType || 'audio/webm' });
      this.transcribeAudio(blob);
    };
    recorder.stop();
  }

  private transcribeAudio(blob: Blob) {
    const formData = new FormData();
    formData.append('audio', blob, 'voice.webm');

    const apiUrl = this.getApiUrl();
    fetch(`${apiUrl}/mcp/transcribe`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('access_token') || ''}`,
      },
      body: formData,
    })
      .then(resp => resp.json())
      .then(data => {
        if (data.success && data.text) {
          this.inputMessage = data.text;
          this.cdr.markForCheck();
          this.sendMessage();
        } else {
          this.showFeedback('error', data.error || 'No se pudo transcribir el audio');
        }
      })
      .catch(() => {
        this.showFeedback('error', 'Error de red al transcribir el audio');
      })
      .finally(() => {
        this.resetVoiceState();
      });
  }

  private resetVoiceState() {
    this.voiceState = 'idle';
    this.recordingTime = 0;
    this.clearRecordingTimer();
    this.stopMediaTracks();
    this.mediaRecorder = null;
    this.audioChunks = [];
    this.cdr.markForCheck();
  }

  private clearRecordingTimer() {
    if (this.recordingTimer) {
      clearInterval(this.recordingTimer);
      this.recordingTimer = null;
    }
  }

  private stopMediaTracks() {
    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach(track => track.stop());
      this.mediaStream = null;
    }
  }

  private scrollToBottom() {
    try {
      if (this.scrollContainer) {
        const el = this.scrollContainer.nativeElement;
        el.scrollTop = el.scrollHeight;
      }
    } catch {
      // ignore
    }
  }
}
