// DCE — Diego Centeno Estuvo Acá
import { Component, OnInit } from '@angular/core';
import { AdminService } from '../../../../core/services/admin.service';
import { YapeTransaction, YapeDashboardStats } from '../../../../core/models/yape';
import { fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter } from '../../../../core/animations';

@Component({
  selector: 'app-yape-import',
  standalone: false,
  templateUrl: './yape-import.html',
  styleUrl: './yape-import.scss',
  animations: [fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter]
})
export class YapeImport implements OnInit {
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

  constructor(private admin: AdminService) {}

  ngOnInit() {
    this.loadDashboard();
    this.loadHistory();
  }

  loadDashboard() {
    this.admin.getYapeDashboard().subscribe({
      next: (res) => { this.dashboard = res; }
    });
    this.admin.getYapePending().subscribe({
      next: (res) => { this.pendingTransactions = res.transactions; }
    });
  }

  loadHistory() {
    this.loading = true;
    this.admin.getYapeHistory().subscribe({
      next: (res) => { this.history = res; this.loading = false; },
      error: () => { this.loading = false; }
    });
  }

  openImportModal() { this.showImportModal = true; this.selectedFile = null; this.statusText = ''; }

  closeImportModal() { this.showImportModal = false; }

  onFileSelected(event: any) {
    this.selectedFile = event.target.files[0] || null;
  }

  importFile() {
    if (!this.selectedFile) return;
    this.importing = true;
    this.statusText = '';
    this.admin.importYapeFile(this.selectedFile).subscribe({
      next: (res) => {
        this.importing = false;
        this.statusText = res.success ? 'Importación exitosa' : 'Error en la importación';
        if (res.success) {
          this.closeImportModal();
          this.loadDashboard();
          this.loadHistory();
        }
      },
      error: () => { this.importing = false; this.statusText = 'Error al procesar el archivo'; }
    });
  }

  searchYape() {
    if (!this.searchQuery.trim()) return;
    this.admin.searchYape(this.searchQuery).subscribe({
      next: (res) => { this.transactions = res.results; }
    });
  }
}
