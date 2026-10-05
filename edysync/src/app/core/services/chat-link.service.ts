import { HttpClient } from '@angular/common/http';
import { Injectable, inject, signal } from '@angular/core';
import { Observable } from 'rxjs';

export interface ChatLoginCode {
  code: string;
  expires_in: number;
  instructions: string;
}

export interface ChatAccount {
  chat_id: number;
  username: string | null;
  first_name: string | null;
  notifications_enabled: boolean;
  last_interaction_at: string | null;
}

export interface ChatLinkStatus {
  linked: boolean;
  role: string;
  accounts: ChatAccount[];
  /** @usuario del bot (getMe); null si Telegram no respondió: la UI degrada a instrucciones sin enlace. */
  bot_username: string | null;
}

/** Código vigente. Vive en el servicio y no en el componente: el menú de preferencias destruye su contenido al cerrarse. */
export interface PendingChatCode {
  code: string;
  expiresAt: number;
}

/** Acceso HTTP a la vinculación del chat (Telegram) del usuario autenticado. Vale para cualquier rol. */
@Injectable({ providedIn: 'root' })
export class ChatLinkService {
  private http = inject(HttpClient);

  readonly pendingCode = signal<PendingChatCode | null>(null);

  getStatus(): Observable<ChatLinkStatus> {
    return this.http.get<ChatLinkStatus>('/api/telegram/me');
  }

  requestCode(): Observable<ChatLoginCode> {
    return this.http.post<ChatLoginCode>('/api/telegram/login-code', {});
  }

  unlink(chatId: number): Observable<{ status: string }> {
    return this.http.post<{ status: string }>('/api/telegram/me/unlink', { chat_id: chatId });
  }
}
