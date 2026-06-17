import { Injectable, signal } from '@angular/core';

const STORAGE_KEY = 'edysync_hide_charts';

@Injectable({ providedIn: 'root' })
export class GlobalSettingsService {
  hideCharts = signal<boolean>(this.load());

  private load(): boolean {
    try {
      return localStorage.getItem(STORAGE_KEY) === 'true';
    } catch {
      return false;
    }
  }

  toggleHideCharts(): void {
    const next = !this.hideCharts();
    this.hideCharts.set(next);
    try {
      localStorage.setItem(STORAGE_KEY, String(next));
    } catch {}
  }
}
