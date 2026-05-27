import { Component, OnInit } from '@angular/core';
import { IconProp } from '@fortawesome/fontawesome-svg-core';

interface NavItem {
  path: string;
  label: string;
  icon: IconProp;
}

@Component({
  selector: 'app-sidebar',
  standalone: false,
  templateUrl: './sidebar.html',
  styleUrl: './sidebar.scss',
})
export class Sidebar implements OnInit {
  theme: string = 'light';

  readonly navItems: NavItem[] = [
    { path: '/admin/dashboard', label: 'Panel Admin', icon: ['fas', 'tachometer-alt'] },
    { path: '/admin/sessions', label: 'Sesiones Globales', icon: ['fas', 'calendar-alt'] },
    { path: '/admin/users', label: 'Admin Usuarios', icon: ['fas', 'users'] },
    { path: '/admin/sedes', label: 'Sedes', icon: ['fas', 'building'] },
    { path: '/admin/finanzas', label: 'Finanzas', icon: ['fas', 'university'] },
    { path: '/admin/yape', label: 'Importar Yape', icon: ['fas', 'qrcode'] },
    { path: '/admin/games', label: 'Admin Juegos', icon: ['fas', 'gamepad'] },
    { path: '/admin/reports', label: 'Admin Reportes', icon: ['fas', 'chart-bar'] },
    { path: '/admin/messages', label: 'Admin Mensajes', icon: ['fas', 'envelope'] },
  ];

  ngOnInit() {
    const saved = localStorage.getItem('theme');
    const isDark = document.documentElement.classList.contains('dark');
    if (saved === 'dark' || (!saved && isDark)) {
      this.theme = 'dark';
      document.documentElement.classList.add('dark');
    } else if (saved !== 'dark') {
      document.documentElement.classList.remove('dark');
    }
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
