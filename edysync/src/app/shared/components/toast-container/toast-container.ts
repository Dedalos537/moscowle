import { Component, ChangeDetectionStrategy, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { IconProp } from '@fortawesome/fontawesome-svg-core';
import { Subscription } from 'rxjs';
import { ToastService } from '../../../core/services/toast.service';
import { Toast, ToastType } from '../../../core/models/toast';

@Component({
  selector: 'app-toast-container',
  standalone: true,
  imports: [CommonModule, FontAwesomeModule],
  templateUrl: './toast-container.html',
  styleUrl: './toast-container.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ToastContainer implements OnInit, OnDestroy {
  toasts: Toast[] = [];
  private sub = new Subscription();

  constructor(private toastService: ToastService) {}

  ngOnInit() {
    this.sub.add(
      this.toastService.toasts$.subscribe(t => {
        this.toasts = t;
      })
    );
  }

  ngOnDestroy() {
    this.sub.unsubscribe();
  }

  dismiss(id: number) {
    this.toastService.remove(id);
  }

  alertClasses(type: ToastType): string {
    switch (type) {
      case 'success': return 'bg-success-container text-on-success-container border-success-container';
      case 'error': return 'bg-error-container text-on-error-container border-error-container';
      case 'warning': return 'bg-warning-container text-warning border-warning-container';
      case 'info': return 'bg-info-container text-info border-info-container';
    }
  }

  icon(type: ToastType): IconProp {
    switch (type) {
      case 'success': return ['fas', 'check-circle'];
      case 'error': return ['fas', 'exclamation-circle'];
      case 'warning': return ['fas', 'exclamation-triangle'];
      case 'info': return ['fas', 'info-circle'];
    }
  }
}
