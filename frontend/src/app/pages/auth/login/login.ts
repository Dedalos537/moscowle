import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormsModule, ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import axiosInstance from '../../../../axiosConfig';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, FormsModule, ReactiveFormsModule, RouterLink],
  templateUrl: './login.html',
  styleUrl: './login.css',
})
export class Login {
  showPassword = false;
  loading = false;
  message = '';
  loginForm: FormGroup;

  private router = inject(Router);
  private fb = inject(FormBuilder);

  constructor() {
    this.loginForm = this.fb.group({
      email: ['', [Validators.required, Validators.email]],
      password: ['', [Validators.required]],
    });
  }

  get email() {
    return this.loginForm.get('email');
  }

  get password() {
    return this.loginForm.get('password');
  }

  handleLinkClick(): void {
    this.router.navigate(['/home']);
  }

  async handleSubmit(): Promise<void> {
    if (this.loginForm.invalid) {
      this.message = 'Por favor, completa el formulario correctamente.';
      return;
    }

    this.loading = true;
    this.message = '';

    try {
      const { email, password } = this.loginForm.value;
      // Llama al backend para autenticar
      const res = await axiosInstance.post('/login', { email, password });
      console.log('Respuesta login:', res.data); // <-- depuración
      const { rol, token } = res.data;
      this.message = '¡Inicio de sesión exitoso!';
      // Guardar autenticación, rol y token en localStorage
      localStorage.setItem('isAuthenticated', 'true');
      localStorage.setItem('rol', rol);
      if (token) {
        localStorage.setItem('authToken', token);
      }
      // Redirección según el rol
      if (rol === 'ADMIN') {
        this.router.navigate(['/dashboard']);
      } else if (rol === 'USER' || rol === 'ALUMNO') {
        this.router.navigate(['/cursos']);
      } else {
        this.router.navigate(['/']);
      }
    } catch (err: any) {
      this.message = 'Credenciales inválidas o sin autorización aún';
    } finally {
      this.loading = false;
    }
  }

}
