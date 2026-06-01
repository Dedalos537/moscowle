import { Component, OnInit, OnDestroy, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { IconProp } from '@fortawesome/fontawesome-svg-core';
import { AuthService } from '../../services/auth.service';
import { Subscription } from 'rxjs';

interface NavItem {
  path: string;
  label: string;
  icon: IconProp;
  supervisor?: boolean;
}

@Component({
  selector: 'app-sidebar',
  standalone: false,
  templateUrl: './sidebar.html',
  styleUrl: './sidebar.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Sidebar implements OnInit, OnDestroy {
  theme: string = 'light';
  userRole: string = '';
  error: string | null = null;

  private subs = new Subscription();

  readonly allItems: NavItem[] = [
    { path: '/admin/dashboard', label: 'Panel Admin', icon: ['fas', 'tachometer-alt'], supervisor: true },
    { path: '/admin/sessions', label: 'Sesiones Globales', icon: ['fas', 'calendar-alt'], supervisor: true },
    { path: '/admin/users', label: 'Admin Usuarios', icon: ['fas', 'users'] },
    { path: '/admin/sedes', label: 'Sedes', icon: ['fas', 'building'], supervisor: true },
    { path: '/admin/finanzas', label: 'Finanzas', icon: ['fas', 'university'], supervisor: true },
    { path: '/admin/debtors', label: 'Deudores', icon: ['fas', 'exclamation-triangle'], supervisor: true },
    { path: '/admin/yape-import', label: 'Importar Yape', icon: ['fas', 'qrcode'] },
    { path: '/admin/games', label: 'Admin Juegos', icon: ['fas', 'gamepad'] },
    { path: '/admin/reports', label: 'Admin Reportes', icon: ['fas', 'chart-bar'], supervisor: true },
    { path: '/admin/messages', label: 'Admin Mensajes', icon: ['fas', 'envelope'], supervisor: true },
    { path: '/admin/logs', label: 'Visor de Logs', icon: ['fas', 'terminal'], supervisor: true },
  ];

  get navItems(): NavItem[] {
    if (this.userRole === 'supervisor') {
      return this.allItems.filter(i => i.supervisor);
    }
    return this.allItems;
  }

  constructor(private auth: AuthService, private cdr: ChangeDetectorRef) {}

  ngOnInit() {
    const saved = localStorage.getItem('theme');
    const isDark = document.documentElement.classList.contains('dark');
    if (saved === 'dark' || (!saved && isDark)) {
      this.theme = 'dark';
      document.documentElement.classList.add('dark');
    } else if (saved !== 'dark') {
      document.documentElement.classList.remove('dark');
    }
    this.subs.add(this.auth.currentUser$.subscribe(u => {
      this.userRole = u?.role || '';
      this.cdr.markForCheck();
    }));
  }

  ngOnDestroy() {
    this.subs.unsubscribe();
  }

  toggleDarkMode() {
    this.theme = this.theme === 'light' ? 'dark' : 'light';
    if (this.theme === 'dark') {
      document.documentElement.classList.add('dark');
      localStorage.setItem('theme', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('theme', 'light');
    }
  }
}
