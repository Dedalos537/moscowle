import { Component, OnInit, OnDestroy, ChangeDetectorRef } from '@angular/core';
import { AuthService } from '../../services/auth.service';
import { ThemeService } from '../../services/theme.service';
import { Router } from '@angular/router';
import { Observable, firstValueFrom, Subscription } from 'rxjs';
import { ConfirmService } from '../../services/confirm.service';

@Component({
  selector: 'app-navbar',
  standalone: false,
  templateUrl: './navbar.html',
  styleUrl: './navbar.scss',
})
export class Navbar implements OnInit, OnDestroy {
  user$: Observable<any>;
  theme: string = 'light';
  private subs = new Subscription();

  constructor(
    private authService: AuthService,
    private themeService: ThemeService,
    private router: Router,
    private confirmService: ConfirmService,
    private cdr: ChangeDetectorRef,
  ) {
    this.user$ = this.authService.currentUser$;
  }

  ngOnInit() {
    this.subs.add(this.themeService.theme$.subscribe(t => {
      this.theme = t;
      this.cdr.markForCheck();
    }));
  }

  ngOnDestroy() {
    this.subs.unsubscribe();
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
    this.themeService.toggle();
  }
}
