import { Component, OnInit, OnDestroy, ViewChild, TemplateRef, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { Subscription } from 'rxjs';
import { AdminService } from '../../../../../core/services/admin.service';
import { HeaderService } from '../../../../../core/services/header.service';
import { Sede } from '../../../../../core/models/sede';
import { fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter } from '../../../../../core/animations';
import { firstValueFrom } from 'rxjs';
import { SelectOption } from '../../../../../shared/components/select/select';
import { ConfirmService } from '../../../../../core/services/confirm.service';
import { Spinner } from '../../../../../shared/components/spinner/spinner';
import { Button } from '../../../../../shared/components/button/button';
import { Select } from '../../../../../shared/components/select/select';
import { Input } from '../../../../../shared/components/input/input';
import { Drawer } from '../../../../../shared/components/drawer/drawer';
import { Table, TableCell } from '../../../../../shared/components/table/table';
import { UsersStatsCards } from '../components/users-stats-cards/users-stats-cards';

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
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule, FontAwesomeModule, Spinner, Button, Select, Input, Drawer, Table, TableCell, UsersStatsCards],
  templateUrl: './users-list.html',
  styleUrl: './users-list.scss',
  animations: [fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class UsersList implements OnInit, OnDestroy {
  readonly Math = Math;
  @ViewChild('headerActions', { static: true }) headerActions!: TemplateRef<any>;

  users: UserRow[] = [];
  filteredUsers: UserRow[] = [];
  paginatedUsers: UserRow[] = [];
  sedes: Sede[] = [];
  activeSedes: Pick<Sede, 'id' | 'name'>[] = [];
  therapists: { id: number; username: string; email: string }[] = [];

  activeFilter = 'all';
  searchQuery = '';
  selectedSedeId: number | null = null;
  selectedTherapistId: number | null = null;
  selectedStatus: string | null = null;
  loading = true;

  currentPage = 1;
  pageSize = 20;
  totalPages = 1;

  stats = { total: 0, active: 0, inactive: 0, patients: 0, therapists: 0, supervisors: 0, admins: 0, retired: 0, debtors: 0 };

  showEditDrawer = false;
  showResetDrawer = false;
  showCreateDrawer = false;

  editData: any = {};
  currentEditUser: UserRow | null = null;
  resetData = { userId: 0, loginCount: 0, newPassword: '', showPassword: false, status: '', firstTime: false };
  newUser = { email: '', username: '', role: 'jugador', sede_id: null as number | null, sede_ids: [] as number[], salary: null as number | null, hours: null as number | null, modality: null as number | null, frequency: 'monthly', plan_type: 'individual', amount: null as number | null, generate_schedule: true, start_date: '', start_time: '', schedule_therapist: null as number | null, days: [] as number[] };
  createStatus = '';

  toastMessage = '';
  toastType: 'success' | 'error' = 'success';
  showToast = false;

  private sedeLookup: Record<string, string> = {};
  private subscriptions = new Subscription();

  roleOptions: SelectOption[] = [
    {value: 'jugador', label: 'Paciente'},
    {value: 'terapista', label: 'Terapeuta'},
    {value: 'supervisor', label: 'Supervisor'},
    {value: 'admin', label: 'Administrador'},
  ];

  modalityOptions: SelectOption[] = [
    {value: 'presencial', label: 'Presencial'},
    {value: 'online', label: 'Online'},
  ];

  planTypeOptions: SelectOption[] = [
    {value: 'individual', label: 'Individual'},
    {value: 'group', label: 'Grupal'},
  ];

  frequencyOptions: SelectOption[] = [
    {value: 'monthly', label: 'Mensual'},
    {value: 'biweekly', label: 'Quincenal'},
    {value: 'weekly', label: 'Semanal'},
  ];

  editModalityOptions: SelectOption[] = [
    {value: 0, label: 'Sin paquete'},
    {value: 1, label: '1x (4 ses)'},
    {value: 2, label: '2x (8 ses)'},
    {value: 3, label: '3x (12 ses)'},
  ];

  createModalityOptions: SelectOption[] = [
    {value: 1, label: '1x Semana (4 ses)'},
    {value: 2, label: '2x Semana (8 ses)'},
    {value: 3, label: '3x Semana (12 ses)'},
  ];

  accountStatusOptions: SelectOption[] = [
    {value: 'active', label: 'Activo'},
    {value: 'inactive', label: 'Inactivo'},
    {value: 'debtor', label: 'Deudor'},
    {value: 'retired', label: 'Retirado'},
  ];

  get editTherapistOptions(): SelectOption[] {
    return this.therapists.map(t => ({value: t.id, label: t.username}));
  }

  get sedeOptions(): SelectOption[] {
    return [{value: null, label: 'Todas las Sedes'}, ...this.activeSedes.map(s => ({value: s.id, label: s.name}))];
  }

  get statusOptions(): SelectOption[] {
    return [
      {value: null, label: 'Todos los estados'},
      {value: 'active', label: 'Activo'},
      {value: 'inactive', label: 'Inactivo'},
      {value: 'debtor', label: 'Deudor'},
      {value: 'retired', label: 'Retirado'},
    ];
  }

  get therapistOptions(): SelectOption[] {
    return [{value: null, label: 'Todos los terapeutas'}, ...this.therapists.map(t => ({value: t.id, label: t.username}))];
  }

  get therapistOptionsAll(): SelectOption[] {
    return this.therapists.map(t => ({value: t.id, label: t.username}));
  }

  get patientSedeOptions(): SelectOption[] {
    return [{value: null, label: '— Sin asignar —'}, ...this.activeSedes.map(s => ({value: s.id, label: s.name}))];
  }

  get multiSedeOptions(): SelectOption[] {
    return this.activeSedes.map(s => ({value: s.id, label: s.name}));
  }

  get scheduleTherapistOptions(): SelectOption[] {
    return [{value: null, label: '— Seleccionar —'}, ...this.therapists.map(t => ({value: t.id, label: t.username + ' (' + t.email + ')'}))];
  }

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
    this.restoreFiltersFromUrl();
    this.loadData();
  }

  ngOnDestroy() {
    this.headerService.reset();
    this.subscriptions.unsubscribe();
  }

  private restoreFiltersFromUrl() {
    const params = new URLSearchParams(window.location.search);
    const search = params.get('search');
    const filter = params.get('filter');
    const sede = params.get('sede');
    const therapist = params.get('therapist');
    const status = params.get('status');
    const page = params.get('page');
    if (search) this.searchQuery = search;
    if (filter) this.activeFilter = filter;
    if (sede) this.selectedSedeId = Number(sede);
    if (therapist) this.selectedTherapistId = Number(therapist);
    if (status) this.selectedStatus = status;
    if (page) this.currentPage = Number(page);
  }

  private persistFiltersToUrl() {
    const params = new URLSearchParams();
    if (this.searchQuery) params.set('search', this.searchQuery);
    if (this.activeFilter !== 'all') params.set('filter', this.activeFilter);
    if (this.selectedSedeId) params.set('sede', String(this.selectedSedeId));
    if (this.selectedTherapistId) params.set('therapist', String(this.selectedTherapistId));
    if (this.selectedStatus) params.set('status', this.selectedStatus);
    if (this.currentPage > 1) params.set('page', String(this.currentPage));
    const qs = params.toString();
    const newUrl = qs ? `${window.location.pathname}?${qs}` : window.location.pathname;
    window.history.replaceState({}, '', newUrl);
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

    this.subscriptions.add(
      this.adminService.getActiveSedes().subscribe({
        next: (list) => {
          this.activeSedes = list;
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
    else if (this.activeFilter === 'inactive') result = result.filter((u) => !u.is_active);

    if (this.selectedStatus) {
      result = result.filter((u) => u.account_status === this.selectedStatus);
    }

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
    this.totalPages = Math.max(1, Math.ceil(result.length / this.pageSize));
    if (this.currentPage > this.totalPages) this.currentPage = 1;
    this.updatePagination();
    this.calcStats();
    this.persistFiltersToUrl();
  }

  private updatePagination() {
    const start = (this.currentPage - 1) * this.pageSize;
    this.paginatedUsers = this.filteredUsers.slice(start, start + this.pageSize);
  }

  setFilter(filter: string) {
    this.activeFilter = filter;
    this.currentPage = 1;
    this.applyFilters();
  }

  onSearch(query: string | number) {
    this.searchQuery = String(query);
    this.currentPage = 1;
    this.applyFilters();
  }

  onSedeChange(sedeId: number | null) {
    this.selectedSedeId = sedeId;
    this.currentPage = 1;
    this.applyFilters();
  }

  onTherapistFilterChange(therapistId: number | null) {
    this.selectedTherapistId = therapistId;
    this.currentPage = 1;
    this.applyFilters();
  }

  onStatusChange(status: string | null) {
    this.selectedStatus = status;
    this.currentPage = 1;
    this.applyFilters();
  }

  get hasActiveFilters(): boolean {
    return this.searchQuery !== '' || this.activeFilter !== 'all' || this.selectedSedeId !== null || this.selectedTherapistId !== null || this.selectedStatus !== null;
  }

  clearAllFilters() {
    this.searchQuery = '';
    this.activeFilter = 'all';
    this.selectedSedeId = null;
    this.selectedTherapistId = null;
    this.selectedStatus = null;
    this.currentPage = 1;
    this.persistFiltersToUrl();
    this.applyFilters();
  }

  goToPage(page: number) {
    if (page < 1 || page > this.totalPages) return;
    this.currentPage = page;
    this.updatePagination();
    this.persistFiltersToUrl();
  }

  get pageNumbers(): number[] {
    const pages: number[] = [];
    const total = this.totalPages;
    const current = this.currentPage;
    const start = Math.max(1, current - 2);
    const end = Math.min(total, current + 2);
    for (let i = start; i <= end; i++) pages.push(i);
    return pages;
  }

  toggleActive(user: UserRow, event: Event) {
    const checked = (event.target as HTMLInputElement).checked;
    const prev = user.is_active;
    user.is_active = checked;
    this.subscriptions.add(
      this.adminService.updateUser({ id: user.id, is_active: checked }).subscribe({
        next: (res: any) => {
          if (res.success) {
            this.showSuccessToast(checked ? 'Usuario activado' : 'Usuario desactivado');
          } else {
            user.is_active = prev;
            this.showErrorToast(res.message || 'Error al actualizar');
          }
          this.cdr.markForCheck();
        },
        error: () => {
          user.is_active = prev;
          this.showErrorToast('Error de conexion');
          this.cdr.markForCheck();
        },
      }),
    );
  }

  assignTherapist(user: UserRow) {
    this.subscriptions.add(
      this.adminService.assignTherapist(user.id, user.therapist_ids).subscribe({
        next: (res: any) => {
          if (res.success) this.showSuccessToast('Terapeuta asignado');
          this.cdr.markForCheck();
        },
        error: () => this.cdr.markForCheck(),
      }),
    );
  }

  openEditDrawer(user: UserRow) {
    this.editData = {
      id: user.id,
      username: user.username,
      email: user.email,
      role: user.role,
      is_active: user.is_active,
      account_status: user.account_status || 'active',
      sede_id: user.sede_id,
      sede_ids: user.assigned_sedes?.map((s) => s.id) || [],
      edit_therapist_ids: user.therapist_ids || [],
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
      new_password: '',
      show_password: false,
    };
    this.currentEditUser = user;
    this.showEditDrawer = true;
  }

  closeEditDrawer() {
    this.showEditDrawer = false;
    this.editData = {};
    this.currentEditUser = null;
  }

  saveEditUser() {
    const payload: any = { id: this.editData.id };
    if (this.editData.username) payload.username = this.editData.username;
    if (this.editData.is_active !== undefined) payload.is_active = this.editData.is_active;
    if (this.editData.account_status) payload.account_status = this.editData.account_status;
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
            this.updateUserLocally(payload);
            const promises: Promise<any>[] = [];

            if (this.editData.role === 'jugador' && this.editData.edit_therapist_ids?.length) {
              promises.push(firstValueFrom(this.adminService.assignTherapist(this.editData.id, this.editData.edit_therapist_ids)));
            }

            if (this.editData.new_password) {
              promises.push(firstValueFrom(this.adminService.resetPassword(this.editData.id, this.editData.new_password)));
            }

            if (promises.length) {
              Promise.all(promises).then(() => {
                this.closeEditDrawer();
                this.showSuccessToast('Usuario actualizado');
              }).catch(() => {
                this.closeEditDrawer();
                this.showSuccessToast('Usuario actualizado (algunas opciones pendientes)');
              });
            } else {
              this.closeEditDrawer();
              this.showSuccessToast('Usuario actualizado');
            }
          } else {
            this.showErrorToast(res.message || 'Error al guardar');
          }
          this.cdr.markForCheck();
        },
        error: () => {
          this.showErrorToast('Error de conexion');
          this.cdr.markForCheck();
        },
      }),
    );
  }

  private updateUserLocally(payload: any) {
    const idx = this.users.findIndex((u) => u.id === payload.id);
    if (idx === -1) return;
    const u = this.users[idx];
    if (payload.username) u.username = payload.username;
    if (payload.is_active !== undefined) u.is_active = payload.is_active;
    if (payload.role) u.role = payload.role;
    if (payload.sede_id) { u.sede_id = payload.sede_id; u.sede_name = this.sedeLookup[String(payload.sede_id)] || u.sede_name; }
    if (payload.sede_ids) u.assigned_sedes = this.activeSedes.filter(s => payload.sede_ids.includes(s.id));
    if (payload.salary_base) u.salary_base = payload.salary_base;
    if (payload.contract_hours) u.contract_hours = payload.contract_hours;
    if (payload.sessions_total) u.sessions_total = payload.sessions_total;
    if (payload.plan_type) u.plan_type = payload.plan_type;
    if (payload.payment_plan) u.payment_plan = payload.payment_plan;
    if (payload.payment_amount) u.payment_amount = payload.payment_amount;
    if (payload.sessions_attended !== undefined) u.sessions_attended = payload.sessions_attended;
    if (payload.has_second_shift !== undefined) u.has_second_shift = payload.has_second_shift;
    this.applyFilters();
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
    this.subscriptions.add(
      this.adminService.resetPassword(this.resetData.userId, this.resetData.newPassword || undefined).subscribe({
        next: (res: any) => {
          if (res.success) {
            this.resetData.status = `Contrasena reseteada. Clave temporal: ${res.temp_password || 'N/A'}`;
            setTimeout(() => this.closeResetDrawer(), 3000);
          } else {
            this.resetData.status = 'Error: ' + (res.message || 'Desconocido');
          }
          this.cdr.markForCheck();
        },
        error: () => {
          this.resetData.status = 'Error de conexion';
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
            this.createStatus = `Creado! Contrasena temporal: ${res.temp_password || 'N/A'}`;
            setTimeout(() => {
              this.closeCreateDrawer();
              this.loadData();
            }, 2000);
          } else {
            this.createStatus = 'Error: ' + (res.message || 'Desconocido');
          }
          this.cdr.markForCheck();
        },
        error: (err: any) => {
          this.createStatus = 'Error: ' + (err.error?.message || 'Error de conexion');
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
            this.showSuccessToast('Usuario eliminado');
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

  getRoleBadgeClass(role: string): string {
    const map: Record<string, string> = {
      jugador: 'bg-secondary-container/15 text-secondary-container',
      terapista: 'bg-info-container/15 text-info-container',
      admin: 'bg-primary-container/15 text-primary-container',
      supervisor: 'bg-tertiary-container/15 text-tertiary-container',
    };
    return map[role] || 'bg-surface-container-high text-on-surface-variant';
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

  getStatusClass(account_status: string): string {
    const map: Record<string, string> = {
      active: 'bg-primary-container/15 text-primary-container',
      inactive: 'bg-tertiary-container/15 text-tertiary-container',
      retired: 'bg-surface-container-highest text-on-surface-variant',
      debtor: 'bg-error-container/30 text-error',
    };
    return map[account_status] || 'bg-primary-container/15 text-primary-container';
  }

  getInitials(name: string): string {
    return name?.slice(0, 2).toUpperCase() || 'US';
  }

  trackById(_: number, u: UserRow): number {
    return u.id;
  }

  columns = [
    {key: 'usuario', label: 'Usuario', width: '24%'},
    {key: 'email', label: 'Email', width: '20%'},
    {key: 'rol', label: 'Rol', width: '14%'},
    {key: 'sede', label: 'Sede', width: '14%'},
    {key: 'estado', label: 'Estado', width: '12%'},
    {key: 'activo', label: 'Activo', align: 'center' as const, width: '8%'},
    {key: 'acciones', label: '', align: 'right' as const, width: '8%'},
  ];

  getRowClass = (u: UserRow, i: number): string => {
    const classes: string[] = [];
    if (u.account_status === 'debtor') classes.push('bg-error-container/10');
    if (u.account_status === 'retired') classes.push('bg-surface-container-highest/40');
    if (!u.is_active && u.account_status !== 'debtor' && u.account_status !== 'retired') classes.push('bg-warning-container/20');
    if (u.account_status === 'active' && u.is_active) classes.push('hover:bg-surface-container-high/50');
    return classes.join(' ');
  };

  trackUser = (i: number, u: UserRow): number => u.id;

  private showSuccessToast(msg: string) {
    this.toastMessage = msg;
    this.toastType = 'success';
    this.showToast = true;
    setTimeout(() => { this.showToast = false; this.cdr.markForCheck(); }, 3000);
    this.cdr.markForCheck();
  }

  private showErrorToast(msg: string) {
    this.toastMessage = msg;
    this.toastType = 'error';
    this.showToast = true;
    setTimeout(() => { this.showToast = false; this.cdr.markForCheck(); }, 4000);
    this.cdr.markForCheck();
  }
}
