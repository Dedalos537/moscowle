import { Component, OnInit, OnDestroy, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { Router, ActivatedRoute } from '@angular/router';
import { Subscription } from 'rxjs';
import { AuthService } from '../../../../core/services/auth.service';

@Component({
  selector: 'app-login',
  standalone: false,
  templateUrl: './login.html',
  styleUrl: './login.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Login implements OnInit, OnDestroy {
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
  }

  ngOnDestroy() {
    this.subs.unsubscribe();
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
