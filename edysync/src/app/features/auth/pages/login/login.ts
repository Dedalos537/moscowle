import { CommonModule } from '@angular/common';
import { Component, OnInit, OnDestroy, ChangeDetectionStrategy, ChangeDetectorRef, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { Router, ActivatedRoute, RouterModule } from '@angular/router';
import { Subscription } from 'rxjs';
import { AuthService } from '../../../../core/services/auth.service';
import { FloatingUiService } from '../../../../core/services/floating-ui.service';
import { Alert } from '../../../../shared/components/alert/alert';
import { ChartsToggle } from '../../../../shared/components/charts-toggle/charts-toggle';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule, FontAwesomeModule, Alert, ChartsToggle],
  templateUrl: './login.html',
  styleUrl: './login.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Login implements OnInit, OnDestroy {
  floating = inject(FloatingUiService);

  email = '';
  password = '';
  showPassword = false;
  isLoading = false;
  loading = false;
  error: string | null = null;

  alertMessage = '';
  alertType: 'success' | 'error' | 'warning' | 'info' = 'info';
  darkMode = false;
  emailError = '';
  passwordError = '';

  showHelp = false;

  guideStep = 0; // 0=none, 1=email, 2=password, 3=button, 4=done
  guidePos = { top: 0, left: 0, arrowLeft: 50 };
  guideText = '';
  guideVisible = false;

  private guideTimer: any;
  private resizeHandler: (() => void) | null = null;

  private subs = new Subscription();

  constructor(
    private authService: AuthService,
    private router: Router,
    private route: ActivatedRoute,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit() {
    this.darkMode = document.documentElement.classList.contains('dark') ||
                    localStorage.getItem('theme') === 'dark';
    this.subs.add(this.route.queryParams.subscribe(params => {
      if (params['logout'] === 'success') {
        this.alertType = 'success';
        this.alertMessage = 'Has cerrado sesión correctamente.';
        this.cdr.markForCheck();
      }
    }));
    this.scheduleGuide();
  }

  ngOnDestroy() {
    this.subs.unsubscribe();
    clearTimeout(this.guideTimer);
    if (this.resizeHandler) {
      window.removeEventListener('resize', this.resizeHandler);
    }
  }

  private scheduleGuide() {
    clearTimeout(this.guideTimer);
    this.guideTimer = setTimeout(() => {
      this.startGuide();
    }, 10000);
  }

  private startGuide() {
    if (this.guideStep > 0 || this.showHelp) return;
    const logo = document.querySelector('.login-logo');
    if (logo) {
      const r = logo.getBoundingClientRect();
      this.guidePos = { top: r.top - 8, left: r.right + 16, arrowLeft: 16 };
    }
    this.guideText = 'Ingresa aquí el correo electrónico que te enviamos para tu login';
    this.guideStep = 1;
    this.guideVisible = true;
    this.cdr.markForCheck();

    setTimeout(() => this.positionGuide('email'), 350);
    this.resizeHandler = () => {
      if (this.guideStep === 1) this.positionGuide('email');
      else if (this.guideStep === 2) this.positionGuide('password');
      else if (this.guideStep === 3) this.positionGuide('login-btn');
    };
    window.addEventListener('resize', this.resizeHandler);
  }

  private positionGuide(targetId: string) {
    const el = document.getElementById(targetId);
    const card = document.querySelector('.login-card');
    if (!el || !card) return;
    const er = el.getBoundingClientRect();
    const cr = card.getBoundingClientRect();

    if (targetId === 'email') {
      this.guidePos = {
        top: er.top - 4,
        left: cr.right + 16,
        arrowLeft: 20,
      };
    } else if (targetId === 'password') {
      this.guidePos = {
        top: er.top - 4,
        left: cr.right + 16,
        arrowLeft: 20,
      };
    } else if (targetId === 'login-btn') {
      const btn = document.querySelector('.login-submit') as HTMLElement;
      if (btn) {
        const br = btn.getBoundingClientRect();
        this.guidePos = {
          top: br.top - 8,
          left: cr.right + 16,
          arrowLeft: 20,
        };
      }
    }
    this.cdr.markForCheck();
  }

  onEmailInput() {
    if (this.guideStep === 1 && this.email.trim().length > 5) {
      this.guideStep = 2;
      this.guideText = 'Ahora ingresa la contraseña que te enviamos';
      this.cdr.markForCheck();
      setTimeout(() => this.positionGuide('password'), 350);
    }
  }

  onPasswordInput() {
    if (this.guideStep === 2 && this.password.length > 0) {
      this.guideStep = 3;
      this.guideText = 'Perfecto! Presiona INICIAR SESIÓN para acceder';
      this.cdr.markForCheck();
      setTimeout(() => this.positionGuide('login-btn'), 350);
    }
  }

  dismissGuide() {
    this.guideStep = 4;
    this.guideVisible = false;
    if (this.resizeHandler) {
      window.removeEventListener('resize', this.resizeHandler);
      this.resizeHandler = null;
    }
    this.cdr.markForCheck();
  }

  toggleHelp() {
    this.showHelp = !this.showHelp;
    if (this.showHelp) {
      this.dismissGuide();
    }
  }

  toggleDarkMode() {
    this.darkMode = !this.darkMode;
    if (this.darkMode) {
      document.documentElement.classList.add('dark');
      localStorage.setItem('theme', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('theme', 'light');
    }
  }

  get isFormValid(): boolean {
    return this.email.trim().length > 5 && this.password.length > 0;
  }

  togglePassword() {
    this.showPassword = !this.showPassword;
  }

  async doLogin() {
    this.emailError = '';
    this.passwordError = '';
    if (!this.email.trim()) {
      this.emailError = 'El correo es obligatorio';
    }
    if (!this.password) {
      this.passwordError = 'La contraseña es obligatoria';
    }
    if (!this.isFormValid) return;

    this.isLoading = true;
    this.loading = true;
    this.error = null;
    this.alertMessage = '';
    this.cdr.markForCheck();

    this.subs.add(this.authService.login(this.email, this.password).subscribe({
      next: (res) => {
        this.isLoading = false;
        this.loading = false;
        this.cdr.markForCheck();
        const route = res.user?.role === 'admin' ? '/admin/dashboard'
                    : res.user?.role === 'supervisor' ? '/admin/dashboard'
                    : res.user?.role === 'terapista' ? '/therapist/dashboard'
                    : res.user?.role === 'jugador' ? '/patient/dashboard'
                    : '/';
        this.router.navigate([route]);
      },
      error: (err) => {
        this.isLoading = false;
        this.loading = false;
        this.error = err.error?.message || 'Credenciales incorrectas o error en el servidor.';
        this.alertType = 'error';
        this.alertMessage = this.error ?? '';
        this.cdr.markForCheck();
      }
    }));
  }
}
