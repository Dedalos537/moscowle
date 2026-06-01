import { Component, OnDestroy, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { Subscription } from 'rxjs';
import { IconProp } from '@fortawesome/fontawesome-svg-core';

@Component({
  selector: 'app-reset-password',
  standalone: false,
  templateUrl: './reset-password.html',
  styleUrl: './reset-password.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ResetPassword implements OnDestroy {
  email = '';
  step: 'request' | 'sent' = 'request';
  submitting = false;
  message = '';
  loading = false;
  error: string | null = null;
  showHelp = false;

  private subs = new Subscription();

  constructor(
    private http: HttpClient,
    public router: Router,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnDestroy() {
    this.subs.unsubscribe();
  }

  requestReset() {
    if (!this.email) return;
    this.submitting = true;
    this.loading = true;
    this.error = null;
    this.cdr.markForCheck();
    this.subs.add(this.http.post('/api/auth/reset-password', { email: this.email }).subscribe({
      next: () => {
        this.step = 'sent';
        this.submitting = false;
        this.loading = false;
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.message = err.error?.message || 'Error al solicitar el cambio de contraseña';
        this.error = this.message;
        this.submitting = false;
        this.loading = false;
        this.cdr.markForCheck();
      },
    }));
  }
}
