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
    if (!this.isFormValid) return;
    
    this.isLoading = true;
    this.alertMessage = '';

    this.authService.login(this.email, this.password).subscribe({
      next: (res) => {
        this.alertType = 'success';
        this.alertMessage = 'Inicio de sesión exitoso. Redirigiendo...';
        
        setTimeout(() => {
           if (res.user && res.user.role === 'admin') {
               this.router.navigate(['/admin/dashboard']);
           } else if (res.user && res.user.role === 'terapista') {
               this.router.navigate(['/therapist/dashboard']);
           } else if (res.user && res.user.role === 'jugador') {
               this.router.navigate(['/patient/dashboard']);
           } else {
               this.router.navigate(['/']);
           }
           this.isLoading = false;
        }, 1000);
      },
      error: (err) => {
        this.isLoading = false;
        this.alertType = 'error';
        this.alertMessage = err.error?.message || 'Credenciales incorrectas o error en el servidor.';
      }
    });
  }
}
