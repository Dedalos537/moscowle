import { Component, inject, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { forkJoin } from 'rxjs';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { ThemeService, type ThemeSchedule } from '../../../../core/services/theme.service';
import { GlobalSettingsService, COLOR_PRESETS, type FontSize } from '../../../../core/services/global-settings.service';
import { NotificationService } from '../../../../core/services/notification.service';
import { AdminService } from '../../../../core/services/admin.service';

@Component({
  selector: 'app-settings',
  standalone: true,
  imports: [FontAwesomeModule],
  template: `
    <div class="settings-page">
      <div class="settings-header">
        <h1 class="text-h3 font-bold text-on-surface">Configuración</h1>
        <p class="text-body-sm text-on-surface-variant mt-1">Personaliza tu experiencia en la plataforma</p>
      </div>

      <!-- ═══════════════════════ APARIENCIA ═══════════════════════ -->
      <section class="settings-section">
        <h2 class="settings-section__title">
          <fa-icon [icon]="['fas', 'palette']" class="text-primary"></fa-icon>
          Apariencia
        </h2>

        <!-- Modo oscuro -->
        <div class="settings-row">
          <div class="settings-row__info">
            <div class="settings-row__icon bg-surface-container-low">
              <fa-icon [icon]="['fas', isDark ? 'sun' : 'moon']" class="text-on-surface-variant"></fa-icon>
            </div>
            <div>
              <p class="settings-row__label">Modo oscuro</p>
              <p class="settings-row__desc">Tema visual de la plataforma</p>
            </div>
          </div>
          <button type="button" class="pref-switch" (click)="toggleDark()" [class.pref-switch--on]="isDark">
            <span class="pref-switch__knob"></span>
          </button>
        </div>

        <!-- Programar modo oscuro -->
        <div class="settings-row">
          <div class="settings-row__info">
            <div class="settings-row__icon bg-surface-container-low">
              <fa-icon [icon]="['fas', 'clock']" class="text-primary"></fa-icon>
            </div>
            <div>
              <p class="settings-row__label">Programar modo oscuro</p>
              <p class="settings-row__desc">Cambio automático por horario</p>
            </div>
          </div>
          <button type="button" class="pref-switch" (click)="toggleSchedule()" [class.pref-switch--on]="schedule.enabled">
            <span class="pref-switch__knob"></span>
          </button>
        </div>

        @if (schedule.enabled) {
          <div class="settings-schedule-row">
            <div class="settings-schedule-select">
              <label class="text-xs font-medium text-on-surface-variant">De</label>
              <select [value]="schedule.from" (change)="setScheduleFrom(+$any($event.target).value)">
                @for (h of hours; track h) {
                  <option [value]="h">{{ h.toString().padStart(2, '0') }}:00</option>
                }
              </select>
            </div>
            <fa-icon [icon]="['fas', 'arrow-right']" class="text-on-surface-variant text-xs mt-4"></fa-icon>
            <div class="settings-schedule-select">
              <label class="text-xs font-medium text-on-surface-variant">Hasta</label>
              <select [value]="schedule.to" (change)="setScheduleTo(+$any($event.target).value)">
                @for (h of hours; track h) {
                  <option [value]="h">{{ h.toString().padStart(2, '0') }}:00</option>
                }
              </select>
            </div>
          </div>
        }

        <!-- Tamaño de fuente -->
        <div class="settings-row">
          <div class="settings-row__info">
            <div class="settings-row__icon bg-surface-container-low">
              <fa-icon [icon]="['fas', 'text-height']" class="text-on-surface-variant"></fa-icon>
            </div>
            <div>
              <p class="settings-row__label">Tamaño de fuente</p>
              <p class="settings-row__desc">Ajusta el tamaño del texto general</p>
            </div>
          </div>
          <div class="settings-chip-group">
            <button type="button" class="settings-chip" [class.settings-chip--active]="fontSize() === 'small'" (click)="setFontSize('small')">A</button>
            <button type="button" class="settings-chip settings-chip--md" [class.settings-chip--active]="fontSize() === 'medium'" (click)="setFontSize('medium')">A</button>
            <button type="button" class="settings-chip settings-chip--lg" [class.settings-chip--active]="fontSize() === 'large'" (click)="setFontSize('large')">A</button>
          </div>
        </div>

        <!-- Color primario -->
        <div class="settings-row settings-row--column">
          <div class="settings-row__info">
            <div class="settings-row__icon bg-surface-container-low">
              <fa-icon [icon]="['fas', 'droplet']" class="text-on-surface-variant"></fa-icon>
            </div>
            <div>
              <p class="settings-row__label">Color primario</p>
              <p class="settings-row__desc">Color principal del panel de navegación y acentos</p>
            </div>
          </div>
          <div class="settings-color-grid">
            @for (color of colorPresets; track color.name) {
              <button
                type="button"
                class="settings-color-swatch"
                [class.settings-color-swatch--active]="primaryColor() === color.name"
                [style.background]="color.light"
                (click)="setPrimaryColor(color.name)"
                [attr.aria-label]="color.label"
              >
                @if (primaryColor() === color.name) {
                  <fa-icon [icon]="['fas', 'check']" class="text-white text-xs"></fa-icon>
                }
              </button>
            }
          </div>
        </div>

        <!-- Ocultar gráficos -->
        <div class="settings-row">
          <div class="settings-row__info">
            <div class="settings-row__icon bg-surface-container-low">
              <fa-icon [icon]="['fas', 'chart-bar']" class="text-on-surface-variant"></fa-icon>
            </div>
            <div>
              <p class="settings-row__label">Ocultar gráficos</p>
              <p class="settings-row__desc">Reduce elementos visuales en paneles</p>
            </div>
          </div>
          <button type="button" class="pref-switch" (click)="toggleHideCharts()" [class.pref-switch--on]="hideCharts()">
            <span class="pref-switch__knob"></span>
          </button>
        </div>
      </section>

      <!-- ═══════════════════════ NOTIFICACIONES ═══════════════════════ -->
      <section class="settings-section">
        <h2 class="settings-section__title">
          <fa-icon [icon]="['fas', 'bell']" class="text-primary"></fa-icon>
          Notificaciones
        </h2>

        <!-- Toggle maestro -->
        <div class="settings-row settings-row--highlight">
          <div class="settings-row__info">
            <div class="settings-row__icon bg-primary/10">
              <fa-icon [icon]="['fas', 'bell']" class="text-primary"></fa-icon>
            </div>
            <div>
              <p class="settings-row__label font-bold">Activar notificaciones</p>
              <p class="settings-row__desc">Toggle maestro: On/Off</p>
            </div>
          </div>
          <button type="button" class="pref-switch" (click)="toggleNotificationsGlobal()" [class.pref-switch--on]="notifPrefs.notifications_enabled">
            <span class="pref-switch__knob"></span>
          </button>
        </div>

        @if (notifPrefs.notifications_enabled) {
          <!-- Deudas -->
          <div class="settings-row">
            <div class="settings-row__info">
              <div class="settings-row__icon bg-warning/10">
                <fa-icon [icon]="['fas', 'money-bill-wave']" class="text-warning"></fa-icon>
              </div>
              <p class="settings-row__label">Deudas</p>
            </div>
            <button type="button" class="pref-switch" (click)="toggleCategory('debt')" [class.pref-switch--on]="notifPrefs.debt_enabled">
              <span class="pref-switch__knob"></span>
            </button>
          </div>

          <!-- Actividad -->
          <div class="settings-row">
            <div class="settings-row__info">
              <div class="settings-row__icon bg-info/10">
                <fa-icon [icon]="['fas', 'calendar-alt']" class="text-info"></fa-icon>
              </div>
              <p class="settings-row__label">Actividad</p>
            </div>
            <button type="button" class="pref-switch" (click)="toggleCategory('activity')" [class.pref-switch--on]="notifPrefs.activity_enabled">
              <span class="pref-switch__knob"></span>
            </button>
          </div>

          <!-- Sistema -->
          <div class="settings-row">
            <div class="settings-row__info">
              <div class="settings-row__icon bg-surface-container-low">
                <fa-icon [icon]="['fas', 'cog']" class="text-primary"></fa-icon>
              </div>
              <p class="settings-row__label">Sistema</p>
            </div>
            <button type="button" class="pref-switch" (click)="toggleCategory('system')" [class.pref-switch--on]="notifPrefs.system_enabled">
              <span class="pref-switch__knob"></span>
            </button>
          </div>

          <!-- Alertas -->
          <div class="settings-row">
            <div class="settings-row__info">
              <div class="settings-row__icon bg-error/10">
                <fa-icon [icon]="['fas', 'exclamation-triangle']" class="text-error"></fa-icon>
              </div>
              <p class="settings-row__label">Alertas</p>
            </div>
            <button type="button" class="pref-switch" (click)="toggleCategory('alert')" [class.pref-switch--on]="notifPrefs.alert_enabled">
              <span class="pref-switch__knob"></span>
            </button>
          </div>

          <!-- Pagos -->
          <div class="settings-row">
            <div class="settings-row__info">
              <div class="settings-row__icon bg-tertiary/10">
                <fa-icon [icon]="['fas', 'credit-card']" class="text-tertiary"></fa-icon>
              </div>
              <p class="settings-row__label">Pagos</p>
            </div>
            <button type="button" class="pref-switch" (click)="toggleCategory('payment')" [class.pref-switch--on]="notifPrefs.payment_enabled">
              <span class="pref-switch__knob"></span>
            </button>
          </div>

          <!-- Telegram -->
          <div class="settings-row">
            <div class="settings-row__info">
              <div class="settings-row__icon bg-[#229ED9]/15">
                <fa-icon [icon]="['fab', 'telegram']" class="text-[#229ED9]"></fa-icon>
              </div>
              <div>
                <p class="settings-row__label">Notif. Telegram</p>
                <p class="settings-row__desc">
                  @if (telegramLoading) { Cargando… }
                  @else if (telegramAccounts.length === 0) { Sin cuenta vinculada }
                  @else { {{ telegramAccounts.length }} cuenta(s) vinculada(s) }
                </p>
              </div>
            </div>
            <button type="button" class="pref-switch"
              [disabled]="telegramLoading || telegramToggling !== null || telegramAccounts.length === 0"
              (click)="toggleTelegramNotifications()"
              [class.pref-switch--on]="telegramAllEnabled()">
              <span class="pref-switch__knob"></span>
            </button>
          </div>

          <!-- Sonido -->
          <div class="settings-row">
            <div class="settings-row__info">
              <div class="settings-row__icon bg-surface-container-low">
                <fa-icon [icon]="['fas', 'volume-up']" class="text-on-surface-variant"></fa-icon>
              </div>
              <p class="settings-row__label">Sonido</p>
            </div>
            <button type="button" class="pref-switch" (click)="toggleSound()" [class.pref-switch--on]="notifPrefs.sound_enabled">
              <span class="pref-switch__knob"></span>
            </button>
          </div>

          <!-- Notificaciones del navegador -->
          <div class="settings-row">
            <div class="settings-row__info">
              <div class="settings-row__icon bg-surface-container-low">
                <fa-icon [icon]="['fas', 'desktop']" class="text-on-surface-variant"></fa-icon>
              </div>
              <div>
                <p class="settings-row__label">Notif. Escritorio</p>
                <p class="settings-row__desc">Notificaciones del navegador</p>
              </div>
            </div>
            <button type="button" class="pref-switch" (click)="toggleBrowserNotif()" [class.pref-switch--on]="notifPrefs.browser_notifications">
              <span class="pref-switch__knob"></span>
            </button>
          </div>
        }
      </section>
    </div>
  `,
  styles: [`
    .settings-page {
      max-width: 720px;
      margin: 0 auto;
      padding: 2rem 1.5rem 4rem;
    }
    .settings-header { margin-bottom: 2rem; }

    .settings-section {
      background: var(--color-surface-container-lowest);
      border: 1px solid var(--color-border);
      border-radius: var(--radius-xl);
      padding: 1.5rem;
      margin-bottom: 1.5rem;
    }
    .settings-section__title {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      font-size: 0.8rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--color-on-surface-variant);
      margin-bottom: 1rem;
      padding-bottom: 0.75rem;
      border-bottom: 1px solid var(--color-outline-variant);
    }

    .settings-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 1rem;
      padding: 0.75rem 0.5rem;
      border-radius: var(--radius-lg);
      transition: background var(--transition-fast);
    }
    .settings-row:hover { background: var(--color-surface-container-low); }
    .settings-row--column { flex-direction: column; align-items: stretch; }
    .settings-row--highlight { background: var(--color-surface-container-low); }
    .settings-row__info { display: flex; align-items: center; gap: 0.75rem; min-width: 0; flex: 1; }
    .settings-row__icon {
      width: 2.25rem; height: 2.25rem; border-radius: var(--radius-md);
      display: flex; align-items: center; justify-content: center; flex-shrink: 0;
      font-size: 0.8rem;
    }
    .settings-row__label { font-size: 0.9rem; font-weight: 600; color: var(--color-on-surface); }
    .settings-row__desc { font-size: 0.75rem; color: var(--color-on-surface-variant); margin-top: 0.1rem; }

    .pref-switch {
      position: relative; width: 40px; height: 22px; border-radius: 999px;
      border: none; cursor: pointer; background: var(--color-outline-variant);
      transition: background 0.2s; flex-shrink: 0; padding: 0;
    }
    .pref-switch--on { background: var(--color-primary); }
    .pref-switch__knob {
      position: absolute; top: 2px; left: 2px; width: 18px; height: 18px;
      border-radius: 50%; background: white; box-shadow: 0 1px 3px rgba(0,0,0,0.2);
      transition: transform 0.2s;
    }
    .pref-switch--on .pref-switch__knob { transform: translateX(18px); }
    .pref-switch:disabled { opacity: 0.4; cursor: not-allowed; }

    .settings-schedule-row {
      display: flex; align-items: center; gap: 0.75rem;
      padding: 0 0.5rem 0.75rem;
    }
    .settings-schedule-select { flex: 1; }
    .settings-schedule-select select {
      width: 100%; margin-top: 0.25rem; height: 2.25rem; border-radius: var(--radius-md);
      background: var(--color-surface-container-low); color: var(--color-on-surface);
      font-size: 0.85rem; padding: 0 0.5rem; border: 1px solid var(--color-outline-variant);
      outline: none; cursor: pointer;
    }
    .settings-schedule-select select:focus { border-color: var(--color-primary); }

    .settings-chip-group { display: flex; gap: 0.375rem; }
    .settings-chip {
      width: 2rem; height: 2rem; border-radius: var(--radius-md); border: 1px solid var(--color-outline-variant);
      background: var(--color-surface); color: var(--color-on-surface); cursor: pointer;
      display: flex; align-items: center; justify-content: center; font-weight: 600;
      transition: all 0.15s;
    }
    .settings-chip { font-size: 0.75rem; }
    .settings-chip--md { font-size: 0.9rem; }
    .settings-chip--lg { font-size: 1.05rem; }
    .settings-chip--active {
      background: var(--color-primary); color: var(--color-on-primary); border-color: var(--color-primary);
    }

    .settings-color-grid {
      display: flex; gap: 0.75rem; margin-top: 0.75rem; flex-wrap: wrap;
    }
    .settings-color-swatch {
      width: 2.5rem; height: 2.5rem; border-radius: 50%; border: 3px solid transparent;
      cursor: pointer; display: flex; align-items: center; justify-content: center;
      transition: all 0.15s; box-shadow: 0 1px 3px rgba(0,0,0,0.15);
    }
    .settings-color-swatch:hover { transform: scale(1.15); }
    .settings-color-swatch--active { border-color: var(--color-on-surface); transform: scale(1.15); }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Settings {
  private theme = inject(ThemeService);
  private settings = inject(GlobalSettingsService);
  private notifService = inject(NotificationService);
  private admin = inject(AdminService);
  private cdr = inject(ChangeDetectorRef);

  hours = Array.from({ length: 24 }, (_, i) => i);
  colorPresets = COLOR_PRESETS;

  get isDark() { return (this.theme.theme$ as any).value === 'dark'; }
  get schedule(): ThemeSchedule { return this.theme.getSchedule(); }
  get fontSize() { return this.settings.fontSize; }
  get primaryColor() { return this.settings.primaryColor; }
  get hideCharts() { return this.settings.hideCharts; }
  get notifPrefs() { return this.notifService.preferences() || this.defaultPrefs; }

  telegramAccounts: any[] = [];
  telegramLoading = false;
  telegramToggling: number | null = null;

  private defaultPrefs = {
    notifications_enabled: true, debt_enabled: true, activity_enabled: true,
    system_enabled: true, alert_enabled: true, payment_enabled: true,
    sound_enabled: true, browser_notifications: false,
  };

  constructor() {
    this.theme.theme$.subscribe(() => this.cdr.markForCheck());
    this.theme.schedule$.subscribe(() => this.cdr.markForCheck());
    this.loadTelegramStatus();
  }

  toggleDark(): void {
    this.theme.toggle();
    this.settings.reapplyPrimaryColor();
    this.cdr.markForCheck();
  }

  toggleSchedule(): void {
    const s = this.theme.getSchedule();
    this.theme.setSchedule({ ...s, enabled: !s.enabled });
    this.cdr.markForCheck();
  }

  setScheduleFrom(hour: number): void {
    this.theme.setSchedule({ ...this.theme.getSchedule(), from: hour });
    this.cdr.markForCheck();
  }

  setScheduleTo(hour: number): void {
    this.theme.setSchedule({ ...this.theme.getSchedule(), to: hour });
    this.cdr.markForCheck();
  }

  setFontSize(size: FontSize): void {
    this.settings.setFontSize(size);
    this.cdr.markForCheck();
  }

  setPrimaryColor(name: string): void {
    this.settings.setPrimaryColor(name);
    this.cdr.markForCheck();
  }

  toggleHideCharts(): void {
    this.settings.toggleHideCharts();
    this.cdr.markForCheck();
  }

  toggleNotificationsGlobal(): void {
    const prefs = this.notifPrefs;
    this.notifService.updatePreferences({ notifications_enabled: !prefs.notifications_enabled }).subscribe(() => {
      this.cdr.markForCheck();
    });
  }

  toggleCategory(cat: string): void {
    const prefs = this.notifPrefs;
    const key = `${cat}_enabled` as keyof typeof prefs;
    this.notifService.updatePreferences({ [key]: !(prefs as any)[key] } as any).subscribe(() => {
      this.cdr.markForCheck();
    });
  }

  toggleSound(): void {
    const prefs = this.notifPrefs;
    this.notifService.updatePreferences({ sound_enabled: !prefs.sound_enabled }).subscribe(() => {
      this.cdr.markForCheck();
    });
  }

  toggleBrowserNotif(): void {
    const prefs = this.notifPrefs;
    const newVal = !prefs.browser_notifications;
    if (newVal) this.notifService.requestBrowserPermission();
    this.notifService.updatePreferences({ browser_notifications: newVal }).subscribe(() => {
      this.cdr.markForCheck();
    });
  }

  loadTelegramStatus(): void {
    this.telegramLoading = true;
    this.admin.getTelegramStatus().subscribe({
      next: (res: any) => {
        this.telegramAccounts = (res?.linked_accounts || []).filter((a: any) => a.is_linked);
        this.telegramLoading = false;
        this.cdr.markForCheck();
      },
      error: () => {
        this.telegramAccounts = [];
        this.telegramLoading = false;
        this.cdr.markForCheck();
      },
    });
  }

  telegramAllEnabled(): boolean {
    return this.telegramAccounts.length > 0 && this.telegramAccounts.every((a: any) => a.notifications_enabled);
  }

  toggleTelegramNotifications(): void {
    if (this.telegramAccounts.length === 0 || this.telegramToggling !== null) return;
    const target = !this.telegramAllEnabled();
    const chain: import('rxjs').Observable<any>[] = [];
    for (const acc of this.telegramAccounts) {
      if (acc.notifications_enabled !== target) {
        chain.push(this.admin.toggleTelegramNotifications(acc.telegram_chat_id, target));
      }
    }
    if (chain.length === 0) return;
    this.telegramToggling = 1;
    this.cdr.markForCheck();
    forkJoin(chain).subscribe({
      next: () => { this.telegramToggling = null; this.loadTelegramStatus(); },
      error: () => { this.telegramToggling = null; this.loadTelegramStatus(); },
    });
  }
}
