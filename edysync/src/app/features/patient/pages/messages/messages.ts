import { Component, OnInit } from '@angular/core';
import { HeaderService } from '../../../../core/services/header.service';
import { PatientService } from '../../../../core/services/patient.service';
import { fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter } from '../../../../core/animations';

@Component({
  selector: 'app-patient-messages',
  standalone: false,
  templateUrl: './messages.html',
  styleUrl: './messages.scss',
  animations: [fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter]
})
export class PatientMessages implements OnInit {
  loading = true;
  messages: any[] = [];
  newMessage = '';
  therapistId: number | null = null;

  constructor(
    private headerService: HeaderService,
    private patientService: PatientService
  ) {}

  ngOnInit() {
    this.headerService.setConfig({
      title: 'Mensajes',
      subtitle: 'Comunicación con tu terapeuta',
      icon: ['fas', 'envelope'],
    });
    this.loadMessages();
  }

  private loadMessages() {
    this.patientService.getMessages().subscribe({
      next: (res) => {
        if (res.success) {
          this.messages = res.messages;
          if (res.messages.length > 0) {
            this.therapistId = res.messages[0].sender_id || res.messages[0].receiver_id;
          }
        }
        this.loading = false;
      },
      error: () => (this.loading = false),
    });
  }

  sendMessage() {
    if (!this.newMessage.trim() || !this.therapistId) return;
    this.patientService.sendMessage(this.therapistId, this.newMessage).subscribe({
      next: () => {
        this.newMessage = '';
        this.loadMessages();
      },
    });
  }
}
