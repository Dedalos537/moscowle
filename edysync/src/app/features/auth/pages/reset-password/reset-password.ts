import { Component } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { IconProp } from '@fortawesome/fontawesome-svg-core';

@Component({
  selector: 'app-reset-password',
  standalone: false,
  templateUrl: './reset-password.html',
  styleUrl: './reset-password.scss',
})
export class ResetPassword {
  email = '';
  step: 'request' | 'sent' = 'request';
  submitting = false;
  message = '';

  constructor(
    private http: HttpClient,
    public router: Router
  ) {}

  requestReset() {
    if (!this.email) return;
    this.submitting = true;
    this.http.post('/api/auth/reset-password', { email: this.email }).subscribe({
      next: () => {
        this.step = 'sent';
        this.submitting = false;
      },
      error: (err) => {
        this.message = err.error?.message || 'Error al solicitar el cambio de contraseña';
        this.submitting = false;
      },
    });
  }
}
