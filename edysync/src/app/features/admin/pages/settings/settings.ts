import { Component, OnInit, OnDestroy, inject, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { forkJoin, Subscription } from 'rxjs';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { ThemeService, type ThemeSchedule } from '../../../../core/services/theme.service';
import { GlobalSettingsService, COLOR_PRESETS, type FontSize } from '../../../../core/services/global-settings.service';
import { NotificationService } from '../../../../core/services/notification.service';
import { AdminService } from '../../../../core/services/admin.service';
import { HeaderService } from '../../../../core/services/header.service';
import type { NotificationPreferences } from '../../../../core/models/notification';

@Component({
  selector: 'app-settings',
  standalone: true,
  imports: [FontAwesomeModule],
  templateUrl: './settings.html',
  styleUrls: ['./settings.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Settings implements OnInit, OnDestroy {
  private theme = inject(ThemeService);
  private settings = inject(GlobalSettingsService);
  private notifService = inject(NotificationService);
  private admin = inject(AdminService);
  private headerService = inject(HeaderService);
  private cdr = inject(ChangeDetectorRef);
  private subs = new Subscription();

  hours = Array.from({ length: 24 }, (_, i) => i);
  colorPresets = COLOR_PRESETS;

  saving = false;
  saved = false;

  currentSchedule: ThemeSchedule = { enabled: false, from: 22, to: 7 };
  isDark = false;

  get schedule() { return this.currentSchedule; }
  get fontSize() { return this.settings.fontSize; }
  get primaryColor() { return this.settings.primaryColor; }
  get hideCharts() { return this.settings.hideCharts; }
  get sidebarPinned() { return this.settings.sidebarPinned; }
  get notifPrefs() { return this.notifService.preferences() ?? this.notifService.defaultPrefs; }

  telegramAccounts: any[] = [];
  telegramLoading = false;
  telegramToggling: number | null = null;

  ngOnInit() {
    this.headerService.setConfig({
      title: 'Configuración',
      subtitle: 'Personaliza tu experiencia en la plataforma',
      icon: ['fas', 'cog'],
    });
    // Re-fetch schedule from API now that user is authenticated
    this.theme.refreshScheduleFromAPI();
  }

  ngOnDestroy() {
    this.subs.unsubscribe();
    this.headerService.reset();
  }

  constructor() {
    this.isDark = (this.theme.theme$ as any).value === 'dark';
    this.subs.add(this.theme.theme$.subscribe(t => {
      this.isDark = t === 'dark';
      this.cdr.markForCheck();
    }));
    this.subs.add(this.theme.schedule$.subscribe(s => {
      this.currentSchedule = { ...s };
      this.cdr.markForCheck();
    }));
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
    // Disable schedule when manually toggling — otherwise the watcher reverts it
    if (this.currentSchedule.enabled) {
      this.currentSchedule = { ...this.currentSchedule, enabled: false };
      this.theme.setSchedule({ ...this.currentSchedule });
    }
    this.cdr.markForCheck();
  }

  toggleSchedule(): void {
    this.currentSchedule = { ...this.currentSchedule, enabled: !this.currentSchedule.enabled };
    this.theme.setSchedule({ ...this.currentSchedule });
    this.cdr.markForCheck();
  }

  setScheduleFrom(hour: number): void {
    this.currentSchedule = { ...this.currentSchedule, from: hour };
    this.theme.setSchedule({ ...this.currentSchedule });
    this.cdr.markForCheck();
  }

  setScheduleTo(hour: number): void {
    this.currentSchedule = { ...this.currentSchedule, to: hour };
    this.theme.setSchedule({ ...this.currentSchedule });
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

  private readonly categoryKeyMap: Record<string, keyof NotificationPreferences> = {
    debt: 'debt_enabled',
    activity: 'activity_enabled',
    system: 'system_enabled',
    alert: 'alert_enabled',
    payment: 'payment_enabled',
  };

  toggleCategory(cat: string): void {
    const key = this.categoryKeyMap[cat];
    if (!key) return;
    const current = this.notifPrefs[key];
    this.notifService.updatePreferences({ [key]: !current } as Partial<NotificationPreferences>).subscribe({
      next: () => this.cdr.markForCheck(),
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
