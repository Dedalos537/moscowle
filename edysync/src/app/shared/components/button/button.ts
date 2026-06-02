import { Component, input, output, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { IconProp } from '@fortawesome/fontawesome-svg-core';

@Component({
  selector: 'app-button',
  standalone: true,
  imports: [CommonModule, FontAwesomeModule],
  templateUrl: './button.html',
  styleUrl: './button.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Button {
  label = input<string>('');
  variant = input<'primary' | 'secondary' | 'danger' | 'ghost'>('primary');
  icon = input<IconProp>();
  disabled = input(false);
  type = input<'button' | 'submit'>('button');

  clicked = output<Event>();

  readonly variantMap: Record<string, Record<string, boolean>> = {
    primary: { 'btn--primary': true },
    secondary: { 'btn--secondary': true },
    danger: { 'btn--danger': true },
    ghost: { 'btn--ghost': true }
  };

  get btnClass(): Record<string, boolean> {
    return {
      ...this.variantMap[this.variant()],
      'btn--disabled': this.disabled()
    };
  }

  onClick(event: Event) {
    if (!this.disabled()) {
      this.clicked.emit(event);
    }
  }
}
