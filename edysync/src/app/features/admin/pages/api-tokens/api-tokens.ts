import { Component, OnInit } from '@angular/core';
import { AdminService } from '../../../../core/services/admin.service';
import { AdminAPIToken } from '../../../../core/models/api-token';
import { fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter } from '../../../../core/animations';
import { firstValueFrom } from 'rxjs';
import { ConfirmService } from '../../../../core/services/confirm.service';

@Component({
  selector: 'app-api-tokens',
  standalone: false,
  templateUrl: './api-tokens.html',
  styleUrl: './api-tokens.scss',
  animations: [fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter]
})
export class ApiTokens implements OnInit {
  tokens: AdminAPIToken[] = [];
  loading = false;
  showCreateModal = false;
  rotate = false;
  newToken: string | null = null;
  creating = false;

  constructor(
    private admin: AdminService,
    private confirmService: ConfirmService,
  ) {}

  ngOnInit() {
    this.loadTokens();
  }

  loadTokens() {
    this.loading = true;
    this.admin.getAPITokens().subscribe({
      next: (res) => { this.tokens = res.tokens; this.loading = false; },
      error: () => { this.loading = false; }
    });
  }

  openCreateModal() { this.showCreateModal = true; this.rotate = false; this.newToken = null; }

  closeCreateModal() { this.showCreateModal = false; }

  createToken() {
    this.creating = true;
    this.admin.createAPIToken(this.rotate).subscribe({
      next: (res) => {
        this.newToken = res.token;
        this.creating = false;
        this.loadTokens();
      },
      error: () => { this.creating = false; }
    });
  }

  async deactivateToken(id: number) {
    const confirmed = await firstValueFrom(this.confirmService.confirm({
      title: 'Desactivar Token',
      message: '¿Estas seguro de que deseas desactivar este token? Los servicios que lo usan dejaran de funcionar.',
      confirmText: 'Desactivar',
      cancelText: 'Cancelar',
      variant: 'danger',
    }));
    if (!confirmed) return;
    this.admin.deactivateAPIToken(id).subscribe({
      next: () => { this.loadTokens(); },
    });
  }

  copyToken(token: string) {
    navigator.clipboard.writeText(token);
  }
}
