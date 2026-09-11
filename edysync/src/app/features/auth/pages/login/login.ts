import { CommonModule } from '@angular/common';
import { Component, OnInit, OnDestroy, AfterViewInit, ChangeDetectionStrategy, ChangeDetectorRef, NgZone, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { Router, ActivatedRoute, RouterModule } from '@angular/router';
import { firstValueFrom, Subscription } from 'rxjs';
import { AuthService } from '../../../../core/services/auth.service';
import { FloatingUiService } from '../../../../core/services/floating-ui.service';
import { Alert } from '../../../../shared/components/alert/alert';
import { PreferencesMenu } from '../../../../shared/components/preferences-menu/preferences-menu';
import { base64urlToBuffer, serializeWebauthnCredential } from '../../../../shared/utils/webauthn';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule, FontAwesomeModule, Alert, PreferencesMenu],
  templateUrl: './login.html',
  styleUrl: './login.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Login implements OnInit, OnDestroy, AfterViewInit {
  floating = inject(FloatingUiService);

  email = '';
  password = '';
  showPassword = false;
  isLoading = false;
  loading = false;
  error: string | null = null;

  alertMessage = '';
  alertType: 'success' | 'error' | 'warning' | 'info' = 'info';
  emailError = '';
  passwordError = '';

  showHelp = false;

  wfModalOpen = false;
  wfChecking = false;
  wfAutoTrigger = false;

  guideStep = 0; // 0=none, 1=email, 2=password, 3=button, 4=done
  guidePos = { top: 0, left: 0, arrowLeft: 50 };
  guideText = '';
  guideVisible = false;

  private guideTimer: any;
  private resizeHandler: (() => void) | null = null;
  private _lastFormValid = false;
  private wfIdentifierKey = 'moscowle_webauthn_identity';
  private lastCheckedEmail = '';

  private subs = new Subscription();

  constructor(
    private authService: AuthService,
    private router: Router,
    private route: ActivatedRoute,
    private cdr: ChangeDetectorRef,
    private ngZone: NgZone,
  ) {}

  ngOnInit() {
    this.subs.add(this.route.queryParams.subscribe(params => {
      if (params['logout'] === 'success') {
        this.alertType = 'success';
        this.alertMessage = 'Has cerrado sesión correctamente.';
        this.cdr.markForCheck();
      }
    }));
    this.scheduleGuide();
    this.restoreRemembered();
  }

  ngAfterViewInit() {
    setTimeout(() => {
      if (this.wfAutoTrigger && this.wfModalOpen) {
        const btn = document.getElementById('webauthn-modal-btn');
        if (btn) { btn.click(); return; }
        this.loginWithFingerprint();
      }
    }, 500);
  }

  ngOnDestroy() {
    this.subs.unsubscribe();
    clearTimeout(this.guideTimer);
    if (this.resizeHandler) {
      window.removeEventListener('resize', this.resizeHandler);
    }
  }

  private scheduleGuide() {
    clearTimeout(this.guideTimer);
    this.guideTimer = setTimeout(() => {
      this.ngZone.run(() => {
        this.startGuide();
      });
    }, 10000);
  }

  private startGuide() {
    if (this.guideStep > 0 || this.showHelp) return;
    const logo = document.querySelector('.login-logo');
    if (logo) {
      const r = logo.getBoundingClientRect();
      this.guidePos = { top: r.top - 8, left: r.right + 16, arrowLeft: 16 };
    }
    this.guideText = 'Ingresa tu correo electrónico o código de acceso (ej: PCJP1)';
    this.guideStep = 1;
    this.guideVisible = true;
    this.cdr.markForCheck();

    setTimeout(() => this.ngZone.run(() => this.positionGuide('email')), 350);
    this.resizeHandler = () => {
      if (this.guideStep === 1) this.positionGuide('email');
      else if (this.guideStep === 2) this.positionGuide('password');
      else if (this.guideStep === 3) this.positionGuide('login-btn');
    };
    window.addEventListener('resize', this.resizeHandler);
  }

  private positionGuide(targetId: string) {
    const el = document.getElementById(targetId);
    const card = document.querySelector('.login-card');
    if (!el || !card) return;
    const er = el.getBoundingClientRect();
    const cr = card.getBoundingClientRect();

    if (targetId === 'email') {
      this.guidePos = {
        top: er.top - 4,
        left: cr.right + 16,
        arrowLeft: 20,
      };
    } else if (targetId === 'password') {
      this.guidePos = {
        top: er.top - 4,
        left: cr.right + 16,
        arrowLeft: 20,
      };
    } else if (targetId === 'login-btn') {
      const btn = document.querySelector('.login-submit') as HTMLElement;
      if (btn) {
        const br = btn.getBoundingClientRect();
        this.guidePos = {
          top: br.top - 8,
          left: cr.right + 16,
          arrowLeft: 20,
        };
      }
    }
    this.cdr.markForCheck();
  }

  onEmailInput() {
    if (this.guideStep === 1 && this.email.trim().length > 2) {
      this.guideStep = 2;
      this.guideText = 'Ahora ingresa la contraseña que te enviamos';
      this.cdr.markForCheck();
      setTimeout(() => this.ngZone.run(() => this.positionGuide('password')), 350);
    }
  }

  onPasswordInput() {
    if (this.guideStep === 2 && this.password.length > 0) {
      this.guideStep = 3;
      this.guideText = 'Perfecto! Presiona INICIAR SESIÓN para acceder';
      this.cdr.markForCheck();
      setTimeout(() => this.ngZone.run(() => this.positionGuide('login-btn')), 350);
    }
  }

  onPasswordFocus() {
    if (!this.authSupported() || this.wfModalOpen) return;
    const email = this.email.trim();
    if (email.length < 3 || email === this.lastCheckedEmail) return;
    this.wfChecking = true;
    this.cdr.markForCheck();
    this.authService.webauthnLoginOptions(email).subscribe({
      next: (res) => {
        this.wfChecking = false;
        this.lastCheckedEmail = email;
        if (res?.success && res.options && email === this.email.trim()) {
          this.wfModalOpen = true;
          this.cdr.markForCheck();
        }
      },
      error: () => {
        this.wfChecking = false;
        this.lastCheckedEmail = email;
      },
    });
  }

  private restoreRemembered() {
    if (!this.authSupported()) return;
    let identifier = '';
    try {
      const raw = localStorage.getItem(this.wfIdentifierKey);
      if (raw) {
        const parsed = JSON.parse(raw);
        identifier = typeof parsed?.identifier === 'string' ? parsed.identifier.trim() : '';
      }
    } catch {
      identifier = '';
    }
    if (!identifier) return;
    this.email = identifier;
    this.cdr.markForCheck();
    this.preAuthorize(identifier, true);
  }

  private preAuthorize(identifier: string, openModalOnOk: boolean) {
    const email = identifier.trim();
    if (!email || this.wfChecking) return;
    this.wfChecking = true;
    this.authService.webauthnLoginOptions(email).subscribe({
      next: (res) => {
        this.wfChecking = false;
        this.lastCheckedEmail = email;
        if (res?.success && res.options) {
          if (openModalOnOk) {
            this.wfModalOpen = true;
            this.wfAutoTrigger = true;
            this.cdr.markForCheck();
          }
        } else {
          this.clearRemembered();
        }
      },
      error: (err) => {
        this.wfChecking = false;
        this.lastCheckedEmail = email;
        if (err?.status === 404) {
          this.clearRemembered();
          if (this.wfModalOpen) {
            this.wfModalOpen = false;
            this.cdr.markForCheck();
          }
        }
      },
    });
  }

  closeWfModal() {
    this.wfModalOpen = false;
    this.cdr.markForCheck();
    const el = document.getElementById('password') as HTMLInputElement | null;
    if (el) el.focus();
  }

  private persistIdentity() {
    try {
      localStorage.setItem(this.wfIdentifierKey, JSON.stringify({ identifier: this.email.trim(), at: Date.now() }));
    } catch {
      // almacenamiento no disponible
    }
  }

  private clearRemembered() {
    try {
      localStorage.removeItem(this.wfIdentifierKey);
    } catch {
      // almacenamiento no disponible
    }
  }

  dismissGuide() {
    this.guideStep = 4;
    this.guideVisible = false;
    if (this.resizeHandler) {
      window.removeEventListener('resize', this.resizeHandler);
      this.resizeHandler = null;
    }
    this.cdr.markForCheck();
  }

  toggleHelp() {
    this.showHelp = !this.showHelp;
    if (this.showHelp) {
      this.dismissGuide();
    }
  }

  get isFormValid(): boolean {
    const valid = this.email.trim().length >= 3 && this.password.length > 0;
    if (valid !== this._lastFormValid) {
      this._lastFormValid = valid;
      this.cdr.markForCheck();
    }
    return valid;
  }

  togglePassword() {
    this.showPassword = !this.showPassword;
  }

  async doLogin() {
    this.emailError = '';
    this.passwordError = '';
    if (!this.email.trim()) {
      this.emailError = 'El correo o código es obligatorio';
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
        this.error = null;
        this.alertMessage = '';
        const route = res.user?.role === 'admin' ? '/admin/dashboard'
                    : res.user?.role === 'supervisor' ? '/admin/dashboard'
                    : res.user?.role === 'terapista' ? '/therapist/dashboard'
                    : res.user?.role === 'jugador' ? '/patient/dashboard'
                    : '/';
        this.router.navigate([route]).finally(() => {
          this.isLoading = false;
          this.loading = false;
          this.cdr.markForCheck();
        });
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

  authSupported(): boolean {
    return typeof window !== 'undefined' && !!window.PublicKeyCredential;
  }

  async loginWithFingerprint() {
    this.emailError = '';
    this.error = null;
    this.alertMessage = '';
    if (!this.email.trim()) {
      this.emailError = 'Escribe tu correo o código antes de usar la huella';
      this.cdr.markForCheck();
      return;
    }
    this.isLoading = true;
    this.loading = true;
    this.cdr.markForCheck();

    try {
      const res = await firstValueFrom(this.authService.webauthnLoginOptions(this.email.trim()));
      if (!res?.success || !res.options) {
        throw { error: { message: res?.error || 'No se pudo iniciar el ingreso con huella.' } };
      }
      const options = res.options;
      options.challenge = base64urlToBuffer(options.challenge);
      if (options.userHandle) {
        options.userHandle = base64urlToBuffer(options.userHandle);
      }
      if (options.allowCredentials?.length) {
        options.allowCredentials = options.allowCredentials.map((c: { id: string; type: string }) => ({
          ...c,
          id: base64urlToBuffer(c.id),
        }));
      }
      const credential = await navigator.credentials.get({ publicKey: options });
      if (!credential) {
        throw { error: { message: 'Autenticación cancelada por el usuario.' } };
      }
      const serialized = serializeWebauthnCredential(credential as PublicKeyCredential);
      const verify = await firstValueFrom(this.authService.webauthnLoginVerify(this.email.trim(), serialized));
      if (!verify?.success) {
        throw { error: { message: verify?.error || 'La huella no fue válida.' } };
      }
      const route = verify.user?.role === 'admin' ? '/admin/dashboard'
                  : verify.user?.role === 'supervisor' ? '/admin/dashboard'
                  : verify.user?.role === 'terapista' ? '/therapist/dashboard'
                  : verify.user?.role === 'jugador' ? '/patient/dashboard'
                  : '/';
      this.persistIdentity();
      this.wfModalOpen = false;
      this.router.navigate([route]).finally(() => {
        this.isLoading = false;
        this.loading = false;
        this.cdr.markForCheck();
      });
    } catch (err: any) {
      this.isLoading = false;
      this.loading = false;
      this.wfModalOpen = false;
      const errText = String(err?.message || err?.error?.message || err?.name || '');
      const cancelled = err?.name === 'NotAllowedError'
        || errText.includes('NotAllowedError')
        || errText.includes('cancelado')
        || errText.includes('cancelled')
        || errText.includes('no permitida');
      this.error = cancelled ? 'La autenticación por huella fue cancelada. Usa tu contraseña.' : (err?.error?.message || 'No se pudo iniciar sesión con huella. Intenta con tu contraseña.');
      this.alertType = 'error';
      this.alertMessage = this.error ?? '';
      this.cdr.markForCheck();
    }
  }
}
