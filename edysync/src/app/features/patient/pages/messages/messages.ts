// DCE — Diego Centeno Estuvo Acá
import { Component, OnInit, OnDestroy, ViewChild, ElementRef, AfterViewInit } from '@angular/core';
import { HeaderService } from '../../../../core/services/header.service';
import { PatientService } from '../../../../core/services/patient.service';
import { AuthService } from '../../../../core/services/auth.service';
import { fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter } from '../../../../core/animations';

@Component({
  selector: 'app-patient-messages',
  standalone: false,
  templateUrl: './messages.html',
  styleUrl: './messages.scss',
  animations: [fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter]
})
export class PatientMessages implements OnInit, OnDestroy, AfterViewInit {
  @ViewChild('chatContainer') chatContainer!: ElementRef;

  loading = true;
  messages: any[] = [];
  newMessage = '';
  therapistId: number | null = null;
  therapistName = '';
  sending = false;
  currentUserId = 0;

  private pollInterval: any;
  private needsScroll = false;

  constructor(
    private headerService: HeaderService,
    private patientService: PatientService,
    private auth: AuthService,
  ) {}

  ngOnInit() {
    this.headerService.setConfig({
      title: 'Mensajes',
      subtitle: 'Comunicación con tu terapeuta',
      icon: ['fas', 'envelope'],
    });

    this.auth.currentUser$.subscribe((user) => {
      if (user) this.currentUserId = user.id;
    });

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
  }

  private loadTherapist() {
    this.patientService.getMyTherapist().subscribe({
      next: (res) => {
        if (res.success && res.data) {
          this.therapistId = res.data.id;
          this.therapistName = res.data.username;
        }
      },
    });
  }

  private loadMessages() {
    this.patientService.getMessages().subscribe({
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
      },
      error: () => (this.loading = false),
    });
  }

  private pollNewMessages() {
    if (!this.therapistId) return;
    this.patientService.getMessages().subscribe({
      next: (res) => {
        if (res.success && res.messages.length > this.messages.length) {
          this.messages = res.messages;
          this.needsScroll = true;
          setTimeout(() => this.scrollToBottom(), 100);
        }
      },
    });
  }

  isOwnMessage(msg: any): boolean {
    return msg.sender_id === this.currentUserId;
  }

  onKeydown(event: Event) {
    const kbEvent = event as KeyboardEvent;
    if (!kbEvent.shiftKey) {
      kbEvent.preventDefault();
      this.sendMessage();
    }
  }

  sendMessage() {
    if (!this.newMessage.trim() || !this.therapistId || this.sending) return;

    this.sending = true;
    this.patientService.sendMessage(this.therapistId, this.newMessage).subscribe({
      next: () => {
        this.sending = false;
        this.newMessage = '';
        this.loadMessages();
      },
      error: () => {
        this.sending = false;
      },
    });
  }

  private scrollToBottom() {
    if (this.chatContainer) {
      try {
        this.chatContainer.nativeElement.scrollTop = this.chatContainer.nativeElement.scrollHeight;
      } catch {}
    }
  }
}
