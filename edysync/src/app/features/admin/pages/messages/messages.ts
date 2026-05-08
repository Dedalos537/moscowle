import { Component, OnInit, OnDestroy, ViewChild, TemplateRef } from '@angular/core';
import { AdminService } from '../../../../core/services/admin.service';
import { HeaderService } from '../../../../core/services/header.service';
import { ContactMessage } from '../../../../core/models/expense';

@Component({
  selector: 'app-messages',
  standalone: false,
  templateUrl: './messages.html',
  styleUrl: './messages.scss',
})
export class Messages implements OnInit, OnDestroy {
  @ViewChild('headerActions', { static: true }) headerActions!: TemplateRef<any>;

  contactMessages: ContactMessage[] = [];
  therapists: { id: number; username: string }[] = [];
  patients: { id: number; username: string }[] = [];
  loading = true;

  selectedTab: 'therapists' | 'patients' = 'therapists';
  selectedReceiverId: number | null = null;
  subject = '';
  body = '';
  sending = false;
  statusText = '';

  constructor(
    private adminService: AdminService,
    private headerService: HeaderService,
  ) {}

  ngOnInit() {
    this.headerService.setConfig({
      title: 'Mensajería',
      subtitle: 'Enviar mensajes a terapeutas y pacientes',
      icon: ['fas', 'envelope'],
      actionTemplate: this.headerActions,
    });
    this.loadData();
  }

  ngOnDestroy() {
    this.headerService.reset();
  }

  private loadData() {
    this.adminService.getContactMessages().subscribe({
      next: (res) => (this.contactMessages = res.data),
    });
    this.adminService.getUsers('terapista').subscribe({
      next: (res) => (this.therapists = res.users.map((u) => ({ id: u.id, username: u.username }))),
    });
    this.adminService.getUsers('jugador').subscribe({
      next: (res) => {
        this.patients = res.users.map((u) => ({ id: u.id, username: u.username }));
        this.loading = false;
      },
      error: () => (this.loading = false),
    });
  }

  switchTab(tab: 'therapists' | 'patients') {
    this.selectedTab = tab;
    this.selectedReceiverId = null;
  }

  selectReceiver(id: number) {
    this.selectedReceiverId = id;
    this.statusText = `Destinatario seleccionado (ID: ${id})`;
  }

  sanitizePhone(phone: string): string {
    return phone.replace(/[\s\+]/g, '');
  }

  sendMessage() {
    if (!this.selectedReceiverId) {
      this.statusText = 'Selecciona un destinatario';
      return;
    }
    this.sending = true;
    this.statusText = 'Enviando...';
    this.adminService
      .broadcastMessage({
        target: 'single',
        receiver_id: this.selectedReceiverId,
        subject: this.subject,
        body: this.body,
      })
      .subscribe({
        next: () => {
          this.sending = false;
          this.statusText = 'Mensaje enviado correctamente.';
          this.subject = '';
          this.body = '';
          this.selectedReceiverId = null;
        },
        error: (err) => {
          this.sending = false;
          this.statusText = err.error?.message || 'Error al enviar';
        },
      });
  }
}
