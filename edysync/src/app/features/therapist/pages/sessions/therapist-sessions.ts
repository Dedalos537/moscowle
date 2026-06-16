import { CommonModule } from '@angular/common';
import { Component, OnInit, OnDestroy, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { Router } from '@angular/router';
import { firstValueFrom, Subscription } from 'rxjs';
import { TherapistService } from '../../../../core/services/therapist.service';
import { RecordingService } from '../../../../core/services/recording.service';
import { HeaderService } from '../../../../core/services/header.service';
import { ConfirmService } from '../../../../core/services/confirm.service';
import { fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter } from '../../../../core/animations';
import { SelectOption } from '../../../../shared/components/select/select';
import { Modal } from '../../../../shared/components/modal/modal';
import { Select } from '../../../../shared/components/select/select';
import { Button } from '../../../../shared/components/button/button';

@Component({
  selector: 'app-therapist-sessions',
  standalone: true,
  imports: [CommonModule, FormsModule, FontAwesomeModule, Modal, Select, Button],
  templateUrl: './therapist-sessions.html',
  styleUrl: './therapist-sessions.scss',
  animations: [fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class TherapistSessions implements OnInit, OnDestroy {
  loading = true;
  agendaEvents: any[] = [];
  showEditModal = false;
  showNotesModal = false;
  selectedNote = '';
  submitting = false;
  deleting = false;
  error: string | null = null;

  fechaSeleccionada: Date = new Date();
  diasSemana: Date[] = [];

  stats = {
    sessions_today: 0,
    completed_sessions: 0,
    pending_sessions: 0,
    active_patients: 0,
  };

  statusOptions: SelectOption[] = [
    {value: 'scheduled', label: 'Programada'},
    {value: 'completed', label: 'Completada'},
    {value: 'cancelled', label: 'Cancelada'},
  ];

  editForm = {
    id: 0,
    title: '',
    date: '',
    start_time: '',
    end_time: '',
    status: 'scheduled' as string,
    patient: '',
  };

  showBriefing = false;
  briefingLoading = false;
  briefing: any = null;

  activeBriefing: any = null;
  activeBriefingLoading = false;
  showActiveBriefing = false;

  private subs = new Subscription();

  constructor(
    private therapistService: TherapistService,
    private recordingService: RecordingService,
    private headerService: HeaderService,
    private router: Router,
    private confirmService: ConfirmService,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit() {
    this.headerService.setConfig({
      title: 'Mis Sesiones',
      subtitle: 'Gestiona tus sesiones con pacientes',
      icon: ['fas', 'calendar-alt'],
    });
    this.generarDias();
    this.loadStats();
    this.cargarSesiones();

    this.subs.add(this.recordingService.activeSession$.subscribe(session => {
      if (session && session.id) {
        this.loadActiveBriefing(session.id);
      } else {
        this.showActiveBriefing = false;
        this.activeBriefing = null;
        this.cdr.markForCheck();
      }
    }));
  }

  ngOnDestroy() {
    this.headerService.reset();
    this.subs.unsubscribe();
  }

  get monthYearLabel(): string {
    const meses = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];
    return meses[this.fechaSeleccionada.getMonth()] + ' ' + this.fechaSeleccionada.getFullYear();
  }

  generarDias() {
    this.diasSemana = [];
    const hoy = new Date(this.fechaSeleccionada);
    const diaSem = hoy.getDay();
    const lunes = new Date(hoy);
    lunes.setDate(hoy.getDate() - ((diaSem + 6) % 7));
    for (let i = 0; i < 7; i++) {
      const d = new Date(lunes);
      d.setDate(lunes.getDate() + i);
      this.diasSemana.push(d);
    }
  }

  prevWeek() {
    const d = new Date(this.fechaSeleccionada);
    d.setDate(d.getDate() - 7);
    this.fechaSeleccionada = d;
    this.generarDias();
    this.cargarSesiones();
  }

  nextWeek() {
    const d = new Date(this.fechaSeleccionada);
    d.setDate(d.getDate() + 7);
    this.fechaSeleccionada = d;
    this.generarDias();
    this.cargarSesiones();
  }

  cambiarFecha(d: Date) {
    this.fechaSeleccionada = d;
    this.generarDias();
    this.cargarSesiones();
  }

  irHoy() {
    this.fechaSeleccionada = new Date();
    this.generarDias();
    this.cargarSesiones();
  }

  diaSemana(d: Date): string {
    return ['Dom', 'Lun', 'Mar', 'Mie', 'Jue', 'Vie', 'Sab'][d.getDay()];
  }

  esHoy(d: Date): boolean {
    return d.toDateString() === new Date().toDateString();
  }

  esSeleccionado(d: Date): boolean {
    return d.toDateString() === this.fechaSeleccionada.toDateString();
  }

  initials(name: string): string {
    if (!name) return '?';
    return name.split(' ').map(w => w[0]).join('').substring(0, 2).toUpperCase();
  }

  formatTime(iso: string): string {
    if (!iso) return '';
    const d = new Date(iso);
    return d.toLocaleTimeString('es-PE', { hour: '2-digit', minute: '2-digit', hour12: false });
  }

  duration(start: string, end: string): string {
    if (!start || !end) return '';
    const diff = new Date(end).getTime() - new Date(start).getTime();
    const mins = Math.round(diff / 60000);
    if (mins < 60) return mins + ' min';
    return Math.floor(mins / 60) + 'h ' + (mins % 60) + 'm';
  }

  private loadStats() {
    this.subs.add(this.therapistService.getDashboardStats().subscribe({
      next: (res) => {
        this.stats = res;
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.error = err.message;
        this.cdr.markForCheck();
      },
    }));
  }

  cargarSesiones() {
    this.loading = true;
    this.cdr.markForCheck();
    const f = this.fechaSeleccionada.toISOString().split('T')[0];
    this.subs.add(this.therapistService.getSessions(f, f).subscribe({
      next: (events) => {
        this.agendaEvents = [...events].sort((a: any, b: any) => {
          return new Date(a.start).getTime() - new Date(b.start).getTime();
        });
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

  openCreateModal() {
    const today = new Date().toISOString().split('T')[0];
    this.editForm = {
      id: 0,
      title: '',
      date: today,
      start_time: '',
      end_time: '',
      status: 'scheduled',
      patient: '',
    };
    this.showEditModal = true;
  }

  irSesion(id: number) {
    this.router.navigate(['/therapist/sessions', id, 'review']);
  }

  viewNotes(e: any) {
    this.selectedNote = e.notes || e.extendedProps?.notes || '';
    this.showNotesModal = true;
  }

  closeNotesModal() {
    this.showNotesModal = false;
  }

  loadBriefing(sessionId: number) {
    this.briefingLoading = true;
    this.briefing = null;
    this.showBriefing = true;
    this.cdr.markForCheck();
    this.subs.add(this.therapistService.getSessionBriefing(sessionId).subscribe({
      next: (res: any) => {
        this.briefing = res;
        this.briefingLoading = false;
        this.cdr.markForCheck();
      },
      error: () => {
        this.briefingLoading = false;
        this.cdr.markForCheck();
      },
    }));
  }

  closeBriefing() {
    this.showBriefing = false;
    this.briefing = null;
  }

  loadActiveBriefing(sessionId: number) {
    this.activeBriefingLoading = true;
    this.showActiveBriefing = true;
    this.cdr.markForCheck();
    this.subs.add(this.therapistService.getSessionBriefing(sessionId).subscribe({
      next: (res: any) => {
        this.activeBriefing = res;
        this.activeBriefingLoading = false;
        this.cdr.markForCheck();
      },
      error: () => {
        this.activeBriefingLoading = false;
        this.cdr.markForCheck();
      },
    }));
  }

  dismissActiveBriefing() {
    this.showActiveBriefing = false;
  }

  irSesionDesdeBriefing() {
    if (this.activeBriefing?.session?.id) {
      this.showActiveBriefing = false;
      this.router.navigate(['/therapist/sessions', this.activeBriefing.session.id, 'review']);
    }
  }

  statusColor(status: string): string {
    const map: any = {
      scheduled: 'var(--color-info)',
      completed: 'var(--color-success)',
      cancelled: 'var(--color-error)',
      in_progress: 'var(--color-warning)',
    };
    return map[status] || 'var(--color-on-surface-variant)';
  }

  statusLabel(status: string): string {
    const map: any = {
      scheduled: 'Programada',
      completed: 'Completada',
      cancelled: 'Cancelada',
      in_progress: 'En curso',
    };
    return map[status] || status;
  }

  onEventClick(event: any) {
    this.editForm = {
      id: event.id,
      title: event.title,
      date: new Date(event.start).toISOString().split('T')[0],
      start_time: event.start ? new Date(event.start).toTimeString().substring(0, 5) : '',
      end_time: event.end ? new Date(event.end).toTimeString().substring(0, 5) : '',
      status: event.status || 'scheduled',
      patient: event.extendedProps?.patient || '',
    };
    this.loadBriefing(event.id);
    this.showEditModal = true;
  }

  closeEditModal() {
    this.showEditModal = false;
  }

  async submitEdit() {
    const f = this.editForm;

    const confirmed = await firstValueFrom(this.confirmService.confirm({
      title: 'Guardar cambios',
      message: '¿Estás seguro de guardar los cambios?',
      confirmText: 'Guardar',
      cancelText: 'Cancelar',
      variant: 'primary',
    }));
    if (!confirmed) return;

    this.submitting = true;
    this.cdr.markForCheck();
    this.subs.add(this.therapistService.updateSession(f.id, {
      title: f.title,
      start_time: `${f.date}T${f.start_time}`,
      end_time: `${f.date}T${f.end_time}`,
      status: f.status as any,
    }).subscribe({
      next: () => {
        this.submitting = false;
        this.closeEditModal();
        this.cdr.markForCheck();
        this.cargarSesiones();
        this.loadStats();
      },
      error: (err) => {
        this.submitting = false;
        this.error = err.message;
        this.cdr.markForCheck();
      },
    }));
  }

  navigateToReview() {
    this.closeEditModal();
    this.router.navigate(['/therapist/sessions', this.editForm.id, 'review']);
  }

  async deleteSession() {
    const confirmed = await firstValueFrom(this.confirmService.confirm({
      title: 'Eliminar sesión',
      message: '¿Estás seguro de eliminar esta sesión?',
      confirmText: 'Eliminar',
      cancelText: 'Cancelar',
      variant: 'danger',
    }));
    if (!confirmed) return;
    this.deleting = true;
    this.cdr.markForCheck();
    this.subs.add(this.therapistService.deleteSession(this.editForm.id).subscribe({
      next: () => {
        this.deleting = false;
        this.closeEditModal();
        this.cdr.markForCheck();
        this.cargarSesiones();
        this.loadStats();
      },
      error: (err) => {
        this.deleting = false;
        this.error = err.message;
        this.cdr.markForCheck();
      },
    }));
  }
}
