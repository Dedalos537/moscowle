import { Injectable } from '@angular/core';
import { Observable, Subscriber } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface McpChip {
  id: string;
  type: string;
  label: string;
  icon: string;
  target?: string;
}

export interface McpPendingConfirm {
  name: string;
  args: Record<string, unknown>;
  tool_call_text?: string;
}

export interface McpToolCallResult {
  name: string;
  args: Record<string, unknown>;
  result: string;
  success: boolean;
}

export interface McpStreamEvent {
  type:
    | 'thinking'
    | 'chunk'
    | 'text'
    | 'tool_call'
    | 'tool_result'
    | 'confirm'
    | 'chips'
    | 'done'
    | 'error';
  content?: string;
  name?: string;
  args?: Record<string, unknown>;
  result?: string;
  success?: boolean;
  tool_call_text?: string;
  chips?: McpChip[];
  pending_confirm?: McpPendingConfirm;
  tool_calls?: McpToolCallResult[];
  error?: string;
}

export interface McpStreamRequest {
  message: string;
  mode: 'chiquito' | 'grande';
  history: { role: string; content: string }[];
  confirmed_tool?: McpPendingConfirm;
  conversation_id?: string;
  signal?: AbortSignal;
}

@Injectable({ providedIn: 'root' })
export class McpChatService {
  private apiUrl = environment.apiBaseUrl;

  stream(req: McpStreamRequest): Observable<McpStreamEvent> {
    return new Observable((subscriber: Subscriber<McpStreamEvent>) => {
      const signal = req.signal ?? new AbortController().signal;

      fetch(`${this.apiUrl}/mcp/chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token') || ''}`,
        },
        credentials: 'include',
        body: JSON.stringify({
          message: req.message,
          mode: req.mode,
          history: req.history,
          confirmed_tool: req.confirmed_tool || undefined,
          conversation_id: req.conversation_id || undefined,
        }),
        signal,
      })
        .then(async (resp) => {
          if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
          const reader = resp.body!.getReader();
          const decoder = new TextDecoder();
          let buffer = '';

          for (;;) {
            const { done, value } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';

            for (const line of lines) {
              if (!line.startsWith('data: ')) continue;
              try {
                const event = JSON.parse(line.slice(6)) as McpStreamEvent;
                subscriber.next(event);
                if (event.type === 'done' || event.type === 'error') {
                  subscriber.complete();
                  return;
                }
              } catch {
                // skip malformed lines
              }
            }
          }
          subscriber.complete();
        })
        .catch((err) => {
          if (err?.name === 'AbortError') return;
          subscriber.next({ type: 'error', error: err?.message || 'Error de conexión' });
          subscriber.complete();
        });
    });
  }
}
