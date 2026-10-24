import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

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
