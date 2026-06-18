import { CommonModule } from '@angular/common';
import { Component, ElementRef, ViewChild, HostBinding, HostListener, AfterViewChecked, OnDestroy, ChangeDetectionStrategy, ChangeDetectorRef, inject, effect } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { IconProp } from '@fortawesome/fontawesome-svg-core';
import { Subscription, firstValueFrom } from 'rxjs';
import { LlamaService, ChatMessage, ActionChip } from '../../../core/services/llama.service';
import { AdminService } from '../../../core/services/admin.service';
import { WizardService } from '../../contextual-help/services/wizard.service';
import { FloatingUiService } from '../../../core/services/floating-ui.service';
import DOMPurify from 'dompurify';

const ALLOWED_REDIRECT_PREFIXES = ['/', '/admin/', '/therapist/', '/patient/', '/auth/'];

const FA_ICON_MAP: Record<string, string> = {
  'chart-line': 'chart-line',
  'users': 'users',
  'calendar': 'calendar',
  'chart-bar': 'chart-bar',
  'dollar-sign': 'dollar-sign',
  'receipt': 'receipt',
  'mobile': 'mobile-alt',
  'question-circle': 'question-circle',
  'history': 'history',
  'user-plus': 'user-plus',
  'user-doctor': 'user-md',
  'user': 'user',
  'building': 'building',
  'calendar-plus': 'calendar-plus',
  'file-alt': 'file-alt',
  'download': 'download',
  'paper-plane': 'paper-plane',
  'gamepad': 'gamepad',
  'exclamation-triangle': 'exclamation-triangle',
  'upload': 'upload',
  'key': 'key',
  'check': 'check',
  'times': 'times',
  'spinner': 'spinner',
  'search': 'search',
  'plus': 'plus',
  'trash': 'trash',
  'edit': 'edit',
  'envelope': 'envelope',
  'ban': 'ban',
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

  isOpen = false;
  fullScreen = false;
  currentMode: 'chiquito' | 'grande' = 'chiquito';
  messages: ChatMessage[] = [];
  inputMessage = '';
  loading = false;
  hasUnread = false;
  error: string | null = null;
  processingAction = false;
  actionFeedback: { type: 'success' | 'error' | 'info'; message: string } | null = null;

  suggestions: string[] = [];
  actionChips: ActionChip[] = [];
  currentPage = 'dashboard';
  welcomeMessage = '¡Hola! Soy Llama';

  private subs = new Subscription();

  constructor(
    private llama: LlamaService,
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

  get mode(): 'chiquito' | 'grande' {
    return this.fullScreen ? 'grande' : 'chiquito';
  }

  sanitize(html: string): string {
    return DOMPurify.sanitize(html, { ALLOWED_TAGS: ['b', 'i', 'em', 'strong', 'a', 'ul', 'ol', 'li', 'br', 'p'], ALLOWED_ATTR: ['href'] });
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
  }

  @HostBinding('class.fullscreen') get fullScreenClass() { return this.fullScreen; }
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
      this.currentMode = 'chiquito';
      this.cdr.markForCheck();
    } else if (this.isOpen) {
      this.togglePanel();
    }
  }

  toggleFullScreen() {
    this.fullScreen = !this.fullScreen;
    this.currentMode = this.fullScreen ? 'grande' : 'chiquito';
    this.cdr.markForCheck();
  }

  togglePanel() {
    this.isOpen = !this.isOpen;
    this.hasUnread = false;
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
    if (url.includes('/sedes')) return 'sedes';
    if (url.includes('/sessions')) return 'sessions';
    if (url.includes('/expenses')) return 'expenses';
    if (url.includes('/reports')) return 'reports';
    if (url.includes('/messages')) return 'messages';
    if (url.includes('/games')) return 'games';
    if (url.includes('/logs')) return 'logs';
    if (url.includes('/profile')) return 'profile';
    if (url.includes('/yape-import')) return 'yape-import';
    if (url.includes('/api-tokens')) return 'api-tokens';
    if (url.includes('/ai')) return 'ai';
    if (url.includes('/csp-reports')) return 'csp-reports';
    return 'dashboard';
  }

  private loadInitialContext() {
    this.currentPage = this.detectCurrentPage();
    this.subs.add(this.llama.sendMessage('context_init', this.currentPage).subscribe({
      next: (res) => {
        if (res.success) {
          this.suggestions = res.suggestions || [];
          this.actionChips = res.action_chips || [];
          if (res.response) {
            this.welcomeMessage = res.response;
          }
        }
        this.cdr.markForCheck();
      },
      error: () => {
        this.suggestions = ['Ver deudores', 'Registrar pago', 'Crear usuario', 'Ir a finanzas', 'Ver reporte'];
        this.cdr.markForCheck();
      },
    }));
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
        if (chip.target && ALLOWED_REDIRECT_PREFIXES.some(p => chip.target.startsWith(p))) {
          setTimeout(() => { window.location.href = chip.target; }, 300);
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

      case 'scroll':
        const el = document.querySelector(chip.target);
        if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
        break;

      case 'action':
        if (chip.target === 'generateReport') {
          this.inputMessage = 'Generar reporte completo';
          this.sendMessage();
        } else if (chip.target === 'exportCSV') {
          const btn = document.querySelector('button[exportCSV]') as HTMLButtonElement;
          if (btn) btn.click();
          this.pushAssistant('Exportación CSV iniciada.');
        } else {
          this.inputMessage = chip.label || chip.target;
          this.sendMessage();
        }
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

      case 'toggleUser':
        this.execToggleUser(chip);
        break;

      default:
        this.inputMessage = chip.label || chip.target || '';
        if (this.inputMessage) this.sendMessage();
        break;
    }
    this.cdr.markForCheck();
  }

  private pushAssistant(content: string) {
    this.messages.push({ role: 'assistant', content });
    this.cdr.markForCheck();
  }

  private async execToggleUser(chip: ActionChip) {
    const userId = parseInt(chip.target, 10);
    if (!userId || isNaN(userId)) return;
    this.processingAction = true;
    this.showFeedback('info', 'Cambiando estado del usuario...');
    try {
      const res: any = await firstValueFrom(this.admin.toggleUserStatus(userId));
      if (res?.success) {
        this.showFeedback('success', res.message || 'Estado actualizado');
        this.pushAssistant(`✅ Usuario actualizado: <b>${res.message || 'Estado cambiado correctamente'}</b>`);
      } else {
        this.showFeedback('error', res?.message || 'Error al cambiar estado');
        this.pushAssistant(`❌ Error: ${res?.message || 'No se pudo cambiar el estado'}`);
      }
    } catch {
      this.showFeedback('error', 'Error de conexión');
      this.pushAssistant('❌ Error de conexión con el servidor');
    }
    this.processingAction = false;
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

    if (this.currentMode === 'grande') {
      this.subs.add(this.llama.sendAgentMessage(msg, 'grande').subscribe({
        next: (res) => {
          this.loading = false;
          this.messages.push({
            role: 'assistant',
            content: res.response,
            intent: res.intent,
            action_chips: res.action_chips,
          });
          this.suggestions = res.suggestions || this.suggestions;
          this.actionChips = res.action_chips || this.actionChips;
          this.cdr.markForCheck();
        },
        error: () => {
          this.loading = false;
          this.error = 'Error de conexion con el servidor';
          this.messages.push({
            role: 'assistant',
            content: 'No se pudo conectar con el servidor',
            error: true,
          });
          this.cdr.markForCheck();
        },
      }));
    } else {
      const page = this.detectCurrentPage();

      this.subs.add(this.llama.sendMessage(msg, page).subscribe({
        next: (res) => {
          this.loading = false;
          if (res.success) {
            this.messages.push({
              role: 'assistant',
              content: res.response,
              intent: res.intent,
              action_chips: res.action_chips,
            });

            this.suggestions = res.suggestions || this.suggestions;
            this.actionChips = res.action_chips || this.actionChips;

            if (res.redirect) {
              const url = res.redirect!;
              const isAllowed = ALLOWED_REDIRECT_PREFIXES.some(p => url.startsWith(p));
              const isSameOrigin = url.startsWith(window.location.origin) || url.startsWith('/');
              if (isAllowed && isSameOrigin) {
                setTimeout(() => { window.location.href = url; }, 1500);
              }
            }
          } else {
            this.messages.push({
              role: 'assistant',
              content: 'Error al procesar tu mensaje',
            });
          }
          this.cdr.markForCheck();
        },
        error: () => {
          this.loading = false;
          this.error = 'Error de conexion con el servidor';
          this.messages.push({
            role: 'assistant',
            content: 'No se pudo conectar con el servidor',
            error: true,
          });
          this.cdr.markForCheck();
        },
      }));
    }
  }

  onFileSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    if (!input.files || input.files.length === 0) return;
    const file = input.files[0];
    const reader = new FileReader();
    reader.onload = () => {
      let content = reader.result as string;
      if (file.type === 'application/pdf' || file.name.endsWith('.docx')) {
        content = `[Archivo: ${file.name} (${(file.size / 1024).toFixed(1)} KB)]`;
      }
      this.inputMessage = content;
      this.cdr.markForCheck();
      this.sendMessage();
    };
    if (file.type.startsWith('text/') || file.type.includes('json') || file.type.includes('csv')) {
      reader.readAsText(file);
    } else {
      reader.readAsDataURL(file);
    }
    input.value = '';
  }

  private scrollToBottom() {
    try {
      if (this.scrollContainer) {
        this.scrollContainer.nativeElement.scrollTop = this.scrollContainer.nativeElement.scrollHeight;
      }
    } catch {}
  }
}
