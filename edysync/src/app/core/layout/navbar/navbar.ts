import { Component, OnInit, OnDestroy, ChangeDetectorRef, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Router } from '@angular/router';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { AuthService } from '../../services/auth.service';
import { ThemeService } from '../../services/theme.service';
import { Observable, firstValueFrom, Subscription } from 'rxjs';
import { ConfirmService } from '../../services/confirm.service';
import { Button } from '../../../shared/components/button/button';

@Component({
  selector: 'app-navbar',
  standalone: true,
  imports: [CommonModule, RouterModule, FontAwesomeModule, Button],
  templateUrl: './navbar.html',
  styleUrl: './navbar.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Navbar implements OnInit, OnDestroy {
  user$: Observable<any>;
  theme: string = 'light';
  showHelp = false;
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

  toggleHelp() {
    this.showHelp = !this.showHelp;
  }
}
