import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface LlamaResponse {
  success: boolean;
  response: string;
  intent: string;
  confidence: number;
  redirect?: string;
  action_result?: any;
  conversation_id?: number;
}

export interface ChatMessage {
  id?: number;
  role: 'user' | 'assistant';
  content: string;
  intent?: string;
  timestamp?: string;
}

@Injectable({ providedIn: 'root' })
export class LlamaService {
  constructor(private http: HttpClient) {}

  getHistory(): Observable<{ success: boolean; messages: ChatMessage[] }> {
    return this.http.get<{ success: boolean; messages: ChatMessage[] }>('/llama/chat/history');
  }

  sendMessage(message: string, page: string = 'dashboard'): Observable<LlamaResponse> {
    return this.http.post<LlamaResponse>('/llama/chat/send', { message, page });
  }
}
