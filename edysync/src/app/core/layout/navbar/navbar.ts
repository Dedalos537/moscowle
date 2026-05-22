import { Component, OnInit } from '@angular/core';
import { AuthService } from '../../services/auth.service';
import { Router } from '@angular/router';
import { Observable, firstValueFrom } from 'rxjs';
import { ConfirmService } from '../../services/confirm.service';

@Component({
  selector: 'app-navbar',
  standalone: false,
  templateUrl: './navbar.html',
  styleUrl: './navbar.scss',
})
export class Navbar implements OnInit {
  user$: Observable<any>;
  theme: string = 'light';

  constructor(
    private authService: AuthService,
    private router: Router,
    private confirmService: ConfirmService,
  ) {
    this.user$ = this.authService.currentUser$;
  }

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

  async logout() {
    const confirmed = await firstValueFrom(this.confirmService.confirm({
      title: 'Cerrar Sesion',
      message: '¿Estas seguro de que deseas cerrar sesion?',
      confirmText: 'Cerrar Sesion',
      variant: 'danger',
      icon: ['fas', 'sign-out-alt'],
    }));
    if (!confirmed) return;
    this.authService.logout().subscribe(() => {
      this.router.navigate(['/auth/login']);
    });
  }

  usuarioSeVaALogin() {
    this.router.navigate(['/auth/login']);
  }

  toggleTheme() {
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
