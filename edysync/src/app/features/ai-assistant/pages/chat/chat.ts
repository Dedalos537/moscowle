// DCE — Diego Centeno Estuvo Acá
import { Component, OnInit, ViewChild, ElementRef } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { HeaderService } from '../../../../core/services/header.service';

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

@Component({
  selector: 'app-ai-assistant-chat',
  standalone: false,
  templateUrl: './chat.html',
  styleUrl: './chat.scss',
})
export class AiAssistantChat implements OnInit {
  @ViewChild('chatContainer') chatContainer!: ElementRef;

  messages: ChatMessage[] = [];
  input = '';
  loading = false;

  constructor(
    private headerService: HeaderService,
    private http: HttpClient
  ) {}

  ngOnInit() {
    this.headerService.setConfig({
      title: 'Asistente IA',
      subtitle: 'Consulta con inteligencia artificial',
      icon: ['fas', 'robot'],
    });
    this.loadHistory();
  }

  private loadHistory() {
    this.http.get<any>('/llama/chat/history').subscribe({
      next: (res) => {
        if (res?.messages) {
          this.messages = res.messages.map((m: any) => ({
            role: m.role,
            content: m.content,
            timestamp: new Date(m.timestamp),
          }));
        }
      },
    });
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

    this.http.post<any>('/llama/chat/send', { message: userInput }).subscribe({
      next: (res) => {
        const assistantMsg: ChatMessage = {
          role: 'assistant',
          content: res.response || res.message || 'Procesado',
          timestamp: new Date(),
        };
        this.messages.push(assistantMsg);
        this.loading = false;
        this.scrollToBottom();
      },
      error: () => {
        this.messages.push({
          role: 'assistant',
          content: 'Lo siento, hubo un error al procesar tu consulta.',
          timestamp: new Date(),
        });
        this.loading = false;
        this.scrollToBottom();
      },
    });
  }

  private scrollToBottom() {
    setTimeout(() => {
      if (this.chatContainer) {
        this.chatContainer.nativeElement.scrollTop = this.chatContainer.nativeElement.scrollHeight;
      }
    }, 100);
  }
}
