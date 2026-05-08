import { Component, OnInit, OnDestroy, ViewChild, TemplateRef } from '@angular/core';
import { AdminService } from '../../../../../core/services/admin.service';
import { HeaderService } from '../../../../../core/services/header.service';
import { Sede } from '../../../../../core/models/sede';

interface UserRow {
  id: number;
  username: string;
  email: string;
  role: string;
  is_active: boolean;
  account_status: string;
  sede_id?: number;
  sede_name?: string;
  assigned_sedes?: { id: number; name: string }[];
  therapist_ids: number[];
}

@Component({
  selector: 'app-users-list',
  standalone: false,
  templateUrl: './users-list.html',
  styleUrl: './users-list.scss',
})
export class UsersList implements OnInit, OnDestroy {
  @ViewChild('headerActions', { static: true }) headerActions!: TemplateRef<any>;

  users: UserRow[] = [];
  filteredUsers: UserRow[] = [];
  sedes: Sede[] = [];
  therapists: { id: number; username: string; email: string }[] = [];
  activeFilter = 'all';
  searchQuery = '';
  selectedSedeId: number | null = null;
  loading = true;

  stats = { total: 0, active: 0, patients: 0, therapists: 0 };

  selectedUser: UserRow | null = null;
  showActionDrawer = false;
  showCreateDrawer = false;

  newUser = { email: '', username: '', role: 'jugador', sede_id: null as number | null, sede_ids: [] as number[] };
  createStatus = '';

  constructor(
    private adminService: AdminService,
    private headerService: HeaderService,
  ) {}

  ngOnInit() {
    this.headerService.setConfig({
      title: 'Usuarios',
      subtitle: 'Crear y gestionar terapeutas y pacientes',
      icon: ['fas', 'users'],
      actionTemplate: this.headerActions,
    });
    this.loadData();
  }

  ngOnDestroy() {
    this.headerService.reset();
  }

  private loadData() {
    this.adminService.getOverview().subscribe({
      next: (res) => {
        if (res.success && res.users) {
          this.users = res.users.map((u) => ({
            id: u.id,
            username: u.username,
            email: u.email,
            role: u.role,
            is_active: true,
            account_status: 'active',
            therapist_ids: [],
          }));
          this.applyFilters();
          this.calcStats();
          this.loading = false;
        }
      },
      error: () => (this.loading = false),
    });

    this.adminService.getSedes().subscribe({
      next: (list) => (this.sedes = list),
    });
  }

  private calcStats() {
    this.stats = {
      total: this.users.length,
      active: this.users.filter((u) => u.is_active).length,
      patients: this.users.filter((u) => u.role === 'jugador').length,
      therapists: this.users.filter((u) => u.role === 'terapista').length,
    };
  }

  applyFilters() {
    let result = [...this.users];
    if (this.activeFilter === 'jugador') result = result.filter((u) => u.role === 'jugador');
    else if (this.activeFilter === 'terapista') result = result.filter((u) => u.role === 'terapista');
    else if (this.activeFilter === 'admin') result = result.filter((u) => u.role === 'admin');
    else if (this.activeFilter === 'deudores') result = result.filter((u) => u.account_status === 'debtor');
    else if (this.activeFilter === 'retirados') result = result.filter((u) => u.account_status === 'retired');

    if (this.searchQuery) {
      const q = this.searchQuery.toLowerCase();
      result = result.filter((u) => u.username.toLowerCase().includes(q) || u.email.toLowerCase().includes(q));
    }

    if (this.selectedSedeId) {
      result = result.filter((u) => u.sede_id === this.selectedSedeId);
    }

    this.filteredUsers = result;
  }

  setFilter(filter: string) {
    this.activeFilter = filter;
    this.applyFilters();
  }

  onSearch(query: string | number) {
    this.searchQuery = String(query);
    this.applyFilters();
  }

  onSedeChange(sedeId: string) {
    this.selectedSedeId = sedeId ? parseInt(sedeId) : null;
    this.applyFilters();
  }

  updateName(user: UserRow, event: Event) {
    const input = event.target as HTMLInputElement;
    user.username = input.value;
    this.adminService.updateUser({ id: user.id, username: user.username }).subscribe();
  }

  updateRole(user: UserRow, event: Event) {
    const select = event.target as HTMLSelectElement;
    user.role = select.value;
    this.adminService.updateUser({ id: user.id, role: user.role as any }).subscribe();
  }

  toggleActive(user: UserRow, event: Event) {
    const checked = (event.target as HTMLInputElement).checked;
    user.is_active = checked;
    this.adminService.updateUser({ id: user.id, is_active: checked }).subscribe();
  }

  assignTherapist(patientId: number, event: Event) {
    const select = event.target as HTMLSelectElement;
    const ids = Array.from(select.selectedOptions).map((o) => parseInt(o.value));
    this.adminService.assignTherapist(patientId, ids).subscribe();
  }

  openActionDrawer(user: UserRow) {
    this.selectedUser = user;
    this.showActionDrawer = true;
  }

  closeActionDrawer() {
    this.showActionDrawer = false;
    this.selectedUser = null;
  }

  openCreateDrawer() {
    this.newUser = { email: '', username: '', role: 'jugador', sede_id: null, sede_ids: [] };
    this.createStatus = '';
    this.showCreateDrawer = true;
  }

  closeCreateDrawer() {
    this.showCreateDrawer = false;
  }

  createUser() {
    this.createStatus = 'Creando...';
    const payload: any = { role: this.newUser.role };
    if (this.newUser.email) payload.email = this.newUser.email;
    if (this.newUser.username) payload.username = this.newUser.username;
    if (this.newUser.role === 'jugador' && this.newUser.sede_id) payload.sede_id = this.newUser.sede_id;
    if (this.newUser.role === 'terapista' && this.newUser.sede_ids.length) payload.sede_ids = this.newUser.sede_ids;

    this.adminService.createUser(payload).subscribe({
      next: (res: any) => {
        if (res.success) {
          this.createStatus = `Creado! Contraseña temporal: ${res.temp_password || 'N/A'}`;
          setTimeout(() => {
            this.closeCreateDrawer();
            this.loadData();
          }, 2000);
        } else {
          this.createStatus = 'Error: ' + (res.message || 'Desconocido');
        }
      },
      error: (err) => {
        this.createStatus = 'Error de conexión';
      },
    });
  }

  deleteUser(user: UserRow) {
    if (!confirm(`¿Eliminar a ${user.username} permanentemente?`)) return;
    this.adminService.deleteUser(user.id).subscribe({
      next: (res: any) => {
        if (res.success) {
          this.users = this.users.filter((u) => u.id !== user.id);
          this.applyFilters();
          this.calcStats();
          this.closeActionDrawer();
        }
      },
    });
  }

  resetPassword(user: UserRow) {
    if (!confirm(`Resetear contraseña de ${user.username}?`)) return;
    this.adminService.resetPassword(user.id).subscribe();
  }

  getSedeName(user: UserRow): string {
    if (user.sede_name) return user.sede_name;
    const sede = this.sedes.find((s) => s.id === user.sede_id);
    return sede?.name || 'Sin Sede';
  }

  getRoleBadge(role: string): string {
    const map: Record<string, string> = { jugador: 'Paciente', terapista: 'Terapeuta', admin: 'Admin' };
    return map[role] || role;
  }

  getInitials(name: string): string {
    return name?.slice(0, 2).toUpperCase() || 'US';
  }

  trackById(_: number, u: UserRow): number {
    return u.id;
  }
}
