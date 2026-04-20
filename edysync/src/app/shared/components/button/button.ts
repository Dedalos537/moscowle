import { Component, Input, Output, EventEmitter } from '@angular/core';
import { IconProp } from '@fortawesome/fontawesome-svg-core';

@Component({
  selector: 'app-button',
  standalone: false,
  templateUrl: './button.html',
  styleUrl: './button.scss'
})
export class Button {
  @Input() label: string = 'Button';
  @Input() variant: 'primary' | 'secondary' | 'danger' | 'ghost' = 'primary';
  // Soporta arreglos como ['fas', 'check'] gracias al FaIconLibrary global que pondremos
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
    const base = 'flex items-center justify-center gap-2 px-6 py-2.5 rounded-full font-medium transition-all shadow-sm focus:outline-none focus:ring-2 focus:ring-offset-2';
    const variants = {
      primary: 'bg-primary text-white hover:bg-opacity-90 focus:ring-primary/50',
      secondary: 'bg-surface border border-gray-200 dark:border-gray-700 text-charcoal hover:bg-gray-50 dark:hover:bg-slate-800 focus:ring-gray-200',
      danger: 'bg-error text-white hover:bg-red-600 focus:ring-error/50',
      ghost: 'bg-transparent text-charcoal hover:bg-gray-100 dark:hover:bg-slate-800 shadow-none'
    };
    const disabledClass = this.disabled ? 'opacity-60 cursor-not-allowed' : 'cursor-pointer';
    
    return `${base} ${variants[this.variant]} ${disabledClass}`;
  }
}
