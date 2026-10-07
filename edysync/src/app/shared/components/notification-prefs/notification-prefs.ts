import { Component, ChangeDetectionStrategy, ChangeDetectorRef, OnDestroy, OnInit, computed, inject, input, output, signal } from '@angular/core';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import type { IconProp } from '@fortawesome/fontawesome-svg-core';
import { Subscription } from 'rxjs';
import { NotificationService } from '../../../core/services/notification.service';
import { AdminService } from '../../../core/services/admin.service';
import { LiveSyncService } from '../../../core/services/live-sync.service';
import { ToastService } from '../../../core/services/toast.service';
import type { NotificationPreferences } from '../../../core/models/notification';
import { Switch } from '../switch/switch';

interface Category {
  key: keyof NotificationPreferences;
  label: string;
  hint: string;
  icon: IconProp;
}

/**
 * Preferencias de notificación: cada interruptor se guarda al instante (sin botón «Guardar»), muestra el resultado
 * y se vuelve a cargar solo si el cambio se hizo en otra pestaña o dispositivo.
 */
@Component({
  selector: 'app-notification-prefs',
  standalone: true,
  imports: [FontAwesomeModule, Switch],
  templateUrl: './notification-prefs.html',
  styleUrl: './notification-prefs.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class NotificationPrefs implements OnInit, OnDestroy {
  /** Los administradores ven el atajo a la configuración de WhatsApp y SMS. */
  isAdmin = input(false);
  openChannels = output<void>();

  private notif = inject(NotificationService);
  private admin = inject(AdminService);
  private live = inject(LiveSyncService);
  private toast = inject(ToastService);
  private cdr = inject(ChangeDetectorRef);
  private subs = new Subscription();
  private savedTimer: ReturnType<typeof setTimeout> | null = null;

  readonly categories: Category[] = [
    { key: 'debt_enabled', label: 'Deudas', hint: 'Pagos vencidos y recordatorios de cobranza', icon: ['fas', 'money-bill-wave'] },
    { key: 'payment_enabled', label: 'Pagos', hint: 'Pagos registrados y confirmaciones', icon: ['fas', 'credit-card'] },
    { key: 'activity_enabled', label: 'Actividad', hint: 'Sesiones, mensajes, juegos y auditorías', icon: ['fas', 'calendar-days'] },
    { key: 'alert_enabled', label: 'Alertas', hint: 'Incidencias y eventos urgentes', icon: ['fas', 'triangle-exclamation'] },
    { key: 'system_enabled', label: 'Sistema', hint: 'Avisos del sistema, reportes y recordatorios', icon: ['fas', 'gear'] },
  ];

  readonly digestChannels: { value: NotificationPreferences['digest_channel']; label: string }[] = [
    { value: 'both', label: 'Correo y Telegram' },
    { value: 'email', label: 'Solo correo' },
    { value: 'telegram', label: 'Solo Telegram' },
  ];

  prefs = computed(() => this.notif.preferences() ?? this.notif.defaultPrefs);
  masterOn = computed(() => this.prefs().notifications_enabled !== false);

  saving = signal(false);
  justSaved = signal(false);

  telegramAccounts: { telegram_chat_id: number; notifications_enabled: boolean; label: string }[] = [];
  telegramBusy = false;

  ngOnInit() {
    this.notif.fetchPreferences();
    this.loadTelegram();
    // Cambios hechos en otra pestaña o dispositivo: se recarga sola.
    this.subs.add(
      this.live.watch(['notif_prefs']).subscribe(() => {
        this.notif.fetchPreferences();
        this.loadTelegram();
      }),
    );
  }

  ngOnDestroy() {
    this.subs.unsubscribe();
    if (this.savedTimer) clearTimeout(this.savedTimer);
  }

  set(key: keyof NotificationPreferences, value: boolean | string) {
    if (key === 'browser_notifications' && value === true) this.notif.requestBrowserPermission();
    this.saving.set(true);
    this.notif.updatePreferences({ [key]: value } as Partial<NotificationPreferences>).subscribe({
      next: () => {
        this.saving.set(false);
        this.flashSaved();
      },
      error: (err) => {
        this.saving.set(false);
        this.toast.show(err?.error?.message || 'No se pudo guardar el cambio. Se restauró el valor anterior.', 'error');
      },
    });
  }

  private flashSaved() {
    this.justSaved.set(true);
    if (this.savedTimer) clearTimeout(this.savedTimer);
    this.savedTimer = setTimeout(() => this.justSaved.set(false), 1800);
  }

  // ── Telegram ─────────────────────────────────────────────────────────────
  private loadTelegram() {
    this.admin.getTelegramStatus().subscribe({
      next: (res: any) => {
        this.telegramAccounts = (res?.linked_accounts || [])
          .filter((a: any) => a.is_linked)
          .map((a: any) => ({
            telegram_chat_id: a.telegram_chat_id,
            notifications_enabled: !!a.notifications_enabled,
            label: a.telegram_username ? '@' + a.telegram_username : a.telegram_first_name || 'Cuenta de Telegram',
          }));
        this.cdr.markForCheck();
      },
      error: () => {
        this.telegramAccounts = [];
        this.cdr.markForCheck();
      },
    });
  }

  get telegramAllOn(): boolean {
    return this.telegramAccounts.length > 0 && this.telegramAccounts.every((a) => a.notifications_enabled);
  }

  toggleTelegram(chatId: number, enabled: boolean) {
    const acc = this.telegramAccounts.find((a) => a.telegram_chat_id === chatId);
    if (!acc || this.telegramBusy) return;
    acc.notifications_enabled = enabled; // optimista
    this.telegramBusy = true;
    this.cdr.markForCheck();
    this.admin.toggleTelegramNotifications(chatId, enabled).subscribe({
      next: () => {
        this.telegramBusy = false;
        this.flashSaved();
        this.cdr.markForCheck();
      },
      error: () => {
        acc.notifications_enabled = !enabled;
        this.telegramBusy = false;
        this.toast.show('No se pudo cambiar la notificación de Telegram.', 'error');
        this.cdr.markForCheck();
      },
    });
  }
}
