import { Component, OnInit, OnDestroy, ChangeDetectionStrategy, ChangeDetectorRef, inject, effect } from '@angular/core';
import { Router, NavigationEnd, RouterModule } from '@angular/router';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { IconProp } from '@fortawesome/fontawesome-svg-core';
import { AuthService } from '../../services/auth.service';
import { SidebarService } from '../../services/sidebar.service';
import { GlobalSettingsService } from '../../services/global-settings.service';
import { HelpStateService } from '../../../shared/contextual-help/services/help-state.service';
import { Logo } from '../../../shared/components/logo/logo';
import { Subscription, filter } from 'rxjs';

interface NavItem {
  path: string;
  label: string;
  subtitle?: string;
  icon: IconProp;
  supervisor?: boolean;
  hideWhenNoCharts?: boolean;
}

@Component({
  selector: 'app-sidebar',
  standalone: true,
  imports: [RouterModule, FontAwesomeModule, Logo],
  templateUrl: './sidebar.html',
  styleUrl: './sidebar.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Sidebar implements OnInit, OnDestroy {
  private settings = inject(GlobalSettingsService);
  private router = inject(Router);
  hideCharts = this.settings.hideCharts;
  sidebarDisplay = this.settings.sidebarDisplay;

  userRole: string = '';
  error: string | null = null;
  isOpen = false;

  /** Index of hovered nav item (individual expand) */
  hoveredIndex: number | null = null;

  private subs = new Subscription();

  private readonly adminItems: NavItem[] = [
    { path: '/admin/dashboard', label: 'Panel Admin', subtitle: 'Resumen general', icon: ['fas', 'gauge-high'], supervisor: true },
    { path: '/admin/sessions', label: 'Sesiones Globales', subtitle: 'Todas las sesiones', icon: ['fas', 'calendar-days'], supervisor: true },
    { path: '/admin/users', label: 'Admin Usuarios', subtitle: 'Gestión de usuarios', icon: ['fas', 'users'] },
    { path: '/admin/sedes', label: 'Sedes', subtitle: 'Sucursales', icon: ['fas', 'building'], supervisor: true },
    { path: '/admin/finanzas', label: 'Finanzas', subtitle: 'Ingresos y gastos', icon: ['fas', 'building-columns'], supervisor: true },
    { path: '/admin/games', label: 'Admin Juegos', subtitle: 'Terapia recreativa', icon: ['fas', 'gamepad'] },
    { path: '/admin/reports', label: 'Admin Reportes', subtitle: 'Estadísticas', icon: ['fas', 'chart-bar'], supervisor: true },
    { path: '/admin/messages', label: 'Admin Mensajes', subtitle: 'Comunicación', icon: ['fas', 'envelope'], supervisor: true },
    { path: '/admin/kanban', label: 'Kanban', subtitle: 'Tablero de tareas', icon: ['fas', 'table-columns'], supervisor: true },
    { path: '/admin/settings', label: 'Configuración', subtitle: 'Cuenta y sistema', icon: ['fas', 'gear'], supervisor: true },
  ];

  private readonly therapistItems: NavItem[] = [
    { path: '/therapist/dashboard', label: 'Dashboard', subtitle: 'Resumen del día', icon: ['fas', 'desktop'] },
    { path: '/therapist/patients', label: 'Mis Pacientes', subtitle: 'Seguimiento', icon: ['fas', 'user-group'] },
    { path: '/therapist/sessions', label: 'Mis Sesiones', subtitle: 'Agenda', icon: ['fas', 'calendar-days'] },
    { path: '/therapist/games', label: 'Juegos', subtitle: 'Terapia recreativa', icon: ['fas', 'gamepad'] },
    { path: '/therapist/reports', label: 'Reportes', subtitle: 'Informes', icon: ['fas', 'chart-bar'] },
    { path: '/therapist/analytics', label: 'Analíticas IA', subtitle: 'Resultados', icon: ['fas', 'brain'] },
    { path: '/therapist/incidents', label: 'Incidencias', subtitle: 'Reportes de incidentes', icon: ['fas', 'triangle-exclamation'] },
    { path: '/therapist/messages', label: 'Mensajes', subtitle: 'Comunicación', icon: ['fas', 'envelope'] },
    { path: '/therapist/kanban', label: 'Kanban', subtitle: 'Tablero de tareas', icon: ['fas', 'table-columns'] },
    { path: '/therapist/profile', label: 'Mi Perfil', subtitle: 'Foto y seguridad', icon: ['fas', 'circle-user'] },
  ];

  private readonly patientItems: NavItem[] = [
    { path: '/patient/dashboard', label: 'Mi Panel', subtitle: 'Resumen', icon: ['fas', 'house'] },
    { path: '/patient/sessions', label: 'Mis Sesiones', subtitle: 'Tus citas', icon: ['fas', 'calendar-days'] },
    { path: '/patient/calendar', label: 'Calendario', subtitle: 'Próximas citas', icon: ['fas', 'calendar-day'] },
    { path: '/patient/progress', label: 'Mi Progreso', subtitle: 'Avances', icon: ['fas', 'chart-line'] },
    { path: '/patient/payments', label: 'Pagos', subtitle: 'Cuotas y recibos', icon: ['fas', 'file-invoice-dollar'] },
    { path: '/patient/my-therapist', label: 'Mi Terapeuta', subtitle: 'Contacto', icon: ['fas', 'user-doctor'] },
    { path: '/patient/incidents', label: 'Incidencias', subtitle: 'Reportes', icon: ['fas', 'triangle-exclamation'] },
    { path: '/patient/kanban', label: 'Mis Tareas', subtitle: 'Pendientes', icon: ['fas', 'table-columns'] },
    { path: '/patient/messages', label: 'Mensajes', subtitle: 'Comunicación', icon: ['fas', 'envelope'] },
    { path: '/patient/profile', label: 'Mi Perfil', subtitle: 'Foto y seguridad', icon: ['fas', 'circle-user'] },
  ];

  /** Menú según el rol: el mismo componente (y las mismas preferencias de barra) para todos los usuarios. */
  get navItems(): NavItem[] {
    const role = this.userRole;
    let items: NavItem[];
    if (role === 'terapista' || role === 'terapeuta') items = this.therapistItems;
    else if (role === 'jugador') items = this.patientItems;
    else if (role === 'admin' || role === 'supervisor') items = this.adminItems;
    else items = [];
    if (role === 'supervisor') items = items.filter((i) => i.supervisor);
    if (this.hideCharts()) items = items.filter((i) => !i.hideWhenNoCharts);
    return items;
  }

  /** Labels (label + subtitle) shown inline next to icons on desktop. */
  get labelsVisible(): boolean {
    return this.sidebarDisplay() === 'labels';
  }

  /** Barra ancha (icono + título + subtítulo) o compacta (solo iconos). Una sola preferencia: «Barra lateral». */
  get expanded(): boolean {
    return this.labelsVisible;
  }

  private hideChartsEffect = effect(() => {
    this.hideCharts();
    this.cdr.markForCheck();
  });

  private sidebarDisplayEffect = effect(() => {
    this.sidebarDisplay();
    this.cdr.markForCheck();
  });

  helpState = inject(HelpStateService);

  constructor(
    private auth: AuthService,
    public sidebarService: SidebarService,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit() {
    this.subs.add(this.auth.currentUser$.subscribe(u => {
      this.userRole = u?.role || '';
      this.cdr.markForCheck();
    }));
    this.subs.add(this.sidebarService.open$.subscribe(open => {
      this.isOpen = open;
      this.cdr.markForCheck();
    }));

    // Clear hovered item on navigation
    this.subs.add(
      this.router.events.pipe(filter(e => e instanceof NavigationEnd)).subscribe(() => {
        this.hoveredIndex = null;
        this.cdr.markForCheck();
      })
    );
  }

  ngOnDestroy() {
    this.subs.unsubscribe();
  }

  onItemHover(index: number) {
    if (!this.expanded) {
      this.hoveredIndex = index;
      this.cdr.markForCheck();
    }
  }

  onItemLeave() {
    this.hoveredIndex = null;
    this.cdr.markForCheck();
  }

  toggleHelp() {
    this.helpState.toggle();
  }
}
