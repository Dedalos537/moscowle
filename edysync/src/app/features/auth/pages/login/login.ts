import { Component } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService } from '../../../../core/services/auth.service';

@Component({
  selector: 'app-login',
  standalone: false,
  templateUrl: './login.html',
  styleUrl: './login.scss'
})
export class Login {
  email = '';
  password = '';
  showPassword = false;
  isLoading = false;
  
  // Para manejar el estado visual (Flash messages simulados)
  alertMessage = '';
  alertType: 'success' | 'error' | 'warning' | 'info' = 'info';

  constructor(
    private authService: AuthService,
    private router: Router
  ) {}

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
      next: (user) => {
        // En tu backend esto ruteaba al /dashboard 
        // y desde ahí el controlador redirigía basado en user.role
        this.alertType = 'success';
        this.alertMessage = 'Inicio de sesión exitoso. Redirigiendo...';
        
                setTimeout(() => {
           if (user && user.role === 'admin') {
               this.router.navigate(['/admin/dashboard']); 
           } else if (user && user.role === 'terapista') {
               this.router.navigate(['/therapist/dashboard']);
               // O usar window.location.href = '/therapist/dashboard' si está en Flask aún, 
               // pero viendo el código de EDYSYNC parece rutar a `/therapist/dashboard`. 
               // ¡Revisaremos y usaremos el routing nativo!
           } else {
               this.router.navigate(['/']); // fallback
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
