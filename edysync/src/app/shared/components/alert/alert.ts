import { Component, input, output, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { IconProp } from '@fortawesome/fontawesome-svg-core';

@Component({
  selector: 'app-alert',
  standalone: true,
  imports: [CommonModule, FontAwesomeModule],
  templateUrl: './alert.html',
  styleUrl: './alert.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Alert {
  type = input<'success' | 'error' | 'warning' | 'info'>('info');
  message = input<string>('');
  dismissible = input(true);
  dismissed = output<void>();

  visible = true;

  get alertClasses() {
    switch(this.type()) {
      case 'success': return 'bg-success-container text-success border-success-container';
      case 'error': return 'bg-error-container text-on-error-container border-error-container';
      case 'warning': return 'bg-warning-container text-warning border-warning-container';
      case 'info': return 'bg-info-container text-info border-info-container';
    }
  }

  get icon(): IconProp {
    switch(this.type()) {
      case 'success': return ['fas', 'circle-check'];
      case 'error': return ['fas', 'circle-exclamation'];
      case 'warning': return ['fas', 'triangle-exclamation'];
      case 'info': return ['fas', 'circle-info'];
    }
  }

  dismiss() {
    this.visible = false;
    this.dismissed.emit();
  }
}
