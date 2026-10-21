import { HttpClient } from '@angular/common/http';
import { Injectable, inject, signal } from '@angular/core';
import { firstValueFrom } from 'rxjs';

const DISMISS_KEY = 'moscowle_push_prompt_until';
const SNOOZE_DAYS = 7;

/**
 * Notificaciones del navegador aunque la página esté cerrada (Web Push con el service worker `push-sw.js`).
 * Pide permiso solo con un clic del usuario (lo exige el navegador) y vuelve a registrar la suscripción en cada
 * inicio de sesión para que el servidor siempre tenga la vigente. En la app de Android no aplica: ahí avisa la app.
 */
@Injectable({ providedIn: 'root' })
export class WebPush {
  private http = inject(HttpClient);
  /** Mostrar el aviso «Activa las notificaciones». */
  readonly shouldPrompt = signal(false);
  readonly busy = signal(false);

  get supported(): boolean {
    if (typeof window === 'undefined') return false;
    const inAndroidApp = !!(window as Window & { MoscowleNative?: unknown }).MoscowleNative;
    return !inAndroidApp && 'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window;
  }

  /** Al entrar: si ya hay permiso, renueva la suscripción en silencio; si nunca se preguntó, ofrece el aviso. */
  async init(): Promise<void> {
    if (!this.supported) return;
    if (Notification.permission === 'granted') {
      await this.subscribe().catch(() => undefined);
      this.shouldPrompt.set(false);
    } else {
      this.shouldPrompt.set(Notification.permission === 'default' && !this.snoozed());
    }
  }

  /** Clic en «Activar»: pide permiso y suscribe este navegador. */
  async enable(): Promise<boolean> {
    if (!this.supported) return false;
    this.busy.set(true);
    try {
      const permission = await Notification.requestPermission();
      if (permission !== 'granted') {
        this.snooze();
        return false;
      }
      await this.subscribe();
      return true;
    } finally {
      this.busy.set(false);
      this.shouldPrompt.set(false);
    }
  }

  snooze(): void {
    try {
      localStorage.setItem(DISMISS_KEY, String(Date.now() + SNOOZE_DAYS * 86_400_000));
    } catch {
      /* sin almacenamiento: se vuelve a ofrecer en la próxima visita */
    }
    this.shouldPrompt.set(false);
  }

  private snoozed(): boolean {
    try {
      return Number(localStorage.getItem(DISMISS_KEY) || 0) > Date.now();
    } catch {
      return false;
    }
  }

  private async subscribe(): Promise<void> {
    const reg = await navigator.serviceWorker.register('push-sw.js');
    await navigator.serviceWorker.ready;
    const { key } = await firstValueFrom(this.http.get<{ key: string }>('/api/push/vapid-key'));
    let sub = await reg.pushManager.getSubscription();
    if (!sub) {
      sub = await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: this.toBytes(key) });
    }
    await firstValueFrom(this.http.post('/api/push/subscribe', sub.toJSON()));
  }

  private toBytes(b64url: string): Uint8Array<ArrayBuffer> {
    const b64 = (b64url + '='.repeat((4 - (b64url.length % 4)) % 4)).replace(/-/g, '+').replace(/_/g, '/');
    const raw = atob(b64);
    const out = new Uint8Array(new ArrayBuffer(raw.length));
    for (let i = 0; i < raw.length; i++) out[i] = raw.charCodeAt(i);
    return out;
  }
}
