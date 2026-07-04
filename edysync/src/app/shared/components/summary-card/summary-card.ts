import { Component, input } from '@angular/core';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { IconProp } from '@fortawesome/fontawesome-svg-core';
import { Spinner } from '../spinner/spinner';

@Component({
  selector: 'app-summary-card',
  standalone: true,
  imports: [FontAwesomeModule, Spinner],
  templateUrl: './summary-card.html',
  styleUrl: './summary-card.scss',
})
export class SummaryCard {
  label = input.required<string>();
  value = input.required<string | number | null>();
  loading = input(false);
  subtitle = input<string>();
  icon = input.required<IconProp>();
  variant = input<'primary' | 'secondary' | 'info' | 'warning' | 'error'>('primary');
  staggerIndex = input<number | undefined>(undefined);
}
