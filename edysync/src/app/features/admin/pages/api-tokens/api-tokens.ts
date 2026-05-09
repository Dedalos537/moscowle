import { Component, OnInit } from '@angular/core';
import { AdminService } from '../../../../core/services/admin.service';
import { AdminAPIToken } from '../../../../core/models/api-token';

@Component({
  selector: 'app-api-tokens',
  standalone: false,
  templateUrl: './api-tokens.html',
  styleUrl: './api-tokens.scss'
})
export class ApiTokens implements OnInit {
  tokens: AdminAPIToken[] = [];
  loading = false;
  showCreateModal = false;
  rotate = false;
  newToken: string | null = null;
  creating = false;

  constructor(private admin: AdminService) {}

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

  deactivateToken(id: number) {
    this.admin.deactivateAPIToken(id).subscribe({
      next: () => { this.loadTokens(); },
    });
  }

  copyToken(token: string) {
    navigator.clipboard.writeText(token);
  }
}
