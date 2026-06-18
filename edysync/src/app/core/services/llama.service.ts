import { Injectable } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';

export interface ActionChip {
  id: string;
  label: string;
  icon: string;
  type: 'navigation' | 'wizard' | 'modal' | 'scroll' | 'filter' | 'action' | 'confirm' | 'cancel' | 'toggleUser';
  target: string;
}

export interface LlamaResponse {
  success: boolean;
  response: string;
  intent: string;
  confidence: number;
  redirect?: string;
  action_result?: any;
  conversation_id?: number;
  action_chips?: ActionChip[];
  suggestions?: string[];
}

export interface AgentResponse {
  response: string;
  intent: string;
  action_chips: ActionChip[];
  suggestions: string[];
  conversation_id: number | null;
}

export interface ChatMessage {
  id?: number;
  role: 'user' | 'assistant';
  content: string;
  intent?: string;
  timestamp?: string;
  error?: boolean;
  action_chips?: ActionChip[];
  filePreview?: string;
}

export interface AgentUploadResponse {
  success: boolean;
  filename: string;
  ocr_text: string;
  extracted: {
    amount: number | null;
    payer: string;
    confidence: number;
    image_type: string;
  };
}

@Injectable({ providedIn: 'root' })
export class LlamaService {
  constructor(private http: HttpClient) {}

  getHistory(): Observable<{ success: boolean; messages: ChatMessage[] }> {
    return this.http.get<{ success: boolean; messages: ChatMessage[] }>('/llama/chat/history');
  }

  sendMessage(message: string, page: string = 'dashboard', mode: 'chiquito' | 'grande' = 'chiquito'): Observable<LlamaResponse> {
    return this.http.post<LlamaResponse>('/llama/chat/send', { message, page, mode });
  }

  sendAgentMessage(message: string, mode: 'chiquito' | 'grande' = 'chiquito'): Observable<AgentResponse> {
    return this.http.post<AgentResponse>('/llama/agent', { message, mode, conversation_id: null }).pipe(
      catchError((error: HttpErrorResponse) => {
        console.error('sendAgentMessage error:', error);
        return throwError(() => error);
      })
    );
  }

  uploadVoucher(file: File): Observable<AgentUploadResponse> {
    const fd = new FormData();
    fd.append('file', file);
    return this.http.post<AgentUploadResponse>('/llama/agent/upload', fd).pipe(
      catchError((error: HttpErrorResponse) => {
        console.error('uploadVoucher error:', error);
        return throwError(() => error);
      })
    );
  }
}
