import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { McpChatService } from './mcp-chat.service';

/** Eventos de `/assistant/ask/stream`: pasos de MiMo y las herramientas MCP en vivo, y al final la respuesta. */
export type AssistantStreamEvent =
  | { type: 'step'; text: string; tool?: string | null }
  | { type: 'done'; thread: AssistantThread; message: AssistantMessage }
  | { type: 'error'; message: string };

export type ValueFormat = 'money' | 'pct' | 'int' | 'dec' | 'date';

export interface KpiItem {
  key: string;
  label: string;
  value: number | null;
  previous: number | null;
  format: ValueFormat;
  delta: number | null;
  good_when: 'up' | 'down';
  status: 'good' | 'warn' | 'bad' | 'none';
}

export interface TableColumn {
  key: string;
  label: string;
  format?: ValueFormat;
  /** Columna de la fila con el enlace (p. ej. a la ficha del paciente). */
  link?: string;
  /** Columna de la fila con el código de la persona (respeta «solo códigos»). */
  person_code?: string;
}

export type AssistantBlock =
  | { type: 'text'; md: string }
  | { type: 'kpis'; items: KpiItem[] }
  | { type: 'chart'; kind: 'line' | 'bar' | 'doughnut'; title: string; x: string[]; series: { name: string; data: (number | null)[] }[]; format: ValueFormat }
  | { type: 'table'; title: string; columns: TableColumn[]; rows: Record<string, unknown>[]; totals?: boolean }
  | { type: 'people'; title: string; items: { id: number; name: string; code: string; detail: string; amount: number | null; link: string }[] }
  | ActionBlock;

/** Campo del formulario de una acción (sale del esquema de la herramienta). */
export interface ActionField {
  key: string;
  label: string;
  type: 'string' | 'integer' | 'number' | 'boolean' | 'enum' | 'list' | 'object';
  required: boolean;
  options?: { value: string | number; label: string }[];
  /** Lista larga (personas, sedes): se busca por nombre y se manda el id. */
  searchable?: boolean;
}

/** Acción que propuso la IA (crear usuario, registrar pago…): se revisa en un formulario y se confirma. */
export interface ActionBlock {
  type: 'action';
  tool: string;
  title: string;
  args: Record<string, unknown>;
  fields: ActionField[];
  status: 'pending' | 'done' | 'error';
  result_text?: string;
}

export interface AssistantSource {
  tool: string;
  range?: string;
  previous?: string;
  scope?: string;
}

export interface AssistantMessage {
  id: number;
  role: 'user' | 'assistant';
  text: string | null;
  blocks: AssistantBlock[];
  sources: AssistantSource[];
  model: string | null;
  question: string | null;
  feedback: number | null;
  created_at: string;
}

export interface AssistantSchedule {
  id: number;
  question: string;
  cadence: 'daily' | 'weekly';
  weekday: number | null;
  hour: number;
  channel: 'email' | 'telegram' | 'both';
  active: boolean;
  thread_id: number | null;
  label: string;
  last_run_at: string | null;
}

export interface AssistantThread {
  id: number;
  title: string;
  pinned: boolean;
  shared: boolean;
  mine: boolean;
  author: string | null;
  created_at: string;
  updated_at: string;
  messages?: AssistantMessage[];
  schedules?: AssistantSchedule[];
}

/** Pantalla del asistente del admin (PRP 015): conversaciones, preguntas con bloques y reportes programados. */
@Injectable({ providedIn: 'root' })
export class AssistantService {
  private http = inject(HttpClient);
  private base = '/api/assistant';
  private mcp = inject(McpChatService);

  home(): Observable<{ suggestions: string[] }> {
    return this.http.get<{ suggestions: string[] }>(`${this.base}/home`);
  }

  threads(q = ''): Observable<{ threads: AssistantThread[] }> {
    const params = q ? new HttpParams().set('q', q) : undefined;
    return this.http.get<{ threads: AssistantThread[] }>(`${this.base}/threads`, { params });
  }

  thread(id: number): Observable<AssistantThread> {
    return this.http.get<AssistantThread>(`${this.base}/threads/${id}`);
  }

  updateThread(id: number, data: Partial<Pick<AssistantThread, 'title' | 'pinned' | 'shared'>>): Observable<AssistantThread> {
    return this.http.patch<AssistantThread>(`${this.base}/threads/${id}`, data);
  }

  deleteThread(id: number): Observable<{ success: boolean }> {
    return this.http.delete<{ success: boolean }>(`${this.base}/threads/${id}`);
  }

  ask(question: string, threadId: number | null): Observable<{ thread: AssistantThread; message: AssistantMessage }> {
    return this.http.post<{ thread: AssistantThread; message: AssistantMessage }>(`${this.base}/ask`, { question, thread_id: threadId });
  }

  /** Pregunta en vivo (SSE con fetch: renueva la sesión si venció). Cancelar la suscripción corta la petición. */
  askStream(question: string, threadId: number | null): Observable<AssistantStreamEvent> {
    return new Observable<AssistantStreamEvent>((sub) => {
      const ctrl = new AbortController();
      this.mcp
        .authFetch(`${environment.apiBaseUrl}${this.base}/ask/stream`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ question, thread_id: threadId }),
          signal: ctrl.signal,
        })
        .then(async (resp) => {
          if (!resp.ok || !resp.body) {
            const body = await resp.json().catch(() => null);
            throw new Error(body?.message || `HTTP ${resp.status}`);
          }
          const reader = resp.body.getReader();
          const decoder = new TextDecoder();
          let buffer = '';
          for (;;) {
            const { done, value } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });
            const parts = buffer.split('\n\n');
            buffer = parts.pop() || '';
            for (const part of parts) {
              const line = part.split('\n').find((l) => l.startsWith('data: '));
              if (!line) continue;
              const ev = JSON.parse(line.slice(6)) as AssistantStreamEvent;
              sub.next(ev);
              if (ev.type === 'done' || ev.type === 'error') return sub.complete();
            }
          }
          sub.error(new Error('Se cortó la conexión antes de terminar.'));
        })
        .catch((err) => {
          if (err?.name !== 'AbortError') sub.error(err);
        });
      return () => ctrl.abort();
    });
  }

    runAction(messageId: number, args: Record<string, unknown>): Observable<{ message: AssistantMessage; reply: AssistantMessage }> {
    return this.http.post<{ message: AssistantMessage; reply: AssistantMessage }>(`${this.base}/messages/${messageId}/action`, { args });
  }

  refresh(messageId: number): Observable<AssistantMessage> {
    return this.http.post<AssistantMessage>(`${this.base}/messages/${messageId}/refresh`, {});
  }

  feedback(messageId: number, value: 1 | -1 | 0): Observable<AssistantMessage> {
    return this.http.post<AssistantMessage>(`${this.base}/messages/${messageId}/feedback`, { value });
  }

  schedule(data: Partial<AssistantSchedule> & { question: string }): Observable<AssistantSchedule> {
    return this.http.post<AssistantSchedule>(`${this.base}/schedules`, data);
  }

  deleteSchedule(id: number): Observable<{ success: boolean }> {
    return this.http.delete<{ success: boolean }>(`${this.base}/schedules/${id}`);
  }
}
