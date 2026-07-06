import { Component, input, ChangeDetectionStrategy } from '@angular/core';
import { RouterModule } from '@angular/router';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { IconProp } from '@fortawesome/fontawesome-svg-core';

@Component({
  selector: 'app-action-card',
  standalone: true,
  imports: [RouterModule, FontAwesomeModule],
  templateUrl: './action-card.html',
  styleUrl: './action-card.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ActionCard {
  routerLink = input.required<string>();
  icon = input.required<IconProp>();
  variant = input<'primary' | 'info' | 'warning'>('primary');
  title = input.required<string>();
  description = input.required<string>();
  actionText = input.required<string>();
}
