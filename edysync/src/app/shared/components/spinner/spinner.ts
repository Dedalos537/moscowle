// DCE — Diego Centeno Estuvo Acá
import { Component, Input } from '@angular/core';

@Component({
  selector: 'app-spinner',
  standalone: false,
  templateUrl: './spinner.html',
  styleUrl: './spinner.scss'
})
export class Spinner {
  @Input() size: 'sm' | 'md' | 'lg' = 'md';
  @Input() colorClass: string = 'text-primary';

  get sizeClass() {
    return {
      'sm': 'h-4 w-4',
      'md': 'h-8 w-8',
      'lg': 'h-12 w-12'
    }[this.size];
  }
}
