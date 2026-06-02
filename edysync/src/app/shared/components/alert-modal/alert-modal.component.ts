import { Component, OnInit, OnDestroy, ChangeDetectionStrategy } from '@angular/core';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { Subscription } from 'rxjs';
import { AlertService, AlertConfig } from '../../../core/services/alert.service';
import { Button } from '../button/button';

@Component({
  selector: 'app-alert-modal',
  standalone: true,
  imports: [FontAwesomeModule, Button],
  templateUrl: './alert-modal.component.html',
  styleUrl: './alert-modal.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
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
