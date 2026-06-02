import { Component, OnInit, OnDestroy, ViewChild, ElementRef, AfterViewInit, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { Subscription } from 'rxjs';
import { HeaderService } from '../../../../core/services/header.service';
import { PatientService } from '../../../../core/services/patient.service';
import { AuthService } from '../../../../core/services/auth.service';
import { fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter } from '../../../../core/animations';
import { Spinner } from '../../../../shared/components/spinner/spinner';
import { Button } from '../../../../shared/components/button/button';

@Component({
  selector: 'app-patient-messages',
  standalone: true,
  imports: [CommonModule, FormsModule, FontAwesomeModule, Spinner, Button],
  templateUrl: './messages.html',
  styleUrl: './messages.scss',
  animations: [fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class PatientMessages implements OnInit, OnDestroy, AfterViewInit {
  @ViewChild('chatContainer') chatContainer!: ElementRef;
  @ViewChild('fileInput') fileInput!: ElementRef;

  loading = true;
  messages: any[] = [];
  newMessage = '';
  therapistId: number | null = null;
  therapistName = '';
  sending = false;
  currentUserId = 0;
  selectedFile: File | null = null;
  selectedFileName = '';
  isRecording = false;
  error: string | null = null;
  mediaRecorder: MediaRecorder | null = null;
  audioChunks: Blob[] = [];

  private pollInterval: any;
  private needsScroll = false;
  private subs = new Subscription();

  constructor(
    private headerService: HeaderService,
    private patientService: PatientService,
    private auth: AuthService,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit() {
    this.headerService.setConfig({
      title: 'Mensajes',
      subtitle: 'Comunicación con tu terapeuta',
      icon: ['fas', 'envelope'],
    });

    this.subs.add(this.auth.currentUser$.subscribe((user) => {
      if (user) this.currentUserId = user.id;
      this.cdr.markForCheck();
    }));

    this.loadTherapist();
    this.loadMessages();
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

  private loadTherapist() {
    this.subs.add(this.patientService.getMyTherapist().subscribe({
      next: (res) => {
        if (res.success && res.data) {
          this.therapistId = res.data.id;
          this.therapistName = res.data.username;
          this.cdr.markForCheck();
        }
      },
      error: (err) => {
        this.error = err.message;
        this.cdr.markForCheck();
      },
    }));
  }

  private loadMessages() {
    this.subs.add(this.patientService.getMessages().subscribe({
      next: (res) => {
        if (res.success) {
          this.messages = res.messages;
          if (res.messages.length > 0 && !this.therapistId) {
            this.therapistId = res.messages[0].sender_id === this.currentUserId
              ? res.messages[0].receiver_id
              : res.messages[0].sender_id;
          }
          this.needsScroll = true;
          setTimeout(() => this.scrollToBottom(), 100);
        }
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

  private pollNewMessages() {
    if (!this.therapistId) return;
    this.subs.add(this.patientService.getMessages().subscribe({
      next: (res) => {
        if (res.success && res.messages.length > this.messages.length) {
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
  }

  isOwnMessage(msg: any): boolean {
    return msg.sender_id === this.currentUserId;
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

  onKeydown(event: Event) {
    const kbEvent = event as KeyboardEvent;
    if (!kbEvent.shiftKey) {
      kbEvent.preventDefault();
      this.sendMessage();
    }
  }

  sendMessage() {
    if ((!this.newMessage.trim() && !this.selectedFile) || !this.therapistId || this.sending) return;

    this.sending = true;
    this.cdr.markForCheck();
    this.subs.add(this.patientService.sendMessage(this.therapistId, this.newMessage.trim(), this.selectedFile).subscribe({
      next: () => {
        this.sending = false;
        this.newMessage = '';
        this.clearFile();
        this.cdr.markForCheck();
        this.loadMessages();
      },
      error: (err) => {
        this.sending = false;
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
