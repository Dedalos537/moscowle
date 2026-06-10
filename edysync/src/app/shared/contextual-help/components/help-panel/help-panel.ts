import { Component, inject, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { RouterModule } from '@angular/router';
import { HelpStateService } from '../../services/help-state.service';
import { HelpContentService } from '../../services/help-content.service';
import { WizardService } from '../../services/wizard.service';

@Component({
  selector: 'app-help-panel',
  standalone: true,
  imports: [CommonModule, FontAwesomeModule, RouterModule],
  templateUrl: './help-panel.html',
  styles: [`
    .help-backdrop {
      position: fixed;
      inset: 0;
      background: rgba(0,0,0,0.25);
      z-index: 66;
      animation: fadeIn 0.2s ease;
    }
    .help-panel {
      position: fixed;
      top: 0;
      right: 0;
      bottom: 0;
      width: 400px;
      max-width: 100vw;
      background: var(--color-surface-container-lowest, #fff);
      border-left: 1px solid var(--color-border, #e5e7eb);
      box-shadow: -8px 0 32px rgba(0,0,0,0.1);
      z-index: 67;
      display: flex;
      flex-direction: column;
      transform: translateX(0);
      transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
      overflow: hidden;
    }
    .help-panel-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 16px 20px;
      border-bottom: 1px solid var(--color-border, #e5e7eb);
      flex-shrink: 0;
    }
    .help-panel-title {
      display: flex;
      align-items: center;
      gap: 10px;
      font-size: 1rem;
      font-weight: 700;
      color: var(--color-on-surface, #1f2937);
    }
    .help-panel-title fa-icon {
      color: var(--color-primary, #2563eb);
      font-size: 1.1rem;
    }
    .help-panel-close {
      width: 32px;
      height: 32px;
      border-radius: 8px;
      border: none;
      background: var(--color-surface-container-low, #f3f4f6);
      color: var(--color-on-surface-variant, #6b7280);
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: background 0.2s;
    }
    .help-panel-close:hover {
      background: var(--color-surface-container-high, #e5e7eb);
    }
    .help-panel-body {
      flex: 1;
      overflow-y: auto;
      padding: 20px;
    }
    .help-description {
      font-size: 0.875rem;
      color: var(--color-on-surface-variant, #6b7280);
      margin-bottom: 20px;
      line-height: 1.5;
    }
    .help-section {
      background: var(--color-surface-container-low, #f9fafb);
      border-radius: 12px;
      padding: 16px;
      margin-bottom: 12px;
    }
    .help-section-title {
      display: flex;
      align-items: center;
      gap: 8px;
      font-weight: 600;
      font-size: 0.875rem;
      color: var(--color-on-surface, #1f2937);
      margin-bottom: 8px;
    }
    .help-section-title fa-icon {
      color: var(--color-primary, #2563eb);
      font-size: 0.8rem;
    }
    .help-section-content {
      font-size: 0.8125rem;
      color: var(--color-on-surface-variant, #6b7280);
      line-height: 1.6;
    }
    .help-section-items {
      margin-top: 8px;
      padding-left: 20px;
      font-size: 0.8125rem;
      color: var(--color-on-surface-variant, #6b7280);
      line-height: 1.7;
    }
    .help-section-items li {
      margin-bottom: 4px;
    }
    .help-tips {
      margin-top: 16px;
      padding: 12px 16px;
      background: var(--color-primary-container, #dbeafe);
      border-radius: 10px;
    }
    .help-tips-title {
      font-weight: 600;
      font-size: 0.8125rem;
      color: var(--color-on-primary-container, #1e40af);
      margin-bottom: 6px;
    }
    .help-tips-list {
      padding-left: 16px;
      font-size: 0.8125rem;
      color: var(--color-on-primary-container, #1e40af);
      line-height: 1.6;
    }
    .help-tips-list li {
      margin-bottom: 2px;
    }
    .help-links {
      margin-top: 12px;
      padding: 12px 16px;
      background: var(--color-surface-container-low, #f3f4f6);
      border-radius: 10px;
    }
    .help-links-title {
      font-weight: 600;
      font-size: 0.8125rem;
      color: var(--color-on-surface, #1f2937);
      margin-bottom: 6px;
    }
    .help-link-item {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 6px 0;
      color: var(--color-primary, #2563eb);
      text-decoration: none;
      font-size: 0.8125rem;
      cursor: pointer;
    }
    .help-link-item:hover {
      text-decoration: underline;
    }
    .help-link-item fa-icon {
      font-size: 0.75rem;
    }
    .help-wizard-btn {
      margin-top: 20px;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      width: 100%;
      padding: 12px;
      border-radius: 12px;
      border: none;
      background: linear-gradient(135deg, var(--color-primary, #2563eb), #7c3aed);
      color: white;
      font-weight: 600;
      font-size: 0.875rem;
      cursor: pointer;
      transition: opacity 0.2s, transform 0.15s;
    }
    .help-wizard-btn:hover {
      opacity: 0.9;
      transform: translateY(-1px);
    }
    .help-wizard-btn:active {
      transform: translateY(0);
    }
    .help-empty {
      text-align: center;
      padding: 40px 20px;
      color: var(--color-on-surface-variant, #9ca3af);
    }
    .help-empty fa-icon {
      font-size: 2rem;
      margin-bottom: 12px;
      opacity: 0.5;
    }
    .help-empty p {
      font-size: 0.875rem;
    }
    @keyframes fadeIn {
      from { opacity: 0; }
      to { opacity: 1; }
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HelpPanel {
  helpState = inject(HelpStateService);
  private wizardService = inject(WizardService);
  helpContentService = inject(HelpContentService);

  close(): void {
    this.helpState.close();
  }

  startWizard(): void {
    this.helpState.close();
    this.wizardService.start();
  }
}
