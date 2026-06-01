import { Component, OnInit, OnDestroy, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { Subscription } from 'rxjs';
import { AdminService } from '../../../../core/services/admin.service';
import { CSPReport, CSPReportFilter } from '../../../../core/models/csp-report';
import { fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter } from '../../../../core/animations';

@Component({
  selector: 'app-csp-reports',
  standalone: false,
  templateUrl: './csp-reports.html',
  styleUrl: './csp-reports.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
  animations: [fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter]
})
export class CspReports implements OnInit, OnDestroy {
  reports: CSPReport[] = [];
  loading = false;
  error: string | null = null;
  total = 0;
  page = 1;
  pages = 1;
  filter: CSPReportFilter = { directive: '', blocked_uri: '', since: '' };
  private subscriptions: Subscription = new Subscription();

  constructor(private admin: AdminService, private cdr: ChangeDetectorRef) {}

  ngOnInit() {
    this.loadReports();
  }

  ngOnDestroy() {
    this.subscriptions.unsubscribe();
  }

  loadReports() {
    this.loading = true;
    this.error = null;
    this.subscriptions.add(
      this.admin.getCSPReports({ ...this.filter, page: this.page, per_page: 25 }).subscribe({
        next: (res) => {
          this.reports = res.items;
          this.total = res.total;
          this.page = res.page;
          this.pages = res.pages;
          this.loading = false;
          this.cdr.markForCheck();
        },
        error: (err) => { this.loading = false; this.error = err.error?.message || err.message || 'Error al cargar reportes CSP'; this.cdr.markForCheck(); }
      })
    );
  }

  onFilterChange() {
    this.page = 1;
    this.loadReports();
  }

  goToPage(p: number) {
    this.page = p;
    this.loadReports();
  }

  exportCsv() {
    this.subscriptions.add(
      this.admin.exportCSPReportsCsv(this.filter).subscribe({
        next: blob => {
          const url = window.URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = 'csp-reports.csv';
          a.click();
          window.URL.revokeObjectURL(url);
          this.cdr.markForCheck();
        },
        error: (err) => { this.error = err.error?.message || err.message || 'Error al exportar CSV'; this.cdr.markForCheck(); }
      })
    );
  }
}
