import { Component, OnInit, OnDestroy, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { Router } from '@angular/router';
import { firstValueFrom, Subscription } from 'rxjs';
import { TherapistService } from '../../../../core/services/therapist.service';
import { HeaderService } from '../../../../core/services/header.service';
import { ConfirmService } from '../../../../core/services/confirm.service';
import { fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter } from '../../../../core/animations';

@Component({
  selector: 'app-therapist-sessions',
  standalone: false,
  templateUrl: './therapist-sessions.html',
  styleUrl: './therapist-sessions.scss',
  animations: [fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class TherapistSessions implements OnInit, OnDestroy {
  loading = true;
  agendaEvents: any[] = [];
  showEditModal = false;
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

  editForm = {
    id: 0,
    title: '',
    date: '',
    start_time: '',
    end_time: '',
    status: 'scheduled' as string,
    patient: '',
  };

  private subs = new Subscription();

  constructor(
    private therapistService: TherapistService,
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
  }

  ngOnDestroy() {
    this.headerService.reset();
    this.subs.unsubscribe();
  }

  generarDias() {
    this.diasSemana = [];
    const hoy = new Date();
    for (let i = 6; i >= 0; i--) {
      const d = new Date(hoy);
      d.setDate(hoy.getDate() - i);
      this.diasSemana.push(d);
    }
  }

  cambiarFecha(d: Date) {
    this.fechaSeleccionada = d;
    this.cargarSesiones();
  }

  irHoy() {
    this.fechaSeleccionada = new Date();
    this.cargarSesiones();
  }

  diaSemana(d: Date): string {
    return ['Dom', 'Lun', 'Mar', 'Mie', 'Jue', 'Vie', 'Sab'][d.getDay()];
  }

  esHoy(d: Date): boolean {
    const hoy = new Date();
    return d.toDateString() === hoy.toDateString();
  }

  esSeleccionado(d: Date): boolean {
    return d.toDateString() === this.fechaSeleccionada.toDateString();
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

  irSesion(id: number) {
    this.router.navigate(['/therapist/sessions', id, 'review']);
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
      status: event.extendedProps?.status || 'scheduled',
      patient: event.extendedProps?.patient || '',
    };
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
