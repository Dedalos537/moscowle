import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';

export interface ThemeSchedule {
  enabled: boolean;
  from: number; // hora 0-23 inicio
  to: number; // hora 0-23 fin (puede cruzar medianoche: from=22, to=7)
}

@Injectable({ providedIn: 'root' })
export class ThemeService {
  private themeSubject = new BehaviorSubject<string>('light');
  theme$ = this.themeSubject.asObservable();

  private schedule: ThemeSchedule = { enabled: false, from: 22, to: 7 };
  private scheduleSubject = new BehaviorSubject<ThemeSchedule>(this.schedule);
  schedule$ = this.scheduleSubject.asObservable();

  private timer: ReturnType<typeof setInterval> | null = null;

  constructor() {
    this.loadSchedule();
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

  private loadSchedule() {
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
