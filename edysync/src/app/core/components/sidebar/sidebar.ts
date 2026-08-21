import { Component, OnInit, OnDestroy, ChangeDetectionStrategy, ChangeDetectorRef, inject, effect, ElementRef } from '@angular/core';
import { Router, NavigationEnd, RouterModule } from '@angular/router';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { IconProp } from '@fortawesome/fontawesome-svg-core';
import { AuthService } from '../../services/auth.service';
import { SidebarService } from '../../services/sidebar.service';
import { GlobalSettingsService } from '../../services/global-settings.service';
import { NotificationService } from '../../services/notification.service';
import { HelpStateService } from '../../../shared/contextual-help/services/help-state.service';
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
  imports: [RouterModule, FontAwesomeModule],
  templateUrl: './sidebar.html',
  styleUrl: './sidebar.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Sidebar implements OnInit, OnDestroy {
  private settings = inject(GlobalSettingsService);
  private router = inject(Router);
  hideCharts = this.settings.hideCharts;

  userRole: string = '';
  error: string | null = null;
  isOpen = false;
  notifCount = 0;

  /** Desktop collapsed state (icons only) */
  collapsed = true;
  /** Hover state for desktop expansion */
  isHovered = false;

  private notifService = inject(NotificationService);
  private notifEffect = effect(() => {
    this.notifCount = this.notifService.unreadCount();
    this.cdr.markForCheck();
  });

  private subs = new Subscription();

  readonly allItems: NavItem[] = [
    { path: '/admin/dashboard', label: 'Panel Admin', subtitle: 'Resumen general', icon: ['fas', 'tachometer-alt'], supervisor: true },
    { path: '/admin/sessions', label: 'Sesiones Globales', subtitle: 'Todas las sesiones', icon: ['fas', 'calendar-alt'], supervisor: true },
    { path: '/admin/users', label: 'Admin Usuarios', subtitle: 'Gestión de usuarios', icon: ['fas', 'users'] },
    { path: '/admin/sedes', label: 'Sedes', subtitle: 'Sucursales', icon: ['fas', 'building'], supervisor: true },
    { path: '/admin/finanzas', label: 'Finanzas', subtitle: 'Ingresos y gastos', icon: ['fas', 'university'], supervisor: true, hideWhenNoCharts: true },

    { path: '/admin/games', label: 'Admin Juegos', subtitle: 'Terapia recreativa', icon: ['fas', 'gamepad'] },
    { path: '/admin/reports', label: 'Admin Reportes', subtitle: 'Estadísticas', icon: ['fas', 'chart-bar'], supervisor: true },
    { path: '/admin/messages', label: 'Admin Mensajes', subtitle: 'Comunicación', icon: ['fas', 'envelope'], supervisor: true },
    { path: '/admin/visor-funcionamiento', label: 'Centro de Operaciones', subtitle: 'Monitoreo', icon: ['fas', 'desktop'], supervisor: true },
    { path: '/admin/settings', label: 'Configuración', subtitle: 'Preferencias', icon: ['fas', 'cog'] },
  ];

  get navItems(): NavItem[] {
    let items = this.allItems;
    if (this.userRole === 'supervisor') {
      items = items.filter(i => i.supervisor);
    }
    if (this.hideCharts()) {
      items = items.filter(i => !i.hideWhenNoCharts);
    }
    return items;
  }

  /** Whether sidebar should visually expand */
  get isExpanded(): boolean {
    return !this.collapsed || this.isHovered;
  }

  private hideChartsEffect = effect(() => {
    this.hideCharts();
    this.cdr.markForCheck();
  });

  helpState = inject(HelpStateService);

  constructor(
    private auth: AuthService,
    public sidebarService: SidebarService,
    private cdr: ChangeDetectorRef,
    private el: ElementRef,
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

    // Auto-collapse sidebar on every navigation (desktop)
    this.subs.add(
      this.router.events.pipe(filter(e => e instanceof NavigationEnd)).subscribe(() => {
        this.collapsed = true;
        this.isHovered = false;
        this.cdr.markForCheck();
      })
    );
  }

  ngOnDestroy() {
    this.subs.unsubscribe();
  }

  toggleCollapse() {
    this.collapsed = !this.collapsed;
    this.cdr.markForCheck();
  }

  onMouseEnter() {
    if (this.collapsed) {
      this.isHovered = true;
      this.cdr.markForCheck();
    }
  }

  onMouseLeave() {
    this.isHovered = false;
    this.cdr.markForCheck();
  }

  toggleHelp() {
    this.helpState.toggle();
  }
}
