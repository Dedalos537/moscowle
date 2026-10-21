import { Injectable, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { ToastService } from '../services/toast.service';
import { NoticeTone, NotificationEvent, Presentation, presentationOf, toneOf } from './notification-kinds';

export interface Notice {
  key: string;
  id: number;
  kind: string;
  title: string;
  message: string;
  tone: NoticeTone;
  icon: string;
  action: { label: string; link: string } | null;
}

const QUIET_FROM = 21;
const QUIET_TO = 7;
const MAX_BANNERS = 4;

/**
 * Decide cómo se muestra cada notificación (PRP 011 · E2): badge (lo lleva NotificationService), toast, snackbar,
 * banner, modal o push. Aplica contexto (si ya estás en esa pantalla no interrumpe), «no molestar» de 21:00 a
 * 07:00 (solo urgentes) y evita duplicados.
 */
/** Puente que expone la app de Android (MainActivity → MoscowleNative). */
type NativeWindow = Window & { MoscowleNative?: { notify?: (json: string) => void } };

@Injectable({ providedIn: 'root' })
export class NotificationPresenterService {
  private router = inject(Router);
  private toast = inject(ToastService);

  readonly snackbar = signal<Notice | null>(null);
  readonly banners = signal<Notice[]>([]);
  readonly modals = signal<Notice[]>([]);

  /** Lo pone NotificationService con las preferencias del usuario. */
  pushEnabled = false;

  private seen = new Set<string>();
  private snackTimer: ReturnType<typeof setTimeout> | null = null;
  private snackRemaining = 0;
  private snackStartedAt = 0;

  present(ev: NotificationEvent): void {
    const dedupe = `${ev.id}:${ev.group_count ?? 1}:${ev.payload?.['resolved'] ? 'r' : 'f'}`;
    if (this.seen.has(dedupe)) return;
    this.seen.add(dedupe);
    if (this.seen.size > 300) this.seen = new Set([...this.seen].slice(-150));

    const notice = this.toNotice(ev);
    this.nativeNotify(ev, notice);
    const shown = new Set<Presentation>(presentationOf(ev));
    const urgent = ev.priority === 'urgent';
    const here = this.isHere(ev.link);

    // Resuelto: retira el banner del mismo aviso y lo cuenta con un toast.
    if (ev.payload?.['resolved']) {
      this.banners.update((list) => list.filter((b) => b.key !== notice.key));
    }
    if (this.quietNow() && !urgent) return; // de noche solo el badge (lo actualiza NotificationService)

    if (shown.has('modal')) this.modals.update((q) => (q.some((m) => m.key === notice.key) ? q : [...q, notice]));
    if (shown.has('banner')) {
      this.banners.update((list) => [notice, ...list.filter((b) => b.key !== notice.key)].slice(0, MAX_BANNERS));
    }
    if (!here) {
      if (shown.has('snackbar') && notice.action) this.showSnackbar(notice);
      else if (shown.has('snackbar') || shown.has('toast')) this.showToast(notice);
    }
    if (shown.has('push') && !here) this.push(ev, notice);
  }

  // ── snackbar (una a la vez, 8 s, se pausa con el puntero o el foco) ──
  showSnackbar(n: Notice, ms = 8000): void {
    this.clearSnackTimer();
    this.snackbar.set(n);
    this.snackRemaining = ms;
    this.resumeSnackbar();
  }

  pauseSnackbar(): void {
    if (!this.snackTimer) return;
    this.snackRemaining -= Date.now() - this.snackStartedAt;
    this.clearSnackTimer();
  }

  resumeSnackbar(): void {
    if (!this.snackbar() || this.snackTimer) return;
    this.snackStartedAt = Date.now();
    this.snackTimer = setTimeout(() => this.dismissSnackbar(), Math.max(1500, this.snackRemaining));
  }

  dismissSnackbar(): void {
    this.clearSnackTimer();
    this.snackbar.set(null);
  }

  // ── banner y modal ──
  dismissBanner(key: string): void {
    this.banners.update((list) => list.filter((b) => b.key !== key));
  }

  /** Retira banners y modales de esos avisos (los resolvió alguien, aquí o en otro dispositivo). */
  dismissIds(ids: readonly number[]): void {
    if (!ids.length) return;
    const gone = new Set(ids);
    this.banners.update((list) => list.filter((b) => !gone.has(b.id)));
    this.modals.update((q) => q.filter((m) => !gone.has(m.id)));
  }

  acknowledgeModal(): void {
    this.modals.update((q) => q.slice(1));
  }

  open(n: Notice): void {
    if (n.action?.link) void this.router.navigateByUrl(n.action.link);
  }

  // ── internos ──
  private toNotice(ev: NotificationEvent): Notice {
    const alert = ev.payload?.['alertname'];
    const link = ev.action?.link ?? ev.link ?? null;
    return {
      key: alert ? `${ev.kind}:${alert}` : `${ev.kind ?? 'legacy'}:${ev.id}`,
      id: ev.id,
      kind: ev.kind ?? 'legacy',
      title: ev.title,
      message: ev.message,
      tone: toneOf(ev),
      icon: ev.icon || 'bell',
      action: link ? { label: ev.action?.label || 'Ver', link } : null,
    };
  }

  private showToast(n: Notice): void {
    const type = n.tone === 'danger' ? 'error' : n.tone === 'warning' ? 'warning' : n.tone === 'success' ? 'success' : 'info';
    const text = n.message && n.message !== n.title ? `${n.title}: ${n.message}` : n.title;
    this.toast.show(text, type, 4000);
  }

  private push(ev: NotificationEvent, n: Notice): void {
    if (!this.pushEnabled || typeof window === 'undefined' || !('Notification' in window)) return;
    if (Notification.permission !== 'granted') return;
    // Con Web Push activo, el service worker ya muestra el aviso (también con la página cerrada): no se duplica.
    if (navigator.serviceWorker?.controller) return;
    if (ev.push_when !== 'always' && document.visibilityState === 'visible') return;
    const note = new Notification(n.title, { body: n.message, icon: 'assets/img/logo-silhouette.png', tag: n.key });
    note.onclick = () => {
      window.focus();
      this.open(n);
      note.close();
    };
  }

  /** En la app de Android cada aviso va también a la barra de notificaciones del sistema, siempre
   * (la app lo deduplica con el mismo id y conteo que usa su revisión en segundo plano). */
  private nativeNotify(ev: NotificationEvent, n: Notice): void {
    const bridge = typeof window === 'undefined' ? undefined : (window as NativeWindow).MoscowleNative;
    if (!bridge?.notify) return;
    bridge.notify(
      JSON.stringify({
        id: ev.id,
        count: ev.group_count ?? 1,
        title: n.title,
        message: n.message,
        link: n.action?.link ?? '',
        priority: ev.priority ?? 'normal',
      }),
    );
  }

  /** ¿El usuario ya está en la pantalla del aviso? Entonces no se interrumpe (solo badge). */
  private isHere(link: string | null | undefined): boolean {
    if (!link) return false;
    const path = link.split('?')[0];
    return path.length > 1 && this.router.url.split('?')[0] === path;
  }

  private quietNow(): boolean {
    const h = new Date().getHours();
    return h >= QUIET_FROM || h < QUIET_TO;
  }

  private clearSnackTimer(): void {
    if (this.snackTimer) clearTimeout(this.snackTimer);
    this.snackTimer = null;
  }
}
