import { Component, OnInit, OnDestroy, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { Subscription } from 'rxjs';
import { AdminService } from '../../../../core/services/admin.service';
import { AITrainingStatus } from '../../../../core/models/ai-training';
import { fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter } from '../../../../core/animations';
import { Button } from '../../../../shared/components/button/button';
import { Spinner } from '../../../../shared/components/spinner/spinner';
import { Card } from '../../../../shared/components/card/card';
import { Alert } from '../../../../shared/components/alert/alert';

@Component({
  selector: 'app-ai-training',
  standalone: true,
  templateUrl: './ai-training.html',
  styleUrl: './ai-training.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
  animations: [fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter],
  imports: [CommonModule, FontAwesomeModule, Button, Spinner, Card, Alert],
})
export class AiTraining implements OnInit, OnDestroy {
  status: AITrainingStatus = { model_exists: false, training_in_progress: false };
  loading = false;
  training = false;
  statusText = '';
  private subscriptions: Subscription = new Subscription();

  constructor(private admin: AdminService, private cdr: ChangeDetectorRef) {}

  ngOnInit() {
    this.loadStatus();
  }

  ngOnDestroy() {
    this.subscriptions.unsubscribe();
  }

  loadStatus() {
    this.loading = true;
    this.subscriptions.add(
      this.admin.getAITrainingStatus().subscribe({
        next: (res) => { this.status = res; this.loading = false; this.cdr.markForCheck(); },
        error: () => { this.loading = false; this.cdr.markForCheck(); }
      })
    );
  }

  triggerTraining() {
    this.training = true;
    this.statusText = '';
    this.subscriptions.add(
      this.admin.triggerAITraining().subscribe({
        next: (res) => {
          this.training = false;
          this.statusText = res.started ? 'Entrenamiento iniciado en segundo plano' : 'No se pudo iniciar';
          if (res.started) {
            this.status.model_exists = true;
            this.status.training_in_progress = true;
            setTimeout(() => this.loadStatus(), 5000);
          }
          this.cdr.markForCheck();
        },
        error: () => { this.training = false; this.statusText = 'Error al iniciar entrenamiento'; this.cdr.markForCheck(); }
      })
    );
  }
}
