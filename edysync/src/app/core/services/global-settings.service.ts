import { Injectable, inject, signal, NgZone } from '@angular/core';
import { HttpClient } from '@angular/common/http';

export type FontSize = 'small' | 'medium' | 'large';

export interface ColorPreset {
  name: string;
  label: string;
  light: string;
  dark: string;
  secondaryLight: string;
  secondaryDark: string;
}

export const COLOR_PRESETS: ColorPreset[] = [
  { name: 'green',    label: 'Verde',    light: '#75a83a', dark: '#a5d087', secondaryLight: '#4a7a14', secondaryDark: '#c8e09e' },
  { name: 'blue',     label: 'Azul',     light: '#2196F3', dark: '#64B5F6', secondaryLight: '#1565C0', secondaryDark: '#42A5F5' },
  { name: 'purple',   label: 'Morado',   light: '#9C27B0', dark: '#CE93D8', secondaryLight: '#FFCA28', secondaryDark: '#FFD54F' },
  { name: 'rose',     label: 'Fucsia',   light: '#E91E63', dark: '#F48FB1', secondaryLight: '#880E4F', secondaryDark: '#C2185B' },
  { name: 'orange',   label: 'Naranja',  light: '#FF9800', dark: '#FFB74D', secondaryLight: '#BF360C', secondaryDark: '#E64A19' },
  { name: 'teal',     label: 'Turquesa', light: '#00BCD4', dark: '#4DD0E1', secondaryLight: '#006064', secondaryDark: '#0097A7' },
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
  sidebarPinned = signal<boolean>(this.loadLocal('edysync_sidebar_pinned') === 'true');

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

  setSidebarPinned(pinned: boolean): void {
    this.sidebarPinned.set(pinned);
    this.saveLocal('edysync_sidebar_pinned', String(pinned));
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
    const secHex = isDark ? preset.secondaryDark : preset.secondaryLight;
    const root = document.documentElement.style;
    const [h, s, l] = this.hexToHsl(hex);

    // Base primary
    root.setProperty('--color-primary', hex);
    root.setProperty('--color-primary-rgb', this.hexToRgbStr(hex));

    // Secondary (contrast) color
    root.setProperty('--color-secondary', secHex);
    root.setProperty('--color-secondary-rgb', this.hexToRgbStr(secHex));

    // Container: lighter tint for light, darker for dark
    root.setProperty('--color-primary-container', isDark
      ? this.hslToHex(h, Math.max(20, s * 0.6), Math.min(25, l * 0.4))
      : this.hslToHex(h, Math.max(15, s * 0.5), Math.min(92, l + (95 - l) * 0.7)));
    root.setProperty('--color-on-primary', isDark ? '#1a1a1a' : '#ffffff');
    root.setProperty('--color-on-primary-container', isDark ? '#ffffff' : '#1a1a1a');

    // Secondary container
    const [sh, ss, sl] = this.hexToHsl(secHex);
    root.setProperty('--color-secondary-container', isDark
      ? this.hslToHex(sh, Math.max(20, ss * 0.5), Math.min(25, sl * 0.5))
      : this.hslToHex(sh, Math.max(15, ss * 0.4), Math.min(93, sl + (95 - sl) * 0.7)));
    root.setProperty('--color-on-secondary', isDark ? '#1a1a1a' : '#ffffff');
    root.setProperty('--color-on-secondary-container', isDark ? '#ffffff' : '#1a1a1a');

    // Sidebar / nav active
    root.setProperty('--color-nav-active-bg', `color-mix(in srgb, ${hex} 12%, transparent)`);
    root.setProperty('--color-nav-active-border', hex);

    // Hover states
    root.setProperty('--color-primary-hover', isDark
      ? this.hslToHex(h, s, Math.min(75, l + 15))
      : this.hslToHex(h, s, Math.max(25, l - 15)));
    root.setProperty('--color-primary-container-hover', `color-mix(in srgb, ${hex} 15%, transparent)`);

    // Loading overlay
    root.setProperty('--color-loader-bg', `color-mix(in srgb, ${hex} 6%, var(--color-background))`);

    // Borders
    root.setProperty('--color-border-accent', `color-mix(in srgb, ${hex} 30%, transparent)`);

    // Accent = secondary (contrast) color
    root.setProperty('--color-accent', secHex);
    root.setProperty('--color-accent-container', isDark
      ? this.hslToHex(sh, Math.max(15, ss * 0.4), 20)
      : this.hslToHex(sh, Math.max(15, ss * 0.4), 92));

    // Tonal scale 50–900
    for (const step of [50, 100, 200, 300, 400, 500, 600, 700, 800, 900]) {
      const stepL = isDark
        ? Math.min(90, 20 + (step / 900) * 70)
        : Math.max(10, 95 - (step / 900) * 75);
      const stepS = Math.max(10, s * (1 - Math.abs(500 - step) / 600));
      root.setProperty(`--color-primary-${step}`, this.hslToHex(h, stepS, stepL));
    }

    // Semantic: success (green-shifted from primary hue)
    const successH = h < 180 ? Math.min(h + 40, 150) : Math.max(h - 40, 120);
    root.setProperty('--color-success', this.hslToHex(successH, isDark ? 55 : 60, isDark ? 50 : 35));
    root.setProperty('--color-success-container', this.hslToHex(successH, isDark ? 30 : 35, isDark ? 15 : 88));

    // Semantic: warning (amber)
    root.setProperty('--color-warning', this.hslToHex(45, isDark ? 90 : 85, isDark ? 55 : 50));
    root.setProperty('--color-warning-container', this.hslToHex(45, isDark ? 40 : 50, isDark ? 18 : 92));

    // Semantic: info (shifted toward blue)
    const infoH = Math.max(200, Math.min(220, h + Math.abs(210 - h) * 0.3));
    root.setProperty('--color-info', this.hslToHex(infoH, isDark ? 60 : 70, isDark ? 55 : 45));
    root.setProperty('--color-info-container', this.hslToHex(infoH, isDark ? 30 : 40, isDark ? 18 : 90));

    root.setProperty('--color-border', isDark ? '#3e4040' : `color-mix(in srgb, ${hex} 20%, #e0e0e0)`);

    // ── Background / surface tinting with secondary color ───────────
    const secMixPct = isDark ? 4 : 6;
    const secMixPctLight = isDark ? 3 : 4;
    const secMixPctLighter = isDark ? 2 : 3;
    const baseLight = isDark ? '#1e1f20' : '#f8fbed';
    const baseMid = isDark ? '#242526' : '#edefe2';
    const baseHigh = isDark ? '#2a2b2d' : '#e7e9dc';
    const baseHighest = isDark ? '#373839' : '#e1e4d7';

    // Main page background — subtle secondary tint
    root.setProperty('--color-background', isDark
      ? baseLight
      : `color-mix(in srgb, ${secHex} ${secMixPct}%, ${baseLight})`);
    root.setProperty('--color-surface', isDark
      ? baseLight
      : `color-mix(in srgb, ${secHex} ${secMixPct}%, ${baseLight})`);
    root.setProperty('--color-surface-bright', isDark
      ? baseHighest
      : `color-mix(in srgb, ${secHex} ${secMixPctLighter}%, ${baseLight})`);
    root.setProperty('--color-surface-dim', isDark
      ? baseLight
      : `color-mix(in srgb, ${secHex} ${secMixPctLight}%, #d9dbce)`);

    // Surface containers — cards, panels, modals
    root.setProperty('--color-surface-container-lowest', isDark ? '#18191a' : '#ffffff');
    root.setProperty('--color-surface-container-low', isDark
      ? '#1a1b1c'
      : `color-mix(in srgb, ${secHex} ${secMixPctLighter}%, #f3f5e7)`);
    root.setProperty('--color-surface-container', isDark
      ? baseMid
      : `color-mix(in srgb, ${secHex} ${secMixPctLight}%, ${baseMid})`);
    root.setProperty('--color-surface-container-high', isDark
      ? baseHigh
      : `color-mix(in srgb, ${secHex} ${secMixPct}%, ${baseHigh})`);
    root.setProperty('--color-surface-container-highest', isDark
      ? baseHighest
      : `color-mix(in srgb, ${secHex} ${secMixPct}%, ${baseHighest})`);
    root.setProperty('--color-surface-variant', isDark
      ? baseHighest
      : `color-mix(in srgb, ${secHex} ${secMixPctLight}%, ${baseHighest})`);

    // Surface tint (the subtle color wash over surfaces)
    root.setProperty('--color-surface-tint', `color-mix(in srgb, ${secHex} ${isDark ? 6 : 8}%, transparent)`);
  }

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

  // --- HSL color utilities ---

  private hexToHsl(hex: string): [number, number, number] {
    const r = parseInt(hex.slice(1, 3), 16) / 255;
    const g = parseInt(hex.slice(3, 5), 16) / 255;
    const b = parseInt(hex.slice(5, 7), 16) / 255;
    const max = Math.max(r, g, b), min = Math.min(r, g, b);
    const l = (max + min) / 2;
    let h = 0, s = 0;
    if (max !== min) {
      const d = max - min;
      s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
      switch (max) {
        case r: h = ((g - b) / d + (g < b ? 6 : 0)) / 6; break;
        case g: h = ((b - r) / d + 2) / 6; break;
        case b: h = ((r - g) / d + 4) / 6; break;
      }
    }
    return [Math.round(h * 360), Math.round(s * 100), Math.round(l * 100)];
  }

  private hslToHex(h: number, s: number, l: number): string {
    s /= 100;
    l /= 100;
    const a = s * Math.min(l, 1 - l);
    const f = (n: number) => {
      const k = (n + h / 30) % 12;
      const color = l - a * Math.max(Math.min(k - 3, 9 - k, 1), -1);
      return Math.round(255 * color).toString(16).padStart(2, '0');
    };
    return `#${f(0)}${f(8)}${f(4)}`;
  }

  private hexToRgbStr(hex: string): string {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return `${r}, ${g}, ${b}`;
  }
}
