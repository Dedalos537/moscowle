import { Component, Input } from '@angular/core';

@Component({
  selector: 'app-pill-status',
  standalone: false,
  templateUrl: './pill-status.html',
  styleUrl: './pill-status.scss'
})
export class PillStatus {
  @Input() status: 'active' | 'completed' | 'pending' | 'error' | 'warning' = 'active';
  @Input() label: string = '';

  get pillClasses() {
    const base = 'inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-label-caps';
    const variants = {
      active: 'bg-primary/10 text-primary',
      completed: 'bg-primary/10 text-primary',
      pending: 'bg-surface-container-high text-on-surface-variant',
      error: 'bg-error-container text-on-error-container',
      warning: 'bg-amber-50 text-amber-700 dark:bg-amber-500/10 dark:text-amber-400'
    };
    return `${base} ${variants[this.status]}`;
  }

  get dotClass() {
    const variants = {
      active: 'bg-primary',
      completed: 'bg-primary',
      pending: 'bg-outline',
      error: 'bg-error',
      warning: 'bg-amber-500'
    };
    return `w-1.5 h-1.5 rounded-full ${variants[this.status]}`;
  }
}
