import { Component, inject, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { HelpStateService } from '../../services/help-state.service';

@Component({
  selector: 'app-help-button',
  standalone: true,
  imports: [CommonModule, FontAwesomeModule],
  template: `
    <button
      (click)="state.toggle()"
      class="help-fab"
      [class.is-open]="state.panelOpen()"
      title="Ayuda contextual"
      aria-label="Abrir ayuda">
      <fa-icon [icon]="state.panelOpen() ? ['fas', 'times'] : ['fas', 'question']" class="help-fab__icon"></fa-icon>
    </button>
  `,
  styles: [`
    .help-fab {
      position: fixed;
      bottom: 24px;
      left: 24px;
      width: 56px;
      height: 56px;
      border-radius: 50%;
      background: var(--color-primary, #2563eb);
      color: white;
      border: none;
      box-shadow: 0 4px 16px rgba(37, 99, 235, 0.35);
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
      z-index: 65;
    }
    .help-fab:hover {
      transform: scale(1.08);
      box-shadow: 0 6px 24px rgba(37, 99, 235, 0.45);
    }
    .help-fab:active {
      transform: scale(0.95);
    }
    .help-fab.is-open {
      background: var(--color-error, #dc2626);
      box-shadow: 0 4px 16px rgba(220, 38, 38, 0.35);
    }
    .help-fab__icon {
      font-size: 1.25rem;
      transition: transform 0.3s ease;
    }
    .is-open .help-fab__icon {
      transform: rotate(90deg);
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HelpButton {
  state = inject(HelpStateService);
}
