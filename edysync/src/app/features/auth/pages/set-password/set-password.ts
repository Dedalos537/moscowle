import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { Logo } from '../../../../shared/components/logo/logo';
import { PreferencesMenu } from '../../../../shared/components/preferences-menu/preferences-menu';
import { ToastService } from '../../../../core/services/toast.service';

/**
 * Crear la contraseña desde el enlace del correo (bienvenida o cambio hecho por un admin). Los correos ya no
 * llevan la contraseña escrita: traen este enlace de un solo uso que vence a las 72 h.
 */
@Component({
  selector: 'app-set-password',
  imports: [Logo, FormsModule, RouterModule, FontAwesomeModule, PreferencesMenu],
  templateUrl: './set-password.html',
  styleUrls: ['../login/login.scss', '../reset-password/reset-password.scss', './set-password.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SetPassword {
  private http = inject(HttpClient);
  private router = inject(Router);
  private toast = inject(ToastService);
  private token = inject(ActivatedRoute).snapshot.queryParamMap.get('t') || '';

  readonly state = signal<'checking' | 'ready' | 'invalid' | 'done'>('checking');
  readonly name = signal('');
  readonly loginCode = signal<string | null>(null);
  readonly error = signal('');
  readonly saving = signal(false);
  readonly show = signal(false);
  password = '';
  confirm = '';

  constructor() {
    if (!this.token) {
      this.state.set('invalid');
      return;
    }
    this.http.get<{ success: boolean; name: string; login_code: string | null; error?: string }>(
      '/api/auth/set-password', { params: { t: this.token } },
    ).subscribe({
      next: (r) => {
        this.name.set(r.name);
        this.loginCode.set(r.login_code);
        this.state.set('ready');
      },
      error: () => this.state.set('invalid'),
    });
  }

  save() {
    if (this.saving()) return;
    if (this.password.length < 8) {
      this.error.set('Usa al menos 8 caracteres.');
      return;
    }
    if (this.password !== this.confirm) {
      this.error.set('Las dos contraseñas no coinciden.');
      return;
    }
    this.error.set('');
    this.saving.set(true);
    this.http.post<{ success: boolean; message: string }>('/api/auth/set-password', { token: this.token, new_password: this.password })
      .subscribe({
        next: (r) => {
          this.saving.set(false);
          this.state.set('done');
          this.toast.show(r.message || 'Contraseña creada.', 'success');
        },
        error: (e) => {
          this.saving.set(false);
          if (e?.status === 400 && /venció|usó/.test(e?.error?.error || '')) this.state.set('invalid');
          else this.error.set(e?.error?.error || 'No se pudo guardar. Intenta de nuevo.');
        },
      });
  }

  goLogin() {
    void this.router.navigateByUrl('/auth/login');
  }
}
