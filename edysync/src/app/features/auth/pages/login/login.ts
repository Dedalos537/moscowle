import { Component, OnInit } from '@angular/core';
import { Router, ActivatedRoute } from '@angular/router';
import { AuthService } from '../../../../core/services/auth.service';

@Component({
  selector: 'app-login',
  standalone: false,
  templateUrl: './login.html',
  styleUrl: './login.scss'
})
export class Login implements OnInit {
  email = '';
  password = '';
  showPassword = false;
  isLoading = false;
  
  alertMessage = '';
  alertType: 'success' | 'error' | 'warning' | 'info' = 'info';
  darkMode = false;
  emailError = '';
  passwordError = '';

  constructor(
    private authService: AuthService,
    private router: Router,
    private route: ActivatedRoute
  ) {}

  ngOnInit() {
    this.darkMode = document.documentElement.classList.contains('dark') ||
                    localStorage.getItem('theme') === 'dark';
    this.route.queryParams.subscribe(params => {
      if (params['logout'] === 'success') {
        this.alertType = 'success';
        this.alertMessage = 'Has cerrado sesión correctamente.';
      }
    });
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
    this.alertMessage = '';

    this.authService.login(this.email, this.password).subscribe({
      next: (res) => {
        this.isLoading = false;
        const route = res.user?.role === 'admin' ? '/admin/dashboard'
                    : res.user?.role === 'terapista' ? '/therapist/dashboard'
                    : res.user?.role === 'jugador' ? '/patient/dashboard'
                    : '/';
        this.router.navigate([route]);
      },
      error: (err) => {
        this.isLoading = false;
        this.alertType = 'error';
        this.alertMessage = err.error?.message || 'Credenciales incorrectas o error en el servidor.';
      }
    });
  }
}
