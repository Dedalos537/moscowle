import { Component, inject, ChangeDetectionStrategy } from '@angular/core';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { GlobalSettingsService } from '../../../core/services/global-settings.service';
import { FloatingUiService } from '../../../core/services/floating-ui.service';

@Component({
  selector: 'app-charts-toggle',
  standalone: true,
  imports: [FontAwesomeModule],
  template: `
    <div class="charts-fab__inner">
      <fa-icon [icon]="['fas', 'chart-bar']" class="charts-fab__icon"></fa-icon>
      <span class="charts-fab__label">Ocultar gráficos</span>
      <button
        type="button"
        class="charts-fab__switch"
        (click)="toggle()"
        [class.charts-fab__switch--on]="hideCharts()"
        [attr.aria-label]="hideCharts() ? 'Mostrar gráficos' : 'Ocultar gráficos'"
      >
        <span class="charts-fab__knob"></span>
      </button>
    </div>
  `,
  host: {
    class: 'floating-ui charts-fab',
    '[class.floating-ui--hidden]': 'floating.hidden()',
    '[style.bottom.px]': 'floating.leftStackOffset(1)',
  },
  styles: [`
    :host {
      position: fixed;
      left: 24px;
      z-index: 64;
      transition: bottom 0.35s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.25s ease, transform 0.25s ease;
    }
    :host(.floating-ui--hidden) {
      opacity: 0;
      pointer-events: none;
      transform: scale(0.9);
    }
    .charts-fab__inner {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 8px 12px;
      border-radius: 14px;
      background: color-mix(in srgb, var(--color-surface-container-lowest) 92%, transparent);
      backdrop-filter: blur(8px);
      border: 1px solid color-mix(in srgb, var(--color-border) 40%, transparent);
      box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
    }
    .charts-fab__inner--compact {
      padding: 6px;
      border-radius: 12px;
    }
    .charts-fab__icon {
      font-size: 0.875rem;
      color: var(--color-on-surface-variant);
    }
    .charts-fab__label {
      font-size: 0.75rem;
      font-weight: 600;
      color: var(--color-on-surface-variant);
      white-space: nowrap;
    }
    .charts-fab__switch {
      position: relative;
      width: 36px;
      height: 20px;
      border-radius: 999px;
      border: none;
      cursor: pointer;
      background: var(--color-outline-variant);
      transition: background 0.2s;
      flex-shrink: 0;
      padding: 0;
    }
    .charts-fab__switch--on {
      background: var(--color-primary);
    }
    .charts-fab__knob {
      position: absolute;
      top: 2px;
      left: 2px;
      width: 16px;
      height: 16px;
      border-radius: 50%;
      background: white;
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
      transition: transform 0.2s;
    }
    .charts-fab__switch--on .charts-fab__knob {
      transform: translateX(16px);
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ChartsToggle {
  private settings = inject(GlobalSettingsService);
  floating = inject(FloatingUiService);
  hideCharts = this.settings.hideCharts;

  toggle(): void {
    this.settings.toggleHideCharts();
  }
}
