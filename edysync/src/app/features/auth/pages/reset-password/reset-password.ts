import { Component, OnDestroy, ChangeDetectionStrategy, ChangeDetectorRef, ElementRef, ViewChild } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { HttpClient } from '@angular/common/http';
import { RouterModule } from '@angular/router';
import { Subscription } from 'rxjs';
import { Logo } from '../../../../shared/components/logo/logo';
import { PreferencesMenu } from '../../../../shared/components/preferences-menu/preferences-menu';

/** Pedido de contraseña nueva: acepta el correo o el código de acceso (los pacientes ingresan con código). */
@Component({
  selector: 'app-reset-password',
  standalone: true,
  imports: [Logo, FormsModule, RouterModule, FontAwesomeModule, PreferencesMenu],
  templateUrl: './reset-password.html',
  styleUrls: ['../login/login.scss', './reset-password.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ResetPassword implements OnDestroy {
  @ViewChild('identifierInput') identifierInput?: ElementRef<HTMLInputElement>;

  identifier = '';
  step: 'request' | 'sent' = 'request';
  submitting = false;
  message = '';

  private subs = new Subscription();

  constructor(
    private http: HttpClient,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnDestroy() {
    this.subs.unsubscribe();
  }

  requestReset() {
    if (this.submitting) return;
    const identifier = this.identifier.trim();
    if (!identifier) {
      this.message = 'Escribe tu correo o tu código.';
      this.cdr.markForCheck();
      this.identifierInput?.nativeElement.focus();
      return;
    }
    this.submitting = true;
    this.message = '';
    this.cdr.markForCheck();
    this.subs.add(
      this.http.post('/api/auth/reset-password', { email: identifier }).subscribe({
        next: () => {
          this.step = 'sent';
          this.submitting = false;
          this.cdr.markForCheck();
        },
        error: (err) => {
          const status = err?.status ?? 0;
          this.message =
            status === 429
              ? 'Ya pediste varias veces en la última hora. Espera un poco o escribe a soporte.'
              : status === 0 || status >= 500
                ? 'No pudimos conectar con el centro. Revisa tu internet e inténtalo otra vez.'
                : err?.error?.error || 'No pudimos enviar tu pedido. Inténtalo otra vez.';
          this.submitting = false;
          this.cdr.markForCheck();
          this.identifierInput?.nativeElement.focus();
        },
      }),
    );
  }
}
