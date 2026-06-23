import {
  Component,
  inject,
  signal,
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  input,
  HostListener,
  ElementRef,
} from '@angular/core';
import { AsyncPipe } from '@angular/common';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { ThemeService } from '../../../core/services/theme.service';
import { GlobalSettingsService } from '../../../core/services/global-settings.service';
import { NotificationService } from '../../../core/services/notification.service';
import { AuthService } from '../../../core/services/auth.service';
import { NotificationPreferences } from '../../../core/models/notification';

@Component({
  selector: 'app-preferences-menu',
  standalone: true,
  imports: [FontAwesomeModule, AsyncPipe],
  template: `
    <div class="relative">
      <button
        type="button"
        (click)="toggle($event)"
        class="w-10 h-10 rounded-xl bg-surface-container-low text-on-surface-variant flex items-center justify-center hover:bg-surface-container-high transition-colors focus:outline-none focus:ring-2 focus:ring-primary-container/30 shadow-soft border border-border/50"
        [class.w-11]="fixed()"
        [class.h-11]="fixed()"
        title="Configuración"
        aria-label="Configuración"
      >
        <fa-icon [icon]="['fas', 'sliders-h']"></fa-icon>
      </button>

      @if (open) {
        <div
          class="absolute right-0 mt-3 w-80 bg-surface-container-lowest/95 backdrop-blur-xl rounded-xl shadow-soft border border-border/50 z-50 flex flex-col animate-fade-in"
          (click)="$event.stopPropagation()"
        >
          <div class="p-4 border-b border-border/30 flex justify-between items-center bg-surface-container-low/80 rounded-t-xl">
            <h3 class="text-sm font-bold text-on-surface">Configuración</h3>
            <button
              type="button"
              (click)="close()"
              class="w-8 h-8 rounded-full flex items-center justify-center text-on-surface-variant hover:bg-surface-container-high transition-colors"
              aria-label="Cerrar configuración"
            >
              <fa-icon [icon]="['fas', 'times']" class="text-sm"></fa-icon>
            </button>
          </div>

          <div class="p-3 space-y-1 max-h-[60vh] overflow-y-auto">
            <div class="flex items-center justify-between gap-3 px-3 py-3 rounded-xl hover:bg-surface-container-low/60 transition-colors">
              <div class="flex items-center gap-3 min-w-0">
                <div class="w-8 h-8 rounded-lg bg-surface-container-low flex items-center justify-center shrink-0">
                  @if ((theme.theme$ | async) === 'dark') {
                    <fa-icon [icon]="['fas', 'sun']" class="text-warning text-sm"></fa-icon>
                  } @else {
                    <fa-icon [icon]="['fas', 'moon']" class="text-on-surface-variant text-sm"></fa-icon>
                  }
                </div>
                <div class="min-w-0">
                  <p class="text-sm font-semibold text-on-surface">Modo oscuro</p>
                  <p class="text-xs text-on-surface-variant">Tema visual de la plataforma</p>
                </div>
              </div>
              <button
                type="button"
                class="pref-switch"
                (click)="toggleDark()"
                [class.pref-switch--on]="(theme.theme$ | async) === 'dark'"
                [attr.aria-label]="(theme.theme$ | async) === 'dark' ? 'Desactivar modo oscuro' : 'Activar modo oscuro'"
              >
                <span class="pref-switch__knob"></span>
              </button>
            </div>

            <div class="flex items-center justify-between gap-3 px-3 py-3 rounded-xl hover:bg-surface-container-low/60 transition-colors">
              <div class="flex items-center gap-3 min-w-0">
                <div class="w-8 h-8 rounded-lg bg-surface-container-low flex items-center justify-center shrink-0">
                  <fa-icon [icon]="['fas', 'chart-bar']" class="text-on-surface-variant text-sm"></fa-icon>
                </div>
                <div class="min-w-0">
                  <p class="text-sm font-semibold text-on-surface">Ocultar gráficos</p>
                  <p class="text-xs text-on-surface-variant">Reduce elementos visuales en paneles</p>
                </div>
              </div>
              <button
                type="button"
                class="pref-switch"
                (click)="toggleCharts()"
                [class.pref-switch--on]="hideCharts()"
                [attr.aria-label]="hideCharts() ? 'Mostrar gráficos' : 'Ocultar gráficos'"
              >
                <span class="pref-switch__knob"></span>
              </button>
            </div>

            @if (userRole() === 'admin') {
              <div class="border-t border-border/20 pt-3 mt-3">
                <div class="px-3 mb-2">
                  <p class="text-xs font-bold text-on-surface uppercase tracking-wider">Notificaciones</p>
                </div>

                <div class="flex items-center justify-between gap-3 px-3 py-3 rounded-xl hover:bg-surface-container-low/60 transition-colors">
                  <div class="flex items-center gap-3 min-w-0">
                    <div class="w-8 h-8 rounded-lg bg-warning-container flex items-center justify-center shrink-0">
                      <fa-icon [icon]="['fas', 'money-bill-wave']" class="text-warning text-sm"></fa-icon>
                    </div>
                    <p class="text-sm font-semibold text-on-surface">Deudas</p>
                  </div>
                  <button
                    type="button"
                    class="pref-switch"
                    (click)="toggleCategory('debt')"
                    [class.pref-switch--on]="prefs.debt_enabled"
                  >
                    <span class="pref-switch__knob"></span>
                  </button>
                </div>

                <div class="flex items-center justify-between gap-3 px-3 py-3 rounded-xl hover:bg-surface-container-low/60 transition-colors">
                  <div class="flex items-center gap-3 min-w-0">
                    <div class="w-8 h-8 rounded-lg bg-info/10 flex items-center justify-center shrink-0">
                      <fa-icon [icon]="['fas', 'calendar-alt']" class="text-info text-sm"></fa-icon>
                    </div>
                    <p class="text-sm font-semibold text-on-surface">Actividad</p>
                  </div>
                  <button
                    type="button"
                    class="pref-switch"
                    (click)="toggleCategory('activity')"
                    [class.pref-switch--on]="prefs.activity_enabled"
                  >
                    <span class="pref-switch__knob"></span>
                  </button>
                </div>

                <div class="flex items-center justify-between gap-3 px-3 py-3 rounded-xl hover:bg-surface-container-low/60 transition-colors">
                  <div class="flex items-center gap-3 min-w-0">
                    <div class="w-8 h-8 rounded-lg bg-surface-container-low flex items-center justify-center shrink-0">
                      <fa-icon [icon]="['fas', 'cog']" class="text-primary text-sm"></fa-icon>
                    </div>
                    <p class="text-sm font-semibold text-on-surface">Sistema</p>
                  </div>
                  <button
                    type="button"
                    class="pref-switch"
                    (click)="toggleCategory('system')"
                    [class.pref-switch--on]="prefs.system_enabled"
                  >
                    <span class="pref-switch__knob"></span>
                  </button>
                </div>

                <div class="flex items-center justify-between gap-3 px-3 py-3 rounded-xl hover:bg-surface-container-low/60 transition-colors">
                  <div class="flex items-center gap-3 min-w-0">
                    <div class="w-8 h-8 rounded-lg bg-error-container flex items-center justify-center shrink-0">
                      <fa-icon [icon]="['fas', 'exclamation-triangle']" class="text-error text-sm"></fa-icon>
                    </div>
                    <p class="text-sm font-semibold text-on-surface">Alertas</p>
                  </div>
                  <button
                    type="button"
                    class="pref-switch"
                    (click)="toggleCategory('alert')"
                    [class.pref-switch--on]="prefs.alert_enabled"
                  >
                    <span class="pref-switch__knob"></span>
                  </button>
                </div>

                <div class="flex items-center justify-between gap-3 px-3 py-3 rounded-xl hover:bg-surface-container-low/60 transition-colors">
                  <div class="flex items-center gap-3 min-w-0">
                    <div class="w-8 h-8 rounded-lg bg-tertiary-container flex items-center justify-center shrink-0">
                      <fa-icon [icon]="['fas', 'credit-card']" class="text-tertiary text-sm"></fa-icon>
                    </div>
                    <p class="text-sm font-semibold text-on-surface">Pagos</p>
                  </div>
                  <button
                    type="button"
                    class="pref-switch"
                    (click)="toggleCategory('payment')"
                    [class.pref-switch--on]="prefs.payment_enabled"
                  >
                    <span class="pref-switch__knob"></span>
                  </button>
                </div>

                <div class="border-t border-border/10 pt-2 mt-2 space-y-1">
                  <div class="flex items-center justify-between gap-3 px-3 py-3 rounded-xl hover:bg-surface-container-low/60 transition-colors">
                    <div class="flex items-center gap-3 min-w-0">
                      <div class="w-8 h-8 rounded-lg bg-surface-container-low flex items-center justify-center shrink-0">
                        <fa-icon [icon]="['fas', 'volume-up']" class="text-on-surface-variant text-sm"></fa-icon>
                      </div>
                      <p class="text-sm font-semibold text-on-surface">Sonido</p>
                    </div>
                    <button
                      type="button"
                      class="pref-switch"
                      (click)="toggleSound()"
                      [class.pref-switch--on]="prefs.sound_enabled"
                    >
                      <span class="pref-switch__knob"></span>
                    </button>
                  </div>

                  <div class="flex items-center justify-between gap-3 px-3 py-3 rounded-xl hover:bg-surface-container-low/60 transition-colors">
                    <div class="flex items-center gap-3 min-w-0">
                      <div class="w-8 h-8 rounded-lg bg-surface-container-low flex items-center justify-center shrink-0">
                        <fa-icon [icon]="['fas', 'desktop']" class="text-on-surface-variant text-sm"></fa-icon>
                      </div>
                      <div class="min-w-0">
                        <p class="text-sm font-semibold text-on-surface">Notif. Escritorio</p>
                        <p class="text-xs text-on-surface-variant">Notificaciones del navegador</p>
                      </div>
                    </div>
                    <button
                      type="button"
                      class="pref-switch"
                      (click)="toggleBrowserNotif()"
                      [class.pref-switch--on]="prefs.browser_notifications"
                    >
                      <span class="pref-switch__knob"></span>
                    </button>
                  </div>
                </div>
              </div>
            }
          </div>
        </div>
      }
    </div>
  `,
  host: {
    '[class.preferences-menu--fixed]': 'fixed()',
  },
  styles: [`
    :host(.preferences-menu--fixed) {
      position: fixed;
      top: 1.25rem;
      right: 1.25rem;
      z-index: 50;
    }
    .pref-switch {
      position: relative;
      width: 40px;
      height: 22px;
      border-radius: 999px;
      border: none;
      cursor: pointer;
      background: var(--color-outline-variant);
      transition: background 0.2s;
      flex-shrink: 0;
      padding: 0;
    }
    .pref-switch--on {
      background: var(--color-primary);
    }
    .pref-switch__knob {
      position: absolute;
      top: 2px;
      left: 2px;
      width: 18px;
      height: 18px;
      border-radius: 50%;
      background: white;
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
      transition: transform 0.2s;
    }
    .pref-switch--on .pref-switch__knob {
      transform: translateX(18px);
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PreferencesMenu {
  fixed = input(false);

  open = false;
  theme = inject(ThemeService);
  settings = inject(GlobalSettingsService);
  notifService = inject(NotificationService);
  auth = inject(AuthService);
  hideCharts = this.settings.hideCharts;
  userRole = signal('');

  get prefs() {
    return this.notifService.preferences() || {
      debt_enabled: true, activity_enabled: true, system_enabled: true,
      alert_enabled: true, payment_enabled: true, sound_enabled: true, browser_notifications: false
    };
  }

  private cdr = inject(ChangeDetectorRef);
  private el = inject(ElementRef);

  constructor() {
    this.auth.currentUser$.subscribe(u => {
      this.userRole.set(u?.role || '');
      this.cdr.markForCheck();
    });
  }

  toggle(event: MouseEvent): void {
    event.stopPropagation();
    this.open = !this.open;
    this.cdr.markForCheck();
  }

  close(): void {
    if (!this.open) return;
    this.open = false;
    this.cdr.markForCheck();
  }

  toggleDark(): void {
    this.theme.toggle();
    this.cdr.markForCheck();
  }

  toggleCharts(): void {
    this.settings.toggleHideCharts();
    this.cdr.markForCheck();
  }

  toggleCategory(cat: string): void {
    const prefs = this.notifService.preferences();
    if (!prefs) return;
    const key = `${cat}_enabled` as keyof NotificationPreferences;
    this.notifService.updatePreferences({ [key]: !prefs[key] }).subscribe(() => {
      this.cdr.markForCheck();
    });
  }

  toggleSound(): void {
    const prefs = this.notifService.preferences();
    if (!prefs) return;
    this.notifService.updatePreferences({ sound_enabled: !prefs.sound_enabled }).subscribe(() => {
      this.cdr.markForCheck();
    });
  }

  toggleBrowserNotif(): void {
    const prefs = this.notifService.preferences();
    if (!prefs) return;
    const newVal = !prefs.browser_notifications;
    if (newVal) {
      this.notifService.requestBrowserPermission();
    }
    this.notifService.updatePreferences({ browser_notifications: newVal }).subscribe(() => {
      this.cdr.markForCheck();
    });
  }

  @HostListener('document:click', ['$event'])
  onDocumentClick(event: MouseEvent): void {
    if (!this.el.nativeElement.contains(event.target as Node)) {
      this.close();
    }
  }
}
