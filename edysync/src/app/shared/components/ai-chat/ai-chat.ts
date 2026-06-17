import { Component, ElementRef, ViewChild, HostListener, AfterViewChecked, OnDestroy, ChangeDetectionStrategy, ChangeDetectorRef, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { IconProp } from '@fortawesome/fontawesome-svg-core';
import { Subscription } from 'rxjs';
import { LlamaService, ChatMessage, ActionChip } from '../../../core/services/llama.service';
import { WizardService } from '../../contextual-help/services/wizard.service';
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
};

@Component({
  selector: 'app-ai-chat',
  standalone: true,
  imports: [FormsModule, FontAwesomeModule],
  templateUrl: './ai-chat.html',
  styleUrl: './ai-chat.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AiChat implements AfterViewChecked, OnDestroy {
  @ViewChild('scrollContainer') scrollContainer!: ElementRef;
  @ViewChild('inputEl') inputEl!: ElementRef;

  private wizardService = inject(WizardService);

  isOpen = false;
  messages: ChatMessage[] = [];
  inputMessage = '';
  loading = false;
  hasUnread = false;
  error: string | null = null;

  suggestions: string[] = [];
  actionChips: ActionChip[] = [];
  currentPage = 'dashboard';

  private subs = new Subscription();

  constructor(
    private llama: LlamaService,
    private cdr: ChangeDetectorRef,
  ) {}

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

  @HostListener('document:keydown.escape')
  onEscape() {
    if (this.isOpen) this.togglePanel();
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
          if (res.response && res.intent === 'general_chat') {
            this.messages.push({
              role: 'assistant',
              content: res.response,
              action_chips: res.action_chips,
            });
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

  handleActionChip(chip: ActionChip) {
    switch (chip.type) {
      case 'navigation':
        if (chip.target && ALLOWED_REDIRECT_PREFIXES.some(p => chip.target.startsWith(p))) {
          setTimeout(() => { window.location.href = chip.target; }, 300);
        }
        break;
      case 'wizard':
        this.wizardService.resetAll();
        setTimeout(() => { this.wizardService.start(); }, 500);
        break;
      case 'modal':
        this.messages.push({
          role: 'assistant',
          content: `Para <b>${chip.label.toLowerCase()}</b>, te redirijo a la página correspondiente donde podrás completar la acción.`,
        });
        break;
      case 'scroll':
        const el = document.querySelector(chip.target);
        if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
        break;
      case 'filter':
        this.messages.push({
          role: 'assistant',
          content: `Filtrando por: <b>${chip.label}</b>...`,
        });
        break;
      case 'action':
        if (chip.target === 'generateReport') {
          this.inputMessage = 'Generar reporte completo';
          this.sendMessage();
        } else if (chip.target === 'exportCSV') {
          const btn = document.querySelector('button[exportCSV]') as HTMLButtonElement;
          if (btn) btn.click();
          this.messages.push({
            role: 'assistant',
            content: 'Exportación CSV iniciada.',
          });
        }
        break;
    }
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

  private scrollToBottom() {
    try {
      if (this.scrollContainer) {
        this.scrollContainer.nativeElement.scrollTop = this.scrollContainer.nativeElement.scrollHeight;
      }
    } catch {}
  }
}
