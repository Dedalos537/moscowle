import { Injectable, signal, computed, inject } from '@angular/core';
import { BeaconService, BeaconStep } from 'ng-beacon';
import { WIZARD_STEPS } from '../config/wizard-steps.config';
import { ContextDetectorService } from './context-detector.service';

@Injectable({ providedIn: 'root' })
export class WizardService {
  private beaconService = inject(BeaconService);
  private contextDetector = inject(ContextDetectorService);

  private readonly STORAGE_KEY = 'edysync_wizard_completed';

  steps = computed<BeaconStep[]>(() => {
    const ctx = this.contextDetector.context();
    if (!ctx.role || !ctx.route) return [];

    return WIZARD_STEPS
      .filter(w => w.route === ctx.route && (!w.role || w.role === ctx.role))
      .flatMap(w => w.steps.map(s => ({
        id: `${ctx.route}_${s.title.replace(/\s+/g, '_').toLowerCase()}`,
        title: s.title,
        content: s.description,
        position: (s.position === 'left' ? 'start' : s.position === 'right' ? 'end' : s.position === 'center' ? 'center' : s.position === 'top' ? 'above' : 'below') as 'above' | 'below' | 'start' | 'end' | 'center',
        selector: s.selector,
        showWithoutTarget: s.position === 'center',
      })));
  });

  active = this.beaconService.isActive;
  currentStepIndex = computed(() => this.beaconService.currentStepIndex() ?? 0);
  totalSteps = this.beaconService.totalSteps;
  isLastStep = this.beaconService.isLastStep;

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
    const steps = this.steps();
    if (steps.length > 0) {
      this.beaconService.start(steps);
    }
  }

  next(): void {
    this.beaconService.next();
  }

  prev(): void {
    this.beaconService.prev();
  }

  finish(): void {
    this.beaconService.stop();
  }

  dismiss(): void {
    this.beaconService.stop();
  }

  resetAll(): void {
    try {
      Object.keys(localStorage)
        .filter(k => k.startsWith(this.STORAGE_KEY))
        .forEach(k => localStorage.removeItem(k));
    } catch {
      // localStorage unavailable
    }
    this.beaconService.stop();
  }
}
