// DCE — Diego Centeno Estuvo Acá
import { Component, OnInit } from '@angular/core';
import { AdminService } from '../../../../core/services/admin.service';
import { CSPReport, CSPReportFilter } from '../../../../core/models/csp-report';
import { fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter } from '../../../../core/animations';

@Component({
  selector: 'app-csp-reports',
  standalone: false,
  templateUrl: './csp-reports.html',
  styleUrl: './csp-reports.scss',
  animations: [fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter]
})
export class CspReports implements OnInit {
  reports: CSPReport[] = [];
  loading = false;
  total = 0;
  page = 1;
  pages = 1;
  filter: CSPReportFilter = { directive: '', blocked_uri: '', since: '' };

  constructor(private admin: AdminService) {}

  ngOnInit() {
    this.loadReports();
  }

  loadReports() {
    this.loading = true;
    this.admin.getCSPReports({ ...this.filter, page: this.page, per_page: 25 }).subscribe({
      next: (res) => {
        this.reports = res.items;
        this.total = res.total;
        this.page = res.page;
        this.pages = res.pages;
        this.loading = false;
      },
      error: () => { this.loading = false; }
    });
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
    this.admin.exportCSPReportsCsv(this.filter).subscribe(blob => {
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'csp-reports.csv';
      a.click();
      window.URL.revokeObjectURL(url);
    });
  }
}
