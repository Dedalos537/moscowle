import { Component, OnInit, ViewChild, ElementRef, OnDestroy, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { Subscription } from 'rxjs';
import { HeaderService } from '../../../../core/services/header.service';
import { environment } from '../../../../../environments/environment';
import { McpChatService, McpChip, McpPendingConfirm, McpStreamEvent, McpTraceStep } from '../../../../core/services/mcp-chat.service';
import { ChatConfirmDialog, PendingAction } from '../../../../shared/components/chat-confirm-dialog/chat-confirm-dialog';
import DOMPurify from 'dompurify';

interface ToolCallEntry {
  name: string;
  args: Record<string, any>;
  result?: string;
  success?: boolean;
  expanded?: boolean;
}

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  /** Llamadas a herramientas adjuntas al turno (no son mensajes propios). */
  toolCalls?: ToolCallEntry[];
  /** Traza de pasos del pipeline para la tarjeta colapsada. */
  trace?: McpTraceStep[];
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

  /** Traza viva del turno: nunca se escribe en `messages` (sin prefijos en la burbuja). */
  private liveTrace: McpTraceStep[] = [];
  private streamToolCalls: ToolCallEntry[] = [];

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
    this.liveTrace = [];
    this.streamToolCalls = [];

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
      case 'thinking': {
        // Nunca toca `messages`: la burbuja solo recibe texto del modelo.
        const step = event.step ?? { kind: 'route', text: event.content || '' };
        if (step?.text) this.liveTrace.push(step);
        this.cdr.markForCheck();
        break;
      }

      case 'tool_call': {
        // La prosa previa al tool_call no es la respuesta: vacía la burbuja.
        const prev = this.messages[this.messages.length - 1];
        if (prev?.role === 'assistant') prev.content = '';
        this.streamToolCalls.push({
          name: event.name || '',
          args: event.args || {},
          expanded: false,
        });
        this.liveTrace.push({ kind: 'tool', tool: event.name || '', text: `Llamando a la herramienta: ${event.name || '?'}` });
        this.cdr.markForCheck();
        break;
      }

      case 'tool_result': {
        const entry = [...this.streamToolCalls].reverse().find((t) => t.name === event.name && t.result === undefined);
        if (entry) {
          entry.result = event.result || '';
          entry.success = event.success !== false;
        }
        this.liveTrace.push({
          kind: 'result',
          tool: event.name || '',
          ok: event.success !== false,
          text: `Resultado de ${event.name}: ${event.success !== false ? 'obtuve' : 'error en'} → ${(event.result || '').slice(0, 120)}`,
        });
        this.cdr.markForCheck();
        break;
      }

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
          // Las llamadas viven en el msg asistente, nunca como mensajes aparte.
          const current = this.messages[this.messages.length - 1];
          if (this.streamToolCalls.length) current.toolCalls = [...this.streamToolCalls];
          this.cdr.markForCheck();
          this.scrollToBottom();
        }
        break;

      case 'final': {
        // Texto final normalizado: REEMPLAZA lo transmitido en chunks.
        const lastF = this.messages[this.messages.length - 1];
        if (lastF?.role === 'assistant') {
          lastF.content = event.content || '';
        } else if (event.content) {
          this.messages.push({ role: 'assistant', content: event.content, timestamp: new Date() });
        }
        this.cdr.markForCheck();
        this.scrollToBottom();
        break;
      }

      case 'reset_text': {
        const lastR = this.messages[this.messages.length - 1];
        if (lastR?.role === 'assistant') lastR.content = '';
        this.cdr.markForCheck();
        break;
      }

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

      case 'done': {
        this.loading = false;
        const trace = event.trace?.length ? event.trace : [...this.liveTrace];
        const tools = this.streamToolCalls.length ? [...this.streamToolCalls] : undefined;
        this.liveTrace = [];
        this.streamToolCalls = [];
        const last = this.messages[this.messages.length - 1];
        if (last?.role === 'assistant') {
          if (tools) last.toolCalls = tools;
          if (trace.length) last.trace = trace;
        }
        if (event.pending_confirm?.name && !this.pendingAction) {
          this.pendingAction = event.pending_confirm;
          this.cdr.markForCheck();
          setTimeout(() => this.confirmDialog?.open(event.pending_confirm!));
        }
        this.cdr.markForCheck();
        break;
      }

      case 'error':
        this.messages.push({
          role: 'assistant',
          content: `Error: ${event.error}`,
          timestamp: new Date(),
        });
        this.loading = false;
        this.liveTrace = [];
        this.streamToolCalls = [];
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

  toggleToolEntry(entry: ToolCallEntry) {
    entry.expanded = !entry.expanded;
    this.cdr.markForCheck();
  }

  /** Resumen de la tarjeta colapsada: "· N herramientas · M pasos". */
  traceSummary(msg: ChatMessage): string {
    const toolNames = new Set<string>();
    for (const step of msg.trace || []) {
      if (step.tool) toolNames.add(step.tool);
    }
    for (const tc of msg.toolCalls || []) {
      if (tc.name) toolNames.add(tc.name);
    }
    const tools = toolNames.size;
    const steps = msg.trace?.length || 0;
    return `· ${tools} herramienta${tools === 1 ? '' : 's'} · ${steps} paso${steps === 1 ? '' : 's'}`;
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
    this.liveTrace = [];
    this.streamToolCalls = [];
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
