import { Component, OnInit, OnDestroy } from '@angular/core';
import { Subscription } from 'rxjs';
import { AlertService, AlertConfig } from '../../../core/services/alert.service';

@Component({
  selector: 'app-alert-modal',
  standalone: false,
  templateUrl: './alert-modal.component.html',
  styleUrl: './alert-modal.component.scss',
})
export class AlertModal implements OnInit, OnDestroy {
  visible = false;
  config: AlertConfig | null = null;
  private sub!: Subscription;

  constructor(private alertService: AlertService) {}

  ngOnInit() {
    this.sub = this.alertService.state$.subscribe((state) => {
      this.visible = state.visible;
      this.config = state.config;
    });
  }

  ngOnDestroy() {
    this.sub?.unsubscribe();
  }

  close() {
    this.alertService.close();
  }

  getDefaultTitle(type: string): string {
    switch (type) {
      case 'success': return 'Operación exitosa';
      case 'error': return 'Error';
      case 'warning': return 'Advertencia';
      default: return 'Información';
    }
  }
}
