import { Injectable, signal, computed, inject } from '@angular/core';
import { WIZARD_STEPS } from '../config/wizard-steps.config';
import { WizardStep } from '../models/wizard-step.model';
import { ContextDetectorService } from './context-detector.service';

@Injectable({ providedIn: 'root' })
export class WizardService {
  private contextDetector = inject(ContextDetectorService);

  private readonly STORAGE_KEY = 'edysync_wizard_completed';

  private isActive = signal(false);
  private currentIndex = signal(0);
  private dismissed = signal(false);

  steps = computed<WizardStep[]>(() => {
    const ctx = this.contextDetector.context();
    if (!ctx.role || !ctx.route) return [];

    return WIZARD_STEPS
      .filter(w => w.route === ctx.route && (!w.role || w.role === ctx.role))
      .flatMap(w => w.steps);
  });

  active = signal(false);
  currentStepIndex = signal(0);
  currentStep = computed<WizardStep | null>(() => {
    const s = this.steps();
    const i = this.currentStepIndex();
    return s.length > 0 && i < s.length ? s[i] : null;
  });

  totalSteps = computed(() => this.steps().length);
  isLastStep = computed(() => this.currentStepIndex() >= this.steps().length - 1);

  isPageCompleted(route: string, role: string): boolean {
    try {
      const key = `${this.STORAGE_KEY}_${role}_${route}`;
      return localStorage.getItem(key) === 'true';
    } catch {
      return false;
    }
  }

  markPageCompleted(route: string, role: string): void {
    try {
      const key = `${this.STORAGE_KEY}_${role}_${route}`;
      localStorage.setItem(key, 'true');
    } catch {
      // localStorage unavailable
    }
  }

  shouldAutoStart(): boolean {
    const ctx = this.contextDetector.context();
    if (!ctx.role || !ctx.route) return false;
    if (this.steps().length === 0) return false;
    return !this.isPageCompleted(ctx.route, ctx.role);
  }

  start(): void {
    const ctx = this.contextDetector.context();
    if (ctx.role && ctx.route) {
      this.markPageCompleted(ctx.route, ctx.role);
    }
    this.currentStepIndex.set(0);
    this.dismissed.set(false);
    this.active.set(true);
  }

  next(): void {
    if (this.currentStepIndex() < this.steps().length - 1) {
      this.currentStepIndex.update(i => i + 1);
    }
  }

  prev(): void {
    if (this.currentStepIndex() > 0) {
      this.currentStepIndex.update(i => i - 1);
    }
  }

  finish(): void {
    this.active.set(false);
    this.currentStepIndex.set(0);
    this.dismissed.set(true);
  }

  dismiss(): void {
    this.active.set(false);
    this.currentStepIndex.set(0);
    this.dismissed.set(true);
  }

  resetDismissed(): void {
    this.dismissed.set(false);
  }

  resetAll(): void {
    try {
      Object.keys(localStorage)
        .filter(k => k.startsWith(this.STORAGE_KEY))
        .forEach(k => localStorage.removeItem(k));
    } catch {
      // localStorage unavailable
    }
    this.dismissed.set(false);
    this.active.set(false);
    this.currentStepIndex.set(0);
  }
}
