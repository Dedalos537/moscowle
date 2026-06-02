import { Component, input, ChangeDetectionStrategy } from '@angular/core';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';

@Component({
  selector: 'app-spinner',
  standalone: true,
  imports: [FontAwesomeModule],
  templateUrl: './spinner.html',
  styleUrl: './spinner.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Spinner {
  size = input<'sm' | 'md' | 'lg'>('md');
  colorClass = input<string>('text-primary');

  get sizeClass() {
    return {
      'sm': 'h-4 w-4',
      'md': 'h-8 w-8',
      'lg': 'h-12 w-12'
    }[this.size()];
  }
}
