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
      case 'error': return 'bg-red-50 text-red-700 border-red-200 dark:bg-red-500/10 dark:text-red-400 dark:border-red-500/20';
      case 'warning': return 'bg-yellow-50 text-yellow-700 border-yellow-200 dark:bg-yellow-500/10 dark:text-yellow-400 dark:border-yellow-500/20';
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
