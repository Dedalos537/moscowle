import { Component, OnInit, OnDestroy, inject, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { forkJoin } from 'rxjs';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { ThemeService, type ThemeSchedule } from '../../../../core/services/theme.service';
import { GlobalSettingsService, COLOR_PRESETS, type FontSize } from '../../../../core/services/global-settings.service';
import { NotificationService } from '../../../../core/services/notification.service';
import { AdminService } from '../../../../core/services/admin.service';
import { HeaderService } from '../../../../core/services/header.service';

@Component({
  selector: 'app-settings',
  standalone: true,
  imports: [FontAwesomeModule],
  template: `
    <div class="settings-page">
      <div class="settings-cards-grid">
      <!-- ═══════════════════════ APARIENCIA ═══════════════════════ -->
      <section class="settings-card">
        <div class="settings-card__header">
          <div class="settings-card__icon settings-card__icon--green">
            <fa-icon [icon]="['fas', 'palette']"></fa-icon>
          </div>
          <div>
            <h2 class="settings-card__title">Apariencia</h2>
            <p class="settings-card__subtitle">Personaliza el tema visual de la plataforma</p>
          </div>
        </div>

        <div class="settings-card__body">
          <!-- Modo oscuro -->
          <div class="setting-item">
            <div class="setting-item__left">
              <div class="setting-item__icon setting-item__icon--primary">
                <fa-icon [icon]="['fas', isDark ? 'sun' : 'moon']"></fa-icon>
              </div>
              <div class="setting-item__text">
                <span class="setting-item__label">Modo oscuro</span>
                <span class="setting-item__desc">Tema visual de la plataforma</span>
              </div>
            </div>
            <button type="button" class="toggle" [class.toggle--on]="isDark" (click)="toggleDark()">
              <span class="toggle__thumb"></span>
            </button>
          </div>

          <!-- Programar modo oscuro -->
          <div class="setting-item">
            <div class="setting-item__left">
              <div class="setting-item__icon setting-item__icon--blue">
                <fa-icon [icon]="['fas', 'clock']"></fa-icon>
              </div>
              <div class="setting-item__text">
                <span class="setting-item__label">Programar modo oscuro</span>
                <span class="setting-item__desc">Cambio automático por horario</span>
              </div>
            </div>
            <button type="button" class="toggle" [class.toggle--on]="schedule.enabled" (click)="toggleSchedule()">
              <span class="toggle__thumb"></span>
            </button>
          </div>

          @if (schedule.enabled) {
            <div class="setting-item setting-item--indent">
              <div class="schedule-selects">
                <div class="schedule-field">
                  <label>De</label>
                  <select [value]="schedule.from" (change)="setScheduleFrom(+$any($event.target).value)">
                    @for (h of hours; track h) {
                      <option [value]="h">{{ h.toString().padStart(2, '0') }}:00</option>
                    }
                  </select>
                </div>
                <fa-icon [icon]="['fas', 'arrow-right']" class="schedule-arrow"></fa-icon>
                <div class="schedule-field">
                  <label>Hasta</label>
                  <select [value]="schedule.to" (change)="setScheduleTo(+$any($event.target).value)">
                    @for (h of hours; track h) {
                      <option [value]="h">{{ h.toString().padStart(2, '0') }}:00</option>
                    }
                  </select>
                </div>
              </div>
            </div>
          }

          <div class="setting-divider"></div>

          <!-- Anclar sidebar -->
          <div class="setting-item">
            <div class="setting-item__left">
              <div class="setting-item__icon setting-item__icon--primary">
                <fa-icon [icon]="['fas', 'thumbtack']"></fa-icon>
              </div>
              <div class="setting-item__text">
                <span class="setting-item__label">Anclar sidebar</span>
                <span class="setting-item__desc">Mantener menú lateral expandido</span>
              </div>
            </div>
            <button type="button" class="toggle" [class.toggle--on]="sidebarPinned()" (click)="toggleSidebarPinned()">
              <span class="toggle__thumb"></span>
            </button>
          </div>

          <div class="setting-divider"></div>

          <!-- Tamaño de fuente -->
          <div class="setting-item">
            <div class="setting-item__left">
              <div class="setting-item__icon setting-item__icon--primary">
                <fa-icon [icon]="['fas', 'text-height']"></fa-icon>
              </div>
              <div class="setting-item__text">
                <span class="setting-item__label">Tamaño de fuente</span>
                <span class="setting-item__desc">Ajusta el tamaño del texto general</span>
              </div>
            </div>
            <div class="font-size-group">
              <button type="button" class="font-btn" [class.font-btn--active]="fontSize() === 'small'" (click)="setFontSize('small')">A</button>
              <button type="button" class="font-btn font-btn--md" [class.font-btn--active]="fontSize() === 'medium'" (click)="setFontSize('medium')">A</button>
              <button type="button" class="font-btn font-btn--lg" [class.font-btn--active]="fontSize() === 'large'" (click)="setFontSize('large')">A</button>
            </div>
          </div>

          <div class="setting-divider"></div>

          <!-- Color primario -->
          <div class="setting-item setting-item--column">
            <div class="setting-item__left">
              <div class="setting-item__icon setting-item__icon--primary">
                <fa-icon [icon]="['fas', 'droplet']"></fa-icon>
              </div>
              <div class="setting-item__text">
                <span class="setting-item__label">Color primario</span>
                <span class="setting-item__desc">Color principal del panel de navegación y acentos</span>
              </div>
            </div>
            <div class="color-grid">
              @for (color of colorPresets; track color.name) {
                <button
                  type="button"
                  class="color-swatch"
                  [class.color-swatch--active]="primaryColor() === color.name"
                  [style.background]="color.light"
                  (click)="setPrimaryColor(color.name)"
                  [attr.aria-label]="color.label"
                >
                  @if (primaryColor() === color.name) {
                    <fa-icon [icon]="['fas', 'check']"></fa-icon>
                  }
                </button>
              }
            </div>
          </div>

          <div class="setting-divider"></div>

          <!-- Ocultar gráficos -->
          <div class="setting-item">
            <div class="setting-item__left">
              <div class="setting-item__icon setting-item__icon--primary">
                <fa-icon [icon]="['fas', 'chart-bar']"></fa-icon>
              </div>
              <div class="setting-item__text">
                <span class="setting-item__label">Ocultar gráficos</span>
                <span class="setting-item__desc">Reduce elementos visuales en paneles</span>
              </div>
            </div>
            <button type="button" class="toggle" [class.toggle--on]="hideCharts()" (click)="toggleHideCharts()">
              <span class="toggle__thumb"></span>
            </button>
          </div>
        </div>
      </section>

      <!-- ═══════════════════════ NOTIFICACIONES ═══════════════════════ -->
      <section class="settings-card">
        <div class="settings-card__header">
          <div class="settings-card__icon settings-card__icon--amber">
            <fa-icon [icon]="['fas', 'bell']"></fa-icon>
          </div>
          <div>
            <h2 class="settings-card__title">Notificaciones</h2>
            <p class="settings-card__subtitle">Gestiona cómo recibes las alertas</p>
          </div>
        </div>

        <div class="settings-card__body">
          <!-- Toggle maestro -->
          <div class="setting-item setting-item--highlight">
            <div class="setting-item__left">
              <div class="setting-item__icon setting-item__icon--primary">
                <fa-icon [icon]="['fas', 'bell']"></fa-icon>
              </div>
              <div class="setting-item__text">
                <span class="setting-item__label setting-item__label--bold">Activar notificaciones</span>
                <span class="setting-item__desc">Toggle maestro: On/Off</span>
              </div>
            </div>
            <button type="button" class="toggle" [class.toggle--on]="notifPrefs.notifications_enabled" (click)="toggleNotificationsGlobal()">
              <span class="toggle__thumb"></span>
            </button>
          </div>

          @if (notifPrefs.notifications_enabled) {
            <div class="setting-item">
              <div class="setting-item__left">
                <div class="setting-item__icon setting-item__icon--amber">
                  <fa-icon [icon]="['fas', 'money-bill-wave']"></fa-icon>
                </div>
                <span class="setting-item__label">Deudas</span>
              </div>
              <button type="button" class="toggle" [class.toggle--on]="notifPrefs.debt_enabled" (click)="toggleCategory('debt')">
                <span class="toggle__thumb"></span>
              </button>
            </div>

            <div class="setting-item">
              <div class="setting-item__left">
                <div class="setting-item__icon setting-item__icon--blue">
                  <fa-icon [icon]="['fas', 'calendar-alt']"></fa-icon>
                </div>
                <span class="setting-item__label">Actividad</span>
              </div>
              <button type="button" class="toggle" [class.toggle--on]="notifPrefs.activity_enabled" (click)="toggleCategory('activity')">
                <span class="toggle__thumb"></span>
              </button>
            </div>

            <div class="setting-item">
              <div class="setting-item__left">
                <div class="setting-item__icon setting-item__icon--blue">
                  <fa-icon [icon]="['fas', 'cog']"></fa-icon>
                </div>
                <span class="setting-item__label">Sistema</span>
              </div>
              <button type="button" class="toggle" [class.toggle--on]="notifPrefs.system_enabled" (click)="toggleCategory('system')">
                <span class="toggle__thumb"></span>
              </button>
            </div>

            <div class="setting-item">
              <div class="setting-item__left">
                <div class="setting-item__icon setting-item__icon--red">
                  <fa-icon [icon]="['fas', 'exclamation-triangle']"></fa-icon>
                </div>
                <span class="setting-item__label">Alertas</span>
              </div>
              <button type="button" class="toggle" [class.toggle--on]="notifPrefs.alert_enabled" (click)="toggleCategory('alert')">
                <span class="toggle__thumb"></span>
              </button>
            </div>

            <div class="setting-item">
              <div class="setting-item__left">
                <div class="setting-item__icon setting-item__icon--purple">
                  <fa-icon [icon]="['fas', 'credit-card']"></fa-icon>
                </div>
                <span class="setting-item__label">Pagos</span>
              </div>
              <button type="button" class="toggle" [class.toggle--on]="notifPrefs.payment_enabled" (click)="toggleCategory('payment')">
                <span class="toggle__thumb"></span>
              </button>
            </div>

            <div class="setting-divider"></div>

            <!-- Telegram -->
            <div class="setting-item">
              <div class="setting-item__left">
                <div class="setting-item__icon setting-item__icon--telegram">
                  <fa-icon [icon]="['fab', 'telegram']"></fa-icon>
                </div>
                <div class="setting-item__text">
                  <span class="setting-item__label">Notif. Telegram</span>
                  <span class="setting-item__desc">
                    @if (telegramLoading) { Cargando… }
                    @else if (telegramAccounts.length === 0) { Sin cuenta vinculada }
                    @else { {{ telegramAccounts.length }} cuenta(s) vinculada(s) }
                  </span>
                </div>
              </div>
              <button type="button" class="toggle"
                [disabled]="telegramLoading || telegramToggling !== null || telegramAccounts.length === 0"
                [class.toggle--on]="telegramAllEnabled()"
                (click)="toggleTelegramNotifications()">
                <span class="toggle__thumb"></span>
              </button>
            </div>

            <div class="setting-item">
              <div class="setting-item__left">
                <div class="setting-item__icon setting-item__icon--primary">
                  <fa-icon [icon]="['fas', 'volume-up']"></fa-icon>
                </div>
                <span class="setting-item__label">Sonido</span>
              </div>
              <button type="button" class="toggle" [class.toggle--on]="notifPrefs.sound_enabled" (click)="toggleSound()">
                <span class="toggle__thumb"></span>
              </button>
            </div>

            <div class="setting-item">
              <div class="setting-item__left">
                <div class="setting-item__icon setting-item__icon--primary">
                  <fa-icon [icon]="['fas', 'desktop']"></fa-icon>
                </div>
                <div class="setting-item__text">
                  <span class="setting-item__label">Notif. Escritorio</span>
                  <span class="setting-item__desc">Notificaciones del navegador</span>
                </div>
              </div>
              <button type="button" class="toggle" [class.toggle--on]="notifPrefs.browser_notifications" (click)="toggleBrowserNotif()">
                <span class="toggle__thumb"></span>
              </button>
            </div>
          }
        </div>
      </section>
      </div>

      <!-- Save button -->
      <div class="settings-save-bar">
        <button type="button" class="save-btn" (click)="saveAll()" [class.save-btn--saving]="saving" [disabled]="saving">
          @if (saving) {
            <span class="save-spinner"></span>
            <span>Guardando…</span>
          } @else if (saved) {
            <fa-icon [icon]="['fas', 'check']"></fa-icon>
            <span>Guardado</span>
          } @else {
            <fa-icon [icon]="['fas', 'save']"></fa-icon>
            <span>Guardar cambios</span>
          }
        </button>
      </div>
    </div>
  `,
  styles: [`
    .settings-page {
      max-width: 900px;
      margin: 0 auto;
      padding: 1rem 1rem 5rem;
    }

    @media (min-width: 1024px) {
      .settings-page {
        max-width: 100%;
        padding: 1.25rem 2rem 5rem;
      }
      .settings-page .settings-cards-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 1.25rem;
      }
    }

    /* ── Card ─────────────────────────────────────────────── */
    .settings-card {
      background: var(--color-surface-container-lowest);
      border: 1px solid var(--color-outline-variant);
      border-radius: 1rem;
      overflow: hidden;
      transition: border-color 0.2s;
    }
    .settings-card:hover { border-color: var(--color-outline); }

    .settings-card__header {
      display: flex; align-items: center; gap: 0.875rem;
      padding: 1.25rem 1.5rem;
      background: var(--color-surface-container-low);
      border-bottom: 1px solid var(--color-outline-variant);
    }
    .settings-card__icon {
      width: 2.5rem; height: 2.5rem; border-radius: 0.75rem;
      display: flex; align-items: center; justify-content: center;
      font-size: 0.9rem; color: var(--color-on-surface-variant);
      background: var(--color-surface-container-highest);
      flex-shrink: 0;
    }
    .settings-card__icon--green { color: var(--color-success); background: var(--color-success-container); }
    .settings-card__icon--amber { color: var(--color-warning); background: var(--color-warning-container); }
    .settings-card__title { font-size: 1rem; font-weight: 700; color: var(--color-on-surface); }
    .settings-card__subtitle { font-size: 0.78rem; color: var(--color-on-surface-variant); margin-top: 0.1rem; }

    .settings-card__body { padding: 0.25rem 0; }

    /* ── Setting row ─────────────────────────────────────── */
    .setting-item {
      display: flex; align-items: center; justify-content: space-between; gap: 1rem;
      padding: 0.875rem 1.5rem;
      transition: background 0.15s;
    }
    .setting-item:hover { background: var(--color-surface-container-low); }
    .setting-item--column { flex-direction: column; align-items: stretch; }
    .setting-item--highlight { background: var(--color-surface-container-low); }
    .setting-item--indent { padding-left: 3.5rem; }

    .setting-item__left { display: flex; align-items: center; gap: 0.75rem; min-width: 0; flex: 1; }
    .setting-item__icon {
      width: 2rem; height: 2rem; border-radius: 0.5rem;
      display: flex; align-items: center; justify-content: center;
      font-size: 0.75rem; color: var(--color-on-surface-variant);
      background: var(--color-surface-container-highest); flex-shrink: 0;
    }
    .setting-item__icon--primary { color: var(--color-primary); background: var(--color-nav-active-bg, color-mix(in srgb, var(--color-primary) 12%, transparent)); }
    .setting-item__icon--amber { color: var(--color-warning); background: var(--color-warning-container); }
    .setting-item__icon--blue { color: var(--color-info); background: var(--color-info-container); }
    .setting-item__icon--red { color: var(--color-error); background: var(--color-error-container); }
    .setting-item__icon--purple { color: #7c3aed; background: color-mix(in srgb, #7c3aed 12%, transparent); }
    .setting-item__icon--telegram { color: #229ED9; background: color-mix(in srgb, #229ED9 12%, transparent); }

    .setting-item__text { display: flex; flex-direction: column; }
    .setting-item__label { font-size: 0.875rem; font-weight: 600; color: var(--color-on-surface); }
    .setting-item__label--bold { font-weight: 700; }
    .setting-item__desc { font-size: 0.72rem; color: var(--color-on-surface-variant); margin-top: 0.1rem; }

    .setting-divider {
      height: 1px; margin: 0 1.5rem;
      background: var(--color-outline-variant);
    }

    /* ── Toggle switch ───────────────────────────────────── */
    .toggle {
      position: relative; width: 42px; height: 24px; border-radius: 999px;
      border: none; cursor: pointer; background: var(--color-outline-variant);
      transition: background 0.25s cubic-bezier(0.4, 0, 0.2, 1);
      flex-shrink: 0; padding: 0;
    }
    .toggle--on { background: var(--color-primary); }
    .toggle__thumb {
      position: absolute; top: 3px; left: 3px; width: 18px; height: 18px;
      border-radius: 50%; background: white;
      box-shadow: 0 1px 3px rgba(0,0,0,0.25);
      transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1);
    }
    .toggle--on .toggle__thumb { transform: translateX(18px); }
    .toggle:disabled { opacity: 0.35; cursor: not-allowed; }

    /* ── Schedule selects ────────────────────────────────── */
    .schedule-selects { display: flex; align-items: center; gap: 0.75rem; width: 100%; }
    .schedule-field { flex: 1; }
    .schedule-field label {
      display: block; font-size: 0.7rem; font-weight: 600;
      text-transform: uppercase; letter-spacing: 0.04em;
      color: var(--color-on-surface-variant); margin-bottom: 0.25rem;
    }
    .schedule-field select {
      width: 100%; height: 2.25rem; border-radius: 0.5rem;
      background: var(--color-surface-container-high); color: var(--color-on-surface);
      font-size: 0.85rem; padding: 0 0.5rem;
      border: 1px solid var(--color-outline-variant); outline: none; cursor: pointer;
      transition: border-color 0.15s;
    }
    .schedule-field select:focus { border-color: var(--color-primary); }
    .schedule-arrow { color: var(--color-on-surface-variant); font-size: 0.7rem; margin-top: 1.25rem; }

    /* ── Font size buttons ───────────────────────────────── */
    .font-size-group { display: flex; gap: 0.25rem; }
    .font-btn {
      width: 2.25rem; height: 2.25rem; border-radius: 0.5rem;
      border: 1.5px solid var(--color-outline-variant); background: var(--color-surface);
      color: var(--color-on-surface); cursor: pointer;
      display: flex; align-items: center; justify-content: center;
      font-weight: 600; transition: all 0.15s;
    }
    .font-btn { font-size: 0.75rem; }
    .font-btn--md { font-size: 0.9rem; }
    .font-btn--lg { font-size: 1.05rem; }
    .font-btn--active {
      background: var(--color-primary); color: var(--color-on-primary);
      border-color: var(--color-primary);
    }

    /* ── Color swatches ──────────────────────────────────── */
    .color-grid { display: flex; gap: 0.625rem; margin-top: 0.75rem; flex-wrap: wrap; }
    .color-swatch {
      width: 2.75rem; height: 2.75rem; border-radius: 50%;
      border: 3px solid transparent; cursor: pointer;
      display: flex; align-items: center; justify-content: center;
      transition: all 0.15s; box-shadow: 0 2px 6px rgba(0,0,0,0.12);
      color: white; font-size: 0.7rem;
    }
    .color-swatch:hover { transform: scale(1.12); box-shadow: 0 3px 10px rgba(0,0,0,0.2); }
    .color-swatch--active {
      border-color: var(--color-on-surface); transform: scale(1.12);
      box-shadow: 0 3px 10px rgba(0,0,0,0.2);
    }

    /* ── Save bar ────────────────────────────────────────── */
    .settings-save-bar {
      display: flex; justify-content: flex-end; padding: 0.5rem 0 2rem;
      position: sticky; bottom: 0;
    }
    .save-btn {
      display: inline-flex; align-items: center; gap: 0.5rem;
      padding: 0.75rem 1.75rem; border-radius: 0.75rem;
      border: none; cursor: pointer;
      background: var(--color-primary); color: var(--color-on-primary);
      font-size: 0.9rem; font-weight: 700;
      box-shadow: 0 2px 8px color-mix(in srgb, var(--color-primary) 35%, transparent);
      transition: all 0.2s;
    }
    .save-btn:hover { transform: translateY(-1px); box-shadow: 0 4px 16px color-mix(in srgb, var(--color-primary) 40%, transparent); }
    .save-btn:active { transform: translateY(0); }
    .save-btn:disabled { opacity: 0.7; cursor: not-allowed; transform: none; }
    .save-btn--saving { background: var(--color-on-surface-variant); }
    .save-spinner {
      width: 1rem; height: 1rem; border: 2px solid rgba(255,255,255,0.3);
      border-top-color: white; border-radius: 50%;
      animation: spin 0.6s linear infinite;
    }
    @keyframes spin { to { transform: rotate(360deg); } }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Settings implements OnInit, OnDestroy {
  private theme = inject(ThemeService);
  private settings = inject(GlobalSettingsService);
  private notifService = inject(NotificationService);
  private admin = inject(AdminService);
  private headerService = inject(HeaderService);
  private cdr = inject(ChangeDetectorRef);

  hours = Array.from({ length: 24 }, (_, i) => i);
  colorPresets = COLOR_PRESETS;

  saving = false;
  saved = false;

  get isDark() { return (this.theme.theme$ as any).value === 'dark'; }
  get schedule(): ThemeSchedule { return this.theme.getSchedule(); }
  get fontSize() { return this.settings.fontSize; }
  get primaryColor() { return this.settings.primaryColor; }
  get hideCharts() { return this.settings.hideCharts; }
  get sidebarPinned() { return this.settings.sidebarPinned; }
  get notifPrefs() { return this.notifService.preferences() || this.defaultPrefs; }

  telegramAccounts: any[] = [];
  telegramLoading = false;
  telegramToggling: number | null = null;

  private defaultPrefs = {
    notifications_enabled: true, debt_enabled: true, activity_enabled: true,
    system_enabled: true, alert_enabled: true, payment_enabled: true,
    sound_enabled: true, browser_notifications: false,
  };

  ngOnInit() {
    this.headerService.setConfig({
      title: 'Configuración',
      subtitle: 'Personaliza tu experiencia en la plataforma',
      icon: ['fas', 'cog'],
    });
  }

  ngOnDestroy() {
    this.headerService.reset();
  }

  constructor() {
    this.theme.theme$.subscribe(() => this.cdr.markForCheck());
    this.theme.schedule$.subscribe(() => this.cdr.markForCheck());
    this.loadTelegramStatus();
  }

  saveAll(): void {
    this.saving = true;
    this.cdr.markForCheck();

    const prefs = this.notifPrefs;
    this.notifService.updatePreferences({
      notifications_enabled: prefs.notifications_enabled,
      debt_enabled: prefs.debt_enabled,
      activity_enabled: prefs.activity_enabled,
      system_enabled: prefs.system_enabled,
      alert_enabled: prefs.alert_enabled,
      payment_enabled: prefs.payment_enabled,
      sound_enabled: prefs.sound_enabled,
      browser_notifications: prefs.browser_notifications,
    }).subscribe({
      next: () => {
        this.saving = false;
        this.saved = true;
        this.cdr.markForCheck();
        setTimeout(() => { this.saved = false; this.cdr.markForCheck(); }, 2500);
      },
      error: () => {
        this.saving = false;
        this.cdr.markForCheck();
      },
    });
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

  toggleSidebarPinned(): void {
    this.settings.setSidebarPinned(!this.sidebarPinned());
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
