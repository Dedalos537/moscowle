import { Component, OnInit, OnDestroy, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';

import { AdminService } from '../../../../core/services/admin.service';
import { HeaderService } from '../../../../core/services/header.service';
import { ToastService } from '../../../../core/services/toast.service';
import { Spinner } from '../../../../shared/components/spinner/spinner';

interface PasswordResetRow {
  id: number;
  user_id: number | null;
  email: string;
  status: string;
  created_at: string;
  expires_at: string;
  completed_at: string | null;
  admin_id: number | null;
  admin_decision: string | null;
  decision_at: string | null;
  requester_ip: string | null;
  target_username?: string;
  target_role?: string;
  temp_password?: string;
}

@Component({
  selector: 'app-password-resets',
  standalone: true,
  imports: [CommonModule, FontAwesomeModule, Spinner],
  templateUrl: './password-resets.html',
  styleUrl: './password-resets.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PasswordResets implements OnInit, OnDestroy {
  items: PasswordResetRow[] = [];
  loading = false;
  filter: 'awaiting_approval' | 'approved' | 'rejected' | 'all' = 'awaiting_approval';
  showApprovedModal = false;
  approvedTempPassword = '';
  approvedTargetUser: any = null;

  private destroy$ = new Subject<void>();

  constructor(
    private adminService: AdminService,
    private headerService: HeaderService,
    private toastService: ToastService,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit() {
    this.headerService.setConfig({
      title: 'Solicitudes de Reseteo de Contraseña',
      subtitle: 'Aprueba o rechaza solicitudes de recuperación',
      icon: ['fas', 'key'],
    });
    this.load();
  }

  ngOnDestroy() {
    this.headerService.reset();
    this.destroy$.next();
    this.destroy$.complete();
  }

  load() {
    this.loading = true;
    this.cdr.markForCheck();
    this.adminService.listPasswordResets(this.filter).pipe(takeUntil(this.destroy$)).subscribe({
      next: (res: any) => {
        if (res.success) this.items = (res.items as PasswordResetRow[]) || [];
        this.loading = false;
        this.cdr.markForCheck();
      },
      error: () => {
        this.loading = false;
        this.cdr.markForCheck();
        this.toastService.show('Error al cargar solicitudes', 'error');
      },
    });
  }

  switchFilter(f: 'awaiting_approval' | 'approved' | 'rejected' | 'all') {
    this.filter = f;
    this.load();
  }

  approve(item: PasswordResetRow) {
    if (!confirm(`Aprobar reseteo de contraseña para ${item.target_username || item.email}?`)) return;
    this.adminService.approvePasswordReset(item.id).pipe(takeUntil(this.destroy$)).subscribe({
      next: (res: any) => {
        if (res.success) {
          this.approvedTempPassword = res.temp_password || '';
          this.approvedTargetUser = res.target_user || null;
          this.showApprovedModal = true;
          this.toastService.show('Solicitud aprobada', 'success');
          this.load();
        } else {
          this.toastService.show(res.error || 'Error al aprobar', 'error');
        }
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.toastService.show(err.error?.error || 'Error de red', 'error');
        this.cdr.markForCheck();
      },
    });
  }

  reject(item: PasswordResetRow) {
    const reason = prompt(`Motivo de rechazo para ${item.target_username || item.email} (opcional):`);
    if (reason === null) return;
    this.adminService.rejectPasswordReset(item.id, reason).pipe(takeUntil(this.destroy$)).subscribe({
      next: (res) => {
        if (res.success) {
          this.toastService.show('Solicitud rechazada', 'success');
          this.load();
        } else {
          this.toastService.show(res.error || 'Error al rechazar', 'error');
        }
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.toastService.show(err.error?.error || 'Error de red', 'error');
        this.cdr.markForCheck();
      },
    });
  }

  closeApprovedModal() {
    this.showApprovedModal = false;
    this.approvedTempPassword = '';
    this.approvedTargetUser = null;
  }

  copyPassword() {
    if (!this.approvedTempPassword) return;
    navigator.clipboard?.writeText(this.approvedTempPassword).then(
      () => this.toastService.show('Contraseña copiada al portapapeles', 'success'),
      () => this.toastService.show('No se pudo copiar', 'error'),
    );
  }

  statusLabel(s: string): string {
    const m: Record<string, string> = {
      awaiting_approval: 'Esperando aprobación',
      approved: 'Aprobada',
      rejected: 'Rechazada',
      pending: 'Pendiente',
      completed: 'Completada',
      expired: 'Expirada',
      verified: 'Verificada',
    };
    return m[s] || s;
  }

  statusClass(s: string): string {
    if (s === 'awaiting_approval') return 'bg-warning/15 text-warning border-warning/30';
    if (s === 'approved' || s === 'completed') return 'bg-success/15 text-success border-success/30';
    if (s === 'rejected' || s === 'expired') return 'bg-error/15 text-error border-error/30';
    return 'bg-surface-container-high text-on-surface-variant border-border/30';
  }

  formatDate(s: string | null | undefined): string {
    if (!s) return '—';
    try {
      return new Date(s).toLocaleString('es-PE', { dateStyle: 'short', timeStyle: 'short' });
    } catch {
      return s;
    }
  }
}
