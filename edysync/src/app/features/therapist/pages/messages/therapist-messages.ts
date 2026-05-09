import { Component, OnInit, OnDestroy, ViewChild, TemplateRef, ElementRef, AfterViewChecked } from '@angular/core';
import { TherapistService, Conversation, MessageItem } from '../../../../core/services/therapist.service';
import { HeaderService } from '../../../../core/services/header.service';
import { AuthService } from '../../../../core/services/auth.service';

@Component({
  selector: 'app-therapist-messages',
  standalone: false,
  templateUrl: './therapist-messages.html',
  styleUrl: './therapist-messages.scss',
})
export class TherapistMessages implements OnInit, OnDestroy, AfterViewChecked {
  @ViewChild('headerActions', { static: true }) headerActions!: TemplateRef<any>;
  @ViewChild('chatContainer') chatContainer!: ElementRef;
  @ViewChild('fileInput') fileInput!: ElementRef;

  conversations: Conversation[] = [];
  selectedUserId: number | null = null;
  selectedUserName = '';
  messages: MessageItem[] = [];
  currentUserId = 0;

  newMessage = '';
  selectedFile: File | null = null;
  selectedFileName = '';
  sending = false;
  loading = true;
  loadingThread = false;
  isRecording = false;
  mediaRecorder: MediaRecorder | null = null;
  audioChunks: Blob[] = [];

  private pollInterval: any;

  constructor(
    private therapistService: TherapistService,
    private headerService: HeaderService,
    private auth: AuthService,
  ) {}

  ngOnInit() {
    this.headerService.setConfig({
      title: 'Mensajes',
      subtitle: 'Conversaciones con tus pacientes',
      icon: ['fas', 'envelope'],
      actionTemplate: this.headerActions,
    });

    this.auth.currentUser$.subscribe((user) => {
      if (user) this.currentUserId = user.id;
    });

    this.loadConversations();
    this.pollInterval = setInterval(() => this.pollNewMessages(), 5000);
  }

  ngAfterViewChecked() {
    this.scrollToBottom();
  }

  ngOnDestroy() {
    this.headerService.reset();
    if (this.pollInterval) clearInterval(this.pollInterval);
  }

  private loadConversations() {
    this.loading = true;
    this.therapistService.getConversations().subscribe({
      next: (res) => {
        this.conversations = res.conversations;
        this.loading = false;
      },
      error: () => (this.loading = false),
    });
  }

  selectConversation(userId: number, userName: string) {
    this.selectedUserId = userId;
    this.selectedUserName = userName;
    this.loadingThread = true;
    this.messages = [];
    this.newMessage = '';
    this.selectedFile = null;
    this.selectedFileName = '';

    this.therapistService.getMessageThread(userId).subscribe({
      next: (res) => {
        this.messages = res.messages;
        this.loadingThread = false;
        this.markConversationRead(userId);
      },
      error: () => (this.loadingThread = false),
    });
  }

  private markConversationRead(userId: number) {
    const conv = this.conversations.find((c) => c.user_id === userId);
    if (conv) conv.unread_count = 0;
  }

  private pollNewMessages() {
    if (!this.selectedUserId) return;
    this.therapistService.getMessageThread(this.selectedUserId).subscribe({
      next: (res) => {
        if (res.messages.length > this.messages.length) {
          this.messages = res.messages;
        }
      },
    });
  }

  onKeydown(event: Event) {
    const kbEvent = event as KeyboardEvent;
    if (!kbEvent.shiftKey) {
      kbEvent.preventDefault();
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
    if ((!this.newMessage.trim() && !this.selectedFile) || !this.selectedUserId) return;

    this.sending = true;
    this.therapistService.sendMessage(this.selectedUserId, this.newMessage.trim(), this.selectedFile).subscribe({
      next: () => {
        this.sending = false;
        this.newMessage = '';
        this.clearFile();
        this.refreshThread();
      },
      error: () => (this.sending = false),
    });
  }

  private refreshThread() {
    if (!this.selectedUserId) return;
    this.therapistService.getMessageThread(this.selectedUserId).subscribe({
      next: (res) => (this.messages = res.messages),
    });
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
    }).catch(() => {
      this.isRecording = false;
    });
  }

  stopRecording() {
    if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
      this.mediaRecorder.stop();
      this.isRecording = false;
    }
  }

  isOwnMessage(msg: MessageItem): boolean {
    return msg.sender_id === this.currentUserId;
  }

  getFileIcon(fileType: string | null): string {
    if (!fileType) return 'fas fa-file';
    if (fileType.startsWith('image/')) return 'fas fa-image';
    if (fileType.startsWith('video/')) return 'fas fa-video';
    if (fileType.startsWith('audio/')) return 'fas fa-music';
    return 'fas fa-file';
  }

  private scrollToBottom() {
    if (this.chatContainer) {
      try {
        this.chatContainer.nativeElement.scrollTop = this.chatContainer.nativeElement.scrollHeight;
      } catch {}
    }
  }
}
