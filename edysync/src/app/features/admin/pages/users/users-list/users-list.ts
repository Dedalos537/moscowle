import { Component, OnInit, OnDestroy, ViewChild, TemplateRef, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { Subscription } from 'rxjs';
import { AdminService } from '../../../../../core/services/admin.service';
import { HeaderService } from '../../../../../core/services/header.service';
import { Sede } from '../../../../../core/models/sede';
import { Chart, registerables } from 'chart.js';
import type { ChartConfiguration, ChartData } from 'chart.js';
import { fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter } from '../../../../../core/animations';
import { firstValueFrom } from 'rxjs';
import { ConfirmService } from '../../../../../core/services/confirm.service';

Chart.register(...registerables);

interface UserRow {
  id: number;
  username: string;
  email: string;
  role: string;
  is_active: boolean;
  account_status: string;
  admin_password_changed_count: number;
  sede_id?: number;
  sede_name?: string;
  assigned_sedes?: { id: number; name: string }[];
  therapist_ids: number[];
  payment_plan?: string;
  payment_amount?: number;
  sessions_total?: number;
  sessions_attended?: number;
  plan_type?: string;
  has_second_shift?: boolean;
  payment_amount_2?: number;
  sessions_total_2?: number;
  sessions_attended_2?: number;
  plan_type_2?: string;
  salary_base?: number;
  contract_hours?: number;
  work_start_time?: string;
  work_end_time?: string;
  work_days?: string;
}

@Component({
  selector: 'app-users-list',
  standalone: false,
  templateUrl: './users-list.html',
  styleUrl: './users-list.scss',
  animations: [fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter],
  changeDetection: ChangeDetectionStrategy.OnPush,
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
  selectedTherapistId: string | null = null;
  loading = true;

  stats = { total: 0, active: 0, inactive: 0, patients: 0, therapists: 0, supervisors: 0, admins: 0, retired: 0, debtors: 0 };

  selectedUser: UserRow | null = null;
  showActionDrawer = false;
  showResetDrawer = false;
  showEditDrawer = false;
  resetData = { userId: 0, loginCount: 0, newPassword: '', showPassword: false, status: '', firstTime: false };
  editData: any = {};

  showCreateDrawer = false;
  newUser = { email: '', username: '', role: 'jugador', sede_id: null as number | null, sede_ids: [] as number[], salary: null as number | null, hours: null as number | null, modality: null as number | null, frequency: 'monthly', plan_type: 'individual', amount: null as number | null, generate_schedule: true, start_date: '', start_time: '', schedule_therapist: null as number | null, days: [] as number[] };
  createStatus = '';

  chartSede: ChartData<'bar'> = { labels: [], datasets: [] };
  chartSedeOpt: ChartConfiguration<'bar'>['options'] = {};
  chartActive: ChartData<'doughnut'> = { labels: [], datasets: [] };
  chartActiveOpt: ChartConfiguration<'doughnut'>['options'] = {};
  chartRole: ChartData<'doughnut'> = { labels: [], datasets: [] };
  chartRoleOpt: ChartConfiguration<'doughnut'>['options'] = {};

  private sedeLookup: Record<string, string> = {};

  private subscriptions = new Subscription();

  constructor(
    private adminService: AdminService,
    private headerService: HeaderService,
    private confirmService: ConfirmService,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit() {
    this.headerService.setConfig({
      title: 'Usuarios',
      subtitle: 'Crear y gestionar terapeutas y pacientes',
      icon: ['fas', 'users'],
      actionTemplate: this.headerActions,
    });
    const params = new URLSearchParams(window.location.search);
    const search = params.get('search');
    if (search) this.searchQuery = search;
    this.loadData();
  }

  ngOnDestroy() {
    this.headerService.reset();
    this.subscriptions.unsubscribe();
  }

  private loadData() {
    this.subscriptions.add(
      this.adminService.getOverview().subscribe({
        next: (res: any) => {
          if (res.success && res.users) {
            this.users = res.users.map((u: any) => ({
              id: u.id,
              username: u.username,
              email: u.email,
              role: u.role,
              is_active: u.is_active ?? true,
              account_status: u.account_status || 'active',
              admin_password_changed_count: u.admin_password_changed_count || 0,
              sede_id: u.sede_id,
              sede_name: u.sede_name,
              assigned_sedes: u.assigned_sedes || [],
              therapist_ids: u.therapist_ids || [],
              payment_plan: u.payment_plan,
              payment_amount: u.payment_amount || 0,
              sessions_total: u.sessions_total || 0,
              sessions_attended: u.sessions_attended || 0,
              plan_type: u.plan_type || 'individual',
              has_second_shift: u.has_second_shift || false,
              payment_amount_2: u.payment_amount_2 || 0,
              sessions_total_2: u.sessions_total_2 || 0,
              sessions_attended_2: u.sessions_attended_2 || 0,
              plan_type_2: u.plan_type_2 || 'individual',
              salary_base: u.salary_base || 0,
              contract_hours: u.contract_hours || 0,
              work_start_time: u.work_start_time,
              work_end_time: u.work_end_time,
              work_days: u.work_days,
            }));
            this.therapists = this.users.filter((u) => u.role === 'terapista').map((u) => ({ id: u.id, username: u.username, email: u.email }));
            this.buildSedeLookup();
            this.applyFilters();
            this.refreshCharts();
            this.loading = false;
          }
          this.cdr.markForCheck();
        },
        error: () => {
          this.loading = false;
          this.cdr.markForCheck();
        },
      }),
    );

    this.subscriptions.add(
      this.adminService.getSedes().subscribe({
        next: (list) => {
          this.sedes = list;
          this.cdr.markForCheck();
        },
        error: () => this.cdr.markForCheck(),
      }),
    );
  }

  private buildSedeLookup() {
    this.sedeLookup = {};
    for (const s of this.sedes) {
      this.sedeLookup[String(s.id)] = s.name;
    }
  }

  private refreshCharts() {
    const total = this.filteredUsers.length;
    const activeC = this.filteredUsers.filter((u) => u.is_active).length;
    const inactiveC = total - activeC;
    const patients = this.filteredUsers.filter((u) => u.role === 'jugador').length;
    const therapistsC = this.filteredUsers.filter((u) => u.role === 'terapista').length;

    const sedeCounts: Record<string, number> = {};
    for (const u of this.filteredUsers) {
      let names: string[] = [];
      if (u.role === 'terapista' && u.assigned_sedes?.length) {
        names = u.assigned_sedes.map((s) => s.name);
      } else if (u.sede_name) {
        names = [u.sede_name];
      } else {
        names = ['Sin Sede'];
      }
      for (const n of names) {
        const key = (n || 'Sin Sede').trim();
        sedeCounts[key] = (sedeCounts[key] || 0) + 1;
      }
    }
    const sedeLabels = Object.keys(sedeCounts);
    const sedeData = sedeLabels.map((l) => sedeCounts[l]);

    this.chartSede = {
      labels: sedeLabels,
      datasets: [{ label: 'Usuarios', data: sedeData, backgroundColor: 'rgba(59,130,246,0.85)' }],
    };
    this.chartSedeOpt = {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      onClick: (_e, elements) => {
        if (elements.length > 0) {
          const idx = elements[0].index;
          const label = sedeLabels[idx];
          for (const s of this.sedes) {
            if (s.name === label) {
              this.selectedSedeId = s.id;
              this.onSedeChange(String(s.id));
              return;
            }
          }
          this.selectedSedeId = null;
          this.onSedeChange('');
        }
      },
    };

    this.chartActive = {
      labels: ['Activos', 'Inactivos'],
      datasets: [{ data: [activeC, inactiveC], backgroundColor: ['#10B981', '#EF4444'] }],
    };
    this.chartActiveOpt = {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { position: 'bottom' } },
      onClick: (_e, elements) => {
        if (elements.length > 0) {
          const idx = elements[0].index;
          this.activeFilter = idx === 0 ? 'all' : 'inactive';
          this.applyFilters();
        }
      },
    };

    this.chartRole = {
      labels: ['Pacientes', 'Terapeutas'],
      datasets: [{ data: [patients, therapistsC], backgroundColor: ['#8B5CF6', '#FB923C'] }],
    };
    this.chartRoleOpt = {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { position: 'bottom' } },
      onClick: (_e, elements) => {
        if (elements.length > 0) {
          const idx = elements[0].index;
          this.setFilter(idx === 0 ? 'jugador' : 'terapista');
        }
      },
    };
  }

  private calcStats() {
    this.stats = {
      total: this.users.length,
      active: this.users.filter((u) => u.is_active).length,
      inactive: this.users.filter((u) => !u.is_active).length,
      patients: this.users.filter((u) => u.role === 'jugador').length,
      therapists: this.users.filter((u) => u.role === 'terapista').length,
      supervisors: this.users.filter((u) => u.role === 'supervisor').length,
      admins: this.users.filter((u) => u.role === 'admin').length,
      retired: this.users.filter((u) => u.account_status === 'retired').length,
      debtors: this.users.filter((u) => u.account_status === 'debtor').length,
    };
  }

  applyFilters() {
    let result = [...this.users];
    if (this.activeFilter === 'jugador') result = result.filter((u) => u.role === 'jugador');
    else if (this.activeFilter === 'terapista') result = result.filter((u) => u.role === 'terapista');
    else if (this.activeFilter === 'supervisor') result = result.filter((u) => u.role === 'supervisor');
    else if (this.activeFilter === 'admin') result = result.filter((u) => u.role === 'admin');
    else if (this.activeFilter === 'deudores') result = result.filter((u) => u.account_status === 'debtor');
    else if (this.activeFilter === 'retirados') result = result.filter((u) => u.account_status === 'retired');
    else if (this.activeFilter === 'inactive') result = result.filter((u) => !u.is_active);

    if (this.searchQuery) {
      const q = this.searchQuery.toLowerCase();
      result = result.filter((u) => u.username?.toLowerCase().includes(q) || u.email?.toLowerCase().includes(q));
    }

    if (this.selectedSedeId) {
      result = result.filter((u) => {
        if (u.role === 'terapista') return u.assigned_sedes?.some((s) => s.id === this.selectedSedeId);
        return u.sede_id === this.selectedSedeId;
      });
    }

    if (this.selectedTherapistId) {
      result = result.filter((u) => {
        if (u.role !== 'jugador') return false;
        return u.therapist_ids.includes(Number(this.selectedTherapistId));
      });
    }

    this.filteredUsers = result;
    this.calcStats();
    this.refreshCharts();
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

  onTherapistFilterChange(therapistId: string) {
    this.selectedTherapistId = therapistId || null;
    this.applyFilters();
  }

  async updateName(user: UserRow, event: Event) {
    const input = event.target as HTMLInputElement;
    const confirmed = await firstValueFrom(this.confirmService.confirm({
      title: 'Cambiar Nombre',
      message: `¿Cambiar nombre de "${user.username}" a "${input.value}"?`,
      confirmText: 'Cambiar',
      cancelText: 'Cancelar',
      variant: 'warning',
    }));
    if (!confirmed) {
      input.value = user.username;
      return;
    }
    user.username = input.value;
    this.subscriptions.add(
      this.adminService.updateUser({ id: user.id, username: user.username }).subscribe({
        error: () => this.cdr.markForCheck(),
      }),
    );
  }

  updateRole(user: UserRow, event: Event) {
    const select = event.target as HTMLSelectElement;
    user.role = select.value;
    this.subscriptions.add(
      this.adminService.updateUser({ id: user.id, role: user.role as any }).subscribe({
        error: () => this.cdr.markForCheck(),
      }),
    );
  }

  toggleActive(user: UserRow, event: Event) {
    const checked = (event.target as HTMLInputElement).checked;
    user.is_active = checked;
    this.subscriptions.add(
      this.adminService.updateUser({ id: user.id, is_active: checked }).subscribe({
        error: () => this.cdr.markForCheck(),
      }),
    );
  }

  assignTherapist(patientId: number, selectEl: HTMLSelectElement) {
    const ids = Array.from(selectEl.selectedOptions).map((o) => parseInt(o.value));
    this.subscriptions.add(
      this.adminService.assignTherapist(patientId, ids).subscribe({
        next: () => {
          const user = this.users.find((u) => u.id === patientId);
          if (user) user.therapist_ids = ids;
          this.cdr.markForCheck();
        },
        error: () => this.cdr.markForCheck(),
      }),
    );
  }

  openActionDrawer(user: UserRow) {
    this.selectedUser = user;
    this.showActionDrawer = true;
  }

  closeActionDrawer() {
    this.showActionDrawer = false;
    this.selectedUser = null;
  }

  openEditDrawer(user: UserRow) {
    this.editData = {
      id: user.id,
      username: user.username,
      email: user.email,
      role: user.role,
      is_active: user.is_active,
      sede_id: user.sede_id,
      sede_ids: user.assigned_sedes?.map((s) => s.id) || [],
      salary: user.salary_base || 0,
      hours: user.contract_hours || 0,
      modality: user.sessions_total ? user.sessions_total / 4 : 0,
      plan_type: user.plan_type || 'individual',
      frequency: user.payment_plan || 'monthly',
      amount: user.payment_amount || 0,
      attended: user.sessions_attended || 0,
      has_shift2: user.has_second_shift || false,
      modality_2: user.sessions_total_2 ? user.sessions_total_2 / 4 : 0,
      plan_type_2: user.plan_type_2 || 'individual',
      amount_2: user.payment_amount_2 || 0,
      attended_2: user.sessions_attended_2 || 0,
      start_time: user.work_start_time || '',
      end_time: user.work_end_time || '',
      days: user.work_days ? user.work_days.split(',').map(Number) : [],
    };
    this.closeActionDrawer();
    this.showEditDrawer = true;
  }

  closeEditDrawer() {
    this.showEditDrawer = false;
    this.editData = {};
  }

  saveEditUser() {
    const payload: any = { id: this.editData.id };
    if (this.editData.username) payload.username = this.editData.username;
    if (this.editData.is_active !== undefined) payload.is_active = this.editData.is_active;
    if (this.editData.role) payload.role = this.editData.role;
    if (this.editData.sede_id) payload.sede_id = this.editData.sede_id;
    if (this.editData.sede_ids?.length) payload.sede_ids = this.editData.sede_ids;
    if (this.editData.salary) payload.salary_base = this.editData.salary;
    if (this.editData.hours) payload.contract_hours = this.editData.hours;
    if (this.editData.modality) payload.sessions_total = this.editData.modality * 4;
    if (this.editData.plan_type) payload.plan_type = this.editData.plan_type;
    if (this.editData.frequency) payload.payment_plan = this.editData.frequency;
    if (this.editData.amount) payload.payment_amount = this.editData.amount;
    if (this.editData.attended !== undefined) payload.sessions_attended = this.editData.attended;
    payload.has_second_shift = this.editData.has_shift2;
    if (this.editData.has_shift2) {
      if (this.editData.modality_2) payload.sessions_total_2 = this.editData.modality_2 * 4;
      if (this.editData.plan_type_2) payload.plan_type_2 = this.editData.plan_type_2;
      if (this.editData.amount_2) payload.payment_amount_2 = this.editData.amount_2;
      if (this.editData.attended_2 !== undefined) payload.sessions_attended_2 = this.editData.attended_2;
    }
    if (this.editData.start_time) payload.work_start_time = this.editData.start_time;
    if (this.editData.end_time) payload.work_end_time = this.editData.end_time;
    if (this.editData.days?.length) payload.work_days = this.editData.days.join(',');

    this.subscriptions.add(
      this.adminService.updateUser(payload).subscribe({
        next: (res: any) => {
          if (res.success) {
            this.closeEditDrawer();
            this.loadData();
          }
          this.cdr.markForCheck();
        },
        error: () => this.cdr.markForCheck(),
      }),
    );
  }

  openResetDrawer(user: UserRow) {
    const firstTime = user.admin_password_changed_count === 0;
    this.resetData = {
      userId: user.id,
      loginCount: user.admin_password_changed_count || 0,
      newPassword: '',
      showPassword: false,
      status: '',
      firstTime,
    };
    this.closeActionDrawer();
    this.showResetDrawer = true;
  }

  closeResetDrawer() {
    this.showResetDrawer = false;
    this.resetData = { userId: 0, loginCount: 0, newPassword: '', showPassword: false, status: '', firstTime: false };
  }

  toggleResetPasswordVisibility() {
    this.resetData.showPassword = !this.resetData.showPassword;
  }

  confirmResetPassword() {
    this.resetData.status = 'Procesando...';
    const payload: any = { id: this.resetData.userId };
    if (this.resetData.firstTime && this.resetData.newPassword) {
      payload.new_password = this.resetData.newPassword;
    }
    this.subscriptions.add(
      this.adminService.resetPassword(this.resetData.userId, this.resetData.newPassword || undefined).subscribe({
        next: (res: any) => {
          if (res.success) {
            this.resetData.status = `Contraseña reseteada. Clave temporal: ${res.temp_password || 'N/A'}`;
            setTimeout(() => this.closeResetDrawer(), 3000);
          } else {
            this.resetData.status = 'Error: ' + (res.message || 'Desconocido');
          }
          this.cdr.markForCheck();
        },
        error: () => {
          this.resetData.status = 'Error de conexión';
          this.cdr.markForCheck();
        },
      }),
    );
  }

  openCreateDrawer() {
    this.newUser = { email: '', username: '', role: 'jugador', sede_id: null, sede_ids: [], salary: null, hours: null, modality: null, frequency: 'monthly', plan_type: 'individual', amount: null, generate_schedule: true, start_date: '', start_time: '', schedule_therapist: null, days: [] };
    this.createStatus = '';
    this.showCreateDrawer = true;
    this.cdr.markForCheck();
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
    if (this.newUser.role === 'supervisor' && this.newUser.sede_ids.length) payload.sede_ids = this.newUser.sede_ids;
    if (this.newUser.role === 'terapista') {
      if (this.newUser.salary) payload.salary_base = this.newUser.salary;
      if (this.newUser.hours) payload.contract_hours = this.newUser.hours;
    }
    if (this.newUser.role === 'jugador') {
      if (this.newUser.modality) payload.modality = this.newUser.modality;
      if (this.newUser.amount) payload.payment_amount = this.newUser.amount;
      payload.payment_frequency = this.newUser.frequency;
      payload.plan_type = this.newUser.plan_type;
      payload.generate_schedule = this.newUser.generate_schedule;
      if (this.newUser.generate_schedule) {
        if (this.newUser.start_date) payload.start_date = this.newUser.start_date;
        if (this.newUser.start_time) payload.start_time = this.newUser.start_time;
        if (this.newUser.schedule_therapist) payload.therapist_id = this.newUser.schedule_therapist;
        if (this.newUser.days.length) payload.days_of_week = this.newUser.days;
      }
    }

    this.subscriptions.add(
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
          this.cdr.markForCheck();
        },
        error: () => {
          this.createStatus = 'Error de conexión';
          this.cdr.markForCheck();
        },
      }),
    );
  }

  async deleteUser(user: UserRow) {
    const confirmed = await firstValueFrom(this.confirmService.confirm({
      title: 'Eliminar Usuario',
      message: `¿Eliminar a ${user.username} permanentemente?`,
      confirmText: 'Eliminar',
      cancelText: 'Cancelar',
      variant: 'danger',
    }));
    if (!confirmed) return;
    this.subscriptions.add(
      this.adminService.deleteUser(user.id).subscribe({
        next: (res: any) => {
          if (res.success) {
            this.users = this.users.filter((u) => u.id !== user.id);
            this.applyFilters();
            this.closeActionDrawer();
          }
          this.cdr.markForCheck();
        },
        error: () => this.cdr.markForCheck(),
      }),
    );
  }

  getSedeName(user: UserRow): string {
    if (user.sede_name) return user.sede_name;
    const sede = this.sedes.find((s) => s.id === user.sede_id);
    return sede?.name || 'Sin Sede';
  }

  getRoleBadge(role: string): string {
    const map: Record<string, string> = { jugador: 'Paciente', terapista: 'Terapeuta', admin: 'Admin', supervisor: 'Supervisor' };
    return map[role] || role;
  }

  getStatusLabel(account_status: string): string {
    const map: Record<string, string> = {
      active: 'Activo',
      inactive: 'Inactivo',
      retired: 'Retirado',
      debtor: 'Deudor',
    };
    return map[account_status] || 'Activo';
  }

  getInitials(name: string): string {
    return name?.slice(0, 2).toUpperCase() || 'US';
  }

  trackById(_: number, u: UserRow): number {
    return u.id;
  }
}
