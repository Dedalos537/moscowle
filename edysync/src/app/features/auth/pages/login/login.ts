import { Component, OnInit, OnDestroy, ChangeDetectionStrategy, ChangeDetectorRef, ElementRef, ViewChild, inject } from '@angular/core';
import { toObservable } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { Router, ActivatedRoute, RouterModule } from '@angular/router';
import { filter, firstValueFrom, Subscription, take } from 'rxjs';
import { AuthService } from '../../../../core/services/auth.service';
import { ToastService } from '../../../../core/services/toast.service';
import { SplashService } from '../../../../core/services/splash.service';
import { PreferencesMenu } from '../../../../shared/components/preferences-menu/preferences-menu';
import { base64urlToBuffer, serializeWebauthnCredential } from '../../../../shared/utils/webauthn';
import { Logo } from '../../../../shared/components/logo/logo';

const HOME_BY_ROLE: Record<string, string> = {
  admin: '/admin/dashboard',
  supervisor: '/admin/dashboard',
  terapista: '/therapist/dashboard',
  jugador: '/patient/dashboard',
};

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [Logo, FormsModule, RouterModule, FontAwesomeModule, PreferencesMenu],
  templateUrl: './login.html',
  styleUrl: './login.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Login implements OnInit, OnDestroy {
  @ViewChild('emailInput') emailInput?: ElementRef<HTMLInputElement>;
  @ViewChild('passwordInput') passwordInput?: ElementRef<HTMLInputElement>;
  @ViewChild('helpDialog') helpDialog?: ElementRef<HTMLDialogElement>;

  email = '';
  password = '';
  showPassword = false;
  isLoading = false;

  emailError = '';
  passwordError = '';
  /** El servidor rechazó la combinación: ambos campos quedan marcados como inválidos. */
  credentialsRejected = false;

  /** Solo se ofrece la huella cuando este equipo ya tiene una registrada para esa cuenta. */
  fingerprintReady = false;
  fingerprintBusy = false;

  private readonly identityKey = 'moscowle_webauthn_identity';
  private checkedIdentity = '';
  private subs = new Subscription();

  constructor(
    private authService: AuthService,
    private router: Router,
    private route: ActivatedRoute,
    private cdr: ChangeDetectorRef,
    private toast: ToastService,
    private splash: SplashService,
  ) {}

  private readonly splashPhase$ = toObservable(inject(SplashService).phase);

  ngOnInit() {
    this.subs.add(
      this.route.queryParams.subscribe((params) => {
        if (params['logout'] !== 'success') return;
        // El aviso espera a que el logo termine de abrirse sobre el login; si salía antes, aparecía
        // encima de la animación de cierre de sesión.
        this.subs.add(
          this.splashPhase$.pipe(filter((p) => p === 'done'), take(1)).subscribe(() =>
            this.toast.show('Cerraste sesión. ¡Hasta pronto!', 'success'),
          ),
        );
      }),
    );
    this.restoreRemembered();
  }

  ngOnDestroy() {
    this.subs.unsubscribe();
  }

  onEmailChange() {
    this.emailError = '';
    this.credentialsRejected = false;
    // Otra cuenta: la huella se vuelve a comprobar al salir del campo.
    if (this.email.trim() !== this.checkedIdentity) {
      this.fingerprintReady = false;
      this.checkedIdentity = '';
    }
  }

  togglePassword() {
    this.showPassword = !this.showPassword;
  }

  // ── ayuda ──────────────────────────────────────────────────────────────────
  openHelp() {
    this.helpDialog?.nativeElement.showModal();
  }

  closeHelp() {
    this.helpDialog?.nativeElement.close();
  }

  /** Tocar el fondo (fuera del contenido) cierra la ayuda. */
  onDialogClick(event: MouseEvent) {
    if (event.target === this.helpDialog?.nativeElement) this.closeHelp();
  }

  // ── contraseña ─────────────────────────────────────────────────────────────
  doLogin() {
    if (this.isLoading) return;
    this.credentialsRejected = false;
    this.emailError = this.email.trim() ? '' : 'Escribe tu correo o tu código.';
    this.passwordError = this.password ? '' : 'Escribe tu contraseña.';
    if (this.emailError || this.passwordError) {
      this.cdr.markForCheck();
      queueMicrotask(() => (this.emailError ? this.emailInput : this.passwordInput)?.nativeElement.focus());
      return;
    }

    this.isLoading = true;
    this.cdr.markForCheck();

    this.subs.add(
      this.authService.login(this.email.trim(), this.password).subscribe({
        next: (res) => this.goHome(res.user?.role),
        error: (err) => {
          this.isLoading = false;
          this.toast.show(this.loginErrorText(err), 'error', 7000);
          this.credentialsRejected = err?.status === 401 || err?.status === 400;
          this.cdr.markForCheck();
          queueMicrotask(() => this.passwordInput?.nativeElement.select());
        },
      }),
    );
  }

  /** El mensaje dice qué pasó y qué hacer, no un «error en el servidor» genérico. */
  private loginErrorText(err: any): string {
    const status = err?.status ?? 0;
    if (status === 0 || status >= 500) {
      return 'No pudimos conectar con el centro. Revisa tu internet e inténtalo otra vez.';
    }
    if (status === 429) {
      return 'Hubo demasiados intentos seguidos. Espera unos minutos antes de volver a intentar.';
    }
    if (status === 403 && err?.error?.message) return err.error.message;
    return 'El correo o código y la contraseña no coinciden. Revisa que estén bien escritos.';
  }

  /** Cubre con el logo, navega y revela el panel a través de la silueta (la misma entrada de la app). */
  private goHome(role?: string) {
    this.splash.cover();
    this.router.navigate([HOME_BY_ROLE[role ?? ''] ?? '/']).finally(() => {
      this.splash.reveal();
      this.isLoading = false;
      this.fingerprintBusy = false;
      this.cdr.markForCheck();
    });
  }

  // ── huella ─────────────────────────────────────────────────────────────────
  private authSupported(): boolean {
    return typeof window !== 'undefined' && !!window.PublicKeyCredential;
  }

  /** Si en este equipo ya se ingresó con huella, se precarga la cuenta y se ofrece el botón (sin abrirlo solo). */
  private restoreRemembered() {
    if (!this.authSupported()) return;
    let identifier = '';
    try {
      const parsed = JSON.parse(localStorage.getItem(this.identityKey) || 'null');
      identifier = typeof parsed?.identifier === 'string' ? parsed.identifier.trim() : '';
    } catch {
      identifier = '';
    }
    if (!identifier) return;
    this.email = identifier;
    this.cdr.markForCheck();
    this.checkFingerprint(identifier, true);
  }

  /** Al salir del campo, se averigua en silencio si esa cuenta tiene huella en este equipo. */
  onEmailBlur() {
    const identifier = this.email.trim();
    if (this.authSupported() && identifier.length >= 3) this.checkFingerprint(identifier, false);
  }

  private checkFingerprint(identifier: string, remembered: boolean) {
    if (!identifier || identifier === this.checkedIdentity) return;
    this.checkedIdentity = identifier;
    this.subs.add(
      this.authService.webauthnLoginOptions(identifier).subscribe({
        next: (res) => {
          this.fingerprintReady = !!(res?.success && res.options) && identifier === this.email.trim();
          if (!this.fingerprintReady && remembered) this.forgetIdentity();
          this.cdr.markForCheck();
        },
        error: () => {
          this.fingerprintReady = false;
          if (remembered) this.forgetIdentity();
          this.cdr.markForCheck();
        },
      }),
    );
  }

  async loginWithFingerprint() {
    const identifier = this.email.trim();
    if (!identifier) {
      this.emailError = 'Escribe tu correo o tu código para usar la huella.';
      this.cdr.markForCheck();
      this.emailInput?.nativeElement.focus();
      return;
    }
    this.isLoading = true;
    this.fingerprintBusy = true;
    this.cdr.markForCheck();

    try {
      const res = await firstValueFrom(this.authService.webauthnLoginOptions(identifier));
      if (!res?.success || !res.options) throw { error: { message: res?.error } };
      const options = res.options;
      options.challenge = base64urlToBuffer(options.challenge);
      if (options.userHandle) options.userHandle = base64urlToBuffer(options.userHandle);
      if (options.allowCredentials?.length) {
        options.allowCredentials = options.allowCredentials.map((c: { id: string; type: string }) => ({ ...c, id: base64urlToBuffer(c.id) }));
      }
      const credential = await navigator.credentials.get({ publicKey: options });
      if (!credential) throw { name: 'NotAllowedError' };
      const verify = await firstValueFrom(this.authService.webauthnLoginVerify(identifier, serializeWebauthnCredential(credential as PublicKeyCredential)));
      if (!verify?.success) throw { error: { message: verify?.error } };
      this.rememberIdentity(identifier);
      this.goHome(verify.user?.role);
    } catch (err: any) {
      this.isLoading = false;
      this.fingerprintBusy = false;
      const cancelled = err?.name === 'NotAllowedError' || err?.name === 'AbortError';
      this.toast.show(
        cancelled
          ? 'Se canceló la lectura de la huella. Puedes intentarlo otra vez o usar tu contraseña.'
          : 'No pudimos validar tu huella. Ingresa con tu contraseña.',
        'error',
        7000,
      );
      this.cdr.markForCheck();
      if (!cancelled) this.passwordInput?.nativeElement.focus();
    }
  }

  private rememberIdentity(identifier: string) {
    try {
      localStorage.setItem(this.identityKey, JSON.stringify({ identifier, at: Date.now() }));
    } catch {
      // almacenamiento no disponible
    }
  }

  private forgetIdentity() {
    try {
      localStorage.removeItem(this.identityKey);
    } catch {
      // almacenamiento no disponible
    }
  }
}
