import { Injectable } from '@angular/core';

/**
 * Sesiones conversacionales del asistente.
 *
 * MVP: persistencia en localStorage, particionada por usuario.
 * Backend-ready: toda la persistencia pasa por `load()` / `save()`; para migrar
 * a base de datos basta reemplazar estos dos métodos por llamadas HTTP
 * (p. ej. GET/POST /mcp/sessions) y añadir `conversation_id` al stream (ver
 * `McpStreamRequest.conversationId`).
 */

export interface ChatSessionToolCall {
  name: string;
  args: Record<string, unknown>;
  result: string;
  success: boolean;
}

export interface ChatSessionMessage {
  role: 'user' | 'assistant';
  content: string;
  intent?: string;
  error?: boolean;
  filePreview?: string;
  toolCalls?: ChatSessionToolCall[];
}

export interface ChatSession {
  id: string;
  title: string;
  messages: ChatSessionMessage[];
  createdAt: number;
  updatedAt: number;
}

export interface ChatSessionState {
  sessions: ChatSession[];
  activeId: string | null;
}

const MAX_MESSAGES_PER_SESSION = 100;

function newSessionId(): string {
  try {
    if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
      return crypto.randomUUID();
    }
  } catch {
    /* fallthrough */
  }
  return 's_' + Date.now().toString(36) + '_' + Math.random().toString(36).slice(2, 10);
}

@Injectable({ providedIn: 'root' })
export class ChatSessionService {
  createSession(): ChatSession {
    const now = Date.now();
    return {
      id: newSessionId(),
      title: 'Nueva conversación',
      messages: [],
      createdAt: now,
      updatedAt: now,
    };
  }

  load(): ChatSessionState {
    try {
      const raw = localStorage.getItem(this.storageKey());
      if (!raw) return { sessions: [], activeId: null };
      const parsed = JSON.parse(raw);
      if (!parsed || !Array.isArray(parsed.sessions)) {
        return { sessions: [], activeId: null };
      }
      const sessions = (parsed.sessions as ChatSession[])
        .filter((s) => s && typeof s.id === 'string')
        .map((s) => ({
          ...s,
          messages: Array.isArray(s.messages) ? s.messages : [],
          title: s.title && s.title.trim() ? s.title : 'Nueva conversación',
        }));
      const activeId = typeof parsed.activeId === 'string' && sessions.some((s) => s.id === parsed.activeId)
        ? parsed.activeId
        : (sessions[0]?.id ?? null);
      return { sessions, activeId };
    } catch {
      return { sessions: [], activeId: null };
    }
  }

  save(state: ChatSessionState): void {
    try {
      const compact = state.sessions.map((s) => ({
        ...s,
        messages: s.messages.slice(-MAX_MESSAGES_PER_SESSION),
      }));
      localStorage.setItem(this.storageKey(), JSON.stringify({ sessions: compact, activeId: state.activeId }));
    } catch (e) {
      console.warn('No se pudieron guardar las sesiones del asistente', e);
    }
  }

  deleteAll(): void {
    try {
      localStorage.removeItem(this.storageKey());
    } catch {
      /* ignore */
    }
  }

  private storageKey(): string {
    return `moscowle_ai_sessions_v1_${this.userId()}`;
  }

  private userId(): string {
    try {
      const raw = localStorage.getItem('user');
      if (raw) {
        const u = JSON.parse(raw);
        if (u && u.id !== undefined && u.id !== null) return String(u.id);
      }
    } catch {
      /* ignore */
    }
    return 'anon';
  }
}
