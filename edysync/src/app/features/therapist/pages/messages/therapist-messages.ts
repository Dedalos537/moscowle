import { CommonModule } from '@angular/common';
import { Component, OnInit, OnDestroy, ViewChild, TemplateRef, ElementRef, AfterViewInit, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { Subscription } from 'rxjs';
import { TherapistService, Conversation, MessageItem } from '../../../../core/services/therapist.service';
import { HeaderService } from '../../../../core/services/header.service';
import { AuthService } from '../../../../core/services/auth.service';
import { fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter } from '../../../../core/animations';
import { Spinner } from '../../../../shared/components/spinner/spinner';
import { Button } from '../../../../shared/components/button/button';

@Component({
  selector: 'app-therapist-messages',
  standalone: true,
  imports: [CommonModule, FormsModule, FontAwesomeModule, Spinner, Button],
  templateUrl: './therapist-messages.html',
  styleUrl: './therapist-messages.scss',
  animations: [fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class TherapistMessages implements OnInit, OnDestroy, AfterViewInit {
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
  error: string | null = null;
  mediaRecorder: MediaRecorder | null = null;
  audioChunks: Blob[] = [];

  private pollInterval: any;
  private needsScroll = false;
  private subs = new Subscription();

  constructor(
    private therapistService: TherapistService,
    private headerService: HeaderService,
    private auth: AuthService,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit() {
    this.headerService.setConfig({
      title: 'Mensajes',
      subtitle: 'Conversaciones con tus pacientes',
      icon: ['fas', 'envelope'],
      actionTemplate: this.headerActions,
    });

    this.subs.add(this.auth.currentUser$.subscribe((user) => {
      if (user) this.currentUserId = user.id;
      this.cdr.markForCheck();
    }));

    this.loadConversations();
    this.pollInterval = setInterval(() => this.pollNewMessages(), 5000);
  }

  ngAfterViewInit() {
    setTimeout(() => this.scrollToBottom(), 300);
  }

  ngOnDestroy() {
    this.headerService.reset();
    if (this.pollInterval) clearInterval(this.pollInterval);
    this.subs.unsubscribe();
  }

  private loadConversations() {
    this.loading = true;
    this.cdr.markForCheck();
    this.subs.add(this.therapistService.getConversations().subscribe({
      next: (res) => {
        this.conversations = res.conversations;
        this.loading = false;
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.loading = false;
        this.error = err.message;
        this.cdr.markForCheck();
      },
    }));
  }

  selectConversation(userId: number, userName: string) {
    this.selectedUserId = userId;
    this.selectedUserName = userName;
    this.loadingThread = true;
    this.messages = [];
    this.newMessage = '';
    this.selectedFile = null;
    this.selectedFileName = '';
    this.cdr.markForCheck();

    this.subs.add(this.therapistService.getMessageThread(userId).subscribe({
      next: (res) => {
        this.messages = res.messages;
        this.loadingThread = false;
        this.markConversationRead(userId);
        this.needsScroll = true;
        this.cdr.markForCheck();
        setTimeout(() => this.scrollToBottom(), 100);
      },
      error: (err) => {
        this.loadingThread = false;
        this.error = err.message;
        this.cdr.markForCheck();
      },
    }));
  }

  private markConversationRead(userId: number) {
    const conv = this.conversations.find((c) => c.user_id === userId);
    if (conv) conv.unread_count = 0;
  }

  private pollNewMessages() {
    if (!this.selectedUserId) return;
    this.subs.add(this.therapistService.getMessageThread(this.selectedUserId).subscribe({
      next: (res) => {
        if (res.messages.length > this.messages.length) {
          this.messages = res.messages;
          this.needsScroll = true;
          this.cdr.markForCheck();
          setTimeout(() => this.scrollToBottom(), 100);
        }
      },
      error: (err) => {
        this.error = err.message;
        this.cdr.markForCheck();
      },
    }));
    this.subs.add(this.therapistService.getConversations().subscribe({
      next: (res) => {
        this.conversations = res.conversations;
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.error = err.message;
        this.cdr.markForCheck();
      },
    }));
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
    if ((!this.newMessage.trim() && !this.selectedFile) || !this.selectedUserId || this.sending) return;

    this.sending = true;
    this.cdr.markForCheck();
    this.subs.add(this.therapistService.sendMessage(this.selectedUserId, this.newMessage.trim(), this.selectedFile).subscribe({
      next: () => {
        this.sending = false;
        this.newMessage = '';
        this.clearFile();
        this.cdr.markForCheck();
        this.refreshThread();
      },
      error: (err) => {
        this.sending = false;
        this.error = err.message;
        this.cdr.markForCheck();
      },
    }));
  }

  private refreshThread() {
    if (!this.selectedUserId) return;
    this.subs.add(this.therapistService.getMessageThread(this.selectedUserId).subscribe({
      next: (res) => {
        this.messages = res.messages;
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.error = err.message;
        this.cdr.markForCheck();
      },
    }));
  }

  startRecording() {
    if (!navigator.mediaDevices?.getUserMedia) return;
    this.isRecording = true;
    this.cdr.markForCheck();
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
        this.cdr.markForCheck();
      };
      this.mediaRecorder.start();
    }).catch(() => {
      this.isRecording = false;
      this.cdr.markForCheck();
    });
  }

  stopRecording() {
    if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
      this.mediaRecorder.stop();
      this.isRecording = false;
      this.cdr.markForCheck();
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
