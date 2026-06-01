import { Component, Input, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';

@Component({
  selector: 'app-progress-bar',
  standalone: false,
  templateUrl: './progress-bar.html',
  styleUrl: './progress-bar.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ProgressBar {
  @Input() value: number = 0;
  @Input() max: number = 100;
  @Input() showLabel: boolean = false;
  @Input() size: 'sm' | 'md' | 'lg' = 'md';

  constructor(private cdr: ChangeDetectorRef) {}

  get percentage(): number {
    return Math.min(Math.max((this.value / this.max) * 100, 0), 100);
  }

  get trackClass(): string {
    const heights = { sm: 'h-1', md: 'h-2', lg: 'h-3' };
    return `${heights[this.size]} bg-border/50 rounded-full`;
  }

  get fillClass(): string {
    const heights = { sm: 'h-1', md: 'h-2', lg: 'h-3' };
    return `${heights[this.size]} bg-primary rounded-full transition-all duration-500 ease-out`;
  }
}
