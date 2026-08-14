import { Component, OnInit, ViewChild, ElementRef, OnDestroy, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { Subscription } from 'rxjs';
import { HeaderService } from '../../../../core/services/header.service';
import { environment } from '../../../../../environments/environment';
import { McpChatService, McpChip, McpPendingConfirm, McpStreamEvent } from '../../../../core/services/mcp-chat.service';
import { ChatConfirmDialog, PendingAction } from '../../../../shared/components/chat-confirm-dialog/chat-confirm-dialog';
import DOMPurify from 'dompurify';

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

type VoiceState = 'idle' | 'recording' | 'transcribing' | 'unsupported';

@Component({
  selector: 'app-ai-assistant-chat',
  standalone: true,
  imports: [CommonModule, FormsModule, FontAwesomeModule, ChatConfirmDialog],
  templateUrl: './chat.html',
  styleUrl: './chat.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AiAssistantChat implements OnInit, OnDestroy {
  @ViewChild('chatContainer') chatContainer!: ElementRef;
  @ViewChild('confirmDialog') confirmDialog!: ChatConfirmDialog;

  messages: ChatMessage[] = [];
  input = '';
  loading = false;
  error: string | null = null;
  mode: 'chiquito' | 'grande' = 'grande';
  toolsCount = 0;

  actionChips: McpChip[] = [];
  pendingAction: McpPendingConfirm | null = null;

  voiceState: VoiceState = 'idle';
  recordingTime = 0;
  voiceError: string | null = null;
  private mediaRecorder: MediaRecorder | null = null;
  private audioChunks: Blob[] = [];
  private mediaStream: MediaStream | null = null;
  private recordingTimer: ReturnType<typeof setInterval> | null = null;

  private subs = new Subscription();
  private eventSource: EventSource | null = null;
  private streamSub: Subscription | null = null;
  private abortCtrl: AbortController | null = null;
  private lastRequest: { message: string; history: { role: string; content: string }[] } | null = null;

  constructor(
    private headerService: HeaderService,
    private cdr: ChangeDetectorRef,
    private mcpChat: McpChatService,
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
    this.streamSub?.unsubscribe();
    this.abortCtrl?.abort();
    this.closeEventSource();
    this.clearRecordingTimer();
    this.stopMediaTracks();
    if (this.mediaRecorder) {
      this.mediaRecorder.onstop = null;
      try { this.mediaRecorder.stop(); } catch { /* ignore */ }
      this.mediaRecorder = null;
    }
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
    if (!this.input.trim() || this.loading || this.pendingAction) return;

    const userMsg: ChatMessage = {
      role: 'user',
      content: this.input,
      timestamp: new Date(),
    };
    this.messages.push(userMsg);
    const userInput = this.input;
    this.input = '';
    const history = this.messages
      .slice(0, -1)
      .filter((m) => m.role === 'user' || m.role === 'assistant')
      .slice(-20)
      .map((m) => ({ role: m.role, content: m.content }));
    this.lastRequest = { message: userInput, history };
    this.loading = true;
    this.error = null;
    this.cdr.markForCheck();
    this.scrollToBottom();

    this.streamToServer(userInput, history);
  }

  private streamToServer(message: string, history: { role: string; content: string }[], confirmed?: McpPendingConfirm) {
    this.closeEventSource();
    this.streamSub?.unsubscribe();
    this.abortCtrl?.abort();
    this.abortCtrl = new AbortController();
    this.actionChips = [];

    this.streamSub = this.mcpChat
      .stream({
        message,
        mode: this.mode,
        history,
        confirmed_tool: confirmed,
        signal: this.abortCtrl.signal,
      })
      .subscribe({
        next: (event) => this.handleStreamEvent(event),
      });
  }

  private handleStreamEvent(event: McpStreamEvent) {
    switch (event.type) {
      case 'thinking':
        const lastThinking = this.messages[this.messages.length - 1];
        if (lastThinking?.role === 'assistant') {
          lastThinking.content = event.content || '';
        } else {
          this.messages.push({
            role: 'assistant',
            content: event.content || '',
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
        const lastToolCall = [...this.messages].reverse().find((m) => m.role === 'tool_call' && m.toolName === event.name && !m.toolResult);
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
          this.pendingAction = pending;
          this.cdr.markForCheck();
          setTimeout(() => this.confirmDialog?.open(pending));
        }
        break;
      }

      case 'done':
        this.loading = false;
        if (event.pending_confirm?.name && !this.pendingAction) {
          this.pendingAction = event.pending_confirm;
          this.cdr.markForCheck();
          setTimeout(() => this.confirmDialog?.open(event.pending_confirm!));
        }
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
        this.scrollToBottom();
        break;
    }
  }

  onConfirmAction(action: PendingAction) {
    this.pendingAction = null;
    this.cdr.markForCheck();
    if (this.lastRequest) {
      this.loading = true;
      this.streamToServer(this.lastRequest.message, this.lastRequest.history, action);
    }
  }

  onCancelConfirm() {
    this.pendingAction = null;
    this.messages.push({
      role: 'assistant',
      content: 'Acción cancelada. ¿Necesitas ayuda con algo más?',
      timestamp: new Date(),
    });
    this.cdr.markForCheck();
    this.scrollToBottom();
  }

  handleActionChip(chip: McpChip) {
    switch (chip.type) {
      case 'navigation':
        if (chip.target) {
          window.location.href = chip.target;
        }
        break;
      default:
        this.input = chip.label || chip.target || '';
        if (this.input) this.sendMessage();
        break;
    }
  }

  toggleToolCall(msg: ChatMessage) {
    msg.expanded = !msg.expanded;
    this.cdr.markForCheck();
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

  getObjectKeys(obj: any): string[] {
    return obj ? Object.keys(obj) : [];
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
      this.showVoiceError('Tu navegador no soporta grabación de voz');
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
        this.recordingTimer = setInterval(() => {
          this.recordingTime++;
          this.cdr.markForCheck();
        }, 1000);
        this.cdr.markForCheck();
      })
      .catch(() => {
        this.voiceState = 'unsupported';
        this.showVoiceError('Tu navegador no soporta grabación de voz');
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

    const apiUrl = environment.apiBaseUrl || '';
    fetch(`${apiUrl}/mcp/transcribe`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('access_token') || ''}`,
      },
      credentials: 'include',
      body: formData,
    })
      .then(resp => resp.json())
      .then(data => {
        if (data.success && data.text) {
          this.input = data.text;
          this.cdr.markForCheck();
          this.sendMessage();
        } else {
          this.showVoiceError(data.error || 'No se pudo transcribir el audio');
        }
      })
      .catch(() => {
        this.showVoiceError('Error de red al transcribir el audio');
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

  private showVoiceError(message: string) {
    this.voiceError = message;
    this.cdr.markForCheck();
    setTimeout(() => {
      this.voiceError = null;
      this.cdr.markForCheck();
    }, 4000);
  }

  retry() {
    this.error = null;
  }

  clearChat() {
    this.messages = [];
    this.error = null;
    this.actionChips = [];
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
