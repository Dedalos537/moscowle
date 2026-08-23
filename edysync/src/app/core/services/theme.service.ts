import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject } from 'rxjs';
import { GlobalSettingsService } from './global-settings.service';

export interface ThemeSchedule {
  enabled: boolean;
  from: number; // hora 0-23 inicio
  to: number; // hora 0-23 fin (puede cruzar medianoche: from=22, to=7)
}

@Injectable({ providedIn: 'root' })
export class ThemeService {
  private http = inject(HttpClient);
  private globalSettings = inject(GlobalSettingsService);

  private themeSubject = new BehaviorSubject<string>('light');
  theme$ = this.themeSubject.asObservable();

  private schedule: ThemeSchedule = { enabled: false, from: 22, to: 7 };
  private scheduleSubject = new BehaviorSubject<ThemeSchedule>(this.schedule);
  schedule$ = this.scheduleSubject.asObservable();

  private timer: ReturnType<typeof setInterval> | null = null;

  constructor() {
    this.loadScheduleFromAPI();
    const saved = localStorage.getItem('theme');
    const isDark = document.documentElement.classList.contains('dark');
    if (saved === 'dark' || (!saved && isDark)) {
      this.themeSubject.next('dark');
      document.documentElement.classList.add('dark');
    } else {
      this.themeSubject.next('light');
      document.documentElement.classList.remove('dark');
    }
    this.startScheduleWatcher();
  }

  toggle() {
    const next = this.themeSubject.value === 'light' ? 'dark' : 'light';
    this.setTheme(next);
  }

  private setTheme(theme: string) {
    this.themeSubject.next(theme);
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
    localStorage.setItem('theme', theme);
    // Re-derive all primary-derived colors for the new theme
    this.globalSettings.reapplyPrimaryColor();
  }

  // ── Programación por hora ────────────────────────────────────────────────

  getSchedule(): ThemeSchedule {
    return { ...this.schedule };
  }

  setSchedule(schedule: ThemeSchedule) {
    this.schedule = {
      enabled: !!schedule.enabled,
      from: Math.max(0, Math.min(23, Math.floor(schedule.from))),
      to: Math.max(0, Math.min(23, Math.floor(schedule.to))),
    };
    localStorage.setItem('themeSchedule', JSON.stringify(this.schedule));
    this.scheduleSubject.next({ ...this.schedule });
    this.saveScheduleToAPI();
    if (this.schedule.enabled) {
      this.applySchedule();
    }
  }

  clearSchedule() {
    this.setSchedule({ enabled: false, from: 22, to: 7 });
  }

  /** Devuelve true si la hora `hour` cae dentro del rango [from, to) soportando medianoche. */
  isDarkHour(hour: number): boolean {
    const { from, to } = this.schedule;
    if (from === to) {
      return false;
    }
    if (from < to) {
      return hour >= from && hour < to;
    }
    return hour >= from || hour < to; // cruza medianoche
  }

  private applySchedule() {
    if (!this.schedule.enabled) return;
    const hour = new Date().getHours();
    const desired = this.isDarkHour(hour) ? 'dark' : 'light';
    if (desired !== this.themeSubject.value) {
      this.setTheme(desired);
    }
  }

  /** Public: re-fetch schedule from API (e.g. after login) */
  refreshScheduleFromAPI(): void {
    this.loadScheduleFromAPI();
  }

  private loadScheduleFromAPI() {
    this.http.get<ThemeSchedule>('/api/user/schedule').subscribe({
      next: (data) => {
        this.schedule = {
          enabled: !!data.enabled,
          from: Number.isInteger(data.from) ? Math.max(0, Math.min(23, data.from)) : 22,
          to: Number.isInteger(data.to) ? Math.max(0, Math.min(23, data.to)) : 7,
        };
        localStorage.setItem('themeSchedule', JSON.stringify(this.schedule));
        this.scheduleSubject.next({ ...this.schedule });
      },
      error: () => {
        this.loadScheduleFromLocal();
      },
    });
  }

  private loadScheduleFromLocal() {
    try {
      const raw = localStorage.getItem('themeSchedule');
      if (raw) {
        const parsed = JSON.parse(raw) as Partial<ThemeSchedule>;
        this.schedule = {
          enabled: !!parsed.enabled,
          from: Number.isInteger(parsed.from) ? Math.max(0, Math.min(23, parsed.from!)) : 22,
          to: Number.isInteger(parsed.to) ? Math.max(0, Math.min(23, parsed.to!)) : 7,
        };
      }
    } catch {
      this.schedule = { enabled: false, from: 22, to: 7 };
    }
    this.scheduleSubject.next({ ...this.schedule });
  }

  private saveScheduleToAPI() {
    this.http.put('/api/user/schedule', this.schedule).subscribe({ error: () => {} });
  }

  private startScheduleWatcher() {
    this.stopScheduleWatcher();
    this.timer = setInterval(() => this.applySchedule(), 60_000);
  }

  private stopScheduleWatcher() {
    if (this.timer !== null) {
      clearInterval(this.timer);
      this.timer = null;
    }
  }
}
