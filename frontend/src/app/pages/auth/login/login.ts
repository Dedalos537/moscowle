import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormsModule, ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';

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

  
handleSubmit(): void {
  if (this.loginForm.invalid) {
    this.message = 'Por favor, completa el formulario correctamente.';
    return;
  }

  this.loading = true;
  this.message = '';

  setTimeout(() => {
    const { email, password } = this.loginForm.value;

    if (email === 'alumno@juanpabloii.edu.pe' && password === '123456') {
      const rol = 'ALUMNO';
      localStorage.setItem('rol', rol);
      this.message = '¡Inicio de sesión exitoso!';
      this.router.navigate(['/cursos']);
    } else if (email === 'admin@juanpabloii.edu.pe' && password === 'admin123') {
      const rol = 'ADMIN';
      localStorage.setItem('rol', rol);
      this.message = '¡Inicio de sesión exitoso!';
      this.router.navigate(['/dashboard']);
    } else {
      this.message = 'Credenciales incorrectas';
    }

    this.loading = false;
  }, 1000);
}

}
