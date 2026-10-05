import { Component, OnInit, OnDestroy, ViewChild, TemplateRef, ChangeDetectionStrategy, ChangeDetectorRef, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule, Router } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { Subject, Subscription, debounceTime } from 'rxjs';
import { AdminService } from '../../../../../core/services/admin.service';
import { HeaderService } from '../../../../../core/services/header.service';
import { Sede } from '../../../../../core/models/sede';
import { fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter } from '../../../../../core/animations';
import { firstValueFrom } from 'rxjs';
import { SelectOption } from '../../../../../shared/components/select/select';
import { ConfirmService } from '../../../../../core/services/confirm.service';
import { Alert } from '../../../../../shared/components/alert/alert';
import { Spinner } from '../../../../../shared/components/spinner/spinner';
import { Button } from '../../../../../shared/components/button/button';
import { Select } from '../../../../../shared/components/select/select';
import { Input } from '../../../../../shared/components/input/input';
import { Drawer } from '../../../../../shared/components/drawer/drawer';
import { Modal } from '../../../../../shared/components/modal/modal';
import { StatKey, UsersStatsCards } from '../components/users-stats-cards/users-stats-cards';

/** Valor del filtro de terapeuta que significa "pacientes sin ningun terapeuta asignado". */
const NO_THERAPIST = -1;

type EditTabKey = 'cuenta' | 'plan' | 'seguridad';

/** Pestañas del drawer de edición según el rol (referencias estables: no se crean arrays por ciclo). */
const EDIT_TABS: Record<string, { key: EditTabKey; label: string }[]> = {
  terapista: [{ key: 'cuenta', label: 'Cuenta' }, { key: 'plan', label: 'Contrato y horario' }, { key: 'seguridad', label: 'Seguridad' }],
  jugador: [{ key: 'cuenta', label: 'Cuenta' }, { key: 'plan', label: 'Plan y terapeuta' }, { key: 'seguridad', label: 'Seguridad' }],
  default: [{ key: 'cuenta', label: 'Cuenta' }, { key: 'seguridad', label: 'Seguridad' }],
};

/** Pasos del asistente de alta según el rol. */
const CREATE_STEPS: Record<string, { key: string; label: string }[]> = {
  jugador: [{ key: 'datos', label: 'Datos' }, { key: 'plan', label: 'Plan y horario' }, { key: 'apoderado', label: 'Apoderado' }],
  terapista: [{ key: 'datos', label: 'Datos' }, { key: 'contrato', label: 'Contrato' }],
  default: [{ key: 'datos', label: 'Datos' }],
};

interface UserRow {
  id: number;
  username: string;
  email: string;
  login_code?: string;
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

interface StatusLogRow {
  id: number;
  old_status: string;
  new_status: string;
  justification: string;
  changed_by_username: string | null;
  changed_at: string;
}

@Component({
  selector: 'app-users-list',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule, FontAwesomeModule, Spinner, Alert, Button, Select, Input, Drawer, Modal, UsersStatsCards],
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
  activeSedes: Pick<Sede, 'id' | 'name'>[] = [];
  therapists: { id: number; username: string; email: string }[] = [];

  activeFilter = 'jugador';
  searchQuery = '';
  selectedSedeId: number | null = null;
  selectedTherapistId: number | null = null;
  selectedStatus: string | null = 'active';
  loading = true;
  loadError = false;

  /** Una sola vista de lista en el DOM: tabla en >=1280px (con el menu lateral abierto no cabe antes), tarjetas por debajo. */
  isDesktop = window.matchMedia('(min-width: 1280px)').matches;
  showFilters = false;
  editSaving = false;
  editTab: EditTabKey = 'cuenta';
  createStep = 1;

  readonly roleChips = [
    { value: 'all', label: 'Todos' },
    { value: 'jugador', label: 'Pacientes' },
    { value: 'terapista', label: 'Terapeutas' },
    { value: 'supervisor', label: 'Supervisores' },
    { value: 'admin', label: 'Administradores' },
  ];
  private mediaQuery = window.matchMedia('(min-width: 1280px)');
  private onMediaChange = (event: MediaQueryListEvent) => {
    this.isDesktop = event.matches;
    this.cdr.markForCheck();
  };

  stats = { total: 0, active: 0, inactive: 0, patients: 0, activePatients: 0, therapists: 0, supervisors: 0, admins: 0, retired: 0, debtors: 0, noTherapist: 0 };

  showEditDrawer = false;
  showResetDrawer = false;
  showCreateDrawer = false;
  showGroupDrawer = false;
  showGroupModal = false;

  showPatientDetailModal = false;
  patientDetailData: any = null;
  patientDetailLoading = false;

  showEditPatientModal = false;
  patientDetailForm: any = {};
  patientDetailStatus = '';
  patientDetailSaving = false;

  editData: any = {};
  currentEditUser: UserRow | null = null;
  resetData = { userId: 0, loginCount: 0, newPassword: '', showPassword: false, status: '', firstTime: false };
  newUser = { email: '', username: '', role: 'jugador', sede_id: null as number | null, sede_ids: [] as number[], salary: null as number | null, hours: null as number | null, modality: null as number | null, evaluation_date: '' as string, frequency: 'monthly', plan_type: 'individual', amount: null as number | null, generate_schedule: true, start_date: '', start_time: '', schedule_therapist: null as number | null, days: [] as number[], guardian_name: '', guardian_type: 'tutor', guardian_dni: '', guardian_contact: '' };
  createStatus = '';

  /** Clave temporal recien generada (alta o restablecimiento). Se muestra hasta que el admin pulse "Listo". */
  tempCredentials: { context: 'created' | 'reset'; name: string; password: string } | null = null;
  passwordCopied = false;

  patientGroups: any[] = [];
  groupForm: any = {};
  editingGroupId: number | null = null;
  groupTherapistPatients: any[] | null = null;
  groupSearchQuery = '';
  groupPatientsLoading = false;

  groupCalendarMonth: Date = new Date();
  groupCalendarDays: { date: Date; day: number; selected: boolean; disabled: boolean }[][] = [];
  groupRangeMode = false;
  groupRangeStartStr: string | null = null;
  groupUnlockPast = false;
  groupMonths = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Setiembre', 'Octubre', 'Noviembre', 'Diciembre'];

  toastMessage = '';
  toastType: 'success' | 'error' = 'success';
  showToast = false;

  showStatusModal = false;
  statusModalUser: UserRow | null = null;
  statusModalStatus = 'active';
  statusModalJustification = '';
  statusModalSaving = false;
  statusHistory: StatusLogRow[] = [];
  statusHistoryLoading = false;

  private sedeLookup: Record<string, string> = {};
  private subscriptions = new Subscription();
  private search$ = new Subject<void>();

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

  // Las opciones se reconstruyen al cargar terapeutas/sedes (rebuildOptions): antes eran getters que
  // devolvian arrays nuevos en cada ciclo de deteccion y obligaban a app-select a recalcular todo.
  editTherapistOptions: SelectOption[] = [];
  sedeOptions: SelectOption[] = [{ value: null, label: 'Todas las sedes' }];
  readonly statusOptions: SelectOption[] = [
    { value: null, label: 'Todos los estados' },
    { value: 'active', label: 'Activo' },
    { value: 'inactive', label: 'Inactivo' },
    { value: 'debtor', label: 'Deudor' },
    { value: 'retired', label: 'Retirado' },
  ];
  therapistOptions: SelectOption[] = [{ value: null, label: 'Todos los terapeutas' }];
  therapistOptionsAll: SelectOption[] = [];
  groupTherapistOptions: SelectOption[] = [{ value: null, label: '— Seleccionar terapeuta —' }];
  patientSedeOptions: SelectOption[] = [{ value: null, label: '— Sin asignar —' }];
  multiSedeOptions: SelectOption[] = [];
  scheduleTherapistOptions: SelectOption[] = [{ value: null, label: '— Seleccionar —' }];

  private rebuildOptions() {
    const therapistItems = this.therapists.map((t) => ({ value: t.id, label: t.username }));
    const sedeItems = this.activeSedes.map((s) => ({ value: s.id, label: s.name }));
    this.editTherapistOptions = therapistItems;
    this.therapistOptionsAll = therapistItems;
    this.therapistOptions = [
      { value: null, label: 'Todos los terapeutas' },
      { value: NO_THERAPIST, label: 'Sin terapeuta asignado' },
      ...therapistItems,
    ];
    this.groupTherapistOptions = [{ value: null, label: '— Seleccionar terapeuta —' }, ...therapistItems];
    this.scheduleTherapistOptions = [
      { value: null, label: '— Seleccionar —' },
      ...this.therapists.map((t) => ({ value: t.id, label: t.username + ' (' + t.email + ')' })),
    ];
    this.sedeOptions = [{ value: null, label: 'Todas las sedes' }, ...sedeItems];
    this.patientSedeOptions = [{ value: null, label: '— Sin asignar —' }, ...sedeItems];
    this.multiSedeOptions = sedeItems;
  }

  private http = inject(HttpClient);

  constructor(
    private adminService: AdminService,
    private headerService: HeaderService,
    private confirmService: ConfirmService,
    private cdr: ChangeDetectorRef,
    private router: Router,
  ) {}

  ngOnInit() {
    this.headerService.setConfig({
      title: 'Usuarios',
      subtitle: 'Crear y gestionar terapeutas y pacientes',
      icon: ['fas', 'users'],
      actionTemplate: this.headerActions,
    });
    this.mediaQuery.addEventListener('change', this.onMediaChange);
    this.subscriptions.add(this.search$.pipe(debounceTime(200)).subscribe(() => this.applyFilters(false)));
    this.restoreFiltersFromUrl();
    this.loadData();
    this.loadGroups();
  }

  ngOnDestroy() {
    if (this.toastTimer) clearTimeout(this.toastTimer);
    this.mediaQuery.removeEventListener('change', this.onMediaChange);
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
    if (search) this.searchQuery = search;
    if (filter) this.activeFilter = filter;
    if (sede) this.selectedSedeId = Number(sede);
    if (therapist) this.selectedTherapistId = Number(therapist);
    if (status) this.selectedStatus = status === 'all' ? null : status;
  }

  private persistFiltersToUrl() {
    const params = new URLSearchParams();
    if (this.searchQuery) params.set('search', this.searchQuery);
    params.set('filter', this.activeFilter);
    if (this.selectedSedeId) params.set('sede', String(this.selectedSedeId));
    if (this.selectedTherapistId) params.set('therapist', String(this.selectedTherapistId));
    params.set('status', this.selectedStatus ?? 'all');
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
              login_code: u.login_code || '',
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
            this.rebuildOptions();
            this.buildSedeLookup();
            this.applyFilters();
            this.loading = false;
            this.loadError = false;
          } else {
            this.loading = false;
            this.loadError = true;
          }
          this.cdr.markForCheck();
        },
        error: () => {
          this.loading = false;
          this.loadError = true;
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
        error: () => {
          this.showErrorToast('No se pudieron cargar las sedes. Revisa tu conexión.');
        },
      }),
    );

    this.subscriptions.add(
      this.adminService.getActiveSedes().subscribe({
        next: (list) => {
          this.activeSedes = list;
          this.rebuildOptions();
          this.cdr.markForCheck();
        },
        error: () => {
          this.showErrorToast('No se pudieron cargar las sedes. Revisa tu conexión.');
        },
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
      activePatients: this.users.filter((u) => u.role === 'jugador' && u.account_status === 'active').length,
      noTherapist: this.users.filter((u) => u.role === 'jugador' && u.account_status === 'active' && !u.therapist_ids?.length).length,
      therapists: this.users.filter((u) => u.role === 'terapista').length,
      supervisors: this.users.filter((u) => u.role === 'supervisor').length,
      admins: this.users.filter((u) => u.role === 'admin').length,
      retired: this.users.filter((u) => u.account_status === 'retired').length,
      debtors: this.users.filter((u) => u.account_status === 'debtor').length,
    };
  }

  applyFilters(recalcStats = true) {
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
      result = result.filter((u) => u.username?.toLowerCase().includes(q) || u.email?.toLowerCase().includes(q) || u.login_code?.toLowerCase().includes(q));
    }

    if (this.selectedSedeId) {
      result = result.filter((u) => {
        if (u.role === 'terapista') return u.assigned_sedes?.some((s) => s.id === this.selectedSedeId);
        return u.sede_id === this.selectedSedeId;
      });
    }

    if (this.selectedTherapistId === NO_THERAPIST) {
      result = result.filter((u) => u.role === 'jugador' && !u.therapist_ids?.length);
    } else if (this.selectedTherapistId) {
      result = result.filter((u) => {
        if (u.role !== 'jugador') return false;
        return u.therapist_ids.includes(Number(this.selectedTherapistId));
      });
    }

    this.filteredUsers = result;
    if (recalcStats) this.calcStats();
    this.persistFiltersToUrl();
    this.cdr.markForCheck();
  }

  /** Lo que el admin esta viendo, en palabras: el default (pacientes activos) deja de ser una sorpresa. */
  get filterSummary(): string {
    const roles: Record<string, string> = { jugador: 'Pacientes', terapista: 'Terapeutas', supervisor: 'Supervisores', admin: 'Administradores', inactive: 'Inactivos' };
    const parts: string[] = [roles[this.activeFilter] || 'Todos los usuarios'];
    const statusPlural: Record<string, string> = { active: 'activos', inactive: 'inactivos', debtor: 'deudores', retired: 'retirados' };
    if (this.selectedStatus) parts.push(statusPlural[this.selectedStatus] ?? this.selectedStatus);
    if (this.selectedSedeId) parts.push(`sede ${this.activeSedes.find((s) => s.id === this.selectedSedeId)?.name ?? ''}`.trim());
    if (this.selectedTherapistId === NO_THERAPIST) parts.push('sin terapeuta');
    else if (this.selectedTherapistId) parts.push(`con ${this.therapists.find((t) => t.id === Number(this.selectedTherapistId))?.username ?? 'terapeuta'}`);
    if (this.searchQuery) parts.push(`«${this.searchQuery}»`);
    return parts.join(' · ');
  }

  /** Cantidad de filtros de los selects (no cuenta el rol ni la busqueda): rotula el boton "Filtros" en movil. */
  get selectFilterCount(): number {
    return [this.selectedSedeId, this.selectedStatus, this.selectedTherapistId].filter((v) => v !== null && v !== undefined).length;
  }

  get statsActiveKey(): StatKey | null {
    const noExtra = !this.searchQuery && !this.selectedSedeId;
    if (this.activeFilter === 'all' && !this.selectedStatus && !this.selectedTherapistId && noExtra) return 'total';
    if (this.activeFilter === 'jugador' && this.selectedStatus === 'active' && !this.selectedTherapistId && noExtra) return 'patients_active';
    if (this.activeFilter === 'all' && this.selectedStatus === 'debtor' && !this.selectedTherapistId && noExtra) return 'debtors';
    if (this.activeFilter === 'jugador' && this.selectedStatus === 'active' && this.selectedTherapistId === NO_THERAPIST && noExtra) return 'no_therapist';
    return null;
  }

  onStatSelect(key: StatKey) {
    this.searchQuery = '';
    this.selectedSedeId = null;
    this.selectedTherapistId = null;
    if (key === 'total') {
      this.activeFilter = 'all';
      this.selectedStatus = null;
    } else if (key === 'patients_active') {
      this.activeFilter = 'jugador';
      this.selectedStatus = 'active';
    } else if (key === 'debtors') {
      this.activeFilter = 'all';
      this.selectedStatus = 'debtor';
    } else {
      this.activeFilter = 'jugador';
      this.selectedStatus = 'active';
      this.selectedTherapistId = NO_THERAPIST;
    }
    this.applyFilters(false);
  }

  setFilter(filter: string) {
    this.activeFilter = filter;
    this.applyFilters();
  }

  onSearch(query: string | number) {
    this.searchQuery = String(query);
    this.search$.next();
  }

  onSedeChange(sedeId: number | null) {
    this.selectedSedeId = sedeId;
    this.applyFilters();
  }

  onTherapistFilterChange(therapistId: number | null) {
    this.selectedTherapistId = therapistId;
    this.applyFilters();
  }

  onStatusChange(status: string | null) {
    this.selectedStatus = status;
    this.applyFilters();
  }

  get hasActiveFilters(): boolean {
    return this.searchQuery !== '' || this.activeFilter !== 'all' || this.selectedSedeId !== null || this.selectedTherapistId !== null || this.selectedStatus !== null;
  }

  retryLoad() {
    this.loading = true;
    this.loadError = false;
    this.cdr.markForCheck();
    this.loadData();
  }

  /** Muestra a TODOS los usuarios (antes volvia al valor por defecto pacientes+activos y el boton mentia). */
  clearAllFilters() {
    this.searchQuery = '';
    this.activeFilter = 'all';
    this.selectedSedeId = null;
    this.selectedTherapistId = null;
    this.selectedStatus = null;
    this.persistFiltersToUrl();
    this.applyFilters();
  }

  openStatusModal(user: UserRow) {
    this.statusModalUser = user;
    this.statusModalStatus = user.account_status || 'active';
    this.statusModalJustification = '';
    this.statusHistory = [];
    this.showStatusModal = true;
    this.loadStatusHistory(user.id);
    this.cdr.markForCheck();
  }

  closeStatusModal() {
    this.showStatusModal = false;
    this.statusModalUser = null;
    this.cdr.markForCheck();
  }

  loadStatusHistory(userId: number) {
    this.statusHistoryLoading = true;
    this.subscriptions.add(
      this.adminService.getUserStatusHistory(userId).subscribe({
        next: (res: any) => {
          this.statusHistory = res.logs || [];
          this.statusHistoryLoading = false;
          this.cdr.markForCheck();
        },
        error: () => {
          this.statusHistoryLoading = false;
          this.cdr.markForCheck();
        },
      }),
    );
  }

  /** Retirar, marcar deudor o desactivar son decisiones de alto impacto: exigen dejar el motivo (queda en el historial). */
  get justificationRequired(): boolean {
    return ['retired', 'debtor', 'inactive'].includes(this.statusModalStatus) && this.statusModalStatus !== this.statusModalUser?.account_status;
  }

  get statusConfirmVariant(): 'primary' | 'danger' {
    return this.justificationRequired ? 'danger' : 'primary';
  }

  confirmStatusChange() {
    const user = this.statusModalUser;
    if (!user || this.statusModalSaving) return;
    if (this.justificationRequired && !this.statusModalJustification.trim()) {
      this.showErrorToast('Escribe la justificación del cambio de estado.');
      return;
    }
    if (this.statusModalStatus === user.account_status) {
      this.showErrorToast('El usuario ya tiene ese estado');
      return;
    }
    this.statusModalSaving = true;
    this.subscriptions.add(
      this.adminService
        .updateUserStatus(user.id, this.statusModalStatus, this.statusModalJustification)
        .subscribe({
          next: (res: any) => {
            this.statusModalSaving = false;
            if (res.success) {
              user.account_status = this.statusModalStatus;
              this.statusModalJustification = '';
              this.applyFilters();
              this.closeStatusModal();
              this.showSuccessToast('Estado del usuario actualizado');
            } else {
              this.showErrorToast(res.message || 'Error al actualizar el estado');
            }
            this.cdr.markForCheck();
          },
          error: () => {
            this.statusModalSaving = false;
            this.showErrorToast('Error de conexión');
            this.cdr.markForCheck();
          },
        }),
    );
  }

  formatStatusTimestamp(iso: string): string {
    if (!iso) return '—';
    const d = new Date(iso);
    return d.toLocaleString('es-PE', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  }

  assignTherapist(user: UserRow) {
    this.subscriptions.add(
      this.adminService.assignTherapist(user.id, user.therapist_ids).subscribe({
        next: (res: any) => {
          if (res.success) this.showSuccessToast('Terapeuta asignado');
          else this.showErrorToast(res.message || 'No se pudo asignar el terapeuta.');
          this.cdr.markForCheck();
        },
        error: () => this.showErrorToast('No se pudo asignar el terapeuta. Revisa tu conexión e inténtalo de nuevo.'),
      }),
    );
  }

  viewPatientDetail(user: UserRow) {
    this.router.navigate(['/admin/patients', user.id]);
  }

  openEditDrawer(user: UserRow) {
    this.editTab = 'cuenta';
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
    if (this.editSaving) return;
    this.editSaving = true;
    const payload: any = { id: this.editData.id };
    if (this.editData.username) payload.username = this.editData.username;
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
          this.editSaving = false;
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
                this.showErrorToast('Se guardó el usuario, pero algunas opciones no se pudieron guardar. Revisa los datos.');
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
          this.editSaving = false;
          this.showErrorToast('Error de conexión');
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
    if (payload.account_status) u.account_status = payload.account_status;
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

  // --- Drawer de edición por pestañas ---
  get editTabs() {
    return EDIT_TABS[this.editData?.role] ?? EDIT_TABS['default'];
  }

  get activeEditTab(): EditTabKey {
    return this.editTabs.some((t) => t.key === this.editTab) ? this.editTab : 'cuenta';
  }

  onEditTabsKeydown(event: KeyboardEvent) {
    const keys = this.editTabs.map((t) => t.key);
    const current = keys.indexOf(this.activeEditTab);
    let next = -1;
    if (event.key === 'ArrowRight') next = (current + 1) % keys.length;
    else if (event.key === 'ArrowLeft') next = (current - 1 + keys.length) % keys.length;
    else if (event.key === 'Home') next = 0;
    else if (event.key === 'End') next = keys.length - 1;
    else return;
    event.preventDefault();
    this.editTab = keys[next];
    this.cdr.markForCheck();
    setTimeout(() => document.getElementById('edit-tab-' + keys[next])?.focus(), 0);
  }

  // --- Asistente de alta por pasos ---
  get createSteps() {
    return CREATE_STEPS[this.newUser.role] ?? CREATE_STEPS['default'];
  }

  get isLastCreateStep(): boolean {
    return this.createStep >= this.createSteps.length;
  }

  prevCreateStep() {
    if (this.createStep > 1) {
      this.createStep--;
      this.createStatus = '';
    }
  }

  nextCreateStep() {
    if (!this.validateCreateStep()) return;
    this.createStatus = '';
    this.createStep = Math.min(this.createStep + 1, this.createSteps.length);
  }

  private validateCreateStep(): boolean {
    if (this.createStep === 1) {
      const username = this.newUser.username.trim();
      const email = this.newUser.email.trim();
      if (!username && !email) {
        this.createStatus = 'Error: escribe un nombre o un correo.';
        return false;
      }
      if (email && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) {
        this.createStatus = 'Error: el correo no tiene un formato válido.';
        return false;
      }
    }
    return true;
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
    this.tempCredentials = null;
    this.passwordCopied = false;
    this.showResetDrawer = true;
  }

  closeResetDrawer() {
    this.showResetDrawer = false;
    this.tempCredentials = null;
    this.passwordCopied = false;
    this.resetData = { userId: 0, loginCount: 0, newPassword: '', showPassword: false, status: '', firstTime: false };
  }

  /** Cierra el panel de credenciales: refresca la lista si fue un alta y cierra el drawer correspondiente. */
  finishCredentials() {
    if (this.tempCredentials?.context === 'created') this.closeCreateDrawer();
    else this.closeResetDrawer();
    this.cdr.markForCheck();
  }

  /** El boton enfocado (Crear/Restablecer) se destruye al mostrar la clave: el foco pasa al titulo del panel. */
  private focusCredentials() {
    setTimeout(() => document.getElementById('credentials-title')?.focus(), 0);
  }

  async copyTempPassword() {
    const password = this.tempCredentials?.password;
    if (!password) return;
    let ok = false;
    try {
      await navigator.clipboard.writeText(password);
      ok = true;
    } catch {
      // Sin contexto seguro (la LAN sirve la app por HTTP) no existe la API moderna.
      const area = document.createElement('textarea');
      area.value = password;
      area.setAttribute('readonly', '');
      area.setAttribute('aria-hidden', 'true');
      area.style.position = 'fixed';
      area.style.opacity = '0';
      document.body.appendChild(area);
      const previous = document.activeElement as HTMLElement | null;
      area.select();
      try {
        ok = document.execCommand('copy');
      } catch {
        ok = false;
      }
      document.body.removeChild(area);
      previous?.focus?.();
    }
    if (ok) {
      this.passwordCopied = true;
      this.showSuccessToast('Clave copiada');
    } else {
      this.showErrorToast('No se pudo copiar. Mantén pulsada la clave para seleccionarla.');
    }
    this.cdr.markForCheck();
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
            this.resetData.status = '';
            this.tempCredentials = {
              context: 'reset',
              name: this.users.find((u) => u.id === this.resetData.userId)?.username || 'el usuario',
              password: res.temp_password || '',
            };
            this.focusCredentials();
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
    this.newUser = { email: '', username: '', role: 'jugador', sede_id: null, sede_ids: [], salary: null, hours: null, modality: null, evaluation_date: '', frequency: 'monthly', plan_type: 'individual', amount: null, generate_schedule: true, start_date: '', start_time: '', schedule_therapist: null, days: [], guardian_name: '', guardian_type: 'tutor', guardian_dni: '', guardian_contact: '' };
    this.createStatus = '';
    this.createStep = 1;
    this.tempCredentials = null;
    this.passwordCopied = false;
    this.showCreateDrawer = true;
    this.cdr.markForCheck();
  }

  closeCreateDrawer() {
    // Si se cerro por la X, Escape o el fondo tras un alta, la lista se refresca igual y la clave no queda en memoria.
    const created = this.tempCredentials?.context === 'created';
    this.showCreateDrawer = false;
    this.tempCredentials = null;
    this.passwordCopied = false;
    if (created) this.loadData();
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
      if (this.newUser.evaluation_date) payload.evaluation_date = this.newUser.evaluation_date;
      if (this.newUser.generate_schedule) {
        if (this.newUser.start_date) payload.start_date = this.newUser.start_date;
        if (this.newUser.start_time) payload.start_time = this.newUser.start_time;
        if (this.newUser.schedule_therapist) payload.therapist_id = this.newUser.schedule_therapist;
        if (this.newUser.days.length) payload.days_of_week = this.newUser.days;
      }
      if (this.newUser.guardian_name) payload.guardian_name = this.newUser.guardian_name;
      if (this.newUser.guardian_type) payload.guardian_type = this.newUser.guardian_type;
      if (this.newUser.guardian_dni) payload.guardian_dni = this.newUser.guardian_dni;
      if (this.newUser.guardian_contact) payload.guardian_contact = this.newUser.guardian_contact;
    }

    this.subscriptions.add(
      this.adminService.createUser(payload).subscribe({
        next: (res: any) => {
          if (res.success) {
            this.createStatus = '';
            this.tempCredentials = {
              context: 'created',
              name: this.newUser.username || this.newUser.email || 'el usuario',
              password: res.temp_password || '',
            };
            this.focusCredentials();
          } else {
            this.createStatus = 'Error: ' + (res.message || 'Desconocido');
          }
          this.cdr.markForCheck();
        },
        error: (err: any) => {
          this.createStatus = 'Error: ' + (err.error?.message || 'Error de conexión');
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
            this.closeEditDrawer();
            this.showSuccessToast('Usuario eliminado');
          } else {
            this.showErrorToast(res.message || 'No se pudo eliminar el usuario.');
          }
          this.cdr.markForCheck();
        },
        error: () => this.showErrorToast('No se pudo eliminar al usuario. Revisa tu conexión e inténtalo de nuevo.'),
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
      jugador: 'badge--neutral',
      terapista: 'badge--info',
      admin: 'badge--primary',
      supervisor: 'badge--tertiary',
    };
    return `badge ${map[role] || 'badge--neutral'}`;
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
      active: 'badge--success',
      inactive: 'badge--warning',
      retired: 'badge--neutral',
      debtor: 'badge--error',
    };
    return `badge ${map[account_status] || 'badge--success'}`;
  }

  getInitials(name: string): string {
    return name?.slice(0, 2).toUpperCase() || 'US';
  }

  private toastTimer: ReturnType<typeof setTimeout> | null = null;

  private scheduleToastHide(ms: number) {
    if (this.toastTimer) clearTimeout(this.toastTimer);
    this.toastTimer = setTimeout(() => { this.showToast = false; this.cdr.markForCheck(); }, ms);
  }

  private showSuccessToast(msg: string) {
    this.toastMessage = msg;
    this.toastType = 'success';
    this.showToast = true;
    this.scheduleToastHide(3000);
    this.cdr.markForCheck();
  }

  private showErrorToast(msg: string) {
    this.toastMessage = msg;
    this.toastType = 'error';
    this.showToast = true;
    this.scheduleToastHide(6000);
    this.cdr.markForCheck();
  }

  // --- PATIENT GROUPS ---
  loadGroups() {
    this.subscriptions.add(
      this.adminService.getPatientGroups().subscribe({
        next: (res: any) => {
          this.patientGroups = res.groups || [];
          this.cdr.markForCheck();
        },
        error: () => this.showErrorToast('No se pudieron cargar los grupos de pacientes.'),
      })
    );
  }

  openGroupModal(group?: any) {
    this.groupTherapistPatients = null;
    this.groupSearchQuery = '';
    this.groupRangeMode = false;
    this.groupRangeStartStr = null;
    this.groupCalendarMonth = new Date();
    if (group) {
      this.editingGroupId = group.id;
      this.groupForm = {
        name: group.name,
        therapist_id: group.therapist_id || null,
        sede_id: group.sede_id,
        start_time: group.start_time || '',
        end_time: group.end_time || '',
        work_days: group.work_days ? group.work_days.split(',').map(Number) : [0,1,2,3,4],
        dates: Array.isArray(group.session_dates) ? [...group.session_dates] : [],
        notes: group.notes || '',
        member_ids: group.member_ids || [],
      };
    } else {
      this.editingGroupId = null;
      this.groupForm = {
        name: '',
        therapist_id: null,
        sede_id: null,
        start_time: '',
        end_time: '',
        work_days: [0,1,2,3,4],
        dates: [] as string[],
        notes: '',
        member_ids: [],
      };
    }
    this.showGroupModal = true;
    this.buildGroupCalendar();
    if (this.groupForm.therapist_id) {
      this.loadTherapistPatients(this.groupForm.therapist_id);
    }
    this.cdr.markForCheck();
  }

  closeGroupModal() {
    this.showGroupModal = false;
    this.editingGroupId = null;
    this.groupForm = {};
    this.groupTherapistPatients = null;
    this.groupSearchQuery = '';
  }

  onGroupTherapistChange(therapistId: number) {
    if (therapistId) {
      this.loadTherapistPatients(therapistId);
    } else {
      this.groupTherapistPatients = null;
      this.groupForm.member_ids = [];
      this.cdr.markForCheck();
    }
  }

  loadTherapistPatients(therapistId: number) {
    this.groupPatientsLoading = true;
    this.cdr.markForCheck();
    this.subscriptions.add(
      this.adminService.getPatientsByTherapist(therapistId).subscribe({
        next: (patients: any[]) => {
          this.groupTherapistPatients = (patients || []).map((p: any) => ({id: p.id, username: p.username}));
          const validIds = this.groupTherapistPatients.map((p: any) => p.id);
          const current = this.groupForm.member_ids || [];
          const kept = current.filter((id: number) => validIds.includes(id));
          if (kept.length !== current.length) {
            this.groupForm.member_ids = kept;
          }
          this.groupPatientsLoading = false;
          this.cdr.markForCheck();
        },
        error: () => {
          this.groupTherapistPatients = [];
          this.groupPatientsLoading = false;
          this.groupForm.member_ids = [];
          this.cdr.markForCheck();
        },
      })
    );
  }

  openPatientDetail() {
    if (!this.currentEditUser || this.currentEditUser.role !== 'jugador') return;
    this.showPatientDetailModal = true;
    this.patientDetailLoading = true;
    this.patientDetailData = null;
    this.cdr.markForCheck();
    this.subscriptions.add(
      this.adminService.getPatientDetails(this.currentEditUser.id).subscribe({
        next: (res: any) => {
          this.patientDetailData = res.patient;
          this.patientDetailLoading = false;
          this.cdr.markForCheck();
        },
        error: () => {
          this.patientDetailLoading = false;
          this.cdr.markForCheck();
        },
      })
    );
  }

  closePatientDetailModal() {
    this.showPatientDetailModal = false;
    this.patientDetailData = null;
  }

  startEditPatientDetails() {
    if (!this.currentEditUser || this.currentEditUser.role !== 'jugador') return;
    this.showEditPatientModal = true;
    this.patientDetailLoading = true;
    this.patientDetailForm = {};
    this.patientDetailStatus = '';
    this.cdr.markForCheck();
    this.subscriptions.add(
      this.adminService.getPatientDetails(this.currentEditUser.id).subscribe({
        next: (res: any) => {
          const p = res.patient;
          this.patientDetailForm = {
            document_number: p.document_number || '',
            phone: p.phone || '',
            date_of_birth: p.date_of_birth || '',
            sex: p.sex || '',
            guardian_name: p.guardian_name || '',
            guardian_type: p.guardian_type || '',
            guardian_dni: p.guardian_dni || '',
            guardian_contact: p.guardian_contact || '',
            preliminary_diagnosis: p.preliminary_diagnosis || '',
            therapy_goals: p.therapy_goals || '',
            notes: p.notes || '',
          };
          this.patientDetailLoading = false;
          this.cdr.markForCheck();
        },
        error: () => {
          this.patientDetailLoading = false;
          this.patientDetailStatus = 'Error de conexión';
          this.cdr.markForCheck();
        },
      })
    );
  }

  cancelEditPatientDetails() {
    this.showEditPatientModal = false;
    this.patientDetailForm = {};
    this.patientDetailStatus = '';
    this.cdr.markForCheck();
  }

  savePatientDetails() {
    if (!this.currentEditUser) return;
    this.patientDetailSaving = true;
    this.patientDetailStatus = '';
    this.cdr.markForCheck();
    this.subscriptions.add(
      this.adminService.updatePatientDetails(this.currentEditUser.id, this.patientDetailForm).subscribe({
        next: (res) => {
          this.patientDetailSaving = false;
          if (res.success) {
            this.patientDetailStatus = 'Guardado correctamente';
            this.showEditPatientModal = false;
            this.loadData();
          } else {
            this.patientDetailStatus = res.error || 'Error al guardar';
          }
          this.cdr.markForCheck();
        },
        error: () => {
          this.patientDetailSaving = false;
          this.patientDetailStatus = 'Error de conexión';
          this.cdr.markForCheck();
        },
      })
    );
  }

  saveGroup() {
    const f = this.groupForm;
    if (!f.name) return;

    const payload = {
      name: f.name,
      therapist_id: f.therapist_id,
      sede_id: f.sede_id,
      start_time: f.start_time,
      end_time: f.end_time,
      work_days: f.work_days?.join(','),
      session_dates: f.dates || [],
      notes: f.notes,
      member_ids: f.member_ids,
    };

    const req = this.editingGroupId
      ? this.adminService.updatePatientGroup(this.editingGroupId, payload)
      : this.adminService.createPatientGroup(payload);

    this.subscriptions.add(
      req.subscribe({
        next: () => {
          this.closeGroupModal();
          this.loadGroups();
          this.showSuccessToast(this.editingGroupId ? 'Grupo actualizado' : 'Grupo creado');
        },
        error: () => {
          this.showErrorToast('Error al guardar grupo');
        },
      })
    );
  }

  deleteGroup(id: number) {
    this.subscriptions.add(
      this.confirmService.confirm({
        title: 'Eliminar grupo',
        message: '¿Eliminar este grupo de pacientes?',
        confirmText: 'Eliminar',
        cancelText: 'Cancelar',
        variant: 'danger',
      }).subscribe((confirmed: boolean) => {
        if (!confirmed) return;
        this.subscriptions.add(
          this.adminService.deletePatientGroup(id).subscribe({
            next: () => {
              this.loadGroups();
              this.showSuccessToast('Grupo eliminado');
            },
            error: () => this.showErrorToast('Error al eliminar'),
          })
        );
      })
    );
  }

  toggleGroupMember(patientId: number) {
    const ids = this.groupForm.member_ids || [];
    const idx = ids.indexOf(patientId);
    if (idx >= 0) {
      this.groupForm.member_ids = ids.filter((id: number) => id !== patientId);
    } else {
      this.groupForm.member_ids = [...ids, patientId];
    }
    this.cdr.markForCheck();
  }

  get groupCalendarLabel(): string {
    return `${this.groupMonths[this.groupCalendarMonth.getMonth()]} ${this.groupCalendarMonth.getFullYear()}`;
  }

  private buildGroupCalendar() {
    const year = this.groupCalendarMonth.getFullYear();
    const month = this.groupCalendarMonth.getMonth();
    const firstDay = new Date(year, month, 1);
    const startOfWeek = new Date(firstDay);
    startOfWeek.setDate(startOfWeek.getDate() - ((startOfWeek.getDay() + 6) % 7));

    const today = new Date();
    today.setHours(0, 0, 0, 0);

    const weeks: { date: Date; day: number; selected: boolean; disabled: boolean }[][] = [];
    let cursor = new Date(startOfWeek);

    for (let w = 0; w < 6; w++) {
      const week: { date: Date; day: number; selected: boolean; disabled: boolean }[] = [];
      for (let d = 0; d < 7; d++) {
        const dateStr = cursor.toISOString().split('T')[0];
        const isPast = cursor.getTime() < today.getTime() && cursor.getMonth() === month && !this.groupUnlockPast;
        week.push({
          date: new Date(cursor),
          day: cursor.getDate(),
          selected: this.groupForm.dates?.includes(dateStr),
          disabled: isPast,
        });
        cursor.setDate(cursor.getDate() + 1);
      }
      weeks.push(week);
      if (cursor.getMonth() !== month && weeks.length >= 4) break;
    }

    this.groupCalendarDays = weeks;
  }

  groupPrevMonth() {
    this.groupCalendarMonth = new Date(this.groupCalendarMonth.getFullYear(), this.groupCalendarMonth.getMonth() - 1, 1);
    this.buildGroupCalendar();
    this.cdr.markForCheck();
  }

  groupNextMonth() {
    this.groupCalendarMonth = new Date(this.groupCalendarMonth.getFullYear(), this.groupCalendarMonth.getMonth() + 1, 1);
    this.buildGroupCalendar();
    this.cdr.markForCheck();
  }

  toggleGroupDate(dateStr: string) {
    const dates = this.groupForm.dates || [];
    const idx = dates.indexOf(dateStr);
    if (idx >= 0) {
      this.groupForm.dates = dates.filter((d: string) => d !== dateStr);
    } else if (dates.length < 10) {
      this.groupForm.dates = [...dates, dateStr];
    }
    this.buildGroupCalendar();
    this.cdr.markForCheck();
  }

  toggleGroupCalendarDate(day: { date: Date; day: number; selected: boolean; disabled: boolean }) {
    if (day.disabled) return;
    const dateStr = day.date.toISOString().split('T')[0];

    if (this.groupRangeMode) {
      if (!this.groupRangeStartStr) {
        this.groupRangeStartStr = dateStr;
        this.toggleGroupDate(dateStr);
      } else {
        const start = new Date(this.groupRangeStartStr);
        const end = new Date(dateStr);
        const minDate = start < end ? this.groupRangeStartStr : dateStr;
        const maxDate = start < end ? dateStr : this.groupRangeStartStr;
        const current = new Date(minDate);
        while (current <= new Date(maxDate)) {
          const ds = current.toISOString().split('T')[0];
          if (!(this.groupForm.dates || []).includes(ds) && (this.groupForm.dates || []).length < 10) {
            this.groupForm.dates = [...(this.groupForm.dates || []), ds];
          }
          current.setDate(current.getDate() + 1);
        }
        this.groupRangeStartStr = null;
        this.groupRangeMode = false;
        this.buildGroupCalendar();
      }
    } else {
      this.toggleGroupDate(dateStr);
    }
    this.cdr.markForCheck();
  }

  toggleGroupRangeMode() {
    this.groupRangeMode = !this.groupRangeMode;
    this.groupRangeStartStr = null;
    this.cdr.markForCheck();
  }

  clearGroupRangeSelection() {
    this.groupRangeMode = false;
    this.groupRangeStartStr = null;
    this.cdr.markForCheck();
  }

  toggleGroupUnlockPast() {
    this.groupUnlockPast = !this.groupUnlockPast;
    this.buildGroupCalendar();
    this.cdr.markForCheck();
  }

  removeGroupDate(dateStr: string) {
    this.groupForm.dates = (this.groupForm.dates || []).filter((d: string) => d !== dateStr);
    this.buildGroupCalendar();
    this.cdr.markForCheck();
  }

  get patientOptionsForGroup(): { id: number; username: string }[] {
    if (!this.groupForm.therapist_id) return [];
    return (this.groupTherapistPatients ?? [])
      .map((u: any) => ({ id: u.id, username: u.username }));
  }

  get groupFilteredPatients(): { id: number; username: string }[] {
    const q = (this.groupSearchQuery || '').trim().toLowerCase();
    const base = this.patientOptionsForGroup;
    if (!q) return base;
    return base.filter(p => p.username.toLowerCase().includes(q));
  }
}
