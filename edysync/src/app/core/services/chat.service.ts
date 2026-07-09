import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, Subject, BehaviorSubject } from 'rxjs';
import { io, Socket } from 'socket.io-client';
import { environment } from '../../../environments/environment';

export interface ContactUser {
  id: number;
  username: string;
  email: string;
  role: string;
  avatar?: string;
  is_online: boolean;
}

export interface ChatItem {
  id: number;
  is_group: boolean;
  created_at: string | null;
  other_user: ContactUser | null;
  unread_count: number;
  last_message: {
    id: number;
    body: string;
    sender_id: number;
    created_at: string | null;
    attachment_type: string | null;
  } | null;
}

export interface MessageData {
  id: number;
  sender_id: number;
  receiver_id: number;
  body: string;
  status: string;
  is_read: boolean;
  file_url: string | null;
  attachment_type: string | null;
  created_at: string | null;
}

@Injectable({ providedIn: 'root' })
export class ChatService {
  private socket!: Socket;
  private readonly SOCKET_URL = environment.docker ? '' : environment.production ? 'https://moscowle-backend-production.up.railway.app' : 'http://127.0.0.1:5001';

  private _onlineUsers = new BehaviorSubject<Set<number>>(new Set());
  onlineUsers$ = this._onlineUsers.asObservable();

  private _newMessage = new Subject<{ chat_id: number; message: MessageData }>();
  newMessage$ = this._newMessage.asObservable();

  private _messageStatus = new Subject<{ chat_id: number; user_id: number; status: string }>();
  messageStatus$ = this._messageStatus.asObservable();

  private _userTyping = new Subject<{ chat_id: number; user_id: number; username: string }>();
  userTyping$ = this._userTyping.asObservable();

  private _userStoppedTyping = new Subject<{ chat_id: number; user_id: number }>();
  userStoppedTyping$ = this._userStoppedTyping.asObservable();

  private _connectionStatus = new BehaviorSubject<boolean>(false);
  connectionStatus$ = this._connectionStatus.asObservable();

  private _notificationEvent = new Subject<any>();
  notificationEvent$ = this._notificationEvent.asObservable();

  constructor(private http: HttpClient) {}

  connect() {
    if (this.socket?.connected) return;
    this.socket = io(this.SOCKET_URL, {
      transports: ['websocket', 'polling'],
      withCredentials: true,
      autoConnect: true,
      reconnection: true,
      reconnectionAttempts: 20,
      reconnectionDelay: 1000,
    });

    this.socket.on('connect', () => {
      this._connectionStatus.next(true);
      const userStr = localStorage.getItem('user');
      if (userStr) {
        const user = JSON.parse(userStr);
        this.socket.emit('user:online', { user_id: user.id });
      }
    });

    this.socket.on('disconnect', () => {
      this._connectionStatus.next(false);
    });

    this.socket.on('connect_error', (err: any) => {
      console.warn('Socket.IO connection error:', err?.message || err);
      this._connectionStatus.next(false);
    });

    this.socket.on('users:online', (data: { user_ids: number[] }) => {
      this._onlineUsers.next(new Set(data.user_ids));
    });

    this.socket.on('user:online', (data: { user_id: number }) => {
      const current = this._onlineUsers.value;
      current.add(data.user_id);
      this._onlineUsers.next(new Set(current));
    });

    this.socket.on('user:offline', (data: { user_id: number }) => {
      const current = this._onlineUsers.value;
      current.delete(data.user_id);
      this._onlineUsers.next(new Set(current));
    });

    this.socket.on('message:new', (data: { chat_id: number; message: MessageData }) => {
      this._newMessage.next(data);
    });

    this.socket.on('message:status', (data: { chat_id: number; user_id: number; status: string }) => {
      this._messageStatus.next(data);
    });

    this.socket.on('user:typing', (data: { chat_id: number; user_id: number; username: string }) => {
      this._userTyping.next(data);
    });

    this.socket.on('user:stop_typing', (data: { chat_id: number; user_id: number }) => {
      this._userStoppedTyping.next(data);
    });

    this.socket.on('notification:new', (data: any) => {
      this._notificationEvent.next(data);
    });
  }

  disconnect() {
    if (this.socket) {
      this.socket.disconnect();
      this._connectionStatus.next(false);
    }
  }

  joinChat(chatId: number) {
    this.socket?.emit('chat:join', { chat_id: chatId });
  }

  leaveChat(chatId: number) {
    this.socket?.emit('chat:leave', { chat_id: chatId });
  }

  startTyping(chatId: number) {
    this.socket?.emit('typing:start', { chat_id: chatId });
  }

  stopTyping(chatId: number) {
    this.socket?.emit('typing:stop', { chat_id: chatId });
  }

  isConnected(): boolean {
    return this.socket?.connected ?? false;
  }

  getContacts(role?: string): Observable<ContactUser[]> {
    const params = role ? `?role=${role}` : '';
    return this.http.get<ContactUser[]>(`/api/contacts${params}`);
  }

  getChats(): Observable<ChatItem[]> {
    return this.http.get<ChatItem[]>('/api/chats');
  }

  createChat(userId: number): Observable<{ success: boolean; chat_id: number; created: boolean }> {
    return this.http.post<{ success: boolean; chat_id: number; created: boolean }>('/api/chats', { user_id: userId });
  }

  getMessages(chatId: number, page: number = 1, limit: number = 50): Observable<{ messages: MessageData[]; total: number; page: number; has_more: boolean }> {
    return this.http.get<{ messages: MessageData[]; total: number; page: number; has_more: boolean }>(`/api/chats/${chatId}/messages?page=${page}&limit=${limit}`);
  }

  sendMessage(chatId: number, body?: string, file?: File | null): Observable<any> {
    if (file) {
      const fd = new FormData();
      if (body) fd.append('body', body);
      fd.append('file', file);
      return this.http.post(`/api/chats/${chatId}/messages`, fd);
    }
    return this.http.post(`/api/chats/${chatId}/messages`, { body });
  }

  markRead(chatId: number): Observable<{ success: boolean }> {
    return this.http.put<{ success: boolean }>(`/api/chats/${chatId}/read`, {});
  }

  deleteChat(chatId: number): Observable<{ success: boolean }> {
    return this.http.delete<{ success: boolean }>(`/api/chats/${chatId}`);
  }
}
