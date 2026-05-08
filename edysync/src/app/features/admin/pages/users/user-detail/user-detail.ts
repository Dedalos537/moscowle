import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { AdminService } from '../../../../../core/services/admin.service';

@Component({
  selector: 'app-user-detail',
  standalone: false,
  templateUrl: './user-detail.html',
  styleUrl: './user-detail.scss',
})
export class UserDetail implements OnInit {
  userId!: number;
  user: any = null;
  stats: any = {};
  loading = true;
  selectedStatus = 'active';
  showEditModal = false;
  editData = { username: '', role: '', is_active: true };

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private adminService: AdminService,
  ) {}

  ngOnInit() {
    this.userId = Number(this.route.snapshot.paramMap.get('id'));
    this.loadUser();
  }

  private loadUser() {
    this.adminService.getOverview().subscribe({
      next: (res) => {
        if (res.success && res.users) {
          const found = res.users.find((u) => u.id === this.userId);
          if (found) {
            this.user = found;
            this.selectedStatus = found.role === 'admin' ? 'active' : 'active';
            this.editData = { username: found.username, role: found.role, is_active: true };
          }
        }
        this.loading = false;
      },
      error: () => (this.loading = false),
    });
  }

  get roleLabel(): string {
    const map: Record<string, string> = { jugador: 'Paciente', terapista: 'Terapeuta', admin: 'Administrador' };
    return map[this.user?.role] || this.user?.role || '';
  }

  get roleColor(): string {
    const map: Record<string, string> = { admin: 'purple', jugador: 'blue', terapista: 'green' };
    return map[this.user?.role] || 'gray';
  }

  getInitials(name: string): string {
    return name?.slice(0, 2).toUpperCase() || 'US';
  }

  updateStatus() {
    this.adminService.updateUser({ id: this.userId, account_status: this.selectedStatus as any, is_active: this.selectedStatus === 'active' }).subscribe({
      next: (res: any) => {
        if (res.success) this.loadUser();
      },
    });
  }

  openEditModal() {
    this.editData = { username: this.user.username, role: this.user.role, is_active: true };
    this.showEditModal = true;
  }

  closeEditModal() {
    this.showEditModal = false;
  }

  saveEdit() {
    this.adminService.updateUser({ id: this.userId, username: this.editData.username, role: this.editData.role as any, is_active: this.editData.is_active }).subscribe({
      next: (res: any) => {
        if (res.success) {
          this.closeEditModal();
          this.loadUser();
        }
      },
    });
  }

  resetPassword() {
    if (!confirm('¿Resetear contraseña de este usuario?')) return;
    this.adminService.resetPassword(this.userId).subscribe();
  }

  deleteUser() {
    if (!confirm('¿Eliminar usuario permanentemente? Esta acción no se puede deshacer.')) return;
    this.adminService.deleteUser(this.userId).subscribe({
      next: (res: any) => {
        if (res.success) this.router.navigate(['/admin/users']);
      },
    });
  }

  goBack() {
    this.router.navigate(['/admin/users']);
  }
}
