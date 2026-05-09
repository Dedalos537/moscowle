import { Component, OnInit } from '@angular/core';
import { AdminService } from '../../../../core/services/admin.service';
import { AITrainingStatus } from '../../../../core/models/ai-training';

@Component({
  selector: 'app-ai-training',
  standalone: false,
  templateUrl: './ai-training.html',
  styleUrl: './ai-training.scss'
})
export class AiTraining implements OnInit {
  status: AITrainingStatus = { model_exists: false, training_in_progress: false };
  loading = false;
  training = false;
  statusText = '';

  constructor(private admin: AdminService) {}

  ngOnInit() {
    this.loadStatus();
  }

  loadStatus() {
    this.loading = true;
    this.admin.getAITrainingStatus().subscribe({
      next: (res) => { this.status = res; this.loading = false; },
      error: () => { this.loading = false; }
    });
  }

  triggerTraining() {
    this.training = true;
    this.statusText = '';
    this.admin.triggerAITraining().subscribe({
      next: (res) => {
        this.training = false;
        this.statusText = res.started ? 'Entrenamiento iniciado en segundo plano' : 'No se pudo iniciar';
        if (res.started) {
          this.status.model_exists = true;
          this.status.training_in_progress = true;
          setTimeout(() => this.loadStatus(), 5000);
        }
      },
      error: () => { this.training = false; this.statusText = 'Error al iniciar entrenamiento'; }
    });
  }
}
