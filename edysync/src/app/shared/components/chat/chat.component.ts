import {
  Component,
  OnInit,
  OnDestroy,
  ViewChild,
  ElementRef,
  ChangeDetectorRef,
  ChangeDetectionStrategy,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { DatePipe } from '@angular/common';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import {
  ChatService,
  ContactUser,
  ChatItem,
  MessageData,
} from '../../../core/services/chat.service';
import { HeaderService } from '../../../core/services/header.service';
import { AuthService } from '../../../core/services/auth.service';
import { Subscription } from 'rxjs';
import { Spinner } from '../spinner/spinner';

@Component({
  selector: 'app-chat',
  standalone: true,
  imports: [FormsModule, DatePipe, FontAwesomeModule, Spinner],
  templateUrl: './chat.component.html',
  styleUrl: './chat.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ChatComponent implements OnInit, OnDestroy {
  @ViewChild('chatMessages') chatMessages!: ElementRef;
  @ViewChild('fileInput') fileInput!: ElementRef;

  contacts: ContactUser[] = [];
  chats: ChatItem[] = [];
  messages: MessageData[] = [];
  currentUserId = 0;
  userRole = '';
  searchQuery = '';
  roleFilter = 'todos';
  showContacts = false;
  roleLabels: Record<string, string> = {
    admin: 'Admin',
    supervisor: 'Supervisor',
    terapista: 'Terapista',
    terapeuta: 'Terapista',
    paciente: 'Paciente',
    jugador: 'Paciente',
  };
  roleOrder = ['admin', 'supervisor', 'terapista', 'paciente'];

  selectedChatId: number | null = null;
  selectedContact: ContactUser | null = null;
  mobileChatOpen = false;
  newMessageText = '';
  selectedFile: File | null = null;
  selectedFileName = '';
  sending = false;
  loading = true;
  loadingMessages = false;
  onlineUsers = new Set<number>();
  connected = false;

  /** ids que ya están rendersados, para evitar duplicados (socket + HTTP) */
  private messageIds = new Set<number>();

  typingUsers: Map<number, { username: string; timeout: any }> = new Map();
  typingChatId: number | null = null;

  isRecording = false;
  recordingSeconds = 0;
  recordingPaused = false;
  private mediaRecorder: MediaRecorder | null = null;
  private audioChunks: Blob[] = [];
  private recTicker: any = null;
  private audioBlobUrl: string | null = null;

  private holdTimer: any = null;
  private holdPointerId: number | null = null;
  private holdStartX = 0;
  private holdStartY = 0;
  private isHoldMode = false;
  private holdRecordingStarted = false;
  private holdCancel = false;

  deleteMenuId: number | null = null;
  audioPlayingId: number | null = null;
  private audioEls = new Map<number, HTMLAudioElement>();

  /** Previsualización mientras se edita / envía */
  selectedFilePreviewUrl: string | null = null;
  lightboxUrl: string | null = null;
  lightboxTitle = '';
  aiPreview: { open: boolean; msg: MessageData | null; loading: boolean; data: any; error: string | null } = {
    open: false, msg: null, loading: false, data: null, error: null,
  };

  private subs: Subscription[] = [];

  constructor(
    private chatService: ChatService,
    private headerService: HeaderService,
    private auth: AuthService,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit() {
    this.headerService.setConfig({
      title: 'Mensajería',
      subtitle: 'Chat en tiempo real',
      icon: ['fas', 'comment-dots'],
    });

    this.subs.push(
      this.auth.currentUser$.subscribe((user) => {
        if (user) {
          this.currentUserId = user.id;
          this.userRole = user.role;
          this.chatService.connect();
          this.loadData();
        }
      })
    );

    this.subs.push(
      this.chatService.onlineUsers$.subscribe((online) => {
        this.onlineUsers = online;
        this.cdr.markForCheck();
      })
    );

    this.subs.push(
      this.chatService.connectionStatus$.subscribe((ok) => {
        this.connected = ok;
        this.cdr.markForCheck();
      })
    );

    this.subs.push(
      this.chatService.newMessage$.subscribe(({ chat_id, message }) => {
        this.onIncomingMessage(chat_id, message);
        this.cdr.markForCheck();
      })
    );

    this.subs.push(
      this.chatService.messageStatus$.subscribe(({ chat_id, user_id, status }) => {
        if (chat_id === this.selectedChatId && user_id === this.selectedContact?.id) {
          // El otro usuario leyó / recibió MIS mensajes → actualizo el comprobante
          this.messages = this.messages.map((m) =>
            m.sender_id === this.currentUserId && m.status !== 'read' && status === 'read'
              ? { ...m, status: 'read', is_read: true }
              : m
          );
          this.cdr.markForCheck();
        }
      })
    );

    this.subs.push(
      this.chatService.userTyping$.subscribe((data) => {
        if (data.chat_id === this.selectedChatId) {
          const existing = this.typingUsers.get(data.user_id);
          if (existing) clearTimeout(existing.timeout);
          const timeout = setTimeout(() => {
            this.typingUsers.delete(data.user_id);
            if (this.typingUsers.size === 0) this.typingChatId = null;
            this.cdr.markForCheck();
          }, 3000);
          this.typingUsers.set(data.user_id, { username: data.username, timeout });
          this.typingChatId = data.chat_id;
          this.cdr.markForCheck();
        }
      })
    );

    this.subs.push(
      this.chatService.userStoppedTyping$.subscribe((data) => {
        if (data.chat_id === this.selectedChatId) {
          const existing = this.typingUsers.get(data.user_id);
          if (existing) clearTimeout(existing.timeout);
          this.typingUsers.delete(data.user_id);
          if (this.typingUsers.size === 0) this.typingChatId = null;
          this.cdr.markForCheck();
        }
      })
    );

    this.subs.push(
      this.chatService.messageDeleted$.subscribe(({ chat_id, message_id, mode }) => {
        this.applyMessageDeleted(chat_id, message_id, mode, true);
      })
    );
  }

  ngOnDestroy() {
    this.headerService.reset();
    this.clearRecording();
    this.audioEls.forEach((el) => {
      el.pause();
      el.removeAttribute('src');
      el.load();
    });
    this.audioEls.clear();
    this.audioPlayingId = null;
    if (this.selectedChatId && this.selectedChatId > 0) this.chatService.leaveChat(this.selectedChatId);
    this.subs.forEach((s) => s.unsubscribe());
  }

  private loadData() {
    this.loading = true;
    this.chatService.getChats().subscribe({
      next: (chats) => {
        this.chats = chats;
        this.clearMessageIds();
        this.loadContacts();
      },
      error: () => (this.loading = false),
    });
  }

  private loadContacts() {
    this.chatService.getContacts(this.roleFilter !== 'todos' ? this.roleFilter : undefined).subscribe({
      next: (contacts) => {
        this.contacts = contacts;
        this.loading = false;
        this.cdr.markForCheck();
      },
      error: () => (this.loading = false),
    });
  }

  setRoleFilter(role: string) {
    this.roleFilter = role;
    this.loadContacts();
  }

  get filteredContacts(): ContactUser[] {
    let list = [...this.contacts];
    if (this.searchQuery.trim()) {
      const q = this.searchQuery.toLowerCase();
      list = list.filter((c) => c.username.toLowerCase().includes(q));
    }
    return list;
  }

  get canFilterByRole(): boolean {
    return this.userRole === 'admin' || this.userRole === 'supervisor' || this.userRole === 'terapista';
  }

  get groupedContacts(): { role: string; users: ContactUser[] }[] {
    const groups: { role: string; users: ContactUser[] }[] = [];
    for (const role of this.roleOrder) {
      const users = this.filteredContacts.filter((c) => this.displayRole(c.role) === role);
      if (users.length > 0) {
        groups.push({ role, users });
      }
    }
    return groups;
  }

  get filteredChats(): ChatItem[] {
    let list = [...this.chats];
    list.sort((a, b) => {
      const ta = a.last_message?.created_at || a.created_at || '';
      const tb = b.last_message?.created_at || b.created_at || '';
      return tb.localeCompare(ta);
    });
    if (!this.searchQuery.trim()) return list;
    const q = this.searchQuery.toLowerCase();
    return list.filter((c) => c.other_user?.username.toLowerCase().includes(q));
  }

  selectContact(contact: ContactUser) {
    this.loadingMessages = true;
    this.selectedContact = contact;
    this.mobileChatOpen = true;
    this.chatService.createChat(contact.id).subscribe({
      next: (res) => {
        this.selectedChatId = res.chat_id;
        this.chatService.joinChat(res.chat_id);
        this.clearMessageIds();
        this.loadMessages();
        this.chatService.markRead(res.chat_id).subscribe();
      },
      error: () => (this.loadingMessages = false),
    });
  }

  selectChat(chat: ChatItem) {
    this.selectedChatId = chat.id;
    this.selectedContact = chat.other_user;
    this.mobileChatOpen = true;
    this.loadingMessages = true;

    if (chat.id > 0) {
      this.chatService.joinChat(chat.id);
    }

    if (chat.unread_count > 0) {
      this.chatService.markRead(chat.id).subscribe();
    }

    this.clearMessageIds();
    this.loadMessages();
    this.markChatRead(chat.id);
  }

  private loadMessages() {
    if (!this.selectedChatId) return;
    this.chatService.getMessages(this.selectedChatId).subscribe({
      next: (res) => {
        this.messages = (res.messages || []).slice().sort((a, b) => this.timeOf(a).localeCompare(this.timeOf(b)));
        this.rebuildMessageIds();
        this.loadingMessages = false;
        setTimeout(() => this.scrollToBottom(), 100);
        this.cdr.markForCheck();
      },
      error: () => (this.loadingMessages = false),
    });
  }

  private markChatRead(chatId: number) {
    const chat = this.chats.find((c) => c.id === chatId);
    if (chat) chat.unread_count = 0;
  }

  private onIncomingMessage(chatId: number, message: MessageData) {
    if (!message || !message.id) return;
    // Quita el placeholder optimista propio pendiente (evita duplicado si el real llega por socket antes del POST)
    if (message.sender_id === this.currentUserId) {
      this.messages = this.messages.filter(
        (m) => !(m.id < 0 && m.sender_id === this.currentUserId && m.receiver_id === message.receiver_id),
      );
    }
    if (this.messageIds.has(message.id)) return;

    this.messageIds.add(message.id);

    if (chatId === this.selectedChatId && this.selectedContact) {
      this.messages = [...this.messages, message].sort((a, b) => this.timeOf(a).localeCompare(this.timeOf(b)));
      this.chatService.markRead(chatId).subscribe();
      setTimeout(() => this.scrollToBottom(), 50);
    } else if (message.sender_id !== this.currentUserId) {
      // no leída en la lista lateral
      const chat = this.chats.find((c) => c.id === chatId);
      if (chat) chat.unread_count += 1;
    }

    this.updateChatLastMessage(chatId, message);
  }

  private updateChatLastMessage(chatId: number, message: MessageData) {
    const chat = this.chats.find((c) => c.id === chatId);
    if (chat) {
      chat.last_message = {
        id: message.id,
        body: message.body || (message.attachment_type ? '📎 Archivo adjunto' : ''),
        sender_id: message.sender_id,
        created_at: message.created_at,
        attachment_type: message.attachment_type,
      };
      const idx = this.chats.indexOf(chat);
      if (idx > 0) {
        this.chats.splice(idx, 1);
        this.chats.unshift(chat);
      }
    }
  }

  private clearMessageIds() {
    this.messageIds.clear();
  }

  private rebuildMessageIds() {
    this.clearMessageIds();
    for (const m of this.messages) {
      if (m.id) this.messageIds.add(m.id);
    }
  }

  onKeydown(event: Event) {
    const kb = event as KeyboardEvent;
    if (!kb.shiftKey) {
      kb.preventDefault();
      this.sendMessage();
    }
  }

  onFileSelected(event: any) {
    const file = event.target.files[0];
    this.setSelectedFile(file);
  }

  setSelectedFile(file: File | null) {
    this.revokePreview();
    this.selectedFile = file;
    this.selectedFileName = file ? file.name : '';
    if (file && file.type.startsWith('image/')) {
      this.selectedFilePreviewUrl = URL.createObjectURL(file);
    } else if (file && (file.type.startsWith('audio/') || file.type.startsWith('video/'))) {
      this.selectedFilePreviewUrl = URL.createObjectURL(file);
    } else {
      this.selectedFilePreviewUrl = null;
    }
    this.cdr.markForCheck();
  }

  clearFile() {
    this.setSelectedFile(null);
    if (this.fileInput) this.fileInput.nativeElement.value = '';
  }

  private revokePreview() {
    if (this.selectedFilePreviewUrl) {
      URL.revokeObjectURL(this.selectedFilePreviewUrl);
      this.selectedFilePreviewUrl = null;
    }
  }

  closeMobileChat() {
    this.mobileChatOpen = false;
    this.cdr.markForCheck();
  }

  sendMessage() {
    const text = this.newMessageText.trim();
    if ((!text && !this.selectedFile) || this.selectedChatId === null || this.selectedChatId < 0 || this.sending) return;

    this.sending = true;
    this.chatService.stopTyping(this.selectedChatId);

    const optimistic: MessageData = {
      id: -Date.now(),
      sender_id: this.currentUserId,
      receiver_id: this.selectedContact?.id || 0,
      body: text || '',
      status: 'sent',
      is_read: false,
      file_url: this.selectedFilePreviewUrl,
      attachment_type: this.selectedFile?.type.startsWith('image/')
        ? 'image'
        : this.selectedFile?.type.startsWith('audio/')
          ? 'audio'
          : this.selectedFile?.type.startsWith('video/')
            ? 'video'
            : this.selectedFile
              ? 'file'
              : null,
      created_at: new Date().toISOString(),
    };

    // animación inmediata
    this.messages = [...this.messages, optimistic];
    setTimeout(() => this.scrollToBottom(), 40);

    this.chatService
      .sendMessage(this.selectedChatId, text || undefined, this.selectedFile)
      .subscribe({
        next: (res: any) => {
          this.sending = false;
          // reemplazo el mensaje optimista por el real
          if (res?.success && res?.message) {
            const real = res.message;
            this.messages = this.messages
              .filter((m) => m.id !== optimistic.id && m.id !== real.id)
              .concat(real)
              .sort((a, b) => this.timeOf(a).localeCompare(this.timeOf(b)));
            this.messageIds.add(real.id);
          } else {
            this.markFailed(optimistic.id);
          }
          this.newMessageText = '';
          this.clearFile();
          this.cdr.markForCheck();
        },
        error: () => {
          this.sending = false;
          this.markFailed(optimistic.id);
          this.cdr.markForCheck();
        },
      });
  }

  private markFailed(id: number) {
    this.messages = this.messages.map((m) => (m.id === id ? { ...m, status: 'failed' } : m));
  }

  retryMessage(msg: MessageData) {
    if (!this.selectedChatId || this.selectedChatId < 0) return;
    this.messages = this.messages.map((m) => (m.id === msg.id ? { ...m, status: 'sent' } : m));
    this.chatService.sendMessage(this.selectedChatId, msg.body || undefined, null).subscribe({
next: (res: any) => {
          if (res?.success && res?.message) {
            const real = res.message;
            this.messages = this.messages
              .filter((m) => m.id !== msg.id && m.id !== real.id)
              .concat(real)
              .sort((a, b) => this.timeOf(a).localeCompare(this.timeOf(b)));
            this.messageIds.add(real.id);
          } else {
            this.markFailed(msg.id);
          }
          this.cdr.markForCheck();
        },
        error: () => {
          this.markFailed(msg.id);
          this.cdr.markForCheck();
        },
      });
    }

  onInput() {
    if (!this.selectedChatId || this.selectedChatId < 0) return;
    if (this.newMessageText.length === 1) {
      this.chatService.startTyping(this.selectedChatId);
    }
    if (this.newMessageText.length === 0) {
      this.chatService.stopTyping(this.selectedChatId);
    }
  }

  async startRecording() {
    if (!navigator.mediaDevices?.getUserMedia || this.isRecording) return;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mime = this.pickAudioMime();
      this.mediaRecorder = mime ? new MediaRecorder(stream, { mimeType: mime }) : new MediaRecorder(stream);
      this.audioChunks = [];
      this.recordingSeconds = 0;
      this.mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) this.audioChunks.push(event.data);
      };
      this.mediaRecorder.onstop = () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(this.audioChunks, { type: this.mediaRecorder?.mimeType || 'audio/webm' });
        const ext = this.extForMime(blob.type);
        this.setSelectedFile(new File([blob], `nota_${Date.now()}.${ext}`, { type: blob.type }));
      };
      this.mediaRecorder.start();
      this.isRecording = true;
      this.recordingPaused = false;
      this.startTicker();
      this.cdr.markForCheck();
    } catch {
      this.isRecording = false;
    }
  }

  private startTicker() {
    if (this.recTicker) clearInterval(this.recTicker);
    this.recTicker = setInterval(() => {
      this.recordingSeconds += 1;
      if (this.recordingSeconds >= 300) this.stopRecording(true);
      this.cdr.markForCheck();
    }, 1000);
  }

  togglePauseRecording() {
    if (!this.mediaRecorder) return;
    if (this.mediaRecorder.state === 'recording') {
      this.mediaRecorder.pause();
      this.recordingPaused = true;
      if (this.recTicker) {
        clearInterval(this.recTicker);
        this.recTicker = null;
      }
    } else if (this.mediaRecorder.state === 'paused') {
      this.mediaRecorder.resume();
      this.recordingPaused = false;
      this.startTicker();
    }
    this.cdr.markForCheck();
  }

  stopRecording(autoSend = false) {
    if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
      const mime = this.mediaRecorder.mimeType || 'audio/webm';
      const rec = this.mediaRecorder;
      rec.onstop = () => {
        rec.stream?.getTracks().forEach((t) => t.stop());
        const blob = this.audioChunks.length ? new Blob(this.audioChunks, { type: mime }) : null;
        if (blob) {
          const ext = this.extForMime(blob.type);
          this.setSelectedFile(new File([blob], `nota_${Date.now()}.${ext}`, { type: blob.type }));
        }
        this.finishRecordingUI();
        if (autoSend) {
          setTimeout(() => this.sendMessage(), 150);
        }
        this.cdr.markForCheck();
      };
      rec.stop();
    } else {
      this.finishRecordingUI();
    }
    this.isRecording = false;
  }

  private finishRecordingUI() {
    if (this.recTicker) {
      clearInterval(this.recTicker);
      this.recTicker = null;
    }
    this.recordingSeconds = 0;
    this.recordingPaused = false;
    this.mediaRecorder = null;
  }

  private clearRecording() {
    if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
      this.mediaRecorder.stream?.getTracks().forEach((t) => t.stop());
      try {
        this.mediaRecorder.stop();
      } catch {}
    }
    this.finishRecordingUI();
    if (this.audioBlobUrl) URL.revokeObjectURL(this.audioBlobUrl);
    this.audioBlobUrl = null;
  }

  private pickAudioMime(): string {
    const mimes = ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg;codecs=opus', 'audio/mp4'];
    if (typeof MediaRecorder === 'undefined') return '';
    for (const m of mimes) {
      try {
        if (MediaRecorder.isTypeSupported(m)) return m;
      } catch {}
    }
    return '';
  }

  private extForMime(mime: string): string {
    if (mime.includes('ogg')) return 'ogg';
    if (mime.includes('mp4') || mime.includes('aac') || mime.includes('m4a')) return 'm4a';
    if (mime.includes('wav') || mime.includes('wave')) return 'wav';
    return 'webm';
  }

  formatRecording(): string {
    const s = this.recordingSeconds;
    const mm = String(Math.floor(s / 60)).padStart(2, '0');
    const ss = String(s % 60).padStart(2, '0');
    return `${mm}:${ss}`;
  }

  get slideToCancel(): boolean {
    return this.isHoldMode && this.holdRecordingStarted && this.holdCancel;
  }

  canDeleteForAll(msg: MessageData): boolean {
    return this.isOwnMessage(msg);
  }

  onMicPointerDown(event: PointerEvent) {
    event.preventDefault();
    event.stopPropagation();
    const touch = event.pointerType === 'touch';
    this.holdPointerId = event.pointerId;
    this.holdStartX = event.clientX;
    this.holdStartY = event.clientY;
    this.holdCancel = false;
    this.holdRecordingStarted = false;
    this.isHoldMode = touch;
    if (!touch || this.isRecording) return;
    this.holdTimer = setTimeout(() => {
      if (this.holdPointerId !== null) {
        this.holdRecordingStarted = true;
        this.startRecording();
      }
    }, 120);
  }

  onMicPointerMove(event: PointerEvent) {
    if (!this.isHoldMode || event.pointerId !== this.holdPointerId) return;
    if (this.holdRecordingStarted && this.holdStartY - event.clientY > 70) {
      this.holdCancel = true;
      this.cdr.markForCheck();
    }
  }

  onMicPointerUp(event: PointerEvent) {
    if (event.pointerId !== this.holdPointerId) return;
    const wasHold = this.isHoldMode;
    const started = this.holdRecordingStarted;
    const cancelled = this.holdCancel;
    const dist = Math.hypot(event.clientX - this.holdStartX, event.clientY - this.holdStartY);
    if (this.holdTimer) {
      clearTimeout(this.holdTimer);
      this.holdTimer = null;
    }
    this.resetHold();
    if (wasHold) {
      if (started) {
        this.stopRecording(!cancelled);
      }
      return;
    }
    // Escritorio (mouse): clic sin arrastre = toggle audio
    if (dist < 8) {
      this.toggleRecordingToggle();
    }
    this.cdr.markForCheck();
  }

  onMicPointerCancel(event: PointerEvent) {
    if (event.pointerId !== this.holdPointerId) return;
    const started = this.holdRecordingStarted;
    if (this.holdTimer) {
      clearTimeout(this.holdTimer);
      this.holdTimer = null;
    }
    this.resetHold();
    if (started) this.stopRecording(false);
  }

  private resetHold() {
    this.holdPointerId = null;
    this.holdStartX = 0;
    this.holdStartY = 0;
    this.isHoldMode = false;
    this.holdRecordingStarted = false;
    this.holdCancel = false;
  }

  toggleRecordingToggle() {
    if (this.isRecording) {
      this.stopRecording(false);
    } else {
      this.startRecording();
    }
  }

  toggleDeleteMenu(msg: MessageData, event: Event) {
    event?.stopPropagation();
    this.deleteMenuId = this.deleteMenuId === msg.id ? null : msg.id;
    this.cdr.markForCheck();
  }

  closeDeleteMenu() {
    this.deleteMenuId = null;
    this.cdr.markForCheck();
  }

  deleteMessage(msg: MessageData, scope: 'me' | 'all') {
    if (!msg.id || msg.id < 0) return;
    if (scope === 'all' && !this.canDeleteForAll(msg)) return;
    this.closeDeleteMenu();
    if (!this.selectedChatId || this.selectedChatId < 0) return;
    this.applyMessageDeleted(this.selectedChatId, msg.id, scope, false);
    this.chatService.deleteMessage(this.selectedChatId, msg.id, scope).subscribe({
      error: () => this.cdr.markForCheck(),
    });
  }

  private applyMessageDeleted(chatId: number, messageId: number, mode: string, fromSocket: boolean) {
    if (mode === 'all') {
      this.messages = this.messages.map((m) =>
        m.id === messageId
          ? { ...m, deleted: true, body: 'Este mensaje fue eliminado', file_url: null, attachment_type: null }
          : m
      );
    } else {
      this.messages = this.messages.filter((m) => m.id !== messageId);
    }
    const chat = this.chats.find((c) => c.id === chatId);
    if (chat?.last_message?.id === messageId) {
      chat.last_message = { ...chat.last_message, body: 'Este mensaje fue eliminado', attachment_type: null };
    }
    if (this.audioPlayingId === messageId) {
      const el = this.audioEls.get(messageId);
      el?.pause();
      this.audioPlayingId = null;
    }
    this.cdr.markForCheck();
  }

  toggleAudio(msg: MessageData) {
    if (!msg.file_url || msg.deleted) return;
    if (this.audioPlayingId !== null && this.audioPlayingId !== msg.id) {
      this.pauseAudio(this.audioPlayingId);
    }
    if (this.audioPlayingId === msg.id) {
      this.pauseAudio(msg.id);
      this.audioPlayingId = null;
      this.cdr.markForCheck();
      return;
    }
    let el = this.audioEls.get(msg.id);
    if (!el) {
      el = new Audio(msg.file_url);
      this.audioEls.set(msg.id, el);
      el.addEventListener('timeupdate', () => this.cdr.markForCheck());
      el.addEventListener('ended', () => {
        this.audioPlayingId = null;
        this.cdr.markForCheck();
      });
    }
    el.play().catch(() => {});
    this.audioPlayingId = msg.id;
    this.cdr.markForCheck();
  }

  private pauseAudio(id: number) {
    const el = this.audioEls.get(id);
    el?.pause();
  }

  audioTime(msg: MessageData): string {
    return this.formatAudioTime(this.audioEls.get(msg.id)?.currentTime ?? 0);
  }

  audioDuration(msg: MessageData): string {
    return this.formatAudioTime(this.audioEls.get(msg.id)?.duration ?? 0);
  }

  audioProgress(msg: MessageData): number {
    const el = this.audioEls.get(msg.id);
    if (!el || !el.duration) return 0;
    return Math.min(100, (el.currentTime / el.duration) * 100);
  }

  seekAudio(msg: MessageData, event: Event) {
    const el = this.audioEls.get(msg.id);
    const input = event.target as HTMLInputElement;
    if (el && el.duration && input?.value != null) {
      el.currentTime = (parseFloat(input.value) / 100) * el.duration;
    }
  }

  audioBars(msg: MessageData): number[] {
    const bars: number[] = [];
    let seed = ((msg.id >= 0 ? msg.id : -msg.id) * 2654435761) % 4096;
    seed = seed === 0 ? 12345 : seed;
    for (let i = 0; i < 28; i++) {
      seed = (seed * 1103515245 + 12345) % 2147483648;
      const v = (seed >> 16) & 0x7fff;
      bars.push(0.25 + (v % 70) / 100);
    }
    return bars;
  }

  playedBar(msg: MessageData, idx: number): boolean {
    const el = this.audioEls.get(msg.id);
    if (!el || !el.duration || !el.currentTime) return false;
    return idx / 28 < el.currentTime / el.duration;
  }

  private formatAudioTime(sec: number): string {
    if (!sec || isNaN(sec) || sec < 0) return '0:00';
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    return `${m}:${String(s).padStart(2, '0')}`;
  }

  isOwnMessage(msg: MessageData): boolean {
    return msg.sender_id === this.currentUserId;
  }

  isOnline(userId: number): boolean {
    return this.onlineUsers.has(userId);
  }

  totalUnread(): number {
    return this.chats.reduce((sum, c) => sum + c.unread_count, 0);
  }

  statusIcon(msg: MessageData): any {
    if (msg.status === 'failed') return ['fas', 'triangle-exclamation'];
    if (msg.sender_id !== this.currentUserId) return null;
    if (msg.status === 'read') return ['fas', 'check-double'];
    if (msg.status === 'delivered' || msg.status === 'sent') return ['fas', 'check-double'];
    return ['fas', 'check'];
  }

  statusColor(msg: MessageData): string {
    if (msg.status === 'failed') return 'text-error';
    if (msg.sender_id !== this.currentUserId) return '';
    if (msg.status === 'read') return 'text-info';
    if (msg.status === 'delivered' || msg.status === 'sent') return 'text-on-surface-variant';
    return 'text-on-surface-variant/50';
  }

  openImage(url: string | null, title: string | null = null) {
    if (!url) return;
    this.lightboxUrl = url;
    this.lightboxTitle = title || '';
    this.cdr.markForCheck();
  }

  closeLightbox() {
    this.lightboxUrl = null;
    this.cdr.markForCheck();
  }

  openAiPreview(msg: MessageData) {
    if (!msg.file_url) return;
    this.aiPreview = { open: true, msg, loading: true, data: null, error: null };
    this.chatService.aiPreview(msg.id).subscribe({
      next: (res: any) => {
        this.aiPreview.loading = false;
        this.aiPreview.data = res?.success ? res.preview : null;
        if (!res?.success) this.aiPreview.error = res?.message || 'Error';
      },
      error: () => {
        this.aiPreview.loading = false;
        this.aiPreview.error = 'Error de conexión';
      },
    });
  }

  closeAiPreview() {
    this.aiPreview.open = false;
    this.cdr.markForCheck();
  }

  openFile(url: string) {
    window.open(url, '_blank');
  }

  downloadFile(url: string, name?: string | null) {
    const a = document.createElement('a');
    a.href = url;
    a.download = name || '';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  }

  fileIcon(msg: MessageData): any {
    const name = this.fileName(msg.file_url) || '';
    const ext = name.split('.').pop()?.toLowerCase() || '';
    if (msg.attachment_type === 'image') return ['fas', 'image'];
    if (msg.attachment_type === 'audio') return ['fas', 'headphones'];
    if (msg.attachment_type === 'video') return ['fas', 'video'];
    if (['pdf'].includes(ext)) return ['fas', 'file-pdf'];
    if (['doc', 'docx'].includes(ext)) return ['fas', 'file-word'];
    if (['xls', 'xlsx', 'csv'].includes(ext)) return ['fas', 'file-excel'];
    if (['zip', 'rar', '7z', 'tar', 'gz'].includes(ext)) return ['fas', 'file-zipper'];
    if (['mp3', 'wav', 'ogg', 'm4a', 'webm'].includes(ext)) return ['fas', 'file-audio'];
    if (['mp4', 'mov', 'avi', 'mkv'].includes(ext)) return ['fas', 'file-video'];
    return ['fas', 'file'];
  }

  fileName(url: string | null): string | null {
    if (!url) return null;
    try {
      const parts = url.split('/');
      return parts[parts.length - 1] || null;
    } catch {
      return null;
    }
  }

  isImageUpload(): boolean {
    return !!this.selectedFile && this.selectedFile.type.startsWith('image/');
  }

  isAudioUpload(): boolean {
    return !!this.selectedFile && this.selectedFile.type.startsWith('audio/');
  }

  isDocUpload(): boolean {
    return !!this.selectedFile && !this.selectedFile.type.startsWith('image/');
  }

  isRecorderOverlay(): boolean {
    return this.isRecording;
  }

  scrollToBottom() {
    setTimeout(() => {
      if (this.chatMessages) {
        try {
          this.chatMessages.nativeElement.scrollTop = this.chatMessages.nativeElement.scrollHeight;
        } catch {}
      }
    }, 60);
  }

  trackById(_: number, item: any): number {
    return item.id;
  }

  private timeOf(m: MessageData): string {
    return m.created_at || '';
  }

  sameDayAsPrev(index: number): boolean {
    if (index <= 0) return false;
    const cur = this.messages[index];
    const prev = this.messages[index - 1];
    if (!cur?.created_at || !prev?.created_at) return false;
    return this.dayKey(cur.created_at) === this.dayKey(prev.created_at);
  }

  private dayKey(iso: string): string {
    const d = new Date(iso);
    if (isNaN(d.getTime())) return iso.slice(0, 10);
    return `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`;
  }

  formatDayLabel(value: string | null): string {
    if (!value) return '';
    const d = new Date(value);
    if (isNaN(d.getTime())) return value.slice(0, 10);
    const today = new Date();
    const yesterday = new Date(today.getTime() - 86400000);
    const sameDay = (a: Date, b: Date) =>
      a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
    if (sameDay(d, today)) return 'Hoy';
    if (sameDay(d, yesterday)) return 'Ayer';
    const sameYear = d.getFullYear() === today.getFullYear();
    return d.toLocaleDateString('es-PE', {
      weekday: 'long',
      day: 'numeric',
      month: 'long',
      ...(sameYear ? {} : { year: 'numeric' }),
    });
  }

  displayRole(role: string): string {
    if (!role) return '';
    const normalized: Record<string, string> = {
      admin: 'admin',
      supervisor: 'supervisor',
      terapista: 'terapista',
      terapeuta: 'terapista',
      paciente: 'paciente',
      jugador: 'paciente',
    };
    return normalized[role] || role;
  }

  isSameDay(value: string | null): boolean {
    if (!value) return false;
    const d = new Date(value);
    if (isNaN(d.getTime())) return false;
    const today = new Date();
    return (
      d.getFullYear() === today.getFullYear() &&
      d.getMonth() === today.getMonth() &&
      d.getDate() === today.getDate()
    );
  }
}
