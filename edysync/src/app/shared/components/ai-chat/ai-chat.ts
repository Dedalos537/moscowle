// DCE — Diego Centeno Estuvo Acá
import { Component, ElementRef, ViewChild, HostListener, AfterViewChecked } from '@angular/core';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { LlamaService, ChatMessage } from '../../../core/services/llama.service';

@Component({
  selector: 'app-ai-chat',
  standalone: false,
  templateUrl: './ai-chat.html',
  styleUrl: './ai-chat.scss',
})
export class AiChat implements AfterViewChecked {
  @ViewChild('scrollContainer') scrollContainer!: ElementRef;
  @ViewChild('inputEl') inputEl!: ElementRef;

  isOpen = false;
  messages: ChatMessage[] = [];
  inputMessage = '';
  loading = false;
  hasUnread = false;

  suggestions = [
    'Ver ingresos del mes',
    '¿Quiénes deben pagar esta semana?',
    'Registrar un pago',
    'Análisis financiero',
    'Estado de deudores',
  ];

  constructor(private llama: LlamaService, private sanitizer: DomSanitizer) {}

  sanitize(html: string): SafeHtml {
    return this.sanitizer.bypassSecurityTrustHtml(html);
  }

  ngAfterViewChecked() {
    this.scrollToBottom();
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
    setTimeout(() => this.inputEl?.nativeElement?.focus(), 300);
  }

  private loadHistory() {
    this.llama.getHistory().subscribe({
      next: (res) => {
        if (res.success) {
          this.messages = res.messages.map((m) => ({
            role: m.role as 'user' | 'assistant',
            content: m.content,
            intent: m.intent,
          }));
        }
      },
    });
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

    this.llama.sendMessage(msg, 'dashboard').subscribe({
      next: (res) => {
        this.loading = false;
        if (res.success) {
          this.messages.push({
            role: 'assistant',
            content: res.response,
            intent: res.intent,
          });
          if (res.redirect) {
            setTimeout(() => { window.location.href = res.redirect!; }, 1500);
          }
        } else {
          this.messages.push({
            role: 'assistant',
            content: 'Error al procesar tu mensaje',
          });
        }
      },
      error: () => {
        this.loading = false;
        this.messages.push({
          role: 'assistant',
          content: 'Error de conexion con el servidor',
        });
      },
    });
  }

  private scrollToBottom() {
    try {
      if (this.scrollContainer) {
        this.scrollContainer.nativeElement.scrollTop = this.scrollContainer.nativeElement.scrollHeight;
      }
    } catch {}
  }
}
