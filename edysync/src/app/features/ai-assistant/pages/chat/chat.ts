import { Component, OnInit, ViewChild, ElementRef, OnDestroy, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { HttpClient } from '@angular/common/http';
import { Subscription } from 'rxjs';
import { HeaderService } from '../../../../core/services/header.service';

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
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

  private subs = new Subscription();

  constructor(
    private headerService: HeaderService,
    private http: HttpClient,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit() {
    this.headerService.setConfig({
      title: 'Asistente IA',
      subtitle: 'Consulta con inteligencia artificial',
      icon: ['fas', 'robot'],
    });
    this.loadHistory();
  }

  ngOnDestroy() {
    this.subs.unsubscribe();
  }

  private loadHistory() {
    this.subs.add(this.http.get<any>('/llama/chat/history').subscribe({
      next: (res) => {
        if (res?.messages) {
          this.messages = res.messages.map((m: any) => ({
            role: m.role,
            content: m.content,
            timestamp: new Date(m.timestamp),
          }));
          this.cdr.markForCheck();
        }
      },
      error: (err) => {
        this.error = err.message;
        this.cdr.markForCheck();
      },
    }));
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
    this.cdr.markForCheck();

    this.subs.add(this.http.post<any>('/llama/chat/send', { message: userInput }).subscribe({
      next: (res) => {
        const assistantMsg: ChatMessage = {
          role: 'assistant',
          content: res.response || res.message || 'Procesado',
          timestamp: new Date(),
        };
        this.messages.push(assistantMsg);
        this.loading = false;
        this.cdr.markForCheck();
        this.scrollToBottom();
      },
      error: (err) => {
        this.messages.push({
          role: 'assistant',
          content: 'Lo siento, hubo un error al procesar tu consulta.',
          timestamp: new Date(),
        });
        this.loading = false;
        this.error = err.message;
        this.cdr.markForCheck();
        this.scrollToBottom();
      },
    }));
  }

  retry() {
    this.error = null;
    this.loadHistory();
  }

  private scrollToBottom() {
    setTimeout(() => {
      if (this.chatContainer) {
        this.chatContainer.nativeElement.scrollTop = this.chatContainer.nativeElement.scrollHeight;
      }
    }, 100);
  }
}
