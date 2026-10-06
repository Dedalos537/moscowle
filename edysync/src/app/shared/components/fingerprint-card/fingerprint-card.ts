import { Component, ChangeDetectionStrategy, ChangeDetectorRef, OnInit, inject } from '@angular/core';
import { DatePipe } from '@angular/common';
import { firstValueFrom } from 'rxjs';
import { AuthService } from '../../../core/services/auth.service';
import { ToastService } from '../../../core/services/toast.service';
import { ConfirmService } from '../../../core/services/confirm.service';
import { base64urlToBuffer, serializeWebauthnCredential } from '../../utils/webauthn';

interface Credential {
  id: number;
  device_name?: string;
  created_at?: string;
}

/** Registro de huella / sensor del dispositivo (WebAuthn). Disponible para cualquier rol con sesión. */
@Component({
  selector: 'app-fingerprint-card',
  standalone: true,
  imports: [DatePipe],
  templateUrl: './fingerprint-card.html',
  styleUrl: './fingerprint-card.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FingerprintCard implements OnInit {
  credentials: Credential[] = [];
  loading = true;
  registering = false;
  deviceName = '';
  error = '';

  private auth = inject(AuthService);
  private toast = inject(ToastService);
  private confirm = inject(ConfirmService);
  private cdr = inject(ChangeDetectorRef);

  get supported(): boolean {
    return typeof window !== 'undefined' && !!window.PublicKeyCredential;
  }

  ngOnInit() {
    if (this.supported) this.load();
    else this.loading = false;
  }

  load() {
    this.loading = true;
    this.auth.getCredentials().subscribe({
      next: (res) => { this.credentials = res?.credentials || []; this.loading = false; this.cdr.markForCheck(); },
      error: () => { this.credentials = []; this.loading = false; this.error = 'No se pudo cargar tus dispositivos.'; this.cdr.markForCheck(); },
    });
  }

  async register() {
    if (!this.supported || this.registering) return;
    this.registering = true;
    this.error = '';
    this.cdr.markForCheck();
    try {
      const res = await firstValueFrom(this.auth.webauthnRegisterOptions());
      if (!res?.success || !res.options) throw new Error(res?.error || 'No se pudo iniciar el registro de la huella.');
      const options = res.options;
      options.challenge = base64urlToBuffer(options.challenge);
      if (options.user?.id) options.user.id = base64urlToBuffer(options.user.id);
      if (options.excludeCredentials?.length) {
        options.excludeCredentials = options.excludeCredentials.map((c: { id: string }) => ({ ...c, id: base64urlToBuffer(c.id) }));
      }
      const credential = await navigator.credentials.create({ publicKey: options });
      if (!credential) throw new Error('Registro cancelado.');
      const serialized = serializeWebauthnCredential(credential as PublicKeyCredential);
      const verify = await firstValueFrom(this.auth.webauthnRegisterVerify(serialized, this.deviceName.trim() || 'Dispositivo'));
      if (!verify?.success) throw new Error(verify?.error || 'No se pudo guardar la huella.');
      this.deviceName = '';
      this.rememberIdentity();
      this.toast.show('Huella registrada. Ya puedes ingresar con ella.', 'success');
      this.load();
    } catch (err) {
      const e = err as { name?: string; message?: string; error?: { error?: string; message?: string } };
      const cancelled = e?.name === 'NotAllowedError' || e?.name === 'AbortError';
      this.error = cancelled
        ? 'El registro se canceló o se agotó el tiempo. Inténtalo de nuevo.'
        : e?.error?.error || e?.error?.message || e?.message || 'No se pudo registrar la huella.';
    } finally {
      this.registering = false;
      this.cdr.markForCheck();
    }
  }

  remove(c: Credential) {
    this.confirm
      .confirm({
        title: 'Eliminar dispositivo',
        message: `"${c.device_name || 'Dispositivo'}" ya no podrá usarse para ingresar con huella.`,
        confirmText: 'Eliminar',
      })
      .subscribe((ok) => {
        if (!ok) return;
        this.auth.deleteCredential(c.id).subscribe({
          next: () => { this.toast.show('Dispositivo eliminado', 'success'); this.load(); },
          error: () => { this.error = 'No se pudo eliminar el dispositivo.'; this.cdr.markForCheck(); },
        });
      });
  }

  /** El login con huella pide el correo/código: se recuerda para no tener que escribirlo. */
  private rememberIdentity() {
    try {
      const raw = localStorage.getItem('user');
      const u = raw ? JSON.parse(raw) : null;
      const identifier = (u?.email || u?.login_code || '').trim();
      if (identifier) localStorage.setItem('moscowle_webauthn_identity', JSON.stringify({ identifier, at: Date.now() }));
    } catch {
      // almacenamiento no disponible
    }
  }
}
