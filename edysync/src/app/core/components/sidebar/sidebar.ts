import { Component, OnInit, OnDestroy, ChangeDetectionStrategy, ChangeDetectorRef, inject, effect, Signal } from '@angular/core';
import { RouterModule } from '@angular/router';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { IconProp } from '@fortawesome/fontawesome-svg-core';
import { AuthService } from '../../services/auth.service';
import { SidebarService } from '../../services/sidebar.service';
import { GlobalSettingsService } from '../../services/global-settings.service';
import { NotificationService } from '../../services/notification.service';
import { HelpStateService } from '../../../shared/contextual-help/services/help-state.service';
import { Subscription } from 'rxjs';

interface NavItem {
  path: string;
  label: string;
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
  hideCharts = this.settings.hideCharts;

  userRole: string = '';
  error: string | null = null;
  isOpen = false;
  notifCount = 0;

  private notifService = inject(NotificationService);
  private notifEffect = effect(() => {
    this.notifCount = this.notifService.unreadCount();
    this.cdr.markForCheck();
  });

  private subs = new Subscription();

  readonly allItems: NavItem[] = [
    { path: '/admin/dashboard', label: 'Panel Admin', icon: ['fas', 'tachometer-alt'], supervisor: true },
    { path: '/admin/sessions', label: 'Sesiones Globales', icon: ['fas', 'calendar-alt'], supervisor: true },
    { path: '/admin/users', label: 'Admin Usuarios', icon: ['fas', 'users'] },
    { path: '/admin/sedes', label: 'Sedes', icon: ['fas', 'building'], supervisor: true },
    { path: '/admin/finanzas', label: 'Finanzas', icon: ['fas', 'university'], supervisor: true, hideWhenNoCharts: true },

    { path: '/admin/games', label: 'Admin Juegos', icon: ['fas', 'gamepad'] },
    { path: '/admin/reports', label: 'Admin Reportes', icon: ['fas', 'chart-bar'], supervisor: true },
    { path: '/admin/messages', label: 'Admin Mensajes', icon: ['fas', 'envelope'], supervisor: true },
    { path: '/admin/visor-funcionamiento', label: 'Centro de Operaciones', icon: ['fas', 'desktop'], supervisor: true },
    { path: '/admin/password-resets', label: 'Reseteo Contraseñas', icon: ['fas', 'key'], supervisor: true },
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

  private hideChartsEffect = effect(() => {
    this.hideCharts();
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
  }

  ngOnDestroy() {
    this.subs.unsubscribe();
  }

  toggleHelp() {
    this.helpState.toggle();
  }
}
