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

  onClick(event: Event) {
    if (!this.disabled) {
      this.clicked.emit(event);
    }
  }

  get buttonClasses() {
    const base = 'flex items-center justify-center gap-2 px-6 py-2.5 rounded-lg font-medium transition-all shadow-sm focus:outline-none focus:ring-2 focus:ring-offset-2';
    const variants = {
      primary: 'bg-primary text-on-primary hover:brightness-110 focus:ring-primary/50',
      secondary: 'bg-surface text-charcoal border border-border hover:bg-surface-container-low focus:ring-border/50',
      danger: 'bg-error text-on-error hover:brightness-110 focus:ring-error/50',
      ghost: 'bg-transparent text-charcoal hover:bg-surface-container-low shadow-none focus:ring-border/50'
    };
    const disabledClass = this.disabled ? 'opacity-60 cursor-not-allowed' : 'cursor-pointer';

    return `${base} ${variants[this.variant]} ${disabledClass}`;
  }
}
