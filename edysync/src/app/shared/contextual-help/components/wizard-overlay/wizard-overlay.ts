import { Component, inject, AfterViewInit, effect, signal, ChangeDetectionStrategy, ElementRef, OnDestroy, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { WizardService } from '../../services/wizard.service';

@Component({
  selector: 'app-wizard-overlay',
  standalone: true,
  imports: [CommonModule, FontAwesomeModule],
  templateUrl: './wizard-overlay.html',
  styles: [`
    .wiz-backdrop {
      position: fixed;
      inset: 0;
      z-index: 80;
    }
    .wiz-highlight {
      position: fixed;
      border-radius: 12px;
      box-shadow: 0 0 0 9999px rgba(0,0,0,0.55);
      z-index: 81;
      transition: all 0.35s cubic-bezier(0.4, 0, 0.2, 1);
      pointer-events: none;
    }
    .wiz-tooltip {
      position: fixed;
      z-index: 82;
      background: var(--color-surface-container-lowest, #fff);
      border: 1px solid var(--color-border, #e5e7eb);
      border-radius: 16px;
      padding: 24px;
      max-width: 380px;
      width: 340px;
      box-shadow: 0 16px 48px rgba(0,0,0,0.2);
      transition: opacity 0.3s ease, transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
      animation: tooltipEnter 0.3s ease;
    }
    .wiz-tooltip-header {
      display: flex;
      align-items: center;
      gap: 10px;
      margin-bottom: 10px;
    }
    .wiz-step-indicator {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 28px;
      height: 28px;
      border-radius: 50%;
      background: var(--color-primary, #2563eb);
      color: white;
      font-size: 0.75rem;
      font-weight: 700;
    }
    .wiz-tooltip-title {
      font-size: 1rem;
      font-weight: 700;
      color: var(--color-on-surface, #1f2937);
    }
    .wiz-tooltip-desc {
      font-size: 0.875rem;
      color: var(--color-on-surface-variant, #6b7280);
      line-height: 1.6;
      margin-bottom: 20px;
    }
    .wiz-progress {
      display: flex;
      gap: 6px;
      margin-bottom: 16px;
      justify-content: center;
    }
    .wiz-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: var(--color-surface-container-high, #d1d5db);
      transition: all 0.3s;
    }
    .wiz-dot.active {
      background: var(--color-primary, #2563eb);
      width: 24px;
      border-radius: 4px;
    }
    .wiz-dot.done {
      background: var(--color-primary-container, #93c5fd);
    }
    .wiz-actions {
      display: flex;
      gap: 10px;
    }
    .wiz-btn {
      flex: 1;
      padding: 10px 16px;
      border-radius: 10px;
      border: none;
      font-size: 0.8125rem;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.15s;
    }
    .wiz-btn:hover {
      transform: translateY(-1px);
    }
    .wiz-btn:active {
      transform: translateY(0);
    }
    .wiz-btn-primary {
      background: var(--color-primary, #2563eb);
      color: white;
    }
    .wiz-btn-ghost {
      background: transparent;
      color: var(--color-on-surface-variant, #6b7280);
    }
    .wiz-btn-ghost:hover {
      background: var(--color-surface-container-low, #f3f4f6);
    }
    .wiz-btn-skip {
      background: transparent;
      color: var(--color-on-surface-variant, #9ca3af);
      font-size: 0.75rem;
    }
    @keyframes tooltipEnter {
      from { opacity: 0; transform: translateY(8px); }
      to { opacity: 1; transform: translateY(0); }
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class WizardOverlay implements AfterViewInit, OnDestroy {
  private wizardService = inject(WizardService);
  private elementRef = inject(ElementRef);

  highlightRect = signal<DOMRect | null>(null);
  tooltipStyle = signal<{ top: string; left: string; transform: string }>({ top: '0', left: '0', transform: 'translate(-50%,0)' });

  active = this.wizardService.active;
  currentStep = this.wizardService.currentStep;
  currentStepIndex = this.wizardService.currentStepIndex;
  totalSteps = this.wizardService.totalSteps;
  isLastStep = this.wizardService.isLastStep;

  private resizeObserver: ResizeObserver | null = null;
  private scrollHandler: (() => void) | null = null;

  constructor() {
    effect(() => {
      if (this.wizardService.active()) {
        requestAnimationFrame(() => {
          requestAnimationFrame(() => this.positionHighlight());
        });
      }
    });
  }

  ngAfterViewInit(): void {
    this.resizeObserver = new ResizeObserver(() => {
      if (this.wizardService.active()) {
        this.positionHighlight();
      }
    });
    this.resizeObserver.observe(document.body);
  }

  ngOnDestroy(): void {
    this.resizeObserver?.disconnect();
  }

  @HostListener('document:keydown.escape')
  onEscapeKey(): void {
    if (this.wizardService.active()) {
      this.dismiss();
    }
  }

  private positionHighlight(): void {
    const step = this.wizardService.currentStep();
    if (!step) return;

    if (step.position === 'center') {
      this.highlightRect.set(null);
      this.tooltipStyle.set({ top: '50%', left: '50%', transform: 'translate(-50%,-50%)' });
      return;
    }

    const el = this.findElement(step.selector);
    if (!el) {
      this.highlightRect.set(null);
      this.tooltipStyle.set({ top: '40%', left: '50%', transform: 'translate(-50%,-50%)' });
      return;
    }

    el.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'nearest' });

    const rect = el.getBoundingClientRect();

    if (rect.width === 0 || rect.height === 0) {
      this.highlightRect.set(null);
      this.tooltipStyle.set({ top: '40%', left: '50%', transform: 'translate(-50%,-50%)' });
      return;
    }

    const pad = step.highlightPadding ?? 8;
    this.highlightRect.set(new DOMRect(
      rect.left - pad,
      rect.top - pad,
      rect.width + pad * 2,
      rect.height + pad * 2,
    ));

    const pos = step.position || 'bottom';
    const gap = 14;
    let top: string, left: string, transform: string;
    const vw = window.innerWidth;
    const vh = window.innerHeight;

    switch (pos) {
      case 'top': {
        const rawTop = rect.top - gap;
        const rawLeft = rect.left + rect.width / 2;
        top = `${Math.max(16, rawTop)}px`;
        left = `${Math.min(Math.max(180, rawLeft), vw - 180)}px`;
        transform = 'translate(-50%,-100%)';
        break;
      }
      case 'bottom': {
        const rawTop = rect.bottom + gap;
        const rawLeft = rect.left + rect.width / 2;
        top = `${Math.min(rawTop, vh - 200)}px`;
        left = `${Math.min(Math.max(180, rawLeft), vw - 180)}px`;
        transform = 'translate(-50%,0)';
        break;
      }
      case 'left': {
        const rawLeft = rect.left - gap;
        const rawTop = rect.top + rect.height / 2;
        top = `${Math.min(Math.max(80, rawTop), vh - 160)}px`;
        left = `${Math.max(16, rawLeft)}px`;
        transform = 'translate(-100%,-50%)';
        break;
      }
      case 'right': {
        const rawLeft = rect.right + gap;
        const rawTop = rect.top + rect.height / 2;
        top = `${Math.min(Math.max(80, rawTop), vh - 160)}px`;
        left = `${Math.min(rawLeft, vw - 380)}px`;
        transform = 'translate(0,-50%)';
        break;
      }
      default: {
        top = `${rect.bottom + gap}px`;
        left = `${rect.left + rect.width / 2}px`;
        transform = 'translate(-50%,0)';
      }
    }

    this.tooltipStyle.set({ top, left, transform });
  }

  private findElement(selector: string): Element | null {
    let el = document.querySelector(selector);
    if (el) return el;

    for (let attempt = 0; attempt < 3; attempt++) {
      el = document.querySelector(selector);
      if (el) return el;
    }
    return null;
  }

  next(): void {
    this.wizardService.next();
  }

  prev(): void {
    this.wizardService.prev();
  }

  finish(): void {
    this.wizardService.finish();
  }

  dismiss(): void {
    this.wizardService.dismiss();
  }
}
