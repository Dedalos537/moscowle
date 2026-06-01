import { Component, Input, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';

@Component({
  selector: 'app-chip',
  standalone: false,
  templateUrl: './chip.html',
  styleUrl: './chip.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Chip {
  @Input() label: string = '';
  @Input() variant: 'primary' | 'secondary' | 'outline' = 'primary';
  @Input() removable: boolean = false;

  constructor(private cdr: ChangeDetectorRef) {}

  get chipClasses() {
    const base = 'inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-label-caps transition-colors duration-200';
    const variants = {
      primary: 'bg-primary-container/15 text-primary-container',
      secondary: 'bg-surface-container-low text-on-surface-variant',
      outline: 'bg-transparent text-on-surface-variant border border-border'
    };
    return `${base} ${variants[this.variant]}`;
  }
}
