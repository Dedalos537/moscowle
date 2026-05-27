import { Component, Input, Output, EventEmitter } from '@angular/core';
import { IconProp } from '@fortawesome/fontawesome-svg-core';

@Component({
  selector: 'app-button',
  standalone: false,
  templateUrl: './button.html',
  styleUrl: './button.scss'
})
export class Button {
  @Input() label: string = '';
  @Input() variant: 'primary' | 'secondary' | 'danger' | 'ghost' = 'primary';
  @Input() icon?: IconProp;
  @Input() disabled: boolean = false;
  @Input() type: 'button' | 'submit' = 'button';

  @Output() clicked = new EventEmitter<Event>();

  readonly variantMap: Record<string, Record<string, boolean>> = {
    primary: { 'btn--primary': true },
    secondary: { 'btn--secondary': true },
    danger: { 'btn--danger': true },
    ghost: { 'btn--ghost': true }
  };

  get btnClass(): Record<string, boolean> {
    return {
      ...this.variantMap[this.variant],
      'btn--disabled': this.disabled
    };
  }

  onClick(event: Event) {
    if (!this.disabled) {
      this.clicked.emit(event);
    }
  }
}
