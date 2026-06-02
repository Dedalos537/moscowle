import { Component, input, ChangeDetectionStrategy } from '@angular/core';

@Component({
  selector: 'app-progress-bar',
  standalone: true,
  imports: [],
  templateUrl: './progress-bar.html',
  styleUrl: './progress-bar.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ProgressBar {
  value = input(0);
  max = input(100);
  showLabel = input(false);
  size = input<'sm' | 'md' | 'lg'>('md');

  get percentage(): number {
    return Math.min(Math.max((this.value() / this.max()) * 100, 0), 100);
  }

  get trackClass(): string {
    const heights = { sm: 'h-1', md: 'h-2', lg: 'h-3' };
    return `${heights[this.size()]} bg-border/50 rounded-full`;
  }

  get fillClass(): string {
    const heights = { sm: 'h-1', md: 'h-2', lg: 'h-3' };
    return `${heights[this.size()]} bg-primary rounded-full transition-all duration-500 ease-out`;
  }
}
