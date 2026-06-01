import { Component, Input, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { IconProp } from '@fortawesome/fontawesome-svg-core';

@Component({
  selector: 'app-card',
  standalone: false,
  templateUrl: './card.html',
  styleUrl: './card.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Card {
  @Input() title?: string;
  @Input() subtitle?: string;
  @Input() icon?: IconProp;
  @Input() padding: 'md' | 'lg' = 'md';

  constructor(private cdr: ChangeDetectorRef) {}
}
