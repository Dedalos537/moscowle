import { Component, OnInit, OnDestroy, ViewChild, ChangeDetectionStrategy, ChangeDetectorRef, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { BaseChartDirective } from 'ng2-charts';
import { Chart, registerables } from 'chart.js';
import type { ChartConfiguration, ChartData } from 'chart.js';
import { HeaderService } from '../../../../core/services/header.service';
import { AdminService } from '../../../../core/services/admin.service';
import { LogViewerService, LogEntry } from '../../../../core/services/log-viewer.service';
import { ConfirmService } from '../../../../core/services/confirm.service';
import { CSPReport, CSPReportFilter } from '../../../../core/models/csp-report';
import { AdminAPIToken } from '../../../../core/models/api-token';
import { Subscription, firstValueFrom, interval } from 'rxjs';
import { fadeInUp, scaleIn, listStagger, cardEnter } from '../../../../core/animations';
import { Button } from '../../../../shared/components/button/button';
import { Spinner } from '../../../../shared/components/spinner/spinner';
import { Input } from '../../../../shared/components/input/input';
import { Alert } from '../../../../shared/components/alert/alert';
import { Modal } from '../../../../shared/components/modal/modal';

Chart.register(...registerables);

type TabId = 'railway' | 'logs' | 'csp' | 'tokens';

@Component({
  selector: 'app-visor-funcionamiento',
  standalone: true,
  imports: [CommonModule, FormsModule, FontAwesomeModule, BaseChartDirective, Button, Spinner, Input, Alert, Modal],
  templateUrl: './visor-funcionamiento.html',
  styleUrl: './visor-funcionamiento.scss',
  animations: [fadeInUp, scaleIn, listStagger, cardEnter],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class VisorFuncionamiento implements OnInit, OnDestroy {
  activeTab: TabId = 'railway';

  private headerService = inject(HeaderService);
  private admin = inject(AdminService);
  private logViewer = inject(LogViewerService);
  private confirmService = inject(ConfirmService);
  private cdr = inject(ChangeDetectorRef);

  private subs = new Subscription();

  @ViewChild('railwayChart') railwayChart?: BaseChartDirective;
  @ViewChild('networkChart') networkChart?: BaseChartDirective;

  // --- Railway history ---
  railwayLoading = true;
  railwayError: string | null = null;
  railwayDateFrom = '';
  railwayDateTo = '';
  railwayChartData: ChartData<'bar'> = { labels: [], datasets: [] };
  railwayChartOptions: ChartConfiguration<'bar'>['options'] = {};
  networkChartData: ChartData<'line'> = { labels: [], datasets: [] };
  networkChartOptions: ChartConfiguration<'line'>['options'] = {};
  railwaySnapshot: any = null;

  // --- Logs ---
  logs: LogEntry[] = [];
  logsLoading = true;
  logsError: string | null = null;
  logsLevelFilter = '';
  logsSearchQuery = '';
  logsExpandedIndex: number | null = null;
  logsAutoRefresh = false;
  private logsRefreshSub?: Subscription;
  readonly logsLevels = ['', 'ERROR', 'WARNING', 'INFO', 'DEBUG'];

  // --- CSP ---
  cspReports: CSPReport[] = [];
  cspLoading = false;
  cspError: string | null = null;
  cspTotal = 0;
  cspPage = 1;
  cspPages = 1;
  cspFilter: CSPReportFilter = { directive: '', blocked_uri: '', since: '' };

  // --- Tokens ---
  tokens: AdminAPIToken[] = [];
  tokensLoading = false;
  tokensError: string | null = null;
  showCreateModal = false;
  rotate = false;
  newToken: string | null = null;
  creating = false;

  ngOnInit() {
    this.headerService.setConfig({
      title: 'Centro de Operaciones',
      subtitle: 'Métricas, logs y seguridad del sistema',
      icon: ['fas', 'desktop'],
    });
    const now = new Date();
    const yesterday = new Date(now.getTime() - 24 * 60 * 60 * 1000);
    this.railwayDateFrom = yesterday.toISOString().slice(0, 16);
    this.railwayDateTo = now.toISOString().slice(0, 16);
    this.loadRailwayHistory();
    this.loadRailwaySnapshot();
    this.loadLogs();
    this.loadCspReports();
    this.loadTokens();
  }

  ngOnDestroy() {
    this.headerService.reset();
    this.subs.unsubscribe();
    this.logsRefreshSub?.unsubscribe();
  }

  switchTab(tab: TabId) {
    this.activeTab = tab;
    if (tab === 'railway') {
      setTimeout(() => { this.railwayChart?.update(); this.networkChart?.update(); }, 100);
    }
  }

  // --- Railway ---
  loadRailwaySnapshot() {
    this.subs.add(
      this.admin.getRailwayMetrics().subscribe({
        next: (res) => { this.railwaySnapshot = res; this.cdr.markForCheck(); },
        error: () => {},
      })
    );
  }

  loadRailwayHistory() {
    this.railwayLoading = true;
    this.railwayError = null;
    this.subs.add(
      this.admin.getRailwayMetricsHistory(
        this.railwayDateFrom ? new Date(this.railwayDateFrom).toISOString() : undefined,
        this.railwayDateTo ? new Date(this.railwayDateTo).toISOString() : undefined,
      ).subscribe({
        next: (res) => {
          this.railwayLoading = false;
          if (!res.success || !res.data) {
            this.railwayError = res.error || 'Error al cargar histórico';
            this.cdr.markForCheck();
            return;
          }
          this.buildRailwayChart(res.data);
          this.buildNetworkChart(res.data);
          this.cdr.markForCheck();
        },
        error: (err) => {
          this.railwayLoading = false;
          this.railwayError = err.error?.message || err.message || 'Error al cargar histórico';
          this.cdr.markForCheck();
        },
      })
    );
  }

  private buildRailwayChart(data: any) {
    const series = data.series;
    if (!series?.CPU_USAGE || !series?.MEMORY_USAGE_GB) {
      this.railwayError = 'No hay datos históricos disponibles';
      return;
    }

    const timestamps = series.CPU_USAGE.map((v: any) => {
      const d = new Date(v.ts);
      return d.toLocaleString('es-PE', { hour: '2-digit', minute: '2-digit', month: 'short', day: 'numeric' });
    });

    const cpuLimit = series.CPU_LIMIT?.[0]?.value || 1;
    const cpuPercentage = series.CPU_USAGE.map((v: any) => +(v.value / cpuLimit * 100).toFixed(1));

    const memLimit = series.MEMORY_LIMIT_GB?.[0]?.value || 1;
    const memPercentage = series.MEMORY_USAGE_GB.map((v: any) => +(v.value / memLimit * 100).toFixed(1));

    const allValues = [...cpuPercentage, ...memPercentage];
    const maxVal = Math.max(...allValues, 1);
    const suggestedMax = Math.ceil(maxVal * 1.3);

    this.railwayChartData = {
      labels: timestamps,
      datasets: [
        {
          label: 'CPU (%)',
          data: cpuPercentage,
          backgroundColor: 'rgba(59, 130, 246, 0.7)',
          borderColor: 'rgb(59, 130, 246)',
          borderWidth: 1,
          borderRadius: 4,
        },
        {
          label: 'Memoria (%)',
          data: memPercentage,
          backgroundColor: 'rgba(16, 185, 129, 0.7)',
          borderColor: 'rgb(16, 185, 129)',
          borderWidth: 1,
          borderRadius: 4,
        },
      ],
    };

    this.railwayChartOptions = {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: {
          display: true,
          position: 'top',
          labels: { usePointStyle: true, padding: 16, font: { family: 'var(--font-accent)', size: 12, weight: 700 } },
        },
        tooltip: {
          callbacks: {
            label: (ctx) => `${ctx.dataset.label}: ${ctx.parsed.y}%`,
          },
        },
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: { maxRotation: 45, font: { size: 10 } },
        },
        y: {
          beginAtZero: true,
          suggestedMax,
          grid: { color: 'rgba(0,0,0,0.06)' },
          ticks: { callback: (v) => `${v}%` },
        },
      },
    };

    if (this.railwayChart) this.railwayChart.update();
  }

  private buildNetworkChart(data: any) {
    const series = data.series;
    const rxRaw = series?.NETWORK_RX_BYTES;
    const txRaw = series?.NETWORK_TX_BYTES;

    if (!rxRaw?.length) return;

    const timestamps = rxRaw.map((v: any) => {
      const d = new Date(v.ts);
      return d.toLocaleString('es-PE', { hour: '2-digit', minute: '2-digit', month: 'short', day: 'numeric' });
    });

    const rxData = rxRaw.map((v: any) => +(v.value / 1_000_000).toFixed(3));
    const txData = txRaw?.length ? txRaw.map((v: any) => +(v.value / 1_000_000).toFixed(3)) : [];

    const allNet = [...rxData, ...txData].filter(v => v > 0);
    const maxNet = allNet.length ? Math.max(...allNet) : 1;
    const suggestedMaxNet = Math.ceil(maxNet * 1.3);

    this.networkChartData = {
      labels: timestamps,
      datasets: [
        {
          label: 'RX (Mbps)',
          data: rxData,
          backgroundColor: 'rgba(139, 92, 246, 0.15)',
          borderColor: 'rgb(139, 92, 246)',
          borderWidth: 2,
          fill: true,
          tension: 0.3,
          pointRadius: 2,
          pointHoverRadius: 5,
        },
        {
          label: 'TX (Mbps)',
          data: txData,
          backgroundColor: 'rgba(251, 146, 60, 0.15)',
          borderColor: 'rgb(251, 146, 60)',
          borderWidth: 2,
          fill: true,
          tension: 0.3,
          pointRadius: 2,
          pointHoverRadius: 5,
        },
      ],
    };

    this.networkChartOptions = {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: {
          display: true,
          position: 'top',
          labels: { usePointStyle: true, padding: 16, font: { family: 'var(--font-accent)', size: 12, weight: 700 } },
        },
        tooltip: {
          callbacks: {
            label: (ctx) => `${ctx.dataset.label}: ${ctx.parsed.y} Mbps`,
          },
        },
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: { maxRotation: 45, font: { size: 10 } },
        },
        y: {
          beginAtZero: true,
          suggestedMax: suggestedMaxNet,
          grid: { color: 'rgba(0,0,0,0.06)' },
          ticks: { callback: (v) => `${v} Mbps` },
        },
      },
    };

    if (this.networkChart) this.networkChart.update();
  }

  // --- Logs ---
  loadLogs() {
    this.logsLoading = true;
    this.logsError = null;
    this.subs.add(
      this.logViewer.getLogs(this.logsLevelFilter || undefined, 200, this.logsSearchQuery || undefined).subscribe({
        next: (res) => { this.logs = res.logs; this.logsLoading = false; this.cdr.markForCheck(); },
        error: (err) => { this.logsLoading = false; this.logsError = err.error?.message || err.message || 'Error al cargar logs'; this.cdr.markForCheck(); },
      })
    );
  }

  setLogsLevel(level: string) {
    this.logsLevelFilter = level;
    this.loadLogs();
  }

  searchLogs() {
    this.loadLogs();
  }

  toggleLogExpand(index: number) {
    this.logsExpandedIndex = this.logsExpandedIndex === index ? null : index;
  }

  toggleLogsAutoRefresh() {
    this.logsAutoRefresh = !this.logsAutoRefresh;
    if (this.logsAutoRefresh) {
      this.logsRefreshSub = interval(5000).subscribe(() => this.loadLogs());
    } else {
      this.logsRefreshSub?.unsubscribe();
    }
  }

  logLevelColor(level: string): string {
    const map: Record<string, string> = {
      ERROR: 'var(--color-error)',
      WARNING: 'var(--color-warning)',
      INFO: 'var(--color-info)',
      DEBUG: 'var(--color-outline)',
      CRITICAL: 'var(--color-error)',
    };
    return map[level] || 'var(--color-on-surface-variant)';
  }

  // --- CSP ---
  loadCspReports() {
    this.cspLoading = true;
    this.cspError = null;
    this.subs.add(
      this.admin.getCSPReports({ ...this.cspFilter, page: this.cspPage, per_page: 25 }).subscribe({
        next: (res) => { this.cspReports = res.items; this.cspTotal = res.total; this.cspPage = res.page; this.cspPages = res.pages; this.cspLoading = false; this.cdr.markForCheck(); },
        error: (err) => { this.cspLoading = false; this.cspError = err.error?.message || err.message || 'Error al cargar CSP'; this.cdr.markForCheck(); },
      })
    );
  }

  onCspFilterChange() { this.cspPage = 1; this.loadCspReports(); }

  goToCspPage(p: number) { this.cspPage = p; this.loadCspReports(); }

  exportCspCsv() {
    this.subs.add(
      this.admin.exportCSPReportsCsv(this.cspFilter).subscribe({
        next: blob => { const url = window.URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = 'csp-reports.csv'; a.click(); window.URL.revokeObjectURL(url); this.cdr.markForCheck(); },
        error: (err) => { this.cspError = err.error?.message || err.message || 'Error al exportar'; this.cdr.markForCheck(); },
      })
    );
  }

  // --- Tokens ---
  loadTokens() {
    this.tokensLoading = true;
    this.tokensError = null;
    this.subs.add(
      this.admin.getAPITokens().subscribe({
        next: (res) => { this.tokens = res.tokens; this.tokensLoading = false; this.cdr.markForCheck(); },
        error: (err) => { this.tokensLoading = false; this.tokensError = err.error?.message || err.message || 'Error al cargar tokens'; this.cdr.markForCheck(); },
      })
    );
  }

  openCreateTokenModal() { this.showCreateModal = true; this.rotate = false; this.newToken = null; }

  closeCreateTokenModal() { this.showCreateModal = false; }

  createToken() {
    this.creating = true;
    this.subs.add(
      this.admin.createAPIToken(this.rotate).subscribe({
        next: (res) => { this.newToken = res.token; this.creating = false; this.loadTokens(); this.cdr.markForCheck(); },
        error: (err) => { this.creating = false; this.tokensError = err.error?.message || err.message || 'Error al crear token'; this.cdr.markForCheck(); },
      })
    );
  }

  async deactivateToken(id: number) {
    const confirmed = await firstValueFrom(this.confirmService.confirm({
      title: 'Desactivar Token',
      message: '¿Estás seguro de que deseas desactivar este token?',
      confirmText: 'Desactivar',
      cancelText: 'Cancelar',
      variant: 'danger',
    }));
    if (!confirmed) return;
    this.subs.add(
      this.admin.deactivateAPIToken(id).subscribe({
        next: () => { this.loadTokens(); this.cdr.markForCheck(); },
        error: (err) => { this.tokensError = err.error?.message || err.message || 'Error al desactivar'; this.cdr.markForCheck(); },
      })
    );
  }

  copyToken(token: string) {
    navigator.clipboard.writeText(token);
  }
}
