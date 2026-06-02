import { Component, input, ChangeDetectionStrategy } from '@angular/core';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';

@Component({
  selector: 'app-chip',
  standalone: true,
  imports: [FontAwesomeModule],
  templateUrl: './chip.html',
  styleUrl: './chip.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Chip {
  label = input<string>('');
  variant = input<'primary' | 'secondary' | 'outline'>('primary');
  removable = input(false);

  get chipClasses() {
    const base = 'inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-label-caps transition-colors duration-200';
    const variants = {
      primary: 'bg-primary-container/15 text-primary-container',
      secondary: 'bg-surface-container-low text-on-surface-variant',
      outline: 'bg-transparent text-on-surface-variant border border-border'
    };
    return `${base} ${variants[this.variant()]}`;
  }
}
