// DCE — Diego Centeno Estuvo Acá
import { Component, Input } from '@angular/core';
import { IconProp } from '@fortawesome/fontawesome-svg-core';

@Component({
  selector: 'app-alert',
  standalone: false,
  templateUrl: './alert.html',
  styleUrl: './alert.scss'
})
export class Alert {
  @Input() type: 'success' | 'error' | 'warning' | 'info' = 'info';
  @Input() message: string = '';

  get alertClasses() {
    switch(this.type) {
      case 'success': return 'bg-green-50 text-green-700 border-green-200 dark:bg-green-500/10 dark:text-green-400 dark:border-green-500/20';
      case 'error': return 'bg-error-container text-on-error-container border-error/20';
      case 'warning': return 'bg-amber-50 text-amber-800 border-amber-200 dark:bg-amber-500/10 dark:text-amber-400 dark:border-amber-500/20';
      case 'info': return 'bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-500/10 dark:text-blue-400 dark:border-blue-500/20';
    }
  }

  get icon(): IconProp {
    switch(this.type) {
      case 'success': return ['fas', 'check-circle'];
      case 'error': return ['fas', 'exclamation-circle'];
      case 'warning': return ['fas', 'exclamation-triangle'];
      case 'info': return ['fas', 'info-circle'];
    }
  }
}
