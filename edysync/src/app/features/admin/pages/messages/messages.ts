import { Component, OnInit, OnDestroy, ViewChild, TemplateRef } from '@angular/core';
import { AdminService } from '../../../../core/services/admin.service';
import { HeaderService } from '../../../../core/services/header.service';
import { ContactMessage } from '../../../../core/models/expense';
import { fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter } from '../../../../core/animations';

@Component({
  selector: 'app-messages',
  standalone: false,
  templateUrl: './messages.html',
  styleUrl: './messages.scss',
  animations: [fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter]
})
export class Messages implements OnInit, OnDestroy {
  @ViewChild('headerActions', { static: true }) headerActions!: TemplateRef<any>;

  contactMessages: ContactMessage[] = [];
  selectedMessage: ContactMessage | null = null;
  showAnalysisModal = false;
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
      error: () => (this.contactMessages = []),
    });
    this.adminService.getUsers('terapista').subscribe({
      next: (res) => (this.therapists = res.users.map((u) => ({ id: u.id, username: u.username }))),
      error: () => (this.therapists = []),
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

  viewAnalysis(msg: ContactMessage) {
    this.selectedMessage = msg;
    this.showAnalysisModal = true;
  }

  closeAnalysis() {
    this.showAnalysisModal = false;
    this.selectedMessage = null;
  }

  get selectedAnalysis(): Record<string, any> | null {
    return this.selectedMessage?.ai_analysis ?? null;
  }

  getSentimentIcon(sentiment?: string): string {
    const icons: Record<string, string> = { 'positivo': 'smile', 'neutral': 'meh', 'negativo': 'frown' };
    return icons[sentiment || ''] || 'meh';
  }

  getSentimentColor(sentiment?: string): string {
    const colors: Record<string, string> = { 'positivo': 'text-green-600', 'neutral': 'text-yellow-600', 'negativo': 'text-red-600' };
    return colors[sentiment || ''] || 'text-gray-500';
  }

  getIntentLabel(intent?: string): string {
    const labels: Record<string, string> = {
      'agendar_cita': 'Agendar Cita', 'informacion': 'Información', 'consulta': 'Consulta',
      'queja': 'Queja / Reclamo', 'seguimiento': 'Seguimiento'
    };
    return labels[intent || ''] || intent || '—';
  }

  getConfidenceBadge(conf?: string): string {
    const badges: Record<string, string> = { 'alta': 'bg-green-100 text-green-700', 'media': 'bg-yellow-100 text-yellow-700', 'baja': 'bg-red-100 text-red-700' };
    return badges[conf || ''] || 'bg-gray-100 text-gray-600';
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
