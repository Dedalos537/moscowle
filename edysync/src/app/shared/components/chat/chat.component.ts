import { Component, OnInit, OnDestroy, ViewChild, ElementRef, ChangeDetectorRef, ChangeDetectionStrategy } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { DatePipe } from '@angular/common';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { ChatService, ContactUser, ChatItem, MessageData } from '../../../core/services/chat.service';
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
    paciente: 'Paciente',
  };
  roleOrder = ['admin', 'supervisor', 'terapista', 'paciente'];

  selectedChatId: number | null = null;
  selectedContact: ContactUser | null = null;
  newMessageText = '';
  selectedFile: File | null = null;
  selectedFileName = '';
  sending = false;
  loading = true;
  loadingMessages = false;
  onlineUsers = new Set<number>();

  typingUsers: Map<number, { username: string; timeout: any }> = new Map();
  typingChatId: number | null = null;

  isRecording = false;
  mediaRecorder: MediaRecorder | null = null;
  audioChunks: Blob[] = [];

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

    this.auth.currentUser$.subscribe((user) => {
      if (user) {
        this.currentUserId = user.id;
        this.userRole = user.role;
        this.chatService.connect();
        this.loadData();
      }
    });

    this.subs.push(
      this.chatService.onlineUsers$.subscribe((online) => {
        this.onlineUsers = online;
        this.cdr.markForCheck();
      })
    );

    this.subs.push(
      this.chatService.newMessage$.subscribe(({ chat_id, message }) => {
        if (chat_id === this.selectedChatId) {
          this.messages = [...this.messages, message];
          this.scrollToBottom();
        }
        this.updateChatLastMessage(chat_id, message);
        this.cdr.markForCheck();
      })
    );

    this.subs.push(
      this.chatService.messageStatus$.subscribe(({ chat_id, status }) => {
        if (chat_id === this.selectedChatId) {
          this.messages = this.messages.map((m) =>
            m.sender_id !== this.currentUserId && m.status !== 'read'
              ? { ...m, status, is_read: status === 'read' }
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
            this.typingChatId = null;
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
  }

  ngOnDestroy() {
    this.headerService.reset();
    if (this.selectedChatId && this.selectedChatId > 0) this.chatService.leaveChat(this.selectedChatId);
    this.subs.forEach((s) => s.unsubscribe());
  }

  private loadData() {
    this.loading = true;
    this.chatService.getChats().subscribe({
      next: (chats) => {
        this.chats = chats;
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
    return this.userRole === 'admin' || this.userRole === 'supervisor';
  }

  get groupedContacts(): { role: string; users: ContactUser[] }[] {
    const groups: { role: string; users: ContactUser[] }[] = [];
    for (const role of this.roleOrder) {
      const users = this.filteredContacts.filter((c) => c.role === role);
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
    this.chatService.createChat(contact.id).subscribe({
      next: (res) => {
        this.selectedChatId = res.chat_id;
        this.chatService.joinChat(res.chat_id);
        this.loadMessages();
        this.chatService.markRead(res.chat_id).subscribe();
      },
      error: () => (this.loadingMessages = false),
    });
  }

  selectChat(chat: ChatItem) {
    this.selectedChatId = chat.id;
    this.selectedContact = chat.other_user;
    this.loadingMessages = true;

    if (chat.id > 0) {
      this.chatService.joinChat(chat.id);
    }

    if (chat.unread_count > 0) {
      this.chatService.markRead(chat.id).subscribe();
    }

    this.loadMessages();
    this.markChatRead(chat.id);
  }

  private loadMessages() {
    if (!this.selectedChatId) return;
    this.chatService.getMessages(this.selectedChatId).subscribe({
      next: (res) => {
        this.messages = res.messages;
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

  private updateChatLastMessage(chatId: number, message: MessageData) {
    const chat = this.chats.find((c) => c.id === chatId);
    if (chat) {
      chat.last_message = {
        id: message.id,
        body: message.body || (message.attachment_type ? 'Archivo adjunto' : ''),
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

  onKeydown(event: Event) {
    const kb = event as KeyboardEvent;
    if (!kb.shiftKey) {
      kb.preventDefault();
      this.sendMessage();
    }
  }

  onFileSelected(event: any) {
    const file = event.target.files[0];
    if (file) {
      this.selectedFile = file;
      this.selectedFileName = file.name;
    }
  }

  clearFile() {
    this.selectedFile = null;
    this.selectedFileName = '';
    if (this.fileInput) this.fileInput.nativeElement.value = '';
  }

  sendMessage() {
    if ((!this.newMessageText.trim() && !this.selectedFile) || !this.selectedChatId || this.sending) return;
    if (this.selectedChatId < 0) return;
    this.sending = true;
    this.chatService.stopTyping(this.selectedChatId);
    this.chatService.sendMessage(this.selectedChatId, this.newMessageText.trim() || undefined, this.selectedFile).subscribe({
      next: () => {
        this.sending = false;
        this.newMessageText = '';
        this.clearFile();
        this.cdr.markForCheck();
      },
      error: () => (this.sending = false),
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

  startRecording() {
    if (!navigator.mediaDevices?.getUserMedia) return;
    this.isRecording = true;
    this.audioChunks = [];
    navigator.mediaDevices.getUserMedia({ audio: true }).then((stream) => {
      this.mediaRecorder = new MediaRecorder(stream);
      this.mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) this.audioChunks.push(event.data);
      };
      this.mediaRecorder.onstop = () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(this.audioChunks, { type: 'audio/webm' });
        this.selectedFile = new File([blob], `audio_${Date.now()}.webm`, { type: 'audio/webm' });
        this.selectedFileName = this.selectedFile.name;
      };
      this.mediaRecorder.start();
    }).catch(() => (this.isRecording = false));
  }

  stopRecording() {
    if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
      this.mediaRecorder.stop();
      this.isRecording = false;
    }
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
    if (msg.sender_id !== this.currentUserId) return null;
    if (msg.status === 'read') return ['fas', 'check-double'];
    if (msg.status === 'delivered') return ['fas', 'check-double'];
    return ['fas', 'check'];
  }

  statusColor(msg: MessageData): string {
    if (msg.sender_id !== this.currentUserId) return '';
    if (msg.status === 'read') return 'text-info';
    if (msg.status === 'delivered') return 'text-on-surface-variant';
    return 'text-on-surface-variant/50';
  }

  openFile(url: string) {
    window.open(url, '_blank');
  }

  private scrollToBottom() {
    setTimeout(() => {
      if (this.chatMessages) {
        try {
          this.chatMessages.nativeElement.scrollTop = this.chatMessages.nativeElement.scrollHeight;
        } catch {}
      }
    }, 50);
  }

  trackById(_: number, item: any): number {
    return item.id;
  }
}
