import { Component, OnInit, OnDestroy, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { Subscription } from 'rxjs';
import { AdminService } from '../../../../core/services/admin.service';
import { YapeTransaction, YapeDashboardStats } from '../../../../core/models/yape';
import { fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter } from '../../../../core/animations';

@Component({
  selector: 'app-yape-import',
  standalone: false,
  templateUrl: './yape-import.html',
  styleUrl: './yape-import.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
  animations: [fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter]
})
export class YapeImport implements OnInit, OnDestroy {
  dashboard: YapeDashboardStats = { total: 0, pending: 0 };
  transactions: YapeTransaction[] = [];
  pendingTransactions: YapeTransaction[] = [];
  history: YapeTransaction[] = [];
  loading = false;
  importing = false;
  showImportModal = false;
  selectedFile: File | null = null;
  statusText = '';
  searchQuery = '';
  private subscriptions: Subscription = new Subscription();

  constructor(private admin: AdminService, private cdr: ChangeDetectorRef) {}

  ngOnInit() {
    this.loadDashboard();
    this.loadHistory();
  }

  ngOnDestroy() {
    this.subscriptions.unsubscribe();
  }

  loadDashboard() {
    this.subscriptions.add(
      this.admin.getYapeDashboard().subscribe({
        next: (res) => { this.dashboard = res; this.cdr.markForCheck(); },
        error: () => { this.cdr.markForCheck(); }
      })
    );
    this.subscriptions.add(
      this.admin.getYapePending().subscribe({
        next: (res) => { this.pendingTransactions = res.transactions; this.cdr.markForCheck(); },
        error: () => { this.cdr.markForCheck(); }
      })
    );
  }

  loadHistory() {
    this.loading = true;
    this.subscriptions.add(
      this.admin.getYapeHistory().subscribe({
        next: (res) => { this.history = res; this.loading = false; this.cdr.markForCheck(); },
        error: () => { this.loading = false; this.cdr.markForCheck(); }
      })
    );
  }

  openImportModal() { this.showImportModal = true; this.uploadName = ''; this.statusText = ''; }

  closeImportModal() { this.showImportModal = false; }

  onFileSelected(event: any) {
    this.selectedFile = event.target.files[0] || null;
  }

  importFile() {
    if (!this.selectedFile) return;
    this.importing = true;
    this.statusText = '';
    this.subscriptions.add(
      this.admin.importYapeFile(this.selectedFile).subscribe({
        next: (res) => {
          this.importing = false;
          this.statusText = res.success ? 'Importación exitosa' : 'Error en la importación';
          if (res.success) {
            this.closeImportModal();
            this.loadDashboard();
            this.loadHistory();
          }
          this.cdr.markForCheck();
        },
        error: () => { this.importing = false; this.statusText = 'Error al procesar el archivo'; this.cdr.markForCheck(); }
      })
    );
  }

  searchYape() {
    if (!this.searchQuery.trim()) return;
    this.subscriptions.add(
      this.admin.searchYape(this.searchQuery).subscribe({
        next: (res) => { this.transactions = res.results; this.cdr.markForCheck(); },
        error: () => { this.cdr.markForCheck(); }
      })
    );
  }

  private uploadName = '';
}
