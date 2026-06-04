import { Component, ElementRef, ViewChild, HostListener, AfterViewChecked, OnDestroy, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { Subscription } from 'rxjs';
import { LlamaService, ChatMessage } from '../../../core/services/llama.service';
import DOMPurify from 'dompurify';

const ALLOWED_REDIRECT_PREFIXES = ['/', '/admin/', '/therapist/', '/patient/', '/auth/'];

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

  isOpen = false;
  messages: ChatMessage[] = [];
  inputMessage = '';
  loading = false;
  hasUnread = false;
  error: string | null = null;

  suggestions = [
    'Ver ingresos del mes',
    '¿Quiénes deben pagar esta semana?',
    'Registrar un pago',
    'Análisis financiero',
    'Estado de deudores',
  ];

  private subs = new Subscription();

  constructor(
    private llama: LlamaService,
    private cdr: ChangeDetectorRef,
  ) {}

  sanitize(html: string): string {
    return DOMPurify.sanitize(html, { ALLOWED_TAGS: ['b', 'i', 'em', 'strong', 'a', 'ul', 'ol', 'li', 'br', 'p'], ALLOWED_ATTR: ['href'] });
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
      this.loadHistory();
    }
    this.cdr.markForCheck();
    setTimeout(() => this.inputEl?.nativeElement?.focus(), 300);
  }

  private loadHistory() {
    this.subs.add(this.llama.getHistory().subscribe({
      next: (res) => {
        if (res.success) {
          this.messages = res.messages.map((m) => ({
            role: m.role as 'user' | 'assistant',
            content: m.content,
            intent: m.intent,
          }));
        }
        this.cdr.markForCheck();
      },
    }));
  }

  sendSuggestion(text: string) {
    this.inputMessage = text;
    this.sendMessage();
  }

  sendMessage() {
    const msg = this.inputMessage.trim();
    if (!msg || this.loading) return;

    this.messages.push({ role: 'user', content: msg });
    this.inputMessage = '';
    this.loading = true;
    this.error = null;
    this.cdr.markForCheck();

    this.subs.add(this.llama.sendMessage(msg, 'dashboard').subscribe({
      next: (res) => {
        this.loading = false;
        if (res.success) {
          this.messages.push({
            role: 'assistant',
            content: res.response,
            intent: res.intent,
          });
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
          content: 'Error de conexion con el servidor',
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
