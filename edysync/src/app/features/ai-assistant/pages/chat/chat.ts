import { Component, OnInit, ViewChild, ElementRef, OnDestroy, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { Subscription } from 'rxjs';
import { HeaderService } from '../../../../core/services/header.service';
import { environment } from '../../../../../environments/environment';

interface ChatMessage {
  role: 'user' | 'assistant' | 'tool_call' | 'tool_result';
  content: string;
  timestamp: Date;
  toolName?: string;
  toolArgs?: Record<string, any>;
  toolResult?: any;
  toolResultSuccess?: boolean;
  expanded?: boolean;
}

@Component({
  selector: 'app-ai-assistant-chat',
  standalone: true,
  imports: [CommonModule, FormsModule, FontAwesomeModule],
  templateUrl: './chat.html',
  styleUrl: './chat.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AiAssistantChat implements OnInit, OnDestroy {
  @ViewChild('chatContainer') chatContainer!: ElementRef;

  messages: ChatMessage[] = [];
  input = '';
  loading = false;
  error: string | null = null;
  mode: 'chiquito' | 'grande' = 'grande';
  toolsCount = 0;

  private subs = new Subscription();
  private eventSource: EventSource | null = null;

  constructor(
    private headerService: HeaderService,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit() {
    this.headerService.setConfig({
      title: 'Asistente IA',
      subtitle: 'Copiloto inteligente del Centro Juan Pablo II',
      icon: ['fas', 'robot'],
    });
    this.loadToolsCount();
  }

  ngOnDestroy() {
    this.subs.unsubscribe();
    this.closeEventSource();
  }

  private loadToolsCount() {
    fetch(`${environment.apiBaseUrl || ''}/mcp/tools?mode=${this.mode}`, {
      credentials: 'include',
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('access_token') || ''}`,
      },
    })
      .then(r => r.json())
      .then(data => {
        this.toolsCount = data.count || 0;
        this.cdr.markForCheck();
      })
      .catch(() => {});
  }

  toggleMode() {
    this.mode = this.mode === 'chiquito' ? 'grande' : 'chiquito';
    this.loadToolsCount();
  }

  sendMessage() {
    if (!this.input.trim() || this.loading) return;

    const userMsg: ChatMessage = {
      role: 'user',
      content: this.input,
      timestamp: new Date(),
    };
    this.messages.push(userMsg);
    const userInput = this.input;
    this.input = '';
    this.loading = true;
    this.error = null;
    this.cdr.markForCheck();
    this.scrollToBottom();

    this.streamMessage(userInput);
  }

  private streamMessage(message: string) {
    this.closeEventSource();

    const apiUrl = environment.apiBaseUrl || '';
    const url = `${apiUrl}/mcp/chat/stream`;

    fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('access_token') || ''}`,
      },
      credentials: 'include',
      body: JSON.stringify({
        message,
        mode: this.mode,
        history: this.messages
          .filter(m => m.role === 'user' || m.role === 'assistant')
          .slice(-20)
          .map(m => ({ role: m.role, content: m.content })),
      }),
    })
      .then(response => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const reader = response.body?.getReader();
        if (!reader) throw new Error('No readable stream');

        const decoder = new TextDecoder();
        let buffer = '';

        const processStream = (): Promise<void> => {
          return reader!.read().then(({ done, value }) => {
            if (done) {
              this.loading = false;
              this.cdr.markForCheck();
              return;
            }

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';

            for (const line of lines) {
              if (line.startsWith('data: ')) {
                try {
                  const event = JSON.parse(line.slice(6));
                  this.handleStreamEvent(event);
                } catch {}
              }
            }

            return processStream();
          });
        };

        return processStream();
      })
      .catch(err => {
        this.messages.push({
          role: 'assistant',
          content: 'Lo siento, hubo un error al procesar tu consulta.',
          timestamp: new Date(),
        });
        this.loading = false;
        this.error = err.message;
        this.cdr.markForCheck();
        this.scrollToBottom();
      });
  }

  private handleStreamEvent(event: any) {
    switch (event.type) {
      case 'thinking':
        const lastThinking = this.messages[this.messages.length - 1];
        if (lastThinking?.role === 'assistant') {
          lastThinking.content = event.content;
        } else {
          this.messages.push({
            role: 'assistant',
            content: event.content,
            timestamp: new Date(),
          });
        }
        this.cdr.markForCheck();
        this.scrollToBottom();
        break;

      case 'tool_call':
        this.messages.push({
          role: 'tool_call',
          content: `Ejecutando: ${event.name}`,
          timestamp: new Date(),
          toolName: event.name,
          toolArgs: event.args,
          expanded: false,
        });
        this.cdr.markForCheck();
        this.scrollToBottom();
        break;

      case 'tool_result':
        const lastToolCall = [...this.messages].reverse().find(m => m.role === 'tool_call' && m.toolName === event.name && !m.toolResult);
        if (lastToolCall) {
          lastToolCall.toolResult = event.result;
          lastToolCall.toolResultSuccess = event.success;
        }
        this.cdr.markForCheck();
        break;

      case 'chunk':
      case 'text':
        if (event.content) {
          const lastAssistant = this.messages[this.messages.length - 1];
          if (lastAssistant?.role === 'assistant') {
            lastAssistant.content += event.content;
          } else {
            this.messages.push({
              role: 'assistant',
              content: event.content,
              timestamp: new Date(),
            });
          }
          this.cdr.markForCheck();
          this.scrollToBottom();
        }
        break;

      case 'done':
        this.loading = false;
        this.cdr.markForCheck();
        break;

      case 'error':
        this.messages.push({
          role: 'assistant',
          content: `Error: ${event.error}`,
          timestamp: new Date(),
        });
        this.loading = false;
        this.cdr.markForCheck();
        break;
    }
  }

  toggleToolCall(msg: ChatMessage) {
    msg.expanded = !msg.expanded;
    this.cdr.markForCheck();
  }

  sanitize(html: string): string {
    const rendered = this.markdownToHtml(html);
    return rendered;
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

  getObjectKeys(obj: any): string[] {
    return obj ? Object.keys(obj) : [];
  }

  retry() {
    this.error = null;
  }

  clearChat() {
    this.messages = [];
    this.error = null;
    this.cdr.markForCheck();
  }

  private closeEventSource() {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
  }

  private scrollToBottom() {
    setTimeout(() => {
      if (this.chatContainer) {
        this.chatContainer.nativeElement.scrollTop = this.chatContainer.nativeElement.scrollHeight;
      }
    }, 100);
  }
}
