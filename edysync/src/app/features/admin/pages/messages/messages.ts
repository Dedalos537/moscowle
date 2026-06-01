import { Component, OnInit, OnDestroy, ViewChild, TemplateRef, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { Subscription } from 'rxjs';
import { AdminService } from '../../../../core/services/admin.service';
import { HeaderService } from '../../../../core/services/header.service';
import { ContactMessage } from '../../../../core/models/expense';
import { fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter } from '../../../../core/animations';

@Component({
  selector: 'app-messages',
  standalone: false,
  templateUrl: './messages.html',
  styleUrl: './messages.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
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
  private subscriptions: Subscription = new Subscription();

  constructor(
    private adminService: AdminService,
    private headerService: HeaderService,
    private cdr: ChangeDetectorRef,
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
    this.subscriptions.unsubscribe();
    this.headerService.reset();
  }

  private loadData() {
    this.subscriptions.add(
      this.adminService.getContactMessages().subscribe({
        next: (res) => { this.contactMessages = res.data; this.cdr.markForCheck(); },
        error: () => { this.contactMessages = []; this.cdr.markForCheck(); },
      })
    );
    this.subscriptions.add(
      this.adminService.getUsers('terapista').subscribe({
        next: (res) => { this.therapists = res.users.map((u) => ({ id: u.id, username: u.username })); this.cdr.markForCheck(); },
        error: () => { this.therapists = []; this.cdr.markForCheck(); },
      })
    );
    this.subscriptions.add(
      this.adminService.getUsers('jugador').subscribe({
        next: (res) => {
          this.patients = res.users.map((u) => ({ id: u.id, username: u.username }));
          this.loading = false;
          this.cdr.markForCheck();
        },
        error: () => { this.loading = false; this.cdr.markForCheck(); },
      })
    );
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
    const colors: Record<string, string> = { 'positivo': 'text-success', 'neutral': 'text-warning', 'negativo': 'text-error' };
    return colors[sentiment || ''] || 'text-on-surface-variant';
  }

  getIntentLabel(intent?: string): string {
    const labels: Record<string, string> = {
      'agendar_cita': 'Agendar Cita', 'informacion': 'Información', 'consulta': 'Consulta',
      'queja': 'Queja / Reclamo', 'seguimiento': 'Seguimiento'
    };
    return labels[intent || ''] || intent || '—';
  }

  getConfidenceBadge(conf?: string): string {
    const badges: Record<string, string> = { 'alta': 'bg-success-container text-success', 'media': 'bg-warning-container text-warning', 'baja': 'bg-error-container text-error' };
    return badges[conf || ''] || 'bg-surface-container-high text-on-surface-variant';
  }

  sendMessage() {
    if (!this.selectedReceiverId) {
      this.statusText = 'Selecciona un destinatario';
      return;
    }
    this.sending = true;
    this.statusText = 'Enviando...';
    this.subscriptions.add(
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
            this.cdr.markForCheck();
          },
          error: (err) => {
            this.sending = false;
            this.statusText = err.error?.message || 'Error al enviar';
            this.cdr.markForCheck();
          },
        })
    );
  }
}
