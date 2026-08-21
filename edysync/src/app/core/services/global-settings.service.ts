import { Injectable, inject, signal, NgZone } from '@angular/core';
import { HttpClient } from '@angular/common/http';

export type FontSize = 'small' | 'medium' | 'large';

export interface ColorPreset {
  name: string;
  label: string;
  light: string;
  dark: string;
}

export const COLOR_PRESETS: ColorPreset[] = [
  { name: 'green',  label: 'Verde',     light: '#75a83a', dark: '#a5d087' },
  { name: 'blue',   label: 'Azul',      light: '#2563eb', dark: '#60a5fa' },
  { name: 'purple', label: 'Púrpura',   light: '#7c3aed', dark: '#a78bfa' },
  { name: 'rose',   label: 'Rosa',      light: '#db2777', dark: '#f472b6' },
  { name: 'orange', label: 'Naranja',   light: '#ea580c', dark: '#fb923c' },
  { name: 'teal',   label: 'Turquesa',  light: '#0891b2', dark: '#22d3ee' },
];

const FONT_SIZE_MAP: Record<FontSize, string> = {
  small: '14px',
  medium: '16px',
  large: '18px',
};

@Injectable({ providedIn: 'root' })
export class GlobalSettingsService {
  private http = inject(HttpClient);
  private zone = inject(NgZone);

  hideCharts = signal<boolean>(this.loadLocal('edysync_hide_charts') === 'true');
  fontSize = signal<FontSize>((this.loadLocal('edysync_font_size') as FontSize) || 'medium');
  primaryColor = signal<string>(this.loadLocal('edysync_primary_color') || 'green');

  constructor() {
    this.applyFontSize(this.fontSize());
    this.applyPrimaryColor(this.primaryColor());
    this.loadFromAPI();
  }

  toggleHideCharts(): void {
    const next = !this.hideCharts();
    this.hideCharts.set(next);
    this.saveLocal('edysync_hide_charts', String(next));
    this.saveToAPI({ hide_charts: next });
  }

  setFontSize(size: FontSize): void {
    this.fontSize.set(size);
    this.saveLocal('edysync_font_size', size);
    this.applyFontSize(size);
    this.saveToAPI({ font_size: size });
  }

  setPrimaryColor(colorName: string): void {
    this.primaryColor.set(colorName);
    this.saveLocal('edysync_primary_color', colorName);
    this.applyPrimaryColor(colorName);
    this.saveToAPI({ primary_color: colorName });
  }

  private applyFontSize(size: FontSize): void {
    const px = FONT_SIZE_MAP[size];
    document.documentElement.style.setProperty('--font-size-base', px);
    document.documentElement.style.fontSize = px;
  }

  private applyPrimaryColor(colorName: string): void {
    const preset = COLOR_PRESETS.find(c => c.name === colorName);
    if (!preset) return;
    const isDark = document.documentElement.classList.contains('dark');
    const hex = isDark ? preset.dark : preset.light;
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    document.documentElement.style.setProperty('--color-primary', hex);
    document.documentElement.style.setProperty('--color-primary-rgb', `${r}, ${g}, ${b}`);
    document.documentElement.style.setProperty('--color-primary-container', hex);
    document.documentElement.style.setProperty('--color-on-primary', '#ffffff');
  }

  /** Reapply primary color when theme toggles (light↔dark) */
  reapplyPrimaryColor(): void {
    this.applyPrimaryColor(this.primaryColor());
  }

  private loadLocal(key: string): string {
    try { return localStorage.getItem(key) || ''; } catch { return ''; }
  }

  private saveLocal(key: string, value: string): void {
    try { localStorage.setItem(key, value); } catch {}
  }

  private loadFromAPI(): void {
    this.http.get<{ font_size: FontSize; primary_color: string; hide_charts: boolean }>('/api/user/preferences').subscribe({
      next: (data) => {
        this.zone.run(() => {
          if (data.font_size && data.font_size !== this.fontSize()) {
            this.fontSize.set(data.font_size);
            this.applyFontSize(data.font_size);
            this.saveLocal('edysync_font_size', data.font_size);
          }
          if (data.primary_color && data.primary_color !== this.primaryColor()) {
            this.primaryColor.set(data.primary_color);
            this.applyPrimaryColor(data.primary_color);
            this.saveLocal('edysync_primary_color', data.primary_color);
          }
          if (data.hide_charts !== undefined && data.hide_charts !== this.hideCharts()) {
            this.hideCharts.set(data.hide_charts);
            this.saveLocal('edysync_hide_charts', String(data.hide_charts));
          }
        });
      },
      error: () => {},
    });
  }

  private saveToAPI(data: Partial<{ font_size: FontSize; primary_color: string; hide_charts: boolean }>): void {
    this.http.put('/api/user/preferences', data).subscribe({ error: () => {} });
  }
}
