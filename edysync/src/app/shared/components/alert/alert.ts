import { Component, Input, Output, EventEmitter, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { IconProp } from '@fortawesome/fontawesome-svg-core';

@Component({
  selector: 'app-alert',
  standalone: false,
  templateUrl: './alert.html',
  styleUrl: './alert.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Alert {
  @Input() type: 'success' | 'error' | 'warning' | 'info' = 'info';
  @Input() message: string = '';
  @Input() dismissible: boolean = true;
  @Output() dismissed = new EventEmitter<void>();

  visible = true;

  constructor(private cdr: ChangeDetectorRef) {}

  get alertClasses() {
    switch(this.type) {
      case 'success': return 'bg-success-container text-success border-success-container';
      case 'error': return 'bg-error-container text-on-error-container border-error-container';
      case 'warning': return 'bg-warning-container text-warning border-warning-container';
      case 'info': return 'bg-info-container text-info border-info-container';
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

  dismiss() {
    this.visible = false;
    this.dismissed.emit();
  }
}
