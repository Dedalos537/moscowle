import { Component, Input, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';

@Component({
  selector: 'app-pill-status',
  standalone: false,
  templateUrl: './pill-status.html',
  styleUrl: './pill-status.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PillStatus {
  @Input() status: 'active' | 'completed' | 'pending' | 'error' | 'warning' = 'active';
  @Input() label: string = '';

  constructor(private cdr: ChangeDetectorRef) {}

  get pillClasses() {
    const base = 'inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-label-caps';
    const variants = {
      active: 'bg-primary-container text-primary',
      completed: 'bg-success-container text-success',
      pending: 'bg-surface-container-high text-on-surface-variant',
      error: 'bg-error-container text-on-error-container',
      warning: 'bg-warning-container text-warning'
    };
    return `${base} ${variants[this.status]}`;
  }

  get dotClass() {
    const variants = {
      active: 'bg-primary',
      completed: 'bg-success',
      pending: 'bg-outline',
      error: 'bg-error',
      warning: 'bg-warning'
    };
    return `w-1.5 h-1.5 rounded-full ${variants[this.status]}`;
  }
}
