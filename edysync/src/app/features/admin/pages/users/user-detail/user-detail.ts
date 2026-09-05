import { Component, OnInit, OnDestroy, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { Subscription } from 'rxjs';
import { AdminService } from '../../../../../core/services/admin.service';
import { fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter } from '../../../../../core/animations';
import { firstValueFrom } from 'rxjs';
import { ConfirmService } from '../../../../../core/services/confirm.service';
import { SelectOption } from '../../../../../shared/components/select/select';
import { Spinner } from '../../../../../shared/components/spinner/spinner';
import { Button } from '../../../../../shared/components/button/button';
import { Select } from '../../../../../shared/components/select/select';
import { Input } from '../../../../../shared/components/input/input';
import { Modal } from '../../../../../shared/components/modal/modal';

@Component({
  selector: 'app-user-detail',
  standalone: true,
  imports: [FormsModule, RouterModule, FontAwesomeModule, Spinner, Button, Select, Input, Modal],
  templateUrl: './user-detail.html',
  styleUrl: './user-detail.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
  animations: [fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter]
})
export class UserDetail implements OnInit, OnDestroy {
  userId!: number;
  user: any = null;
  stats: any = {};
  loading = true;
  error: string | null = null;
  selectedStatus = 'active';
  showEditModal = false;
  editData = { username: '', role: '', is_active: true };

  statusOptions: SelectOption[] = [
    {value: 'active', label: 'Activo'},
    {value: 'inactive', label: 'Inactivo'},
    {value: 'retired', label: 'Retirado'},
    {value: 'debtor', label: 'Deudor'},
  ];

  roleOptions: SelectOption[] = [
    {value: 'jugador', label: 'Paciente'},
    {value: 'terapista', label: 'Terapeuta'},
    {value: 'supervisor', label: 'Supervisor'},
    {value: 'admin', label: 'Administrador'},
  ];

  private subscriptions: Subscription = new Subscription();

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private adminService: AdminService,
    private confirmService: ConfirmService,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit() {
    this.userId = Number(this.route.snapshot.paramMap.get('id'));
    this.loadUser();
  }

  ngOnDestroy() {
    this.subscriptions.unsubscribe();
  }

  loadUser() {
    this.loading = true;
    this.error = null;
    this.subscriptions.add(
      this.adminService.getUser(this.userId).subscribe({
        next: (res) => {
          if (res.success && res.user) {
            this.user = res.user;
            this.selectedStatus = res.user.role === 'admin' ? 'active' : 'active';
            this.editData = { username: res.user.username, role: res.user.role, is_active: true };
          }
          this.loading = false;
          this.cdr.markForCheck();
        },
        error: (err) => { this.loading = false; this.error = err.error?.message || err.message || 'Error al cargar usuario'; this.cdr.markForCheck(); },
      })
    );
  }

  get roleLabel(): string {
    const map: Record<string, string> = { jugador: 'Paciente', terapista: 'Terapeuta', admin: 'Administrador', supervisor: 'Supervisor' };
    return map[this.user?.role] || this.user?.role || '';
  }

  get roleColor(): string {
    const map: Record<string, string> = { admin: 'purple', jugador: 'blue', terapista: 'green', supervisor: 'orange' };
    return map[this.user?.role] || 'gray';
  }

  getInitials(name: string): string {
    return name?.slice(0, 2).toUpperCase() || 'US';
  }

  updateStatus() {
    this.subscriptions.add(
      this.adminService.updateUser({ id: this.userId, account_status: this.selectedStatus as any, is_active: this.selectedStatus === 'active' }).subscribe({
        next: (res: any) => {
          if (res.success) this.loadUser();
          this.cdr.markForCheck();
        },
        error: (err) => { this.error = err.error?.message || err.message || 'Error al actualizar estado'; this.cdr.markForCheck(); },
      })
    );
  }

  openEditModal() {
    this.editData = { username: this.user.username, role: this.user.role, is_active: true };
    this.showEditModal = true;
  }

  closeEditModal() {
    this.showEditModal = false;
  }

  saveEdit() {
    this.subscriptions.add(
      this.adminService.updateUser({ id: this.userId, username: this.editData.username, role: this.editData.role as any, is_active: this.editData.is_active }).subscribe({
        next: (res: any) => {
          if (res.success) {
            this.closeEditModal();
            this.loadUser();
          }
          this.cdr.markForCheck();
        },
        error: (err) => { this.error = err.error?.message || err.message || 'Error al guardar cambios'; this.cdr.markForCheck(); },
      })
    );
  }

  async resetPassword() {
    const confirmed = await firstValueFrom(this.confirmService.confirm({
      title: 'Resetear Contraseña',
      message: '¿Resetear contraseña de este usuario?',
      confirmText: 'Resetear',
      cancelText: 'Cancelar',
      variant: 'danger',
    }));
    if (!confirmed) return;
    this.subscriptions.add(
      this.adminService.resetPassword(this.userId).subscribe({
        error: (err) => { this.error = err.error?.message || err.message || 'Error al resetear contraseña'; this.cdr.markForCheck(); }
      })
    );
  }

  async deleteUser() {
    const confirmed = await firstValueFrom(this.confirmService.confirm({
      title: 'Eliminar Usuario',
      message: '¿Eliminar usuario permanentemente? Esta acción no se puede deshacer.',
      confirmText: 'Eliminar',
      cancelText: 'Cancelar',
      variant: 'danger',
    }));
    if (!confirmed) return;
    this.subscriptions.add(
      this.adminService.deleteUser(this.userId).subscribe({
        next: (res: any) => {
          if (res.success) this.router.navigate(['/admin/users']);
          this.cdr.markForCheck();
        },
        error: (err) => { this.error = err.error?.message || err.message || 'Error al eliminar usuario'; this.cdr.markForCheck(); },
      })
    );
  }

  goBack() {
    this.router.navigate(['/admin/users']);
  }

  viewPatientDetail() {
    if (this.user?.role === 'jugador') {
      this.router.navigate(['/admin/patients', this.userId]);
    }
  }
}
