import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
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
}

/** Acceso HTTP a la vinculación del chat (Telegram) del usuario autenticado. Vale para cualquier rol. */
@Injectable({ providedIn: 'root' })
export class ChatLinkService {
  private http = inject(HttpClient);

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
