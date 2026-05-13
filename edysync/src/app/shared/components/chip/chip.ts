import { Component, Input } from '@angular/core';

@Component({
  selector: 'app-chip',
  standalone: false,
  templateUrl: './chip.html',
  styleUrl: './chip.scss'
})
export class Chip {
  @Input() label: string = '';
  @Input() variant: 'primary' | 'secondary' | 'outline' = 'primary';
  @Input() removable: boolean = false;

  get chipClasses() {
    const base = 'inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-label-caps transition-colors duration-200';
    const variants = {
      primary: 'bg-primary/10 text-primary',
      secondary: 'bg-surface-container-low text-on-surface-variant',
      outline: 'bg-transparent text-on-surface-variant border border-outline-variant'
    };
    return `${base} ${variants[this.variant]}`;
  }
}
