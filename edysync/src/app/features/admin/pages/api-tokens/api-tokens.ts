import { Component, OnInit, OnDestroy, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { Subscription } from 'rxjs';
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
  changeDetection: ChangeDetectionStrategy.OnPush,
  animations: [fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter]
})
export class ApiTokens implements OnInit, OnDestroy {
  tokens: AdminAPIToken[] = [];
  loading = false;
  error: string | null = null;
  showCreateModal = false;
  rotate = false;
  newToken: string | null = null;
  creating = false;
  private subscriptions: Subscription = new Subscription();

  constructor(
    private admin: AdminService,
    private confirmService: ConfirmService,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit() {
    this.loadTokens();
  }

  ngOnDestroy() {
    this.subscriptions.unsubscribe();
  }

  loadTokens() {
    this.loading = true;
    this.error = null;
    this.subscriptions.add(
      this.admin.getAPITokens().subscribe({
        next: (res) => { this.tokens = res.tokens; this.loading = false; this.cdr.markForCheck(); },
        error: (err) => { this.loading = false; this.error = err.error?.message || err.message || 'Error al cargar tokens'; this.cdr.markForCheck(); }
      })
    );
  }

  openCreateModal() { this.showCreateModal = true; this.rotate = false; this.newToken = null; }

  closeCreateModal() { this.showCreateModal = false; }

  createToken() {
    this.creating = true;
    this.subscriptions.add(
      this.admin.createAPIToken(this.rotate).subscribe({
        next: (res) => {
          this.newToken = res.token;
          this.creating = false;
          this.loadTokens();
          this.cdr.markForCheck();
        },
        error: (err) => { this.creating = false; this.error = err.error?.message || err.message || 'Error al crear token'; this.cdr.markForCheck(); }
      })
    );
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
    this.subscriptions.add(
      this.admin.deactivateAPIToken(id).subscribe({
        next: () => { this.loadTokens(); this.cdr.markForCheck(); },
        error: (err) => { this.error = err.error?.message || err.message || 'Error al desactivar token'; this.cdr.markForCheck(); }
      })
    );
  }

  copyToken(token: string) {
    navigator.clipboard.writeText(token);
  }
}
