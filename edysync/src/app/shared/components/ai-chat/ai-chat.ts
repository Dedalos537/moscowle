import { CommonModule } from '@angular/common';
import {
  Component, ElementRef, ViewChild, HostBinding, HostListener,
  AfterViewChecked, OnDestroy, ChangeDetectionStrategy, ChangeDetectorRef, inject, effect,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { IconProp } from '@fortawesome/fontawesome-svg-core';
import { Subscription } from 'rxjs';
import { AdminService } from '../../../core/services/admin.service';
import { WizardService } from '../../contextual-help/services/wizard.service';
import { FloatingUiService } from '../../../core/services/floating-ui.service';
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

interface ActionChip {
  id: string;
  type: string;
  label: string;
  icon: string;
  target?: string;
}

const FA_ICON_MAP: Record<string, string> = {
  'chart-line': 'chart-line',
  users: 'users',
  calendar: 'calendar',
  'chart-bar': 'chart-bar',
  'dollar-sign': 'dollar-sign',
  receipt: 'receipt',
  mobile: 'mobile-alt',
  'question-circle': 'question-circle',
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
};

@Component({
  selector: 'app-ai-chat',
  standalone: true,
  imports: [CommonModule, FormsModule, FontAwesomeModule],
  templateUrl: './ai-chat.html',
  styleUrl: './ai-chat.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AiChat implements AfterViewChecked, OnDestroy {
  @ViewChild('scrollContainer') scrollContainer!: ElementRef;
  @ViewChild('inputEl') inputEl!: ElementRef;

  private wizardService = inject(WizardService);
  private floatingUi = inject(FloatingUiService);
  private abortCtrl: AbortController | null = null;

  isOpen = false;
  fullScreen = false;
  messages: ChatMsg[] = [];
  inputMessage = '';
  loading = false;
  hasUnread = false;
  error: string | null = null;
  processingAction = false;
  actionFeedback: { type: 'success' | 'error' | 'info'; message: string } | null = null;

  suggestions: string[] = [];
  actionChips: ActionChip[] = [];
  currentPage = 'dashboard';
  welcomeMessage = '¡Hola! Soy tu asistente IA';

  private pendingFilePreview: string | null = null;
  private subs = new Subscription();

  constructor(
    private admin: AdminService,
    private cdr: ChangeDetectorRef,
  ) {
    effect(() => {
      if (this.floatingUi.hidden() && this.isOpen) {
        this.isOpen = false;
        this.fullScreen = false;
        this.cdr.markForCheck();
      }
    });
  }

  get currentMode(): 'chiquito' | 'grande' {
    return this.fullScreen ? 'grande' : 'chiquito';
  }

  sanitize(html: string): string {
    return DOMPurify.sanitize(html, {
      ALLOWED_TAGS: ['b', 'i', 'em', 'strong', 'a', 'ul', 'ol', 'li', 'br', 'p'],
      ALLOWED_ATTR: ['href'],
    });
  }

  getIcon(iconName: string): IconProp {
    const mapped = FA_ICON_MAP[iconName] || iconName;
    return ['fas', mapped] as IconProp;
  }

  ngAfterViewChecked() {
    this.scrollToBottom();
  }

  ngOnDestroy() {
    this.subs.unsubscribe();
    this.abortCtrl?.abort();
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
    }
    if (this.isOpen && this.messages.length === 0) {
      this.loadInitialContext();
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
    this.suggestions = [
      '¿Cuántas sesiones hay hoy?',
      'Ver incidencias abiertas',
      'Crear sesión para un paciente',
      'Ver reporte semanal',
    ];
    this.welcomeMessage = '¡Hola! Soy tu asistente IA';
    this.cdr.markForCheck();
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

  handleActionChip(chip: ActionChip) {
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
        this.messages.push({
          role: 'assistant',
          content: 'Acción cancelada. ¿Necesitas ayuda con algo más?',
        });
        this.cdr.markForCheck();
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
    this.cdr.markForCheck();
  }

  sendMessage() {
    const msg = this.inputMessage.trim();
    if (!msg || this.loading) return;

    this.messages.push({ role: 'user', content: msg });
    this.inputMessage = '';
    this.loading = true;
    this.error = null;
    this.cdr.markForCheck();

    this.abortCtrl?.abort();
    this.abortCtrl = new AbortController();

    const apiUrl = this.getApiUrl();
    const mode = this.currentMode;

    fetch(`${apiUrl}/mcp/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: msg,
        mode,
        history: this.messages.slice(-10).map((m) => ({ role: m.role, content: m.content })),
      }),
      signal: this.abortCtrl.signal,
    })
      .then((resp) => {
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const reader = resp.body!.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let assistantText = '';
        let toolCalls: ToolCallResult[] = [];

        const processChunk = (): void => {
          reader.read().then(({ done, value }) => {
            if (done) {
              this.loading = false;
              if (assistantText) {
                this.pushAssistant(assistantText, toolCalls.length > 0 ? toolCalls : undefined);
              }
              this.cdr.markForCheck();
              return;
            }

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';

            for (const line of lines) {
              if (!line.startsWith('data: ')) continue;
              try {
                const event = JSON.parse(line.slice(6));
                if (event.type === 'chunk') {
                  assistantText += event.content;
                  this.updateLastAssistant(assistantText, toolCalls);
                } else if (event.type === 'tool_start') {
                  toolCalls.push({
                    name: event.tool,
                    args: event.args || {},
                    result: '',
                    success: false,
                  });
                  this.updateLastAssistant(assistantText, toolCalls);
                } else if (event.type === 'tool_result') {
                  if (toolCalls.length > 0) {
                    const tc = toolCalls[toolCalls.length - 1];
                    tc.result = event.result || '';
                    tc.success = event.success ?? true;
                  }
                  this.updateLastAssistant(assistantText, toolCalls);
                } else if (event.type === 'done') {
                  this.loading = false;
                  if (assistantText) {
                    this.pushAssistant(assistantText, toolCalls.length > 0 ? toolCalls : undefined);
                    assistantText = '';
                    toolCalls = [];
                  }
                } else if (event.type === 'error') {
                  this.loading = false;
                  this.error = event.error;
                  this.pushAssistant('Error: ' + (event.error || 'Error desconocido'));
                }
              } catch {
                // skip malformed lines
              }
            }
            this.cdr.markForCheck();
            processChunk();
          });
        };

        processChunk();
      })
      .catch((err) => {
        if (err.name === 'AbortError') return;
        this.loading = false;
        this.error = 'Error de conexión';
        this.pushAssistant('No se pudo conectar con el servidor');
        this.cdr.markForCheck();
      });
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

    const reader = new FileReader();
    reader.onload = () => {
      this.inputMessage = `[Archivo: ${file.name} (${(file.size / 1024).toFixed(1)} KB)]`;
      this.cdr.markForCheck();
      this.sendMessage();
    };
    reader.readAsText(file);
    input.value = '';
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
